import json,hashlib,subprocess,os,gzip,shutil,sys,time
from pathlib import Path
R=Path('results/fresh_trajectory_divergence_audit_v1'); F=Path('results/fresh_heuristic_causal_cohort_v1'); B=Path('execution_pipeline_v1/trajectory_native_v1'); P=json.loads((R/'TRAJECTORY_DIVERGENCE_PROTOCOL_V1.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(case,rank,mode,out,original=False):
 out.mkdir(parents=True,exist_ok=False);p=F/'cases'/case
 req=(p/'action_routes'/f'rank{rank}'/'request.txt').read_text().split()
 if mode=='baseline':req=req[:8]+['0','0','0','0']
 (out/'request.txt').write_text(' '.join(req)+'\n')
 env=os.environ.copy();env.pop('TRAJECTORY_AUDIT_ON',None)
 if not original:env['TRAJECTORY_AUDIT_ON']='1'
 binary=Path('execution_pipeline_v1/native/replay') if original=='reference' else B/'audit-replay'
 cmd=[str(binary),str(p/'input/input.cnf'),str(out/'proof.drup'),str(out),str(out/'request.txt')]
 t=time.time();z=subprocess.run(cmd,capture_output=True,text=True,env=env)
 (out/'stdout.txt').write_text(z.stdout);(out/'stderr.txt').write_text(z.stderr)
 result={'case':case,'rank':rank,'route':mode,'command':cmd,'returncode':z.returncode,'seconds':time.time()-t}
 if z.returncode:raise RuntimeError(result)
 lines=[json.loads(l) for l in z.stdout.splitlines() if l.startswith('{')];result.update(lines[-2]);result.update(lines[-1])
 q=subprocess.run([str(B/'proof-checker'),str(p/'input/input.cnf'),str(out/'proof.drup')],capture_output=True,text=True)
 (out/'proof_check.txt').write_text(q.stdout+q.stderr);result['proof_verified']=q.returncode==0 and 'VERIFIED' in q.stdout;result['checker_returncode']=q.returncode
 cp=json.loads((out/'checkpoint.json').read_text()); frozen=json.loads((p/'checkpoint/state.json').read_text())
 result['identity_checkpoint_equal']=all(frozen[k]==v for k,v in cp.items())
 result['checkpoint_logical_sha256']=sha(out/'logical.txt');result['checkpoint_heuristic_sha256']=sha(out/'heuristic.txt')
 tel=out/'telemetry.jsonl'
 if tel.exists():
  result['telemetry_sha256']=sha(tel)
  # Retain raw telemetry too: permanent artifacts, no deletion.
 result['artifacts']={f.name:sha(f) for f in out.iterdir() if f.is_file()}
 (out/'execution.json').write_text(json.dumps(result,indent=2))
 assert result['proof_verified'] and result['identity_checkpoint_equal']
 if mode=='action':assert result['action_verified']
 return result

def smoke():
 c=sorted(P['cohort'],key=lambda x:(x['case'],x['rank']))[0];results=[]
 for mode in ['baseline','action']:
  reference=run(c['case'],c['rank'],mode,R/'smoke'/mode/'REFERENCE',original='reference')
  rs=[run(c['case'],c['rank'],mode,R/'smoke'/mode/tag,original=tag=='OFF') for tag in ['OFF','ON1','ON2']]
  keys=['status','conflicts','decisions','propagations','temporal_samples','final_counters','action_verified','state_verified']
  assert all({k:r[k] for k in keys}=={k:reference[k] for k in keys} for r in rs)
  assert rs[1]['telemetry_sha256']==rs[2]['telemetry_sha256']
  results.extend(rs)
 (R/'NONPERTURBATION_SMOKE.json').write_text(json.dumps({'PASS':True,'golden':c,'runs':results},indent=2));print('SMOKE PASS',flush=True)
def batch():
 assert json.loads((R/'NONPERTURBATION_SMOKE.json').read_text())['PASS']
 done=[]
 for idx,c in enumerate(P['cohort']):
  for path,h in c['artifacts'].items():assert sha(path)==h
  d=R/'routes'/c['case']/f'rank{c["rank"]}'
  for mode in ['baseline','action']:
   out=d/mode
   if (out/'execution.json').exists():res=json.loads((out/'execution.json').read_text())
   else:res=run(c['case'],c['rank'],mode,out)
   done.append(res)
  (R/'ROUTE_EXECUTION_MAPPING.json').write_text(json.dumps(done,indent=2))
  print(f'{idx+1}/136 {c["case"]} rank{c["rank"]} VERIFIED',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='smoke':smoke()
 else:batch()
