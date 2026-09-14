"""Two unprimed routes, one clause and at most one legal early enqueue."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/l2_priming_vs_trigger').resolve()
BASE=Path('/private/tmp/satfinding-native-cdcl')
BUILD=Path('/private/tmp/satfinding-l2-priming-vs-trigger')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def jhash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 # Existing exact-state dump helpers only, with no former intervention hooks.
 for rel in ['mtl/Heap.h','core/BoundedQueue.h']:
  shutil.copy2(Path('/private/tmp/satfinding-l2-single-conflict/glucose-3.0')/rel,root/rel)
 local=Path('/private/tmp/satfinding-l2-single-conflict/local.inc').read_text();local=local[:local.index('// Bounded to previous/key/following')]
 (BUILD/'observe.inc').write_text(local+'\n'+Path('l2_priming_vs_trigger.inc').read_text())
 h=root/'core/Solver.h';s='#include <string>\n#include <cstdio>\n'+h.read_text()
 s=replace_once(s,'    void     uncheckedEnqueue',
  '    void lt_snapshot(const std::string&);\n    void lt_restart_json(FILE*);\n'
  '    void ut_register(CRef);\n    void ut_note(const char*,Lit);\n    void ut_pre(Lit);\n'
  '    void ut_dequeue(Lit);\n    void ut_check(const char*,bool);\n    void     uncheckedEnqueue');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text()
 s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include <stdexcept>\n#include "'+str(BUILD/'observe.inc')+'"')
 s=replace_once(s,'        CRef cr = ca.alloc(ps, false);','        CRef cr = ca.alloc(ps, false);\n        ut_register(cr);')
 s=replace_once(s,'void Solver::removeClause(CRef cr) {','void Solver::removeClause(CRef cr) {\n    if(cr==ut_clause)ut_clause=CRef_Undef;')
 s=replace_once(s,'    relocAll(to);','    relocAll(to);\n    if(ut_clause!=CRef_Undef)ut_clause=ca[ut_clause].relocation();')
 s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    ut_pre(p);\n    assigns[var(p)] = lbool(!sign(p));')
 s=replace_once(s,'    trail.push_(p);','    trail.push_(p);\n    ++ut_event;ut_check("POST_ENQUEUE",true);')
 s=replace_once(s,'        trail_lim.shrink(trail_lim.size() - level);','        trail_lim.shrink(trail_lim.size() - level);\n        ++ut_event;ut_check("POST_BACKTRACK",false);')
 s=replace_once(s,'        CRef confl = propagate();','        ut_check("SEARCH_BEFORE_PROPAGATE",true);\n        CRef confl = propagate();')
 s=replace_once(s,"        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.","        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.\n        ut_dequeue(p);")
 cc.write_text(s)
 driver=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {','extern void ut_init(const char*,bool);\nextern void ut_finish();\nint main(int argc, char **argv) {')
 driver=driver.replace('argc != 4','argc != 6').replace('    auto start =','    ut_init(argv[4],atoi(argv[5])!=0);\n    auto start =').replace('    return 0;','    ut_finish();\n    return 0;')
 (BUILD/'driver.cc').write_text(driver)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'source_sha256':{str(p):sha(p) for p in [Path(__file__),Path('l2_priming_vs_trigger.inc'),BUILD/'observe.inc',cc,h,BUILD/'driver.cc']},'no_L2_injection_code':True})

def run(name,treatment):
 d=OUT/name;d.mkdir(exist_ok=False)
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(d/'proof.drup'),'1000000',str(d),'1' if treatment else '0']
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(d/'stdout.txt').write_text(r.stdout+r.stderr);r.check_returncode()
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')));assert stats['status']=='UNSAT'
 check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(d/'proof.drup')],capture_output=True,text=True,timeout=180)
 (d/'proof_check.txt').write_text(check.stdout+check.stderr);assert check.returncode==0 and 's VERIFIED' in check.stdout
 with gzip.open(d/'proof.drup.gz','wb') as f:f.write((d/'proof.drup').read_bytes())
 events=[json.loads(x) for x in (d/'opportunity.jsonl').read_text().splitlines()]
 snapshots={p.name.split('.')[1]:json.loads(p.read_text()) for p in d.glob('local.*.snapshot.json')}
 result={'route':name,'stats':stats,'proof_validation':'VERIFIED','proof_sha256':sha(d/'proof.drup'),'input_sha256':sha(OUT/'A.cnf'),'usage':events[-1],'command':cmd}
 dump(d/'result.json',result);print(name,json.dumps(stats),json.dumps(events),flush=True)
 return result,{'events':events,'snapshots':snapshots}

def main():
 OUT.mkdir(exist_ok=False);shutil.copy2('results/l2_pulse_window/A.cnf',OUT/'A.cnf')
 dump(OUT/'protocol.json',{'routes':['UNPRIMED_BASELINE','UNPRIMED_EARLY_566'],'no_L2':True,'watched_clause':2589,'unit_condition':'566 UNASSIGNED,567 FALSE,565 FALSE; exact original clause content; native layout requires566 at index0','first_unit_monitor':'After every completed native enqueue and completed backtrack; plus safe search entry before propagate. Backtracking cannot create a unit by assigning false literals, but is monitored explicitly.','safe_intervention_sites':'After a completed enqueue or before search propagation; never in a caller with a pending learned/asserting enqueue. Layout-incompatible states are logged, not rewritten.','once_only':True,'clock':'pre/post enqueue, propagation dequeue, completed backtrack each increments task-local global event','baseline_next_action':'Record first default next enqueue and next propagation dequeue after the safe opportunity; no lookahead simulation','interpretation':{'near174k':'strong evidence C600–655 priming not necessary','near345k':'unprimed context does not reproduce short basin; not proof priming necessary','no_opportunity':'NO_UNPRIMED_TRIGGER_OPPORTUNITY; potential exposure role only'},'no_conflict_alignment':True})
 build();base,ba=run('UNPRIMED_BASELINE',False)
 old=json.loads(Path('results/l1_l2_latent/natural_runs.json').read_text())['A'];assert all(base['stats'][k]==v for k,v in old.items() if k!='seconds')
 treatment,ta=run('UNPRIMED_EARLY_566',True)
 found=treatment['usage']['safe_native_opportunity_found']
 summary={'status':'COMPLETED' if found else 'NO_UNPRIMED_TRIGGER_OPPORTUNITY','baseline_exact_match':True,'routes':[base,treatment],'checker_sha256':sha('/private/tmp/satfinding-drat-trim')}
 if found:
  assert treatment['usage']['interventions']==1 and ba['snapshots']['TRIGGER_PRE']==ta['snapshots']['TRIGGER_PRE']
  pre,post=ta['snapshots']['TRIGGER_PRE'],ta['snapshots']['TRIGGER_POST'];assert pre['trail']+[566]==post['trail']
  summary['identical_unprimed_pre_state']=True
  summary['pre_hashes']={k:jhash(pre[k]) for k in ['assignment','trail','levels','qhead','activity','heap']}
 for audit in [ba,ta]:
  for snap in audit['snapshots'].values():snap['hashes']={k:jhash(snap[k]) for k in ['assignment','trail','levels','qhead','activity','heap']}
 dump(OUT/'summary.json',summary);dump(OUT/'trigger_opportunity.json',{'UNPRIMED_BASELINE':ba,'UNPRIMED_EARLY_566':ta})

if __name__=='__main__':main()
