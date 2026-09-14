import gzip,json
from pathlib import Path
P=Path('results/persistent_imprint_replication/T6_T14');O=Path('results/reason_only_fork/T6_T14');O.mkdir(parents=True,exist_ok=True)
rows=[]
for d in sorted(x for x in P.iterdir() if x.is_dir()):
 ev=[json.loads(x) for x in gzip.open(d/'TREATMENT.events.jsonl.gz','rt')]; cert=json.load(open(d/'certificates.json')); lem={tuple(c) for c in cert['lemmas']}; q={r['id']:tuple(r['clause']) for r in ev if r.get('t')=='Q'}; ids={k:i+1 for i,c in enumerate(cert['lemmas']) for k,v in q.items() if v==tuple(c)}; uses=[r for r in ev if r.get('t') in ('E','A','M') and r.get('r') in ids]
 row={'target':d.name,'status':'NO_DUAL_REASON_EVENT','treatment_reason_use_count':len(uses),'dual_reason_event':None,'first_divergences':None,'final_ops_gap_percent':json.load(open(d/'summary.json')).get('relative_ops_gap_percent'),'proof_status':'CONTROL_AND_TREATMENT_VERIFIED','why_no_event':'Existing ledger has reason hash and events but no full per-enqueue assignment/trail snapshot; protocol forbids static clause-scan inference. No fork executed.'}
 (O/(d.name+'.json')).write_text(json.dumps(row,indent=2));rows.append(row)
json.dump({'targets':rows,'t5_excluded':True,'t6_t14_only':True,'forks_executed':0,'claim':'No dual-reason event can be certified from the existing ledger; this is an instrumentation limitation, not evidence of absence.'},open(O/'cohort_summary.json','w'),indent=2)
print([(r['target'],r['treatment_reason_use_count'],r['status']) for r in rows])
