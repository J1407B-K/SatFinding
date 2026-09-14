"""Build a separate observation-only binary, preserving the frozen backend."""
from pathlib import Path
import shutil
import subprocess
import json
from build_native_cdcl import replace_once
from evaluation_oracle_run import sha

BUILD=Path('/private/tmp/satfinding-gold-mechanism')
BASE=Path('/private/tmp/satfinding-native-cdcl')

def build():
    BUILD.mkdir(exist_ok=True);root=BUILD/'glucose-3.0'
    shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
    source=root/'core/Solver.cc';s=source.read_text()
    s=replace_once(s,'using namespace Glucose;', 'using namespace Glucose;\n#include "'+str(Path('gold_mechanism_trace.inc').resolve())+'"')
    s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));',
        '    gm_enqueue(p,from,ca,decisionLevel(),conflicts);\n    assigns[var(p)] = lbool(!sign(p));')
    s=replace_once(s,'        if (p != lit_Undef) SF_COUNT(sf_analysis);',
        '        gm_analysis(c,p,conflicts);\n        if (p != lit_Undef) SF_COUNT(sf_analysis);')
    s=s.replace('        SF_COUNT(sf_redundancy);','        gm_analysis(c,lit_Undef,conflicts,true);\n        SF_COUNT(sf_redundancy);')
    s=replace_once(s,'CRef Solver::propagate()\n{','CRef Solver::propagate()\n{\n    gm_bcp=true;')
    s=replace_once(s,'        num_props++;','        num_props++; ++gm_dequeues;')
    s=replace_once(s,'return wbin[k].cref;','gm_bcp=false; return wbin[k].cref;')
    s=replace_once(s,'    return confl;','    gm_bcp=false; return confl;')
    s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;',
        '\t  conflicts++; conflictC++;conflictsRestarts++;\n          gm_conflict(ca[confl],decisionLevel(),conflicts,propagations,decisions,sf_analysis,trail.size());')
    s=replace_once(s,'            cancelUntil(backtrack_level);',
        '            gm_learn(learnt_clause,decisionLevel(),backtrack_level,nblevels,conflicts,sf_analysis,activity);\n            cancelUntil(backtrack_level);')
    s=replace_once(s,'                next = pickBranchLit();',
        '                next = pickBranchLit();\n                gm_decision(next,decisionLevel()+1,conflicts,decisions);')
    s=replace_once(s,'\t    cancelUntil(bt);',
        '\t    fprintf(gm_out,"{\\"t\\":\\"R\\",\\"c\\":%llu,\\"dl\\":%d,\\"start\\":%llu}\\n",(unsigned long long)conflicts,decisionLevel(),(unsigned long long)starts);\n\t    cancelUntil(bt);')
    source.write_text(s)
    driver=Path('native_cdcl.cc').read_text()
    driver=driver.replace('int main(int argc, char **argv) {','extern void gm_init(const char*,const char*);\nextern void gm_finish();\nint main(int argc, char **argv) {')
    driver=driver.replace('argc != 4','argc != 6')
    driver=driver.replace('    auto start =','    gm_init(argv[4],argv[5]);\n    auto start =')
    driver=driver.replace('    return 0;','    gm_finish();\n    return 0;')
    (BUILD/'driver.cc').write_text(driver)
    cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'trace')]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)
    return dict(command=cmd,binary_sha256=sha(BUILD/'trace'),source_sha256=sha(source),
        baseline_binary_sha256=sha(BASE/'counted'),baseline_source_sha256=sha(BASE/'glucose-3.0/core/Solver.cc'),
        observer_sha256=sha('gold_mechanism_trace.inc'),builder_sha256=sha(__file__))

if __name__=='__main__':print(json.dumps(build(),indent=2))
