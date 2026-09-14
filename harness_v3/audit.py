"""Generic pre-ground-truth and post-route audits, independent of cohort size."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.runner import verify
from harness_v3.features import features
from harness_v3.routes import derive,input_hashes
ALLOWED={'request.txt','logical.txt','heuristic.txt','checkpoint.json','prefix_counters.json','proof.drup','stdout.txt','stderr.txt','command.json','proof.log','proof_command.json','route_metadata.json'}

def compare(a,b):
 if isinstance(a,dict):assert isinstance(b,dict) and a.keys()==b.keys();[compare(a[k],b[k]) for k in a]
 elif isinstance(a,(float,int)) and not isinstance(a,bool):assert math.isfinite(b) and abs(a-b)<=1e-9*max(1,abs(a),abs(b)),(a,b)
 else:assert a==b,(a,b)

def audit_package(p):
 m,st,acts=verify(p);logical=(p/'logical.txt').read_text().splitlines();cs=logical[1].split();assert cs[0]=='counters'
 vals=list(map(int,cs[1:]));assert vals==[st['conflicts'],st['decisions'],st['propagations'],st['enqueues'],st['level'],st['trail_length'],st['qhead']]
 prefix=load(p/'prefix_counters.json');assert prefix['enqueues']==st['enqueues'] and prefix['analysis_resolution_steps']==st['prefix_analysis_ops']
 # Independently enumerate semantic snapshot clauses for the pre-GT first-K audit only.
 assignments={int(l.split()[1]):int(l.split()[2]) for l in logical if l.startswith('var ')}
 eligible=[];clause_by_id={}
 for line in (p/'heuristic.txt').read_text().splitlines():
  if not line.startswith('clause '):continue
  fields=line.split();cid,learned,mark=map(int,fields[1:4]);lits=list(map(int,fields[4:-3] if learned else fields[4:]))
  if mark:continue
  und=[v for v in lits if assignments[abs(v)]==2]
  true=any(assignments[abs(v)]==(0 if v>0 else 1) for v in lits)
  if not true and len(und)==1 and (len(lits)==2 or len(lits)>2 and lits[0]==und[0]):
   eligible.append(cid);clause_by_id[cid]=(lits,und[0],'learned' if learned else 'original')
 assert sorted(eligible)==acts['eligible_ids'],'COMPLETE_ELIGIBLE_SET'
 for a in acts['selected']:
  lits,implied,source=clause_by_id[a['id']];assert a['clause']==lits and a['literal']==implied and a['source']==source
  assert a['true_count']==0 and a['unassigned_count']==1 and a['unit_layout_verified'] is True
 raw=load(p/'temporal_raw.json');computed,n=features(raw);f=load(p/'temporal_features.json');compare(computed,f['features'])
 assert all(s['conflict_index']<=st['conflicts'] for s in raw['logical_samples'])
 assert f['availability']=={'short_8':True,'mid_32':True,'long_128':True}
 return {'state_id':st['state_id'],'target':st['target'],'selected_count':acts['selected_count'],'legal_count':acts['legal_count'],'reference_comparisons':n,'exact_first_K':True,'canonical_identity_present':True}

def verify_build(o):
 co=frozen(Path(o)/'cohort_manifest.json');assert sha(co['build_path'])==co['build_sha256'];b=frozen(Path(co['build_path']))
 for name,h in b['components'].items():assert sha(ROOT/name)==h,('HARNESS_CHANGED',name)
 assert sha(co['plan_path'])==co['plan_sha256'];frozen(Path(co['plan_path']));return co

def pre_audit(o):
 o=Path(o);co=verify_build(o);assert not (o/'route_results').exists(),'GROUND_TRUTH_EXISTS'
 assert co['ground_truth_routes_started']==0 and all(co[k] for k in ['selection_completed_before_any_ground_truth','features_frozen_before_any_ground_truth','actions_frozen_before_any_ground_truth'])
 expected=frozen(o/'expected_routes.json');assert expected==derive(o)
 states=[audit_package(o/e['path']) for e in co['packages']]
 identities=[(load(o/e['path']/'state.json')['target'],load(o/e['path']/'state.json')['canonical_logical_state_hash'],load(o/e['path']/'state.json')['canonical_heuristic_state_hash']) for e in co['packages']]
 assert len(set(identities))==len(identities),'DUPLICATE_STATES'
 result={'PRE_GROUND_TRUTH_AUDIT':'PASSED','time':stamp(),'expected_routes':len(expected),'ground_truth_routes_started':0,'states':states,'input_hashes':input_hashes(o)}
 freeze(o/'pre_ground_truth_audit.json',result)
 # Scientific inputs cannot be rewritten by the replay phase.
 for name in result['input_hashes']:(o/name).chmod(0o444)
 return result

def post_audit(o):
 o=Path(o);co=verify_build(o);pre=frozen(o/'pre_ground_truth_audit.json');assert pre['input_hashes']==input_hashes(o)
 expected=frozen(o/'expected_routes.json');assert expected==derive(o);expected_ids={r['route_id'] for r in expected}
 dirs=list((o/'route_results').iterdir());rows=[]
 assert {d.name for d in dirs}==expected_ids,'ROUTE_DIRECTORY_SET'
 for e in expected:
  d=o/e['output'];assert set(f.name for f in d.iterdir())==ALLOWED,'ROUTE_EMISSIONS'
  r=load(d/'route_metadata.json');p=o/e['package'];_,st,acts=verify(p)
  assert r['route_id']==e['route_id'] and r['package_id']==p.name and r['action_rank']==e['rank']
  assert r['route_type']==e['route'].upper() and r['package_manifest_sha256']==sha(p/'package_manifest.json')
  checkpoint=load(d/'checkpoint.json');assert all(checkpoint[k]==st[k] for k in checkpoint)
  assert sha(d/'logical.txt')==st['canonical_logical_state_hash'] and sha(d/'heuristic.txt')==st['canonical_heuristic_state_hash']
  assert r['logical_verified'] and r['heuristic_verified'] and r['action_verified']==(e['rank'] is not None)
  assert load(d/'prefix_counters.json')==load(p/'prefix_counters.json')==r['prefix_counters']
  assert r['proof']=='VERIFIED' and r['checker_returncode']==0 and 's VERIFIED' in (d/'proof.log').read_text()
  assert sha(d/'proof.drup')==r['proof_sha256'] and Path(r['proof_path'])==d.resolve()/'proof.drup'
  lines=(d/'stdout.txt').read_text().splitlines();native=load(d/'route_metadata.json')['native_result'];base=__import__('json').loads(lines[-2]);cnt=__import__('json').loads(lines[-1])['final_counters'];assert dict(base,**cnt)==native
  for key in ['analysis_resolution_steps','conflicts','decisions','propagations','enqueues','dequeues','watchers','redundancy','binary']:assert isinstance(native[key],int) and native[key]>=0
  assert native['status']=='UNSAT' and native['analysis_resolution_steps']>=r['prefix_counters']['analysis_resolution_steps']
  command=load(d/'command.json');assert command[0]==str(HERE/'frozen_replay_native') and command[1]==str((p/'input.cnf').resolve())
  # Check request identity, including exact frozen action; no fallback can hide behind metadata.
  action=None if e['rank'] is None else acts['selected'][e['rank']-1]
  request=[st['boundary'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead'],st['canonical_logical_state_hash'],st['canonical_heuristic_state_hash']]
  request+= [0,0,0,0] if action is None else [action['id'],action['literal'],int(action['source']=='learned'),len(action['clause'])]+action['clause']
  assert (d/'request.txt').read_text().split()==list(map(str,request))
  rows.append(r)
 ids=[r['route_id'] for r in rows];assert set(ids)==expected_ids and len(ids)==len(set(ids))
 actions=sum(e['rank'] is not None for e in expected)
 result={'ROUTE_INTEGRITY_PASSED':True,'expected_routes':len(expected),'actual_routes':len(rows),'duplicates':0,'missing':0,'extra':0,'canonical_logical_replay':len(rows),'canonical_heuristic_replay':len(rows),'frozen_action_success':actions,'action_routes':actions,'proof_verified':len(rows),'final_analysis_ops_present':len(rows),'collector_emissions':0,'discovery_emissions':0,'package_emissions':0,'package_hashes_unchanged':True,'route_evidence_hashes':tree_hashes(o/'route_results')}
 return result,rows
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--cohort',required=True);ap.add_argument('phase',choices=['pre','post']);a=ap.parse_args()
 if a.phase=='pre':pre_audit(a.cohort)
 else:freeze(Path(a.cohort)/'route_identity_audit.json',post_audit(a.cohort)[0])
