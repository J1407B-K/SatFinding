from pathlib import Path
import sys,shutil,csv,json,collections
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.collect import collect
from harness_v3.routes import freeze_routes,execute,input_hashes
from harness_v3.audit import pre_audit,post_audit
from harness_v3.finalize import finalize
O=ROOT/'results/prospective_temporal_state_cohort_v3'
def flatten(x,prefix=''):
 out={}
 for k,v in x.items():
  name=prefix+'.'+k if prefix else k
  if isinstance(v,dict):out.update(flatten(v,name))
  else:out[name]=v
 return out

def csvwrite(p,rows):
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
 stage=ROOT/'results/prospective_temporal_state_cohort_v3_collection_stage'
 collect(O/'collection_plan.json',stage,O/'build_manifest.json')
 for p in stage.iterdir():p.rename(O/p.name)
 stage.rmdir()
 cohort=frozen(O/'cohort_manifest.json');states=[];temporal=[];static=[]
 for e in cohort['packages']:
  p=O/e['path'];st=load(p/'state.json');acts=load(p/'actions.json');f=load(p/'temporal_features.json');prefix=load(p/'prefix_counters.json')
  states.append(dict(st,selected_count=acts['selected_count'],legal_count=acts['legal_count'],package=e['path'],package_manifest_sha256=e['package_manifest_sha256']))
  temporal.append(dict(state_id=st['state_id'],target=st['target'],**flatten(f['features'])))
  static.append(dict(state_id=st['state_id'],target=st['target'],conflicts=st['conflicts'],decisions=st['decisions'],level=st['level'],trail_length=st['trail_length'],qhead=st['qhead'],pending_count=st['trail_length']-st['qhead'],legal_count=acts['legal_count'],selected_count=acts['selected_count'],enumeration_literal_visits='UNAVAILABLE',prefix_analysis=prefix['analysis_resolution_steps'],prefix_redundancy=prefix['redundancy'],prefix_binary=prefix['binary'],prefix_watchers=prefix['watchers'],prefix_dequeues=prefix['dequeues'],analysis_per_conflict=prefix['analysis_resolution_steps']/st['conflicts'],watchers_per_conflict=prefix['watchers']/st['conflicts'],dequeues_per_conflict=prefix['dequeues']/st['conflicts']))
 assert len(states)==18 and collections.Counter(s['target'] for s in states)=={'T8':6,'T10':6,'T13':6}
 # Compare prior state identities only, never historical features/labels/effects.
 known=set()
 def visit(v,target=None):
  if isinstance(v,dict):
   target=v.get('target',target)
   cf=v.get('conflicts',v.get('conflict_index'));dl=v.get('level',v.get('decision_level'))
   if target in ['T8','T10','T13'] and all(x is not None for x in [cf,dl,v.get('decisions'),v.get('trail_length'),v.get('qhead')]):known.add((target,int(cf),int(v['decisions']),int(dl),int(v['trail_length']),int(v['qhead'])))
   for x in v.values():visit(x,target)
  elif isinstance(v,list):
   for x in v:visit(x,target)
 paths=list((ROOT/'results').rglob('selected_states.json'))+list((ROOT/'results').rglob('state.json'))+list((ROOT/'results').rglob('frozen_state.json'))
 for p in paths:
  if O in p.parents:continue
  try:visit(load(p))
  except (ValueError,TypeError):pass
 for st in states:assert (st['target'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead']) not in known,'PREVIOUS_STATE_IDENTITY'
 dump(O/'novelty_audit.json',{'passed':True,'prior_identity_tuples_checked':len(known),'only_identity_fields_read':True})
 dump(O/'selected_states.json',{'states':states,'selection_completed_before_ground_truth':True})
 csvwrite(O/'temporal_state_features.csv',temporal);csvwrite(O/'static_state_features.csv',static)
 (O/'states').mkdir()
 for st in states:(O/'states'/(st['state_id']+'.json')).symlink_to('../'+st['package']+'/state.json')
 expected=freeze_routes(O)
 # Requested short SHA file names alias exactly the generic harness sidecars.
 for n in ['cohort_manifest','expected_routes']:(O/(n+'.sha256')).symlink_to(n+'.json.sha256')
 pre=pre_audit(O)
 dump(O/'pre_ground_truth_audit.json',pre) if False else None
 # Bind all peripheral pre-GT science tables as well as the locked package inputs.
 freeze(O/'science_input_manifest.json',{'files':{n:sha(O/n) for n in ['HARNESS_LOCK_VERIFICATION.json','analysis_specification.json','collection_plan.json','selected_states.json','temporal_state_features.csv','static_state_features.csv','novelty_audit.json']},'cohort_manifest_sha256':sha(O/'cohort_manifest.json'),'expected_routes_sha256':sha(O/'expected_routes.json'),'ground_truth_routes_started':0})
 for n in frozen(O/'science_input_manifest.json')['files']:(O/n).chmod(0o444)
 print(json.dumps({'pre_audit':'PASSED','states':len(states),'actions':sum(s['selected_count'] for s in states),'expected_routes':len(expected)}),flush=True)
 execute(O)
 audit,rows=post_audit(O);freeze(O/'route_identity_audit.json',audit)
 dump(O/'proof_audit.json',{'proof_verified':audit['proof_verified'],'expected_routes':len(expected),'routes':[{'route_id':r['route_id'],'proof_sha256':r['proof_sha256'],'proof_validation':r['proof']} for r in rows]})
 finalize(O,O/'labels')
 # Keep the generic finalizer output unchanged; add counter deltas in a reporting table.
 gt=list(csv.DictReader((O/'labels/state_action_ground_truth.csv').open()));byid={r['route_id']:r for r in rows}
 bystate={s['state_id']:s for s in states}
 for r in gt:
  st=bystate[r['state_id']];p=O/st['package'];base=byid[route_id(p,None)];a=load(p/'actions.json')['selected'][int(r['action_rank'])-1];action=byid[route_id(p,a)]
  r['clause_id']=a['id']
  for key in ['conflicts','decisions','propagations','enqueues']:r[key+'_delta']=action['native_result'][key]-base['native_result'][key]
 csvwrite(O/'state_action_ground_truth.csv',gt);shutil.copyfile(O/'labels/state_labels.csv',O/'state_labels.csv')
 for n,h in frozen(O/'science_input_manifest.json')['files'].items():assert sha(O/n)==h
 print('ROUTE_INTEGRITY_PASSED; GENERIC LABELS GENERATED',flush=True)
if __name__=='__main__':main()
