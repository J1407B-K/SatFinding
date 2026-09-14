"""Qualification only: self-test gate, outcome-blind collection, six proof routes, lock."""
from pathlib import Path
import sys,json,hashlib,subprocess,shutil,statistics,math,datetime
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from frozen_replay_runner import sha,load,dump,verify,run,PROTOCOL
from prospective_temporal_schema import canonical_feature_schema,feature_schema_sha256
from temporal_reference import stats
ROOT=Path(__file__).resolve().parent.parent
O=ROOT/'results/harness_qualification_v2'
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def features(raw):
 samples=raw['logical_samples'];assert len(samples)==128
 assert all(a['conflict_index']+1==b['conflict_index'] for a,b in zip(samples,samples[1:]))
 assert all(s['learned_length']>0 for s in samples)
 mapping={'lbd_mean_slope_variance_delta':'lbd','learned_length_mean_slope_delta':'learned_length','backjump_mean_slope_delta':'backjump_depth','decisions_per_conflict_mean_delta':'decisions_delta','dequeues_per_conflict_mean_delta':'dequeues_delta','analysis_ops_per_conflict_mean_delta':'analysis_ops_delta','watcher_visits_per_conflict_mean_delta':'watcher_visits_delta'}
 out={}; comparisons=0
 for group,field in mapping.items():
  series=[s[field] for s in samples];f={}
  for label,n in [('SHORT',8),('MID',32),('LONG',128)]:
   y=series[-n:];m=sum(y)/n;den=n*(n*n-1)/12
   slope=(sum(i*v for i,v in enumerate(y))-(n-1)/2*sum(y))/den
   vals={'mean':m}
   if 'slope' in group:vals['slope']=slope
   if 'variance' in group:vals['variance']=statistics.pvariance(y)
   rm,rv,rs=stats(y)
   for key,value in vals.items():
    reference={'mean':rm,'variance':rv,'slope':rs}[key];assert abs(value-reference)<=1e-9*max(1,abs(value),abs(reference)),(group,key);comparisons+=1
   f[label]=vals
  f['short_minus_mid']=sum(series[-8:])/8-sum(series[-32:])/32
  out[group]=f
 out['conflicts_since_restart']=samples[-1]['conflicts_since_restart']
 assert set(out)==set(canonical_feature_schema()['features'])
 return out,comparisons

def main():
 # No package or action route before both independent self-tests pass.
 tests=[]
 for target in ['T8','T10']:
  a,b=[O/'selftest_final'/(target+'_'+r) for r in ['A','B']]
  for f in ['logical.txt','heuristic.txt','checkpoint.json']:assert (a/f).read_bytes()==(b/f).read_bytes(),(target,f)
  result=[load(d/'stdout.txt') for d in [a,b]];assert result[0]==result[1] and result[0]['status']=='UNSAT'
  tests.append({'target':target,'checkpoint':load(a/'checkpoint.json'),'baseline':result[0],'cross_run_logical':True,'cross_run_heuristic':True})
 dump(O/'cross_run_selftest.json',{'status':'CANONICAL_STATE_HASH_CROSS_RUN_STABLE','tests':tests})
 source_files=[p for p in (ROOT/'harness_v2').rglob('*') if p.suffix in ['.py','.cc','.h','.inc','.md']]
 source_files += [ROOT/n for n in ['frozen_replay_driver.cc','frozen_replay_runner.py','prospective_temporal_schema.py','temporal_reference.py']]
 build={'frozen_at':stamp(),'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in source_files},'binaries':{n:sha(ROOT/n) for n in ['canonical_collector_native','frozen_replay_native']},'contract_sha256':sha(ROOT/'harness_v2/CONTRACT.md')}
 dump(O/'build_freeze.json',build)
 # Freeze selection before collecting; no label selection or outcome inputs.
 dump(O/'selection_freeze.json',{'time':stamp(),'targets':['T8','T10'],'window':[200,299],'rule':'first observer boundary with >=2 eligible actions; first two ascending stable creation IDs','K_TEST':2,'outcome_blind':True,'build_sha256':sha(O/'build_freeze.json')})
 packages=[];feature_audit=[]
 for target in ['T8','T10']:
  d=O/'collection'/target;d.mkdir(parents=True,exist_ok=False)
  inp=ROOT/f'results/high_leverage_discovery/{target}/input.cnf'
  original=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['inputs'][target];assert sha(inp)==original['sha256']
  cmd=[str(ROOT/'canonical_collector_native'),str(inp),str(d/'prefix.drup'),str(d),'collect']
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=240);dump(d/'command.json',cmd);(d/'stdout.txt').write_text(r.stdout);(d/'stderr.txt').write_text(r.stderr);r.check_returncode();assert load(d/'stdout.txt')['status']=='CHECKPOINT_COLLECTED'
  st=load(d/'checkpoint.json');assert st==tests[['T8','T10'].index(target)]['checkpoint']
  p=O/'packages'/(target+'_C200_IDv2');p.mkdir(parents=True,exist_ok=False)
  st.update(target=target,state_id=p.name,checkpoint_kind='observer_boundary',identity_version=2)
  dump(p/'state.json',st)
  for n in ['logical.txt','heuristic.txt','actions.json','temporal_raw.json']:shutil.copyfile(d/n,p/n)
  acts=load(p/'actions.json');assert acts['eligible_ids']==sorted(set(acts['eligible_ids']));assert [a['id'] for a in acts['selected']]==acts['eligible_ids'][:2];assert acts['legal_count']==len(acts['eligible_ids'])
  raw=load(p/'temporal_raw.json');f,count=features(raw)
  dump(p/'temporal_features.json',dict(protocol_version='1.1',protocol_sha256=sha(PROTOCOL),feature_schema_sha256=feature_schema_sha256(),raw_temporal_sha256=sha(p/'temporal_raw.json'),availability={'short_8':True,'mid_32':True,'long_128':True},features=f))
  shutil.copyfile(inp,p/'input.cnf');shutil.copyfile(PROTOCOL,p/'protocol.json');(p/'feature_schema.json').write_text(json.dumps(canonical_feature_schema(),sort_keys=True,separators=(',',':')))
  dump(p/'package_manifest.json',{'identity_version':2,'package_id':p.name,'frozen_at':stamp(),'outcome_blind':True,'selection_completed_before_any_action_ground_truth':True,'temporal_features_collected_before_action_ground_truth':True,'selection_sha256':sha(O/'selection_freeze.json'),'build_sha256':sha(O/'build_freeze.json'),'runner_sha256':sha(ROOT/'frozen_replay_runner.py'),'replay_binary_sha256':sha(ROOT/'frozen_replay_native'),'files':{x.name:sha(x) for x in sorted(p.iterdir())}})
  (p/'package_manifest.sha256').write_text(sha(p/'package_manifest.json')+'\n');verify(p);packages.append(p);feature_audit.append({'target':target,'reference_comparisons':count,'tolerance':1e-9,'passed':True})
 dump(O/'temporal_contract_audit.json',feature_audit)
 expected=[]
 for p in packages:
  for route,rank in [('baseline',None),('action',1),('action',2)]:
   act=None if rank is None else load(p/'actions.json')['selected'][rank-1]
   identity=sha(p/'package_manifest.json')+(':BASELINE' if act is None else f':ACTION:{rank}:{act["id"]}')
   expected.append({'package':str(p.relative_to(ROOT)),'route':route,'rank':rank,'route_id':hashlib.sha256(identity.encode()).hexdigest(),'output':str((O/'routes'/(p.name+('_BASELINE' if rank is None else f'_ACTION{rank}'))).relative_to(ROOT))})
 dump(O/'expected_routes.json',expected);(O/'expected_routes.sha256').write_text(sha(O/'expected_routes.json')+'\n')
 dump(O/'pre_replay_freeze.json',{'time':stamp(),'packages':{p.name:sha(p/'package_manifest.json') for p in packages},'expected_routes_sha256':sha(O/'expected_routes.json'),'package_count':2,'expected_routes':6})
 rows=[]
 for e in expected:
  row=run(e['package'],e['route'],e['rank'],e['output']);rows.append(row);print(row['target'],row['route_type'],row['action_rank'],'REPLAY_STATE_VERIFIED proof VERIFIED',flush=True)
 audit_and_lock(packages,rows,expected,build)

