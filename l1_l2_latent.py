"""Build and run only the two frozen natural configurations."""
import json
from pathlib import Path
import shutil
import subprocess
from evaluation_oracle_run import sha,dimacs
from build_native_cdcl import replace_once
from unseen_selector import dump

OUT=Path('results/l1_l2_latent')
BUILD=Path('/private/tmp/satfinding-l1-l2-latent')
BASE=Path('/private/tmp/satfinding-native-cdcl')

def build():
    BUILD.mkdir(exist_ok=True);root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
    p=root/'mtl/Heap.h';s=p.read_text();s='#include <cstdio>\n'+s
    s=replace_once(s,'    Heap(const Comp& c) : lt(c) { }',r'''
    unsigned long long lt_hash_state() const {unsigned long long h=1469598103934665603ULL;auto add=[&](int x){for(unsigned k=0;k<sizeof(x);++k)h=(h^((unsigned char*)&x)[k])*1099511628211ULL;};add(heap.size());for(int i=0;i<heap.size();++i)add(heap[i]);add(indices.size());for(int i=0;i<indices.size();++i)add(indices[i]);return h;}
    void lt_dump(FILE* f) const {fprintf(f,"{\"array\":[");for(int i=0;i<heap.size();++i)fprintf(f,"%s%d",i?",":"",heap[i]);fprintf(f,"],\"indices\":[");for(int i=0;i<indices.size();++i)fprintf(f,"%s%d",i?",":"",indices[i]);fprintf(f,"]}");}
    Heap(const Comp& c) : lt(c) { }
''');p.write_text(s)
    p=root/'core/BoundedQueue.h';s=p.read_text();s=replace_once(s,'public:',r'''public:
 unsigned long long lt_hash_state() const {unsigned long long h=1469598103934665603ULL;auto add=[&](unsigned long long x){for(unsigned k=0;k<sizeof(x);++k)h=(h^((unsigned char*)&x)[k])*1099511628211ULL;};add(first);add(last);add(sumofqueue);add(maxsize);add(queuesize);for(int i=0;i<elems.size();++i)add(elems[i]);return h;}
 void lt_dump(FILE* f) const {fprintf(f,"{\"first\":%d,\"last\":%d,\"sum\":%llu,\"max\":%d,\"size\":%d,\"elems\":[",first,last,sumofqueue,maxsize,queuesize);for(int i=0;i<elems.size();++i)fprintf(f,"%s%llu",i?",":"",(unsigned long long)elems[i]);fprintf(f,"]}");}
''');p.write_text(s)
    p=root/'core/Solver.h';s='#include <string>\n'+p.read_text()
    s=replace_once(s,'    Solver();','    Solver();\n    void lt_start();')
    s=replace_once(s,'    Lit      pickBranchLit    ();',r'''
    void lt_snapshot(const std::string&);
    void lt_restart_json(FILE*);
    unsigned long long lt_restart_hash();
    void lt_event(const char*,int,unsigned long long,bool=false);
    void lt_pre_enqueue(Lit,CRef);
    void lt_post_enqueue(Lit,CRef);
    void lt_analysis(const Clause&,Lit,int);
    void lt_bump(Var);
    void lt_watch(const Clause&,Lit,int);
    Lit      pickBranchLit    ();
''')
    s=replace_once(s,'        order_heap.decrease(v); }','        order_heap.decrease(v);\n    lt_bump(v); }');p.write_text(s)
    source=root/'core/Solver.cc';s=source.read_text();s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include "'+str(Path('l1_l2_latent_trace.inc').resolve())+'"\nvoid Solver::lt_start(){lt_event("INIT",0,0);lt_snapshot("initialized");}')
    s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    lt_pre_enqueue(p,from);\n    assigns[var(p)] = lbool(!sign(p));')
    s=replace_once(s,'    trail.push_(p);','    trail.push_(p);\n    lt_post_enqueue(p,from);')
    s=replace_once(s,'        if (p != lit_Undef) SF_COUNT(sf_analysis);','        lt_analysis(c,p,0);\n        if (p != lit_Undef) SF_COUNT(sf_analysis);')
    s=s.replace('        SF_COUNT(sf_redundancy);','        lt_analysis(c,lit_Undef,1);\n        SF_COUNT(sf_redundancy);')
    s=replace_once(s,'            Lit blocker = i->blocker;','            lt_watch(ca[i->cref],p,0);\n            Lit blocker = i->blocker;')
    s=replace_once(s,'        NextClause:;','        NextClause:;\n            lt_watch(c,p,1);')
    s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;','\t  conflicts++; conflictC++;conflictsRestarts++;\n          lt_event("C",0,lt_clause(ca[confl]),lt_l2(ca[confl]));')
    s=replace_once(s,'\t  trailQueue.push(trail.size());','\t  trailQueue.push(trail.size());\n          lt_event("QT",0,0);')
    s=replace_once(s,'            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);','            lt_event("ANALYZE_PRE",0,0);\n            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);\n            lt_event("L",(int)nblevels,lt_learnt(learnt_clause));')
    s=replace_once(s,'\t    sumLBD += nblevels;','\t    sumLBD += nblevels;\n            lt_event("QL",0,0);')
    s=replace_once(s,'            cancelUntil(backtrack_level);','            cancelUntil(backtrack_level);\n            lt_event("BACK",backtrack_level,0);')
    s=replace_once(s,'                next = pickBranchLit();','                lt_event("D_PRE",0,0);\n                next = pickBranchLit();\n                if(next!=lit_Undef)lt_event("D",lt_int(next),0);')
    s=replace_once(s,'\t    cancelUntil(bt);','\t    lt_event("RESTART",bt,0);\n\t    cancelUntil(bt);');source.write_text(s)
    driver=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {','extern void lt_init(const char*,const char*,const char*);\nextern void lt_finish();\nint main(int argc, char **argv) {')
    driver=driver.replace('argc != 4','argc != 7').replace('    auto start =','    lt_init(argv[4],argv[5],argv[6]);\n    auto start =').replace('    gzclose(in);','    gzclose(in);\n    solver.lt_start();').replace('    return 0;','    lt_finish();\n    return 0;')
    (BUILD/'driver.cc').write_text(driver)
    cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'latent')]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)
    return dict(command=cmd,binary_sha256=sha(BUILD/'latent'),baseline_sha256=sha(BASE/'counted'),source_sha256=sha(source))

