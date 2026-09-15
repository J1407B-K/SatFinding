import json,hashlib
from pathlib import Path
R=Path('/tmp/v2final'); rows=[]
for m in ['ON1','ON2']:
 d=R/m/'S1'; inv=json.load(open(d/'actions.json')); tim={x['id']:x['timing'] for x in json.load(open(d/'timing.json'))}; raw=[json.loads(x) for x in open(d/'raw_events.jsonl')]; enq={}
 for e in raw:
  if e['kind']=='enqueue': enq.setdefault(e['value']['literal'],e)
 checks=[]
 for a in inv['all_actions']:
  e=enq.get(a['literal']); t=tim[a['id']]; ok=bool(e)==t['naturally_enqueued'] and (not e or (t['native_reason_id']==a['id'] and t['bucket']=='BUCKET_1'))
  checks.append(ok)
 rows.append({'mode':m,'checked':len(checks),'pass':sum(checks),'all_pass':all(checks),'timing_sha256':hashlib.sha256((d/'timing.json').read_bytes()).hexdigest()})
Path('results/opportunity_generation_v2/TIMING_CORRECTNESS_QUALIFICATION.json').write_text(json.dumps({'independent_recomputed_timing':sum(x['pass'] for x in rows),'total':sum(x['checked'] for x in rows),'per_run':rows,'pass':all(x['all_pass'] for x in rows)},indent=2)+'\n')
