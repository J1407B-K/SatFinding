"""Generic outcome-blind collection and immutable package assembly."""
import sys,subprocess,shutil,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.features import features
from harness_v3.runner import verify
from prospective_temporal_schema import canonical_feature_schema,feature_schema_sha256

def collect(plan_path,output,build_path):
 plan_path=Path(plan_path);o=Path(output);plan=frozen(plan_path);build=frozen(Path(build_path));o.mkdir(parents=True,exist_ok=False)
 for name,h in build['components'].items():assert sha(ROOT/name)==h,('BUILD_CHANGED',name)
 packages=[]
 for item in plan['collections']:
  target=item['target'];assert target and all(c.isalnum() or c in '_-' for c in target)
  k=item['K'];count=item['requested_state_count'];rule=item['checkpoint_rule'];windows=rule['windows']
  assert rule['kind']=='first_eligible_per_window' and 1<=k<=6 and 1<=count<=len(windows)
  assert rule['minimum_legal_count']>=1
  assert all(0<=lo<=hi for lo,hi in windows) and all(a[1]<b[0] for a,b in zip(windows,windows[1:]))
  inp=ROOT/item['input'];assert sha(inp)==item['input_sha256']
  d=o/'collection'/target;d.mkdir(parents=True,exist_ok=False)
  compiled=[k,count,rule['minimum_legal_count'],len(windows)]+[v for w in windows for v in w]
  (d/'native_plan.txt').write_text(' '.join(map(str,compiled))+'\n');dump(d/'collection_plan.json',item)
  cmd=[str(HERE/'canonical_collector_native'),str(inp),str(d/'prefix.drup'),str(d),str(d/'native_plan.txt')]
  t=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True,timeout=240);(d/'stdout.txt').write_text(r.stdout);(d/'stderr.txt').write_text(r.stderr);dump(d/'command.json',{'argv':cmd,'seconds':time.monotonic()-t,'returncode':r.returncode});r.check_returncode()
  status=load(d/'stdout.txt');assert status['status']=='COLLECTION_COMPLETE'
  exports=sorted((p for p in d.iterdir() if p.is_dir()),key=lambda p:int(p.name[1:]));assert len(exports)==status['collected']
  # Shortfalls are preserved, never filled by outcome-dependent replacement.
  for export in exports:
   st=load(export/'checkpoint.json');p=o/'packages'/(target+'_'+export.name+'_B'+str(st['boundary']));p.mkdir(parents=True,exist_ok=False)
   st.update(target=target,state_id=p.name,checkpoint_kind='observer_boundary',identity_version=2)
   prefix=load(export/'prefix_counters.json');counterline=(export/'logical.txt').read_text().splitlines()[1].split()
   st.update(propagations=int(counterline[3]),enqueues=int(counterline[4]),prefix_analysis_ops=prefix['analysis_resolution_steps'])
   dump(p/'state.json',st)
   for n in ['logical.txt','heuristic.txt','actions.json','temporal_raw.json','prefix_counters.json']:shutil.copyfile(export/n,p/n)
   t=time.monotonic();f,comparisons=features(load(p/'temporal_raw.json'))
   dump(p/'temporal_features.json',dict(protocol_version='1.1',protocol_sha256=sha(PROTOCOL),feature_schema_sha256=feature_schema_sha256(),raw_temporal_sha256=sha(p/'temporal_raw.json'),availability={'short_8':True,'mid_32':True,'long_128':True},features=f))
   dump(export/'feature_compute.json',{'seconds':time.monotonic()-t,'reference_comparisons':comparisons})
   shutil.copyfile(inp,p/'input.cnf');shutil.copyfile(PROTOCOL,p/'protocol.json');dump(p/'collection_plan.json',item)
   (p/'feature_schema.json').write_text(__import__('json').dumps(canonical_feature_schema(),sort_keys=True,separators=(',',':')))
   dump(p/'package_manifest.json',{'identity_version':2,'package_id':p.name,'frozen_at':stamp(),'outcome_blind':True,'actions_frozen_before_ground_truth':True,'temporal_features_collected_before_ground_truth':True,'collection_plan_sha256':sha(plan_path),'build_sha256':sha(build_path),'runner_sha256':sha(HERE/'runner.py'),'replay_binary_sha256':sha(HERE/'frozen_replay_native'),'files':{x.name:sha(x) for x in sorted(p.iterdir())}})
   (p/'package_manifest.sha256').write_text(sha(p/'package_manifest.json')+'\n');verify(p)
   packages.append({'path':str(p.relative_to(o)),'package_manifest_sha256':sha(p/'package_manifest.json'),'target':target,'state_id':p.name})
  assert len(exports)==count,('COLLECTION_SHORTFALL',target,count,len(exports))
 freeze(o/'cohort_manifest.json',{'frozen_at':stamp(),'plan_path':str(plan_path.resolve()),'plan_sha256':sha(plan_path),'build_path':str(Path(build_path).resolve()),'build_sha256':sha(build_path),'packages':packages,'selection_completed_before_any_ground_truth':True,'features_frozen_before_any_ground_truth':True,'actions_frozen_before_any_ground_truth':True,'ground_truth_routes_started':0})
 return o
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--output',required=True);ap.add_argument('--build',required=True);a=ap.parse_args();collect(a.plan,a.output,a.build)
