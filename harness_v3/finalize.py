"""Generic labels from audited frozen packages and route counters. No selection."""
import sys,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.audit import post_audit

def csvwrite(p,rows):
 assert rows
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def finalize(o,output):
 o=Path(o);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 audit,rows=post_audit(o);assert audit['ROUTE_INTEGRITY_PASSED'];co=frozen(o/'cohort_manifest.json');by_id={r['route_id']:r for r in rows};labels=[];states=[]
 for e in co['packages']:
  p=o/e['path'];st=load(p/'state.json');acts=load(p/'actions.json');baseline=by_id[route_id(p,None)];prefix=load(p/'prefix_counters.json')['analysis_resolution_steps']
  b=baseline['native_result']['analysis_resolution_steps']-prefix;assert b>0,'ZERO_BASELINE_REMAINING_OPS'
  high=0
  for a in acts['selected']:
   r=by_id[route_id(p,a)];remaining=r['native_result']['analysis_resolution_steps']-prefix;assert remaining>=0
   delta=100*(remaining/b-1);is_high=abs(delta)>=10;high+=is_high
   labels.append({'target':st['target'],'state_id':p.name,'action_rank':a['rank'],'action_id':a['id'],'literal':a['literal'],'clause':__import__('json').dumps(a['clause']),'prefix_analysis_ops':prefix,'baseline_final_analysis_ops':baseline['native_result']['analysis_resolution_steps'],'action_final_analysis_ops':r['native_result']['analysis_resolution_steps'],'baseline_remaining_ops':b,'action_remaining_ops':remaining,'final_ops_delta_percent':delta,'HIGH_LEVERAGE':is_high,'direction':'speedup' if delta<0 else 'slowdown' if delta>0 else 'zero','conflicts':r['native_result']['conflicts'],'decisions':r['native_result']['decisions'],'propagations':r['native_result']['propagations'],'enqueues':r['native_result']['enqueues'],'proof_sha256':r['proof_sha256'],'proof_validation':r['proof']})
  states.append({'target':st['target'],'state_id':p.name,'selected_count':acts['selected_count'],'HIGH_count':high,'label':'SENSITIVE' if high else 'INERT','scope':'within frozen tested-action budget'})
 csvwrite(out/'state_action_ground_truth.csv',labels);csvwrite(out/'state_labels.csv',states)
 dump(out/'finalizer_audit.json',{'passed':True,'action_rows':len(labels),'state_rows':len(states),'all_deltas_computed':True,'route_integrity':True,'formula':'100 * ((action_final_analysis_ops - prefix_analysis_ops) / (baseline_final_analysis_ops - prefix_analysis_ops) - 1)','high_threshold':10,'inputs_sha256':sha(o/'cohort_manifest.json')})
 return len(labels),len(states)
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--cohort',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();finalize(a.cohort,a.output)
