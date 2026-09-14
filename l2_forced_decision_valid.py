"""Repeat the same two specified decision interventions after heap-legality fix.
Discard earlier post-pop overrides; no new target, points or conditions.
"""
import json,shutil,subprocess,gzip
from pathlib import Path
from evaluation_oracle_run import sha
from unseen_selector import dump
import l2_delayed_amplification as orig
P=Path('results/l2_delayed_amplification/forced_valid');B=Path('/private/tmp/satfinding-l2-forced-valid')
def main():
 P.mkdir(exist_ok=True);B.mkdir(exist_ok=True);assert not (P/'protocol.json').exists()
 root=B/'glucose-3.0';shutil.copytree(orig.B/'glucose-3.0',root,dirs_exist_ok=True)
 s=(orig.B/'trace.inc').read_text();idx=s.index('Lit Solver::da_pick()')
 s=s[:idx]+r'''
Lit Solver::da_pick(){
 bool cp=decisions==828;
 if(cp)lt_snapshot("decision828_before_pick");
 if(cp && (lt_run=="A_FORCED" || lt_run=="B_FORCED")){
  Lit forced=mkLit(lt_run=="A_FORCED"?569:186,true);
  if(value(forced)!=l_Undef || !decision[var(forced)] || qhead!=trail.size())exit(32);
  if(random_var_freq!=0 || rnd_pol)exit(34);
  for(int v=0;v<nVars();++v)if(value(v)==l_Undef&&decision[v]&&!order_heap.inHeap(v))exit(35);
  // Same unconditional RNG draw as native pickBranchLit. Fixed run has zero
  // random-variable frequency and no random polarity. No candidate is popped.
  double before=random_seed;drand(random_seed);
  lt_snapshot("decision828_after_override");
  gzprintf(lt_out,"{\"t\":\"FORCED\",\"c\":%llu,\"d\":%llu,\"e\":%llu,\"forced\":%d,\"legal\":true,\"seed_before\":\"%a\",\"seed_after\":\"%a\",\"heap_unchanged\":true}\n",(LU)conflicts,(LU)decisions,lt_e,lt_int(forced),before,random_seed);
  da_forced=true;return forced;
 }
 double before=random_seed;Lit next=pickBranchLit();
 if(cp){lt_snapshot("decision828_after_native_pick");gzprintf(lt_out,"{\"t\":\"NATIVE_PICK\",\"seed_before\":\"%a\",\"seed_after\":\"%a\"}\n",before,random_seed);}
 return next;
}
'''
 (B/'trace.inc').write_text(s)
 source=root/'core/Solver.cc';source.write_text(source.read_text().replace(str(orig.B/'trace.inc'),str(B/'trace.inc')))
 shutil.copyfile(orig.B/'driver.cc',B/'driver.cc')
 for n in ['A','B']:shutil.copyfile(orig.B/f'{n}.cnf',B/f'{n}.cnf')
 (P/'requests.txt').write_text('')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(B/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(B/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stderr
 dump(P/'protocol.json',dict(fixed_conditions=['A','B','A_FORCED','B_FORCED'],correction='Previous post-pop override fails eligible-variable heap coverage. Invalidated, not evidence. Same predetermined literals tested at branch entry, preserving own heap; lazy removal of assigned forced variable on subsequent native picks is legal.',legality='All eligible unassigned variables present in heap; forced literal undef and eligible; fixed random_var_freq=0/rnd_pol=false; same one RNG draw as native; no other owned-state write.',sources={str(x):sha(x) for x in [Path(__file__),B/'trace.inc',source]},binary_sha256=sha(B/'run')))
 runs={}
 for n in ['A','B','A_FORCED','B_FORCED']:
  inp=n.split('_')[0];proof=B/f'{n}.drup'
  r=subprocess.run([str(B/'run'),str(B/f'{inp}.cnf'),str(proof),'1000000',n,str(P.resolve()),str(P/'requests.txt')],capture_output=True,text=True,timeout=180)
  if r.returncode:runs[n]=dict(status='ABORTED',returncode=r.returncode);print(n,runs[n],flush=True);continue
  stats=json.loads(next(l for l in reversed(r.stdout.splitlines()) if l.startswith('{')));assert stats['status']=='UNSAT'
  check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(B/f'{inp}.cnf'),str(proof)],capture_output=True,text=True,timeout=60)
  (P/f'{n}.proof_check.txt').write_text(check.stdout+check.stderr);assert check.returncode==0 and 'VERIFIED' in check.stdout
  with gzip.open(P/f'{n}.drup.gz','wb') as f:f.write(proof.read_bytes())
  runs[n]=dict(stats=stats,proof_verified=True,proof_sha256=sha(proof));dump(P/f'{n}.result.json',runs[n]);print(n,stats,flush=True)
 dump(P/'runs.json',runs)
 invalid=json.loads((orig.P/'runs.json').read_text())
 dump(orig.P/'invalid_forced_runs.json',dict(reason='Post-pop literal override strands unused native candidate outside heap; do not use as intervention evidence.',discarded={n:invalid[n] for n in ['A_FORCED','B_FORCED']},valid_results='forced_valid/runs.json'))
if __name__=='__main__':main()
