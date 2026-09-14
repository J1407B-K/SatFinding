import gzip,json
from pathlib import Path
P=Path('results/persistent_imprint_replication/T6_T14')
for d in sorted([p for p in P.iterdir() if p.is_dir()]):
 s=json.load(open(d/'summary.json'))
 ev=[json.loads(x) for x in gzip.open(d/'TREATMENT.events.jsonl.gz','rt')]
 cert=json.load(open(d/'certificates.json')); hashes={r['id'] for r in []}; lem=set()
 for r in ev:
  if r.get('t')=='Q' and r.get('clause') in cert['lemmas']:lem.add(r['id'])
 uses=[r for r in ev if r.get('t') in ('E','A','M') and r.get('r') in lem]
 s['reason_use_count']=len(uses);s['first_reason_use']=uses[0] if uses else None
 if s['classification']=='NO_ALIGNED_CHECKPOINT' and not uses:s['classification']='NO_REASON_USE'
 json.dump(s,open(d/'summary.json','w'),indent=2)
rows=[json.load(open(d/'summary.json')) for d in sorted(P.iterdir()) if d.is_dir()]
json.dump({'targets':rows,'t5_excluded':True,'t6_t14_only':True,'eligibility_rule':'abs gap >=10% AND reason use AND aligned exact checkpoint AND heap invariant','interventions_executed':False},open(P/'cohort_summary.json','w'),indent=2)
print([(r['target'],r['relative_ops_gap_percent'],r['reason_use_count'],r['classification']) for r in rows])
