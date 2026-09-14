"""Build a separate observation-only Glucose binary; never edit frozen backend."""
import json
from pathlib import Path
import shutil
import subprocess
from evaluation_oracle_run import sha, dimacs
from build_native_cdcl import replace_once
from oracle_lemma import TARGET
from satcache import normalize

OUT=Path('results/target_local_history')
BUILD=Path('/private/tmp/satfinding-trajectory')


def main():
    BUILD.mkdir(exist_ok=True)
    root=BUILD/'glucose-3.0'
    shutil.copytree('/private/tmp/satfinding-native-cdcl/glucose-3.0',root,dirs_exist_ok=True)
    header=r'''
#include <map>
#include <vector>
#include <algorithm>
std::map<std::vector<int>, int> sf_gold;
std::map<int, unsigned long long> sf_decisions_hist, sf_width, sf_backjump, sf_jump_distance;
std::map<int, unsigned long long> sf_gold_enqueue, sf_gold_analysis;
std::vector<int> sf_prefix;
unsigned long long sf_decision_hash=1469598103934665603ULL;
'''
    source=root/'core/Solver.cc'
    s=header+source.read_text()
    anchor='using namespace Glucose;'
    helper=r'''
int sf_gold_id(const Clause& c) {
    if(c.learnt()) return -1;
    std::vector<int> key;
    for(int i=0;i<c.size();++i) key.push_back((var(c[i])+1)*(sign(c[i])?-1:1));
    std::sort(key.begin(),key.end());
    auto it=sf_gold.find(key);
    return it==sf_gold.end()?-1:it->second;
}
void sf_hist(const char* name, const std::map<int,unsigned long long>& values) {
    printf(",\"%s\":{",name); bool first=true;
    for(auto x:values) { printf("%s\"%d\":%llu",first?"":",",x.first,x.second); first=false; }
    printf("}");
}
void sf_report() {
    printf("{\"trajectory\":true,\"decision_hash\":\"%llu\"",sf_decision_hash);
    sf_hist("decision_variables",sf_decisions_hist); sf_hist("learned_width",sf_width);
    sf_hist("backjump_level",sf_backjump); sf_hist("backjump_distance",sf_jump_distance);
    sf_hist("gold_reason_enqueue",sf_gold_enqueue); sf_hist("gold_analysis_antecedent",sf_gold_analysis);
    printf(",\"decision_prefix\":[");
    for(unsigned i=0;i<sf_prefix.size();++i) printf("%s%d",i?",":"",sf_prefix[i]);
    printf("]}\n");
}
'''
    s=replace_once(s,anchor,anchor+'\n'+helper)
    s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));',
        '    if(from != CRef_Undef) { int id=sf_gold_id(ca[from]); if(id>=0) ++sf_gold_enqueue[id]; }\n    assigns[var(p)] = lbool(!sign(p));')
    s=replace_once(s,'        if (p != lit_Undef) SF_COUNT(sf_analysis);',
        '        { int id=sf_gold_id(c); if(id>=0) ++sf_gold_analysis[id]; }\n        if (p != lit_Undef) SF_COUNT(sf_analysis);')
    anchor='            cancelUntil(backtrack_level);'
    s=replace_once(s,anchor,'            ++sf_width[learnt_clause.size()]; ++sf_backjump[backtrack_level];\n'
        '            ++sf_jump_distance[decisionLevel()-backtrack_level];\n'+anchor)
    anchor='                next = pickBranchLit();'
    s=replace_once(s,anchor,anchor+'\n                if(next != lit_Undef) { int v=var(next)+1; ++sf_decisions_hist[v];\n'
        '                  int signed_v=sign(next)?-v:v; if(sf_prefix.size()<128) sf_prefix.push_back(signed_v);\n'
        '                  sf_decision_hash=(sf_decision_hash^(unsigned long long)(signed_v+100000))*1099511628211ULL; }')
    source.write_text(s)
    driver=Path('native_cdcl.cc').read_text()
    driver='#include <map>\n#include <vector>\n#include <fstream>\n#include <algorithm>\n'+driver
    driver=driver.replace('int main(int argc, char **argv) {',
        'extern std::map<std::vector<int>,int> sf_gold;\nextern void sf_report();\nint main(int argc, char **argv) {')
    driver=driver.replace('argc != 4','argc != 5')
    driver=driver.replace('    auto start =',
        '    std::ifstream gold(argv[4]); int id,lit; while(gold>>id) { std::vector<int> c; while(gold>>lit && lit) c.push_back(lit); std::sort(c.begin(),c.end()); sf_gold[c]=id; }\n    auto start =')
    driver=driver.replace('    return 0;','    sf_report();\n    return 0;')
    (BUILD/'driver.cc').write_text(driver)
    cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),
         str(BUILD/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),
         '-lz','-o',str(BUILD/'trajectory')]
    build_command=cmd.copy()
    subprocess.run(cmd,check=True,capture_output=True)
    cnf=normalize(json.loads(TARGET.read_text())['cnf'])
    templates=json.loads(Path('results/oracle_lemma/metadata.json').read_text())['template_lemmas']
    roots=json.loads((OUT/'classification.json').read_text())
    (BUILD/'gold.txt').write_text(''.join(str(r['id'])+' '+' '.join(map(str,r['clause']))+' 0\n' for r in roots))
    rows=[]
    for route,extra in [('TEMPLATE',[]),('Gold64',[r['clause'] for r in roots])]:
        path=BUILD/f'{route}.cnf'
        dimacs(path,list(cnf)+templates+extra)
        for binary in ('original','trajectory'):
            cmd=([str(BUILD/'trajectory'),str(path),'/dev/null','1000000',str(BUILD/'gold.txt')]
                 if binary=='trajectory' else ['/private/tmp/satfinding-native-cdcl/counted',str(path),'/dev/null','1000000'])
            p=subprocess.run(cmd,capture_output=True,text=True,check=True)
            parsed=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
            rows.append(dict(route=route,binary=binary,stats=parsed[0],trajectory=parsed[1] if len(parsed)>1 else None))
        a,b=rows[-2]['stats'],rows[-1]['stats']
        assert {k:v for k,v in a.items() if k!='seconds'}=={k:v for k,v in b.items() if k!='seconds'}
    (OUT/'trajectory.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'trajectory_build.json').write_text(json.dumps(dict(build_command=build_command,
        source_sha256=sha(source),driver_sha256=sha(BUILD/'driver.cc'),
        binary_sha256=sha(BUILD/'trajectory'),builder_sha256=sha(__file__),
        counters_match=True,scope='nonlearned Gold clause contents; enqueue reasons and first-UIP antecedents'),indent=2))
    print('trajectory counters match original',flush=True)


if __name__=='__main__': main()
