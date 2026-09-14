import json,subprocess,hashlib,csv
from pathlib import Path
R=Path('results/fresh_heuristic_causal_cohort_v1');B=Path('execution_pipeline_v1/native_v2');C=B/'proof-checker'; rows=[]; proofs=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p in sorted((R/'cases').iterdir()):
 if not p.is_dir():continue
 st=json.load(open(p/'checkpoint/state.json')); pref=json.load(open(p/'checkpoint/prefix_counters.json'))['analysis_resolution_steps']; donor=p/'donors';donor.mkdir(exist_ok=True)
 # establish donor files using baseline and action route each k
 for route,rank in [('baseline',None),('action',1)]:
  a=None if rank is None else json.load(open(p/'action/actions.json'))['selected'][0]
  for k in [1,4,16,64]:
   d=donor/f'{route}_k{k}';d.mkdir(exist_ok=True);req=[st['boundary'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead'],st['canonical_logical_state_hash'],st['canonical_heuristic_state_hash']];req += [0,0,0,0] if a is None else [a['id'],a['literal'],0,len(a['clause'])]+a['clause'];(d/'request.txt').write_text(' '.join(map(str,req))+'\n');proof=d/'proof.drup';r=subprocess.run([str(B/'replay'),str(p/'input/input.cnf'),str(proof),str(d),str(d/'request.txt'),str(k),str(donor/'donor.txt')],capture_output=True,text=True);(d/'stdout.txt').write_text(r.stdout);(d/'stderr.txt').write_text(r.stderr);j={'case':p.name,'route':route,'k':k,'returncode':r.returncode,'donor_state':(d/'transplanted.json').exists(),'proof':False}
   if r.returncode==0:
    q=subprocess.run([str(C),str(p/'input/input.cnf'),str(proof)],capture_output=True,text=True);(d/'proof_check.txt').write_text(q.stdout+q.stderr);j['proof']=q.returncode==0 and 'VERIFIED' in q.stdout;j['result']=json.loads(r.stdout.splitlines()[-2]);j['result'].update(json.loads(r.stdout.splitlines()[-1])['final_counters'])
   rows.append(j)
json.dump(rows,open(R/'DONOR_TRANSPLANT_RUNS.json','w'),indent=2);print('runs',len(rows),'proofs',sum(x['proof'] for x in rows))
