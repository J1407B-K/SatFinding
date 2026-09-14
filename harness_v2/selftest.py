from pathlib import Path
import subprocess,json,hashlib,difflib
import sys
O=Path(sys.argv[1] if len(sys.argv)>1 else 'results/harness_qualification_v2/selftest')
O.mkdir(parents=True,exist_ok=True)
for target in ['T8','T10']:
 for run in ['A','B']:
  d=O/(target+'_'+run);d.mkdir(exist_ok=False)
  cmd=['./canonical_collector_native',f'results/high_leverage_discovery/{target}/input.cnf',str(d/'proof.drup'),str(d),'selftest']
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
  (d/'stdout.txt').write_text(p.stdout);(d/'stderr.txt').write_text(p.stderr);(d/'command.json').write_text(json.dumps(cmd))
  print(target,run,p.returncode,p.stdout[-500:],p.stderr[-500:],flush=True);p.check_returncode()
 a,b=[O/(target+'_'+r) for r in ['A','B']]
 for name in ['logical.txt','heuristic.txt','checkpoint.json']:
  x,y=(a/name).read_text(),(b/name).read_text()
  if x!=y: print(''.join(difflib.unified_diff(x.splitlines(True),y.splitlines(True)))[:8000]);raise AssertionError((target,name))
print('CANONICAL_STATE_HASH_CROSS_RUN_STABLE')
