import json,hashlib,collections,math
from pathlib import Path
import analyze_trajectory_audit as a
R=a.R;F=a.F

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 rows=json.loads((R/'ROUTE_COMPARISONS.json').read_text());assert len(rows)==136
 assert {(r['case'],r['rank']) for r in rows}=={(c['case'],c['rank']) for c in a.P['cohort']}
 assert sha(R/'TRAJECTORY_DIVERGENCE_PROTOCOL_V1.json')==(R/'TRAJECTORY_DIVERGENCE_PROTOCOL_V1.sha256').read_text().split()[0]
 old={(r['case'],r['rank']):r for r in json.loads((F/'candidate_action_results.json').read_text()) if r['proof']}
 checks=[];manifest={}
 for r in rows:
  case=F/'cases'/r['case'];d=Path(r['evidence']);req=(d/'action/request.txt').read_text().split()
  assert int(req[8])==r['action_id'] and int(req[9])==r['action_literal'] and sorted(map(int,req[12:]))==sorted(r['action_clause'])
  vline=next(l for l in (d/'baseline/logical.txt').read_text().splitlines() if l.startswith(f'var {abs(r["action_literal"])} '))
  assert vline.split()[2]=='2',vline
  assert r['action_final_ops']==old[r['case'],r['rank']]['ops']
  frozen_lines=[json.loads(l) for l in (case/'baseline/stdout.txt').read_text().splitlines() if l.startswith('{')]
  assert r['baseline_final_ops']==frozen_lines[-1]['final_counters']['analysis_resolution_steps']
  assert r['exact_pre_state_identity'] and r['action_verified'] and r['proof_verified']
  for mode in ['baseline','action']:
   p=d/mode;x=json.loads((p/'execution.json').read_text());assert x['status']=='UNSAT' and x['proof_verified'] and x['checker_returncode']==0
   assert 's VERIFIED' in (p/'proof_check.txt').read_text()
   for name,h in x['artifacts'].items():
    f=p/name;assert sha(f)==h,str(f);manifest[str(f)]={'sha256':h,'bytes':f.stat().st_size}
  checks.append({'case':r['case'],'rank':r['rank'],'checkpoint_identity':'PASS','literal_unassigned':'PASS','literal_clause_request_identity':'PASS','action_verified':True,'frozen_action_ops_reproduced':True,'frozen_baseline_ops_reproduced':True,'baseline_proof':'VERIFIED','action_proof':'VERIFIED','file_hashes':'PASS'})
  print('INTEGRITY',len(checks),r['case'],r['rank'],flush=True)
 for c in a.P['cohort']:
  for p,h in c['artifacts'].items():assert sha(p)==h;manifest[p]={'sha256':h,'bytes':Path(p).stat().st_size}
 s=a.summary(rows)
 s['strongest_speedup']=min((r['delta_percent'] for r in rows if r['delta_percent']<0),default=None)
 s['strongest_slowdown']=max((r['delta_percent'] for r in rows if r['delta_percent']>0),default=None)
 s['content_divergence_counts']={k:sum(r['first_'+k+'_divergence'] is not None for r in rows) for k in ['conflict','learned','decision','restart','backtrack']}
 s['residual_class_count']=sum(r['residual_trajectory_difference'] for r in rows)
 s['milestone_mismatch_counts']={str(k):{f:sum(next(m for m in r['milestones'] if m['k']==k)['equal_fields'][f] is False for r in rows if next(m for m in r['milestones'] if m['k']==k)['equal_fields'] is not None) for f in ['logical','learned','frontier','next_decision']} for k in [1,2,4,8,16]}
 s['same_first_counts']={f:sum(r[f] is True for r in rows) for f in ['same_first_conflict','same_first_learned_clause','same_next_decision']}
 s['next_step']='CHANGE_OPPORTUNITY_GENERATION' if s['naturally_enqueued']>68 and (s['propagation_timing_class'].get('EARLY_SAME_PROPAGATION',0)>68) else 'EXPAND_OUTCOME_BLIND_CANDIDATE_SOURCE'
 (R/'AUDIT_SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n')
 (R/'FINAL_INTEGRITY_CHECKS.json').write_text(json.dumps({'PASS':True,'routes':checks},indent=2)+'\n')
 (R/'PROOF_ROUTE_MAPPING.json').write_text(json.dumps([{'case':r['case'],'rank':r['rank'],'baseline':str(Path(r['evidence'])/'baseline/proof_check.txt'),'action':str(Path(r['evidence'])/'action/proof_check.txt'),'baseline_status':'VERIFIED','action_status':'VERIFIED'} for r in rows],indent=2)+'\n')
 from report_trajectory_audit import report
 report(s)
 for root in [R,Path('execution_pipeline_v1/trajectory_native_v1')]:
  for f in root.rglob('*'):
   if f.is_file() and f.name not in ['EVIDENCE_MANIFEST.json','EVIDENCE_MANIFEST.sha256','finalize.log','batch.log','analysis.log'] and str(f) not in manifest:manifest[str(f)]={'sha256':sha(f),'bytes':f.stat().st_size}
 for f in Path('execution_pipeline_v1').glob('*trajectory*'):
  if f.is_file():manifest[str(f)]={'sha256':sha(f),'bytes':f.stat().st_size}
 out=R/'EVIDENCE_MANIFEST.json';out.write_text(json.dumps({'protocol_sha256':sha(R/'TRAJECTORY_DIVERGENCE_PROTOCOL_V1.json'),'files':manifest},indent=2)+'\n');(R/'EVIDENCE_MANIFEST.sha256').write_text(sha(out)+'  '+out.name+'\n')
 print('FINAL INTEGRITY PASS',flush=True)
if __name__=='__main__':main()