def execute(name):
    p=subprocess.run([str(BUILD/'latent'),str(BUILD/('A.cnf' if name=='A' else 'B.cnf')),str(BUILD/(name+'.drup')),'1000000',name,str(OUT.resolve()),str(OUT/'requests.txt')],capture_output=True,text=True,timeout=180,check=True)
    stats=json.loads(next(l for l in reversed(p.stdout.splitlines()) if l.startswith('{')))
    assert stats['status']=='UNSAT'
    return stats

def main():
    OUT.mkdir(exist_ok=True);assert not (OUT/'natural_runs.json').exists()
    meta=build();inp=json.loads(Path('results/gold_mechanism/inputs.json').read_text())
    for name,ids in [('A',[24458]),('B',[24458,30149])]:dimacs(BUILD/(name+'.cnf'),inp['cnf']+inp['templates']+[inp['gold'][str(i)] for i in ids])
    (OUT/'requests.txt').write_text('L_199_1\nANALYZE_PRE_656_1\nD_PRE_657_1\n')
    dump(OUT/'protocol.json',dict(build=meta,sources={str(p):sha(p) for p in (Path(__file__),Path('l1_l2_latent_trace.inc'),Path('docs/l1-l2-latent-protocol.md'),Path('results/gold_mechanism/inputs.json'))},inputs={n:sha(BUILD/(n+'.cnf')) for n in ('A','B')}))
    old={r['name']:r['stats'] for r in json.loads(Path('results/gold_mechanism/runs.json').read_text())}
    runs={}
    for name,prior in [('A','L1'),('B','L1_L2')]:
        runs[name]=execute(name)
        assert {k:v for k,v in runs[name].items() if k!='seconds'}=={k:v for k,v in old[prior].items() if k!='seconds'}
        print(name,runs[name],flush=True)
    dump(OUT/'natural_runs.json',runs)

if __name__=='__main__':main()
