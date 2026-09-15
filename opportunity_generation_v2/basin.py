import json,hashlib
from pathlib import Path
R=Path('results/fresh_trajectory_divergence_audit_v1/routes');O=Path('results/opportunity_generation_v2')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(e):return json.dumps([e['kind'],e['value']],sort_keys=True,separators=(',',':')).encode()
seq=[];reports=[]
for c,r in [('T10M3',5),('T10M5',4)]:
 d=R/c/f'rank{r}'; p=d/'action/telemetry.jsonl'; higher={k:[] for k in ['conflict','learned','decision']}; hs=[]
 for line in p.open():
  e=json.loads(line)
  if e['kind'] in ('prestate','milestone'):continue
  h=hashlib.sha256(canon(e)).digest();hs.append(h)
  if e['kind'] in higher:higher[e['kind']].append(h)
 comp=json.loads((d/'comparison.json').read_text());ex=json.loads((d/'action/execution.json').read_text());assert sha(p)==ex['telemetry_sha256']
 reports.append({'case':c,'rank':r,'telemetry_sha256':sha(p),'semantic_events':len(hs),'first_divergences':{k:comp[f'first_{k}_divergence'] for k in ['conflict','learned','decision']},'final_counters':ex['final_counters'],'proof_verified':ex['proof_verified']})
 seq.append((hs,higher))
def compare(a,b):
 n=0
 for x,y in zip(reversed(a),reversed(b)):
  if x!=y:break
  n+=1
 return {'lengths':[len(a),len(b)],'identical':a==b,'common_suffix_events':n,'suffix_start_offsets':[len(a)-n,len(b)-n],'common_suffix_sha256':hashlib.sha256(b''.join(a[len(a)-n:])).hexdigest() if n else None,'suffix_fraction_of_shorter':n/min(len(a),len(b))}
s={'routes':reports,'treatment_semantic_suffix':compare(seq[0][0],seq[1][0]),'sequences':{k:compare(seq[0][1][k],seq[1][1][k]) for k in seq[0][1]}}
s['classification']='TWO TRIGGERS INTO ONE OBSERVED ALTERNATE BASIN' if s['treatment_semantic_suffix']['suffix_fraction_of_shorter']>.95 and all(x['suffix_fraction_of_shorter']>.95 for x in s['sequences'].values()) else 'UNRESOLVED'
s['scope']='Observed semantic event suffix identity, not proof of complete internal-state equality or independent mechanisms.'
(O/'HIGH_BASIN_IDENTITY.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({k:v for k,v in s.items() if k!='routes'},indent=2))
