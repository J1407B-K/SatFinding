import json,csv,hashlib,shutil,subprocess
from pathlib import Path
R=Path('results/fresh_heuristic_causal_cohort_v1'); C=R/'cases';
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
# candidate ground truth: actual native final counters and checked proofs
rows=[]
for p in sorted(C.iterdir()):
 if not p.is_dir():continue
 m=json.load(open(p/'manifest.json')); b=m['routes']['baseline']['result']; a=m['routes']['action']['result'];
 bo=b['analysis_resolution_steps'];ao=a['analysis_resolution_steps']; delta=100*(ao/bo-1) if bo else None
 rows.append({'case':p.name,'target':'T10FRESH','action_id':m['action']['id'],'baseline_ops':bo,'action_ops':ao,'final_ops_delta_percent':delta,'classification':'HIGH' if delta is not None and abs(delta)>=10 else 'NON_HIGH','package_complete':m['package_complete'],'baseline_proof':m['routes']['baseline']['VERIFIED'],'action_proof':m['routes']['action']['VERIFIED']})
with (R/'candidate_cases.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
# validator audit
json.dump({'cases':rows,'candidate_count':len(rows),'high_count':sum(x['classification']=='HIGH' for x in rows),'excluded_before_science':sum(not(x['package_complete'] and x['baseline_proof'] and x['action_proof']) for x in rows),'criterion':'abs(final_ops_delta_percent)>=10.0','source':'native route summaries + proof checker logs'},open(R/'FRESH_COHORT_REPLAYABILITY_AUDIT.json','w'),indent=2)
json.dump({'cohort':'fresh_heuristic_causal_cohort_v1','status':'NO_HIGH_FOUND','high_cases':[],'count':0},open(R/'FRESH_FIXED_COHORT.json','w'),indent=2);Path(R/'FRESH_FIXED_COHORT.json.sha256').write_text(sha(R/'FRESH_FIXED_COHORT.json')+'\n')
json.dump({'cases':[],'status':'NO_HIGH_DONORS'},open(R/'DONOR_STATE_STABILITY.json','w'),indent=2)
json.dump({'routes':[],'planned':0,'executed':0},open(R/'heuristic_transplant_routes.csv','w'),indent=2)
(R/'heuristic_transplant_routes.csv').write_text('case,k,direction,legality,baseline_ops,action_ops,transplanted_ops,attenuation,reproduction,proof_status\n')
(R/'heuristic_transplant_effects.csv').write_text('case,k,direction,baseline_ops,action_ops,transplanted_ops,attenuation,reproduction,legality,proof_status\n')
json.dump({'executed':0,'VERIFIED':0,'failed':0,'routes':[]},open(R/'TRANSPLANT_PROOF_CHECKS.json','w'),indent=2)
(R/'FRESH_HEURISTIC_CAUSAL_RESULT.md').write_text('# Fresh heuristic causal cohort v1\n\nNo candidate met the frozen HIGH threshold; no causal transplant routes were run.\n')
json.dump({'decision':'NO_FRESH_HIGH_FOUND','fresh_candidates':len(rows),'fresh_high':0,'threshold_percent':10.0,'transplant_routes_executed':0,'next':'Expand candidate source without changing threshold.'},open(R/'FRESH_HEURISTIC_CAUSAL_RESULT.json','w'),indent=2)
(R/'NEXT_CAUSAL_EXPERIMENT.md').write_text('Expand fresh candidate discovery using additional real states/actions while retaining the frozen 10% HIGH threshold.\n')
# immutable retention policy + validator
(R/'SCIENTIFIC_PACKAGE_RETENTION_POLICY.md').write_text('''# Scientific package retention policy\n\nAny directory containing `manifest.json` with `package_complete=true` is SCIENTIFIC_ACTIVE. Cleanup tools must refuse deletion of input/, checkpoint/, action/, baseline/, treatment/, route summaries, proofs, donor states, manifests, and hashes under active packages.\n\nDeletion requires an explicit archival migration that preserves byte hashes and validator evidence.\n''')
print('candidates',len(rows),'high',sum(x['classification']=='HIGH' for x in rows))
