import json,shutil,subprocess,gzip
from pathlib import Path
from evaluation_oracle_run import sha
from unseen_selector import dump
from build_native_cdcl import replace_once
P=Path('results/l2_delayed_amplification'); B=Path('/private/tmp/satfinding-l2-delayed'); OLD=Path('/private/tmp/satfinding-l1-l2-latent')
POINTS=[0,100,150,180,190,198,200,220,250,300,400,600]
def build():
 B.mkdir(exist_ok=True);root=B/'glucose-3.0';shutil.copytree(OLD/'glucose-3.0',root,dirs_exist_ok=True)
 inc=Path('l1_l2_latent_trace.inc').read_text()
 # Retain read-only exact snapshots, use a compact ledger for all conflicts.
 start=inc.index('void Solver::lt_event(');end=inc.index('void Solver::lt_pre_enqueue',start)
 inc=inc[:start]+'''void Solver::lt_event(const char* kind,int v,LU rh,bool special){
 ++lt_global; LU k=++lt_ord[{kind,conflicts}];
 if(std::string(kind)=="D" || std::string(kind)=="L" || (std::string(kind)=="E" && special))
 gzprintf(lt_out,"{\\"t\\":\\"%s\\",\\"g\\":%llu,\\"c\\":%llu,\\"d\\":%llu,\\"e\\":%llu,\\"k\\":%llu,\\"v\\":%d,\\"r\\":\\"%llu\\",\\"ops\\":%llu}\\n",kind,lt_global,(LU)conflicts,(LU)decisions,lt_e,k,v,rh,sf_analysis);
}
''' + inc[end:]
 start=inc.index('void Solver::lt_pre_enqueue');end=inc.index('void Solver::lt_analysis',start)
 inc=inc[:start]+'''void Solver::lt_pre_enqueue(Lit p,CRef from){}
void Solver::lt_post_enqueue(Lit p,CRef from){++lt_e;lt_event("E",lt_int(p),from==CRef_Undef?0:lt_clause(ca[from]),from!=CRef_Undef&&lt_l2(ca[from]));da_ghost("enqueue");}
'''+inc[end:]
 inc=inc.replace('lt_intervene=run==std::string("B_REASON_RESET");','lt_intervene=false;')
 (B/'trace.inc').write_text(inc+'\n'+Path('l2_delayed_amplification.inc').read_text())
 p=root/'core/Solver.h';s=p.read_text().replace('    void lt_start();','    void lt_start();\n    void da_ghost(const char*);\n    CRef da_inject();\n    Lit da_pick();');p.write_text(s)
 p=root/'core/Solver.cc';s=p.read_text().replace(str(Path('l1_l2_latent_trace.inc').resolve()),str(B/'trace.inc'))
 s=s.replace('void Solver::lt_start(){lt_event("INIT",0,0);lt_snapshot("initialized");}','void Solver::lt_start(){da_setup();lt_event("INIT",0,0);da_ghost("initialized");}')
 s=replace_once(s,'        CRef confl = propagate();','        CRef confl = da_inject();\n        if(confl==CRef_Undef)confl=propagate();')
 s=replace_once(s,'        trail_lim.shrink(trail_lim.size() - level);','        trail_lim.shrink(trail_lim.size() - level);\n        da_ghost("backtrack");')
 s=replace_once(s,'                next = pickBranchLit();','                next = da_pick();');p.write_text(s)
 shutil.copyfile(OLD/'driver.cc',B/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(B/'driver.cc'),str(p),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(B/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stderr
 for n in ['A','B']:shutil.copyfile(OLD/f'{n}.cnf',B/f'{n}.cnf')
 (P/'requests.txt').write_text('')
 return dict(command=cmd,binary=sha(B/'run'),sources={str(x):sha(x) for x in [Path(__file__),Path('l2_delayed_amplification.inc'),Path('docs/l2-delayed-amplification-protocol.md'),B/'trace.inc',p]},inputs={n:sha(B/f'{n}.cnf') for n in ['A','B']})
def main():
 assert not (P/'protocol.json').exists(),'frozen experiment exists'
 meta=build();dump(P/'protocol.json',dict(points=POINTS,forced=['A_FORCED','B_FORCED'],build=meta))
 runs={};old=json.loads(Path('results/l1_l2_latent/natural_runs.json').read_text())
 for n in ['A','B']+[f'I{x}' for x in POINTS if x]+['A_FORCED','B_FORCED']:
  inp='B' if n in ['B','B_FORCED'] else 'A';proof=B/f'{n}.drup'
  r=subprocess.run([str(B/'run'),str(B/f'{inp}.cnf'),str(proof),'1000000',n,str(P.resolve()),str(P/'requests.txt')],capture_output=True,text=True,timeout=180)
  if r.returncode:
   runs[n]=dict(status='ABORTED',returncode=r.returncode,stdout=r.stdout,stderr=r.stderr);dump(P/f'{n}.result.json',runs[n]);print(n,runs[n],flush=True);continue
  stats=json.loads(next(l for l in reversed(r.stdout.splitlines()) if l.startswith('{')));assert stats['status']=='UNSAT'
  if n in old:assert {k:v for k,v in stats.items() if k!='seconds'}=={k:v for k,v in old[n].items() if k!='seconds'}
  check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(B/f'{inp}.cnf'),str(proof)],capture_output=True,text=True,timeout=60)
  (P/f'{n}.proof_check.txt').write_text(check.stdout+check.stderr)
  verified=check.returncode==0 and 'VERIFIED' in check.stdout
  with gzip.open(P/f'{n}.drup.gz','wb') as f:f.write(proof.read_bytes())
  runs[n]=dict(stats=stats,proof_verified=verified,proof_sha256=sha(proof),input_sha256=sha(B/f'{inp}.cnf'),trace_sha256=sha(P/f'{n}.events.jsonl.gz'))
  dump(P/f'{n}.result.json',runs[n]);print(n,stats,'proof',verified,flush=True)
  assert verified,'Proof failed: halt rather than reinterpret'
 dump(P/'runs.json',runs)
if __name__=='__main__':main()
