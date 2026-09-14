"""One fixed activity+heap transplant, with exact-state and proof audits."""
import gzip
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once
from evaluation_oracle_run import sha,dimacs
from unseen_selector import dump

OUT=Path('results/activity_heap_mediation')
BUILD=Path('/private/tmp/satfinding-activity-heap')
BASE=Path('/private/tmp/satfinding-native-cdcl')

HEAP_METHODS=r'''
    void ah_save(FILE* f) const {
        int n=heap.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&heap[0],sizeof(int),n,f);
        n=indices.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&indices[0],sizeof(int),n,f);
    }
    void ah_copy(vec<int>& h,vec<int>& i) const {heap.copyTo(h);indices.copyTo(i);}
    void ah_restore(const vec<int>& h,const vec<int>& i) {h.copyTo(heap);i.copyTo(indices);}
    bool ah_valid() const {
        for(int k=0;k<heap.size();++k) {
            int v=heap[k];if(v<0 || v>=indices.size() || indices[v]!=k)return false;
            if(k && lt(v,heap[(k-1)/2]))return false;
        }
        for(int v=0;v<indices.size();++v)if(indices[v]!=-1 && (indices[v]<0 || indices[v]>=heap.size() || heap[indices[v]]!=v))return false;
        return true;
    }
    void ah_json(FILE* f) const {
        fprintf(f,"{\"array\":[");for(int k=0;k<heap.size();++k)fprintf(f,"%s%d",k?",":"",heap[k]);
        fprintf(f,"],\"indices\":[");for(int k=0;k<indices.size();++k)fprintf(f,"%s%d",k?",":"",indices[k]);fprintf(f,"]}");
    }
'''

def build():
    BUILD.mkdir(exist_ok=True);root=BUILD/'glucose-3.0'
    shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
    heap=root/'mtl/Heap.h'
    heap.write_text('#include <cstdio>\n'+replace_once(heap.read_text(),'    Heap(const Comp& c) : lt(c) { }','    Heap(const Comp& c) : lt(c) { }\n'+HEAP_METHODS))
    types=root/'core/SolverTypes.h'
    types.write_text(replace_once(types.read_text(),'    OccLists(const Deleted& d) : deleted(d) {}',r'''
    void ah_audit(FILE* f) const {
        int n=occs.size();fwrite(&n,sizeof(n),1,f);
        for(int k=0;k<n;++k){int m=occs[k].size();fwrite(&m,sizeof(m),1,f);if(m)fwrite(&occs[k][0],sizeof(occs[k][0]),m,f);}
        n=dirty.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&dirty[0],sizeof(char),n,f);
        n=dirties.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&dirties[0],sizeof(Idx),n,f);
    }
    OccLists(const Deleted& d) : deleted(d) {}
'''))
    queue=root/'core/BoundedQueue.h'
    queue.write_text(replace_once(queue.read_text(),'public:',r'''public:
 void ah_audit(FILE* f) const {int n=elems.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&elems[0],sizeof(T),n,f);}
'''))
    header=root/'core/Solver.h'
    header.write_text(replace_once(header.read_text(),'    Lit      pickBranchLit    ();','    void ah_hook();\n    void ah_dump(const char*);\n    Lit      pickBranchLit    ();'))
    source=root/'core/Solver.cc';s=source.read_text()
    s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include "'+str(Path('activity_heap_mediation.inc').resolve())+'"')
    s=replace_once(s,'                next = pickBranchLit();','                ah_hook();\n                next = pickBranchLit();\n                ah_decision(next,conflicts,decisions,decisionLevel()+1);')
    s=replace_once(s,'            cancelUntil(backtrack_level);','            ah_learn(learnt_clause,conflicts,sf_analysis,nblevels);\n            cancelUntil(backtrack_level);')
    source.write_text(s)
    driver=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {',
        'extern void ah_init(const char*,const char*);\nextern void ah_finish();\nint main(int argc, char **argv) {')
    driver=driver.replace('argc != 4','argc != 6').replace('    auto start =','    ah_init(argv[4],argv[5]);\n    auto start =').replace('    return 0;','    ah_finish();\n    return 0;')
    (BUILD/'driver.cc').write_text(driver)
    cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'mediation')]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)
    return dict(command=cmd,binary_sha256=sha(BUILD/'mediation'),source_sha256=sha(source),
        baseline_binary_sha256=sha(BASE/'counted'),patched_files={str(p.relative_to(root)):sha(p) for p in (heap,types,queue,header,source)})

def main():
    OUT.mkdir(exist_ok=True);assert not (OUT/'runs.json').exists(),'Do not overwrite experiment'
    meta=build()
    inp=json.loads(Path('results/gold_mechanism/inputs.json').read_text())
    original=json.loads(Path('results/gold_mechanism/runs.json').read_text())
    old={r['name']:r for r in original}
    dump(OUT/'protocol.json',dict(target='n200_T_r01_s7201',routes=['CONTROL','GOLD','GOLD_ACTIVITY_RESET'],
        trigger='decisions==22, conflicts==3, qhead==trail.size(), immediately before pickBranchLit',
        allowed=['activity values (bit-exact doubles)','heap array/order','inverse indices'],
        comparator='Retain reference to current Gold activity vector; no sort/heapify.',
        untouched='All other Solver object bytes/live owned buffers and native counters hashed before/after; search locals inaccessible to hook.',
        no_additional_interventions=True,build=meta,
        sources={str(p):sha(p) for p in (Path(__file__),Path('activity_heap_mediation.inc'),Path('native_cdcl.cc'),Path('results/gold_mechanism/inputs.json'))}))
    runs=[]
    for name in ('CONTROL','GOLD','GOLD_ACTIVITY_RESET'):
        extra=[] if name=='CONTROL' else [v for k,v in sorted(inp['gold'].items(),key=lambda kv:int(kv[0]))]
        cnf=BUILD/(name+'.cnf');proof=BUILD/(name+'.drup')
        dimacs(cnf,inp['cnf']+inp['templates']+extra)
        p=subprocess.run([str(BUILD/'mediation'),str(cnf),str(proof),'1000000',name,str(OUT.resolve())],capture_output=True,text=True,check=True,timeout=60)
        stats=json.loads(next(l for l in reversed(p.stdout.splitlines()) if l.startswith('{')))
        assert stats['status']=='UNSAT'
        if name!='GOLD_ACTIVITY_RESET':
            ref=old['CONTROL' if name=='CONTROL' else 'TREATMENT']['stats']
            assert {k:v for k,v in stats.items() if k!='seconds'}=={k:v for k,v in ref.items() if k!='seconds'}
        check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(cnf),str(proof)],capture_output=True,text=True,timeout=60)
        (OUT/(name+'.proof_check.txt')).write_text(check.stdout+check.stderr)
        assert check.returncode==0 and 'VERIFIED' in check.stdout,(name,check.stdout,check.stderr)
        trace=OUT/(name+'.trace.jsonl')
        with gzip.open(OUT/(name+'.trace.jsonl.gz'),'wb') as f:f.write(trace.read_bytes())
        trace.unlink()
        with gzip.open(OUT/(name+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
        row=dict(name=name,stats=stats,input_sha256=sha(cnf),proof_sha256=sha(proof),
            trace_sha256=sha(OUT/(name+'.trace.jsonl.gz')),proof_checker='drat-trim VERIFIED')
        runs.append(row);dump(OUT/(name+'.result.json'),row)
        print(name,stats,flush=True)
    dump(OUT/'runs.json',runs)

if __name__=='__main__':main()
