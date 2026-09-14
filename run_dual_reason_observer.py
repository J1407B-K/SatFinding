import json,shutil,subprocess,gzip,hashlib,time
from pathlib import Path
from build_native_cdcl import replace_once
ROOT=Path('results/persistent_imprint_replication/T6_T14'); OUT=Path('results/dual_reason_observer/T6_T14'); BASE=Path('/private/tmp/satfinding-decision828-l2-remove'); OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 for td in sorted(x for x in ROOT.iterdir() if x.is_dir()):
  n=td.name;o=OUT/n;o.mkdir(exist_ok=True); cert=json.load(open(td/'certificates.json')); lem=[tuple(x) for x in cert['lemmas']]
  B=Path('/private/tmp/dual-'+n);shutil.rmtree(B,ignore_errors=True);shutil.copytree(BASE/'glucose-3.0',B/'glucose-3.0'); src=B/'glucose-3.0/core/Solver.cc'; tr=(BASE/'trace.inc').read_text(); H=B/'glucose-3.0/core/Solver.h'; H.write_text(H.read_text().replace('    void ctx_remove_l2();','    void ctx_remove_l2();\n    void dro_observe(Lit,CRef);'))
  arr=','.join('{'+','.join(map(str,c))+'}' for c in lem)
  fn=r'''void Solver::dro_observe(Lit p,CRef from){\n std::vector<std::vector<int>> L={{LEMS}};\n static bool done=false; if(done||from==CRef_Undef)return;\n Clause& g=ca[from]; bool tg=false; int gl=0; for(int i=0;i<NL;++i){bool eq=g.size()==LEMS[i].size();for(int j=0;j<g.size()&&eq;++j){int z=(var(g[j])+1)*(sign(g[j])?-1:1); bool has=false;for(int k:LEMS[i])if(k==z)has=true;if(!has)eq=false;}if(eq){tg=true;gl=i+1;break;}} if(!tg)return;\n int lit=(var(p)+1)*(sign(p)?-1:1); int count=0,aid=0; for(int i=0;i<clauses.size();++i){Clause& a=ca[clauses[i]];if(a.learnt()||&a==&g)continue;int undef=0,last=0;bool sat=false;for(int j=0;j<a.size();++j){lbool v=value(a[j]);if(v==l_True){sat=true;break;}if(v==l_Undef){undef++;last=(var(a[j])+1)*(sign(a[j])?-1:1);}}if(!sat&&undef==1&&last==lit){count++;if(aid==0)aid=i+1;}}\n if(count){FILE*f=fopen((lt_dir+"/dual_reason.json").c_str(),"w");fprintf(f,"{\\"status\\":\\"FOUND\\",\\"lemma_id\\":%d,\\"a_clause_slot\\":%d,\\"literal\\":%d,\\"conflict\\":%llu,\\"decision\\":%llu,\\"level\\":%d,\\"qhead\\":%d,\\"trail\\":%d,\\"candidate_count\\":%d}\n",gl,aid,lit,(LU)conflicts,(LU)decisions,decisionLevel(),qhead,trail.size(),count);fclose(f);lt_snapshot("dual_reason_checkpoint");done=true;}}\n'''.replace('\\n','\n').replace('NL',str(len(lem))).replace('LEMS','LEMS')
  fn=fn.replace('LEMS',arr)
  tr=tr.replace('void Solver::lt_pre_enqueue(Lit p,CRef from){}',fn+'\nvoid Solver::lt_pre_enqueue(Lit p,CRef from){dro_observe(p,from);}')
  (B/'trace.inc').write_text(tr);src.write_text(src.read_text().replace(str(BASE/'trace.inc'),str(B/'trace.inc')));shutil.copyfile(BASE/'driver.cc',B/'driver.cc');shutil.copyfile(td/'CONTROL.cnf',B/'CONTROL.cnf');shutil.copyfile(td/'TREATMENT.cnf',B/'TREATMENT.cnf');(o/'requests.txt').write_text('')
  cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(B/'glucose-3.0'),str(B/'driver.cc'),str(src),str(B/'glucose-3.0/utils/Options.cc'),str(B/'glucose-3.0/utils/System.cc'),'-lz','-o',str(B/'run')];r=subprocess.run(cmd,capture_output=True,text=True)
  if r.returncode:
   (o/'compile.stderr').write_text(r.stderr)
   json.dump({'target':n,'status':'DUAL_REASON_UNOBSERVABLE','error':'compile','stderr':r.stderr[-4000:]},open(o/'summary.json','w'));continue
  p=subprocess.run([str(B/'run'),str(B/'TREATMENT.cnf'),str(o/'TREATMENT.drup'),'1000000','TREATMENT',str(o),str(o/'requests.txt')],capture_output=True,text=True,timeout=240)
  st=None
  if p.returncode==0:st=json.loads(next(x for x in reversed(p.stdout.splitlines()) if x.startswith('{')))
  ck=subprocess.run(['/private/tmp/satfinding-drat-trim',str(B/'TREATMENT.cnf'),str(o/'TREATMENT.drup')],capture_output=True,text=True) if st else None
  ev=o/'dual_reason.json'; row=dict(target=n,status='FOUND' if ev.exists() else 'NO_DUAL_REASON_EVENT',proof_verified=bool(ck and ck.returncode==0 and 'VERIFIED' in ck.stdout),stats=st)
  if ev.exists():row['event']=json.load(open(ev))
  json.dump(row,open(o/'summary.json','w'),indent=2);print(n,row['status'],flush=True)
 rows=[json.load(open(x/'summary.json')) for x in sorted(OUT.iterdir()) if x.is_dir()];json.dump({'targets':rows,'forks_executed':0,'t5_excluded':True},open(OUT/'cohort_summary.json','w'),indent=2)
if __name__=='__main__':main()
