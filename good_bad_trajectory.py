"""Freeze existing sets, collect strictly early prefixes, then audit/join outcomes."""
from collections import Counter
import gzip
import json
from pathlib import Path
import shutil
import subprocess
from statistics import mean
from time import perf_counter
from build_native_cdcl import replace_once
from evaluation_oracle_run import sha,dimacs
from oracle_lemma import prepare
from unseen_selector import dump

OUT=Path('results/good_bad_trajectory')
BUILD=Path('/private/tmp/satfinding-good-bad')
BASE=Path('/private/tmp/satfinding-native-cdcl')
BASESETS=('TEMPLATE','GOLD64','RANKED64','SHORTEST64','USED64','RANDOM64_17','RANDOM64_29','RANDOM64_43')
PAIRS=('L1','L2','L1_L2','L1_L2_L3')

def build():
    BUILD.mkdir(exist_ok=True);root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
    hp=root/'mtl/Heap.h';s=hp.read_text().replace('namespace Glucose {','namespace Glucose {\nextern unsigned long long gb_heap_insert,gb_heap_pop,gb_heap_decrease,gb_heap_moves;')
    s=replace_once(s,'    void decrease  (int n) {','    void decrease  (int n) { ++gb_heap_decrease;')
    s=replace_once(s,'    void insert(int n)\n    {','    void insert(int n)\n    {\n        ++gb_heap_insert;')
    s=replace_once(s,'    int  removeMin()\n    {','    int  removeMin()\n    {\n        ++gb_heap_pop;')
    s=replace_once(s,'            heap[i]          = heap[p];','            ++gb_heap_moves; heap[i]          = heap[p];')
    s=replace_once(s,'            heap[i]          = heap[child];','            ++gb_heap_moves; heap[i]          = heap[child];');hp.write_text(s)
    header=root/'core/Solver.h';header.write_text(replace_once(header.read_text(),'    Lit      pickBranchLit    ();','    void gb_snapshot(int,unsigned,int);\n    Lit      pickBranchLit    ();'))
    source=root/'core/Solver.cc';s=source.read_text()
    s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include "'+str(Path('good_bad_trajectory_trace.inc').resolve())+'"')
    s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    gb_enqueue(from,ca);\n    assigns[var(p)] = lbool(!sign(p));')
    s=replace_once(s,'        if (p != lit_Undef) SF_COUNT(sf_analysis);','        gb_visit(c,0);\n        if (p != lit_Undef) SF_COUNT(sf_analysis);')
    s=s.replace('        SF_COUNT(sf_redundancy);','        gb_visit(c,1);\n        SF_COUNT(sf_redundancy);')
    s=replace_once(s,'CRef Solver::propagate()\n{','CRef Solver::propagate()\n{\n    gb_bcp=true;')
    s=replace_once(s,'        num_props++;','        num_props++; ++gb_dequeues;')
    s=replace_once(s,'return wbin[k].cref;','gb_bcp=false; return wbin[k].cref;')
    s=replace_once(s,'    return confl;','    gb_bcp=false; return confl;')
    s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;','\t  conflicts++; conflictC++;conflictsRestarts++;\n          gb_visit(ca[confl],2);')
    s=replace_once(s,'            cancelUntil(backtrack_level);','            gb_snapshot(learnt_clause.size(),nblevels,backtrack_level);\n            if(gb_prefix && conflicts==1000)return l_Undef;\n            cancelUntil(backtrack_level);')
    s=replace_once(s,'                next = pickBranchLit();','                next = pickBranchLit();\n                gb_pick(next);')
    s=replace_once(s,'\t    cancelUntil(bt);','\t    gb_restarts.push_back(conflicts);\n\t    cancelUntil(bt);');source.write_text(s)
    driver=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {','extern void gb_init(const char*,const char*,const char*);\nextern void gb_finish();\nint main(int argc, char **argv) {')
    driver=driver.replace('argc != 4','argc != 7').replace('    auto start =','    gb_init(argv[4],argv[5],argv[6]);\n    auto start =').replace('    return 0;','    gb_finish();\n    return 0;')
    (BUILD/'driver.cc').write_text(driver)
    cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'trace')]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)
    return dict(command=cmd,binary_sha256=sha(BUILD/'trace'),source_sha256=sha(source),heap_sha256=sha(hp),baseline_sha256=sha(BASE/'counted'))

def execute(name,mode):
    trace=BUILD/(name+'.'+mode+'.jsonl')
    p=subprocess.run([str(BUILD/'trace'),str(BUILD/(name+'.cnf')),'/dev/null','1000' if mode=='prefix' else '1000000',str(BUILD/(name+'.map')),str(trace),mode],capture_output=True,text=True,timeout=60,check=True)
    stats=json.loads(next(l for l in reversed(p.stdout.splitlines()) if l.startswith('{')))
    rows=[json.loads(l) for l in trace.read_text().splitlines()]
    assert len([r for r in rows if r['t']=='C'])==1000
    assert [r['n'] for r in rows if r['t']=='S']==[50,100,200,500,1000]
    return stats,rows,trace

