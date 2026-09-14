import hashlib,json,pathlib,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'results/full_propagation_frontier_observer_v2/validated'
HERE=ROOT/'full_frontier_v2'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def instrument(tree,include):
 hp=tree/'core/Solver.h';s=hp.read_text();s=replace(s,'    void hc_boundary();','    std::string ff_clause(CRef);\n    void ff_snapshot(std::ostream&,bool);\n    void ff_event(const char*,Lit=lit_Undef,CRef=CRef_Undef,const vec<Lit>* =nullptr,int=0,int=0);\n    void hc_boundary();');hp.write_text('#include <ostream>\n'+s)
 cc=tree/'core/Solver.cc';s=cc.read_text();line=next(x for x in s.splitlines() if '#include ' in x and 'observer.inc' in x);s=replace(s,line,'#include "'+str(include)+'"')
 s=replace(s,'    assigns[var(p)] = lbool(!sign(p));','    ff_event("enqueue",p,from);\n    assigns[var(p)] = lbool(!sign(p));')
 s=replace(s,'        Lit            p   = trail[qhead++];','        ff_event("frontier");\n        Lit            p   = trail[qhead++];')
 s=replace(s,'\t    return wbin[k].cref;','            ff_event("step_end",lit_Undef,wbin[k].cref);\n            ff_event("conflict_detected",lit_Undef,wbin[k].cref);\n\t    return wbin[k].cref;')
 s=replace(s,'        ws.shrink(i - j);','        ws.shrink(i - j);\n        ff_event("step_end",lit_Undef,confl);\n        if(confl!=CRef_Undef)ff_event("conflict_detected",lit_Undef,confl);')
 s=replace(s,'    int pathC = 0;','    ff_event("analysis_begin",lit_Undef,confl);\n    int pathC = 0;')
 s=replace(s,'        Clause& c = ca[confl];','        ff_event("analysis_step",p,confl,nullptr,pathC);\n        Clause& c = ca[confl];')
 s=replace(s,'    out_learnt[0] = ~p;','    ff_event("first_uip",p,CRef_Undef,nullptr,index+1,pathC);\n    out_learnt[0] = ~p;')
 anchor='            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);'
 s=replace(s,anchor,anchor+'\n            ff_event("learned_clause",lit_Undef,CRef_Undef,&learnt_clause,backtrack_level,nblevels);\n            ff_event("backtrack_begin",lit_Undef,CRef_Undef,nullptr,backtrack_level);')
 s=replace(s,'            cancelUntil(backtrack_level);','            cancelUntil(backtrack_level);\n            ff_event("analysis_backtrack_complete",lit_Undef,CRef_Undef,nullptr,backtrack_level);')
 s=replace(s,'        trail_lim.shrink(trail_lim.size() - level);','        trail_lim.shrink(trail_lim.size() - level);\n        ff_event("backtrack",lit_Undef,CRef_Undef,nullptr,level);')
 s=replace(s,"            // Increase decision level and enqueue 'next'",'            ff_event("decision",next);\n'+"            // Increase decision level and enqueue 'next'")
 s=replace(s,'    starts++;','    starts++;\n    ff_event("restart");');cc.write_text(s)
def build():
 dest=OUT/'build';tree=dest/'glucose-3.0';shutil.copytree(ROOT/'harness_v3/glucose-3.0',tree,dirs_exist_ok=True)
 obs=(ROOT/'harness_v3/observer.inc').read_text();obs=obs[:obs.index('void Solver::hc_observe(){')]+'void Solver::hc_observe(){}\n'
 obs += '\n#include "'+str(HERE/'observer.inc')+'"\n'
 obs += '\nvoid observer_open(const char*p,bool e){ff_open(p,e);}\nvoid observer_close(){ff_close();}\nstd::string observer_sequences(){return ff_sequence_summary();}\n'
 (dest/'observer.inc').write_text(obs);instrument(tree,dest/'observer.inc')
 cmd=['c++','-O2','-std=c++11','-Wno-deprecated','-I'+str(tree),str(HERE/'driver.cc'),str(tree/'core/Solver.cc'),str(tree/'utils/Options.cc'),str(tree/'utils/System.cc'),'-lz','-o',str(dest/'native')]
 r=subprocess.run(cmd,capture_output=True,text=True);(dest/'stdout.txt').write_text(r.stdout);(dest/'stderr.txt').write_text(r.stderr)
 files=[p for p in tree.rglob('*') if p.is_file() and p.suffix in ['.cc','.h']]+[HERE/'driver.cc',HERE/'observer.inc',HERE/'build.py',dest/'observer.inc']
 m={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip(),'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in files},'command':cmd,'exit_code':r.returncode,'stdout':str(dest/'stdout.txt'),'stderr':str(dest/'stderr.txt'),'compiler':subprocess.check_output(['c++','--version'],text=True),'binary':str(dest/'native')}
 if r.returncode==0:m['binary_sha256']=sha(dest/'native')
 dump(OUT/'BUILD_MANIFEST.json',m);print(r.stderr[-3000:]);r.check_returncode();return m
if __name__=='__main__':build()
