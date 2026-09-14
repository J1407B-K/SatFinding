import json,subprocess,hashlib,shutil
from pathlib import Path
O=Path('results/fresh_heuristic_causal_cohort_v1');B=Path('execution_pipeline_v1/native/replay');C=Path('execution_pipeline_v1/native/proof-checker')
rows=[]
for p in sorted((O/'cases').iterdir()):
 if not p.is_dir():continue
 st=json.load(open(p/'checkpoint/state.json')); acts=json.load(open(p/'action/actions.json'))['selected']
 for a in acts:
  out=p/'action_routes'/f'rank{a["rank"]}';out.mkdir(parents=True,exist_ok=True);proof=out/'proof.drup';req=[st['boundary'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead'],st['canonical_logical_state_hash'],st['canonical_heuristic_state_hash'],a['id'],a['literal'],0,len(a['clause'])]+a['clause'];(out/'request.txt').write_text(' '.join(map(str,req))+'\n');r=subprocess.run([str(B),str(p/'input/input.cnf'),str(proof),str(out),str(out/'request.txt')],capture_output=True,text=True);ok=False;res={}
  if r.returncode==0:
   try:
    ls=r.stdout.splitlines();res=json.loads(ls[-2]);res.update(json.loads(ls[-1])['final_counters']);q=subprocess.run([str(C),str(p/'input/input.cnf'),str(proof)],capture_output=True,text=True);ok=q.returncode==0 and 'VERIFIED' in q.stdout
   except Exception:pass
  rows.append({'case':p.name,'rank':a['rank'],'action_id':a['id'],'status':res.get('status'),'ops':res.get('analysis_resolution_steps'),'proof':ok})
json.dump(rows,open(O/'candidate_action_results.json','w'),indent=2)
for x in rows:print(x)