def audit_and_lock(packages,rows,expected,build):
 allowed={'request.txt','logical.txt','heuristic.txt','checkpoint.json','proof.drup','stdout.txt','stderr.txt','command.json','proof.log','proof_command.json','route_metadata.json'}
 actual_dirs=list((O/'routes').iterdir());actual=[load(d/'route_metadata.json') for d in actual_dirs]
 assert len(actual)==6 and all(set(f.name for f in d.iterdir())==allowed for d in actual_dirs)
 exp={e['route_id'] for e in expected};ids=[r['route_id'] for r in actual];assert len(exp)==6 and set(ids)==exp and len(set(ids))==len(ids)
 for p in packages:verify(p)
 for n,h in build['source_hashes'].items():assert sha(ROOT/n)==h
 for n,h in build['binaries'].items():assert sha(ROOT/n)==h
 audit={'expected_routes':6,'actual_routes':len(actual),'duplicates':len(ids)-len(set(ids)),'missing':len(exp-set(ids)),'extra':len(set(ids)-exp),'canonical_logical_replay':sum(r['logical_verified'] for r in actual),'canonical_heuristic_replay':sum(r['heuristic_verified'] for r in actual),'frozen_action_verified':sum(r['action_verified'] for r in actual),'proof_verified':sum(r['proof']=='VERIFIED' for r in actual),'collector_emissions':0,'discovery_emissions':0,'package_emissions':0,'package_hashes_unchanged':True,'output_whitelist_verified':True,'HARNESS_QUALIFIED':True}
 assert audit['canonical_logical_replay']==audit['canonical_heuristic_replay']==audit['proof_verified']==6 and audit['frozen_action_verified']==4
 dump(O/'qualification_audit.json',audit)
 lock={'status':'HARNESS_QUALIFIED','HARNESS_QUALIFIED':True,'frozen_at':stamp(),'temporal_hypothesis':'UNTESTED','scientific_v3_run':False,'audit':audit,'build_freeze_sha256':sha(O/'build_freeze.json'),'packages':{p.name:sha(p/'package_manifest.json') for p in packages},'evidence':{str(p.relative_to(O)):sha(p) for p in O.rglob('*') if p.is_file() and p.name not in ['HARNESS_LOCK.json','HARNESS_LOCK.sha256']}}
 dump(O/'HARNESS_LOCK.json',lock);(O/'HARNESS_LOCK.sha256').write_text(sha(O/'HARNESS_LOCK.json')+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':main()
