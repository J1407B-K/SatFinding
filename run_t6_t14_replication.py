import json,hashlib,subprocess,gzip,time,shutil
from pathlib import Path
from certified_lemma_builder import canon,build,check,K
ROOT=Path('results/persistent_imprint_replication'); OUT=ROOT/'T6_T14'; BIN='/private/tmp/satfinding-decision828-context/run'; TARGETS=[f'T{i}' for i in range(6,15)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dimacs(path,cnf):
 with open(path,'w') as f:
  f.write(f'p cnf 600 {len(cnf)}\n');[f.write(' '.join(map(str,c))+' 0\n') for c in cnf]
def run(tag,cnf,path):
 inp=path/(tag+'.cnf');proof=path/(tag+'.drup');dimacs(inp,cnf);(path/'requests.txt').write_text('')
 t=time.time();p=subprocess.run([BIN,str(inp),str(proof),'1000000',tag,str(path),str(path/'requests.txt')],capture_output=True,text=True,timeout=240);wall=time.time()-t
 if p.returncode:return dict(status='ABORT',returncode=p.returncode,stderr=p.stderr,wall_seconds=wall)
 st=json.loads(next(x for x in reversed(p.stdout.splitlines()) if x.startswith('{')))
 ck=subprocess.run(['/private/tmp/satfinding-drat-trim',str(inp),str(proof)],capture_output=True,text=True,timeout=90);(path/(tag+'.proof_check.txt')).write_text(ck.stdout+ck.stderr)
 return dict(status=st['status'],stats=st,wall_seconds=wall,proof_verified=ck.returncode==0 and 'VERIFIED' in ck.stdout,proof_sha256=sha(proof))
def main():
 OUT.mkdir(exist_ok=True);summary=[]
 for name in TARGETS:
  d=OUT/name;d.mkdir(exist_ok=True);src=Path('results/persistent_memory_stream')/name/'target.json';x=json.loads(src.read_text());cnf=[canon(c) for c in x['cnf']]
  try:
   steps=build(cnf);assert len(steps)>=K;steps=steps[:K];assert check(cnf,steps)
   lem=[canon(s['lemma']) for s in steps]; cert=dict(target=name,K=K,max_depth=1,max_clause_length=12,sort='canonical lexical',input_sha256=sha(src),lemmas=[list(c) for c in lem],certificates=steps)
   (d/'certificates.json').write_text(json.dumps(cert,indent=2));dimacs(d/'treatment.cnf',cnf+lem);(d/'input.cnf').write_text((d/'treatment.cnf').read_text().split('p cnf')[0]+'p cnf 600 '+str(len(cnf))+'\n'+'\n'.join(' '.join(map(str,c))+' 0' for c in cnf)+'\n')
   rep=dict(status='PASS',independent_replay=True,lemma_count=len(lem),treatment_sha256=sha(d/'treatment.cnf'));(d/'checker_report.json').write_text(json.dumps(rep,indent=2))
   control=run('CONTROL',cnf,d); treatment=run('TREATMENT',cnf+lem,d)
   gap=(treatment['stats']['analysis_resolution_steps']/control['stats']['analysis_resolution_steps']-1)*100 if control.get('stats') and treatment.get('stats') else None
   row=dict(target=name,control=control,treatment=treatment,relative_ops_gap_percent=gap,reason_use_count=None,first_divergence=None,aligned_checkpoint='NOT_INSTRUMENTED',classification='NO_ALIGNED_CHECKPOINT')
   if not control.get('proof_verified') or not treatment.get('proof_verified'):row['classification']='INVALID/ABORT'
   elif gap is not None and abs(gap)<10:row['classification']='NO_GAP'
   (d/'summary.json').write_text(json.dumps(row,indent=2));summary.append(row);print(name,row['classification'],gap,flush=True)
  except Exception as e:
   row=dict(target=name,classification='INVALID/ABORT',error=repr(e));(d/'summary.json').write_text(json.dumps(row,indent=2));summary.append(row);print(name,'ABORT',e,flush=True)
 (OUT/'cohort_summary.json').write_text(json.dumps({'targets':summary,'frozen_rule':'abs gap >=10%, reason use, aligned exact checkpoint, heap invariant','t5_excluded':True,'t6_t14_only':True},indent=2))
if __name__=='__main__':main()