def main():
    OUT.mkdir(exist_ok=True);assert not (OUT/'early_frozen.json').exists(),'Do not overwrite early data'
    buildmeta=build();data=prepare()
    available={s['route']:s['ids'] for s in json.loads(Path('results/gold64_anatomy/selections.json').read_text())}
    configs={n:available[n] for n in BASESETS}
    # Use the prior protocol, not result stats, for the four fixed diagnostic IDs.
    prior=json.loads(Path('results/gold_mechanism/frozen.json').read_text())['configs']
    configs.update({n:prior[n] for n in PAIRS})
    depth=[0]*data['h'].leaves
    for s in data['h'].history.steps:depth.append(1+max(depth[s.left],depth[s.right]))
    static={}
    for name,ids in configs.items():
        start=perf_counter();_,clauses,validation=data['h'].materialize(data['cnf'],ids);seconds=perf_counter()-start
        dimacs(BUILD/(name+'.cnf'),list(data['cnf'])+data['templates']+clauses)
        (BUILD/(name+'.map')).write_text(''.join('1 -1 '+' '.join(map(str,c))+' 0\n' for c in data['templates'])+
            ''.join(f'2 {i} '+' '.join(map(str,c))+' 0\n' for i,c in zip(ids,clauses)))
        static[name]=dict(K=len(ids),ids=ids,width_histogram=dict(Counter(len(c) for c in clauses)),
            mean_width=mean(map(len,clauses)) if clauses else 0,mean_depth=mean(depth[i] for i in ids) if ids else 0,
            depth_histogram=dict(Counter(depth[i] for i in ids)),validation_seconds=seconds,
            support_inferences=validation['support_inferences'],input_sha256=sha(BUILD/(name+'.cnf')))
    dump(OUT/'static.json',static)
    dump(OUT/'protocol.json',dict(configs=configs,build=buildmeta,
        sources={str(p):sha(p) for p in (Path(__file__),Path('good_bad_trajectory_trace.inc'),Path('docs/good-bad-trajectory-protocol.md'),
            Path('results/gold64_anatomy/selections.json'),Path('results/gold_mechanism/frozen.json'))},static_sha256=sha(OUT/'static.json')))
    checkpoints=[];frozen={}
    for name in configs:
        stats,rows,path=execute(name,'prefix');assert stats['status']=='UNKNOWN' and stats['conflicts']==1000
        with gzip.open(OUT/(name+'.early.jsonl.gz'),'wb') as f:f.write(path.read_bytes())
        checkpoints += [dict(configuration=name,**r) for r in rows if r['t']=='S']
        frozen[name]=dict(sha256=sha(OUT/(name+'.early.jsonl.gz')),stats=stats)
        print(name,'prefix collected to1000, no completion',flush=True)
    dump(OUT/'checkpoints.json',checkpoints)
    dump(OUT/'early_frozen.json',dict(configurations=frozen,checkpoints_sha256=sha(OUT/'checkpoints.json'),
        all_prefixes_frozen_before_outcome_join=True))
    print('ALL early data frozen; now join existing final labels and audit full shadows',flush=True)
    labels={r['route']:r for r in json.loads(Path('results/gold64_anatomy/summary.json').read_text())}
    oldraw={r['route']:r for r in [json.loads(l) for l in Path('results/gold64_anatomy/raw.jsonl').read_text().splitlines()]}
    pairraw={r['name']:r['stats'] for r in json.loads(Path('results/gold_mechanism/runs.json').read_text())}
    outcomes={};audits={}
    fields=('analysis_resolution_steps','conflicts','decisions','propagations','minimization_reason_visits','binary_minimization_candidates')
    for name in configs:
        old=pairraw[name] if name in PAIRS else oldraw[name]
        stats,rows,_=execute(name,'full');assert stats['status']=='UNSAT'
        assert {k:stats[k] for k in fields}=={k:old[k] for k in fields},name
        with gzip.open(OUT/(name+'.early.jsonl.gz'),'rt') as f:early=[json.loads(l) for l in f]
        assert rows==early,name
        outcomes[name]=dict(total_ops=old['analysis_resolution_steps'],total_conflicts=old['conflicts'],good=old['analysis_resolution_steps']<.9*203623)
        audits[name]=dict(full_counters=stats,prefix_exact_match=True,old_native_counters_match=True)
    dump(OUT/'outcomes.json',outcomes);dump(OUT/'shadow_audit.json',audits)
    print('PASS all12 prefix/full equality and native counters',flush=True)

if __name__=='__main__':main()
