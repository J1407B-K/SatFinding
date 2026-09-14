import os,sys,json,subprocess,time
from build import ROOT,OUT,sha,dump
build=json.loads((OUT/'BUILD_MANIFEST.json').read_text());binary=build['binary'];assert sha(binary)==build['binary_sha256']
checker=json.loads((ROOT/'results/prospective_micro_rollout/frozen_protocol.json').read_text())['checker'];assert sha(checker['path'])==checker['sha256']
rows=[]
for target in ['T8','T10']:
 inp=ROOT/f'results/full_propagation_frontier_observer_v2/inputs/{target}_qualification.cnf'
 for mode in ['OFF','ON1','ON2']:
  d=OUT/'runs'/target/mode;d.mkdir(parents=True,exist_ok=False)
  cmd=[binary,str(inp),str(d/'proof.drup'),str(d/'trace.jsonl.gz'),'off' if mode=='OFF' else 'on'];start=time.time()
  with (d/'stdout.txt').open('w') as so,(d/'stderr.txt').open('w') as se:r=subprocess.run(cmd,stdout=so,stderr=se)
  invocation={'command':cmd,'exit_code':r.returncode,'start':start,'end':time.time(),'binary_sha256':sha(binary),'input_sha256':sha(inp),'historical_exact_replay':False,'qualification_case_label':target};dump(d/'invocation.json',invocation);r.check_returncode()
  summary=json.loads((d/'stdout.txt').read_text().splitlines()[-1]);dump(d/'summary.json',summary)
  expected=(6087,7162,476510) if target=='T8' else (9783,11441,770564)
  assert tuple(summary[k] for k in ['conflicts','decisions','propagations'])==expected
  cmd=[checker['path'],str(inp),str(d/'proof.drup')];start=time.time();r=subprocess.run(cmd,capture_output=True,text=True)
  (d/'checker.stdout.txt').write_text(r.stdout);(d/'checker.stderr.txt').write_text(r.stderr)
  row={'case':target,'mode':mode,'input':str(inp),'input_sha256':sha(inp),'proof':str(d/'proof.drup'),'proof_sha256':sha(d/'proof.drup'),'checker_sha256':sha(checker['path']),'command':cmd,'exit_code':r.returncode,'stdout':str(d/'checker.stdout.txt'),'stderr':str(d/'checker.stderr.txt'),'verified':r.returncode==0 and 's VERIFIED' in r.stdout,'start':start,'end':time.time()};dump(d/'proof_check.json',row);rows.append(row);dump(OUT/'PROOF_CHECKS.json',rows)
  assert row['verified'],row
  print(target,mode,'VERIFIED',flush=True)
