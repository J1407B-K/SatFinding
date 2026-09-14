import json,subprocess,hashlib,shutil
from pathlib import Path
R=Path('results/fresh_heuristic_causal_cohort_v1'); B=Path('execution_pipeline_v1/native_v2'); C=B/'proof-checker';
rows=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p in sorted((R/'cases').iterdir()):
 if not p.is_dir():continue
 # overwrite only separate verification dirs
 st=json.load(open(p/'checkpoint/state.json'));acts=json.load(open(p/'action/actions.json'))['selected']; pref=json.load(open(p/'checkpoint/prefix_counters.json'))['analysis_resolution_steps']
 for typ,rank in [('baseline',None),('action',1)]:
  d=p/'verify2'/('baseline' if rank is None else 'action');d.mkdir(parents=True,exist_ok=True);a=None if rank is None else acts[rank-1];req=[st['boundary'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead'],st['canonical_logical_state_hash'],st['canonical_heuristic_state_hash']];req += [0,0,0,0] if a is None else [a['id'],a['literal'],0,len(a['clause'])]+a['clause'];(d/'request.txt').write_text(' '.join(map(str,req))+'\n'); proof=d/'proof.drup';r=subprocess.run([str(B/'replay'),str(p/'input/input.cnf'),str(proof),str(d),str(d/'request.txt')],capture_output=True,text=True);(d/'stdout.txt').write_text(r.stdout);(d/'stderr.txt').write_text(r.stderr);ok=False;res={}
  if r.returncode==0:
   ls=r.stdout.splitlines();res=json.loads(ls[-2]);res.update(json.loads(ls[-1])['final_counters']);q=subprocess.run([str(C),str(p/'input/input.cnf'),str(proof)],capture_output=True,text=True);(d/'proof_check.txt').write_text(q.stdout+q.stderr);ok=q.returncode==0 and 'VERIFIED' in q.stdout
  rows.append({'case':p.name,'route':typ,'rank':rank,'returncode':r.returncode,'ops_remaining':res.get('analysis_resolution_steps',0)-pref if res else None,'conflicts':res.get('conflicts') if res else None,'decisions':res.get('decisions') if res else None,'proof_verified':ok})
json.dump(rows,open(R/'verified_route_results.json','w'),indent=2)
print(json.dumps(rows,indent=2))
