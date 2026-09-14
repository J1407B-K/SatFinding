import json,hashlib,shutil,subprocess,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; O=ROOT/'results/fresh_heuristic_causal_cohort_v1'; raw=O/'raw_more_t8'; cases=O/'cases';cases.mkdir(exist_ok=True)
cnf=ROOT/'results/full_propagation_frontier_observer_v2/inputs/T8_qualification.cnf'; binary=ROOT/'execution_pipeline_v1/native/replay'; checker=ROOT/'execution_pipeline_v1/native/proof-checker'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
allrows=[]
for sdir in sorted([p for p in raw.iterdir() if p.name.startswith('S')],key=lambda p:int(p.name[1:])):
 st=json.load(open(sdir/'checkpoint.json')); act=json.load(open(sdir/'actions.json')); cid='T8M'+sdir.name[1:]; p=cases/cid
 for sub in ['input','checkpoint','action','baseline','treatment']: (p/sub).mkdir(parents=True,exist_ok=True)
 shutil.copy(cnf,p/'input/input.cnf');
 for n in ['checkpoint.json','logical.txt','heuristic.txt','prefix_counters.json']:shutil.copy(sdir/n,p/'checkpoint'/n)
 shutil.copy(sdir/'actions.json',p/'action/actions.json');
 st.update(case_id=cid,target='T8MORE',state_id=f'T10FRESH_{sdir.name}',input_sha256=sha(cnf),binary_sha256=sha(binary),checkpoint_sha256=sha(sdir/'checkpoint.json'))
 dump(p/'checkpoint/state.json',st)
 # select first action (legal; all 5 packages have six)
 a=act['selected'][0];dump(p/'action/action.json',a)
 manifest={'schema':'experiment_package_v1','case':cid,'package_complete':False,'input':{'path':'input/input.cnf','sha256':sha(p/'input/input.cnf'),'size':(p/'input/input.cnf').stat().st_size},'solver':{'binary_path':str(binary),'binary_sha256':sha(binary),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'config':'Glucose3 deterministic certifiedUNSAT','seed':None},'checkpoint':{'path':'checkpoint/state.json','sha256':sha(p/'checkpoint/state.json'),'logical_sha256':sha(p/'checkpoint/logical.txt'),'heuristic_sha256':sha(p/'checkpoint/heuristic.txt'),'conflicts':st['conflicts'],'decisions':st['decisions'],'propagations':st.get('propagations'),'trail':st['trail_length'],'qhead':st['qhead']},'action':a,'routes':{},'proof':{}}
 # run baseline/action via replay requests
 for direction in ['baseline','action']:
  out=p/('baseline' if direction=='baseline' else 'treatment'); proof=out/'proof.drup';
  req=[st['boundary'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead'],st['canonical_logical_state_hash'],st['canonical_heuristic_state_hash']]
  if direction=='baseline': req += [0,0,0,0]
  else:req += [a['id'],a['literal'],0,len(a['clause'])]+a['clause']
  (out/'request.txt').write_text(' '.join(map(str,req))+'\n')
  r=subprocess.run([str(binary),str(p/'input/input.cnf'),str(proof),str(out),str(out/'request.txt')],capture_output=True,text=True)
  (out/'stdout.txt').write_text(r.stdout);(out/'stderr.txt').write_text(r.stderr)
  if r.returncode!=0: print(cid,direction,'FAIL',r.stderr);continue
  lines=r.stdout.splitlines(); result=json.loads(lines[-2]); result.update(json.loads(lines[-1])['final_counters']);
  c=subprocess.run([str(checker),str(p/'input/input.cnf'),str(proof)],capture_output=True,text=True);(out/'proof_check.txt').write_text(c.stdout+c.stderr)
  meta={'result':result,'proof_path':str(proof),'proof_sha256':sha(proof),'checker_command':[str(checker),str(p/'input/input.cnf'),str(proof)],'checker_exit':c.returncode,'VERIFIED':c.returncode==0 and 'VERIFIED' in c.stdout}
  dump(out/'summary.json',meta);manifest['routes'][direction]=meta
 manifest['package_complete']=all((p/x).exists() for x in ['input/input.cnf','checkpoint/state.json','action/action.json','baseline/summary.json','treatment/summary.json'])
 dump(p/'manifest.json',manifest);allrows.append(manifest)
dump(O/'FRESH_CANDIDATES.json',allrows)
print('cases',len(allrows),'complete',sum(x['package_complete'] for x in allrows))
