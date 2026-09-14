"""Exact key-state alternate check and frozen ONE_PROP_L2_REASON replication."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/l2_key_propagation_reason_split').resolve()
BASE=Path('/private/tmp/satfinding-l2-single-propagation')
BUILD=Path('/private/tmp/satfinding-l2-key-reason-split')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 pulse=(BASE/'pulse.inc').read_text().replace('CRef cr=ca.alloc(c,false);','CRef cr=ca.alloc(c,false);kp_register(cr);')
 (BUILD/'pulse.inc').write_text(pulse)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    bool sp_skip(CRef);',
  '    void kp_register(CRef);\n    void kp_relocated();\n    void kp_check(Lit,CRef);\n    void kp_read(const Clause&,Lit);\n    bool sp_skip(CRef);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(BASE/'pulse.inc'),str(BUILD/'pulse.inc'))
 anchor='#include "'+str(Path('l2_single_propagation_pulse.inc').resolve())+'"'
 s=replace_once(s,anchor,anchor+'\n#include "'+str(Path('l2_key_propagation_reason_split.inc').resolve())+'"')
 for anchor in ['CRef cr = ca.alloc(ps, false);','CRef cr = ca.alloc(learnt_clause, true);']:
  s=replace_once(s,anchor,anchor+'\n        kp_register(cr);')
 s=replace_once(s,'void Solver::removeClause(CRef cr) {','void Solver::removeClause(CRef cr) {\n    kp_ids.erase(cr);')
 s=replace_once(s,'    relocAll(to);','    relocAll(to);\n    kp_relocated();')
 s=replace_once(s,'    sp_pre(p,from);','    sp_pre(p,from);\n    kp_check(p,from);')
 s=replace_once(s,'        sp_use(c,0);','        kp_read(c,p);\n        sp_use(c,0);');cc.write_text(s)
 driver=(BASE/'driver.cc').read_text().replace('extern void sp_finish();','extern void sp_finish();\nextern void kp_init(const char*);\nextern void kp_finish();')
 driver=driver.replace('argc != 7','argc != 8').replace('    sp_init(argv[4],argv[6]);','    sp_init(argv[4],argv[6]);\n    kp_init(argv[7]);').replace('    sp_finish();','    sp_finish();\n    kp_finish();')
 (BUILD/'driver.cc').write_text(driver)
 compile_build('build')

def compile_build(tag):
 root=BUILD/'glucose-3.0';cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(root/'core/Solver.cc'),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/(tag+'.log')).write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/(tag+'.json'),{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('l2_key_propagation_reason_split.inc'),Path('l2_single_propagation_pulse.inc'),BUILD/'pulse.inc',BUILD/'driver.cc',root/'core/Solver.cc',root/'core/Solver.h']}})

def run(name,extra=[]):
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(OUT/(name+'.drup')),'1000000','ONE_PROP',str(OUT/(name+'.pulse.jsonl')),str(OUT/(name+'.events.jsonl')),str(OUT/(name+'.check.jsonl'))]+extra
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(OUT/(name+'.stdout.txt')).write_text(r.stdout+r.stderr);r.check_returncode()
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')));assert stats['status']=='UNSAT'
 old=json.loads(Path('results/l2_single_propagation_pulse/ONE_PROP.result.json').read_text())
 assert all(stats[k]==v for k,v in old['stats'].items() if k!='seconds')
 proof=OUT/(name+'.drup');check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(proof)],capture_output=True,text=True,timeout=180)
 (OUT/(name+'.proof_check.txt')).write_text(check.stdout+check.stderr);assert check.returncode==0 and 's VERIFIED' in check.stdout
 events=[json.loads(x) for x in (OUT/(name+'.events.jsonl')).read_text().splitlines()];usage=events[-1]
 assert all(usage[k]==0 for k in ['post_disable_new_reason','post_disable_new_propagation','post_disable_new_conflict'])
 assert usage['post_disable_existing_reason_analysis']==1
 with gzip.open(OUT/(name+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
 result={'route':name,'stats':stats,'proof_validation':'VERIFIED','proof_sha256':sha(proof),'input_sha256':sha(OUT/'A.cnf'),'usage':usage,'command':cmd,'exact_baseline_non_time_counters_match':True}
 dump(OUT/(name+'.result.json'),result);print(json.dumps(result),flush=True);return result

def main():
 OUT.mkdir(exist_ok=False);shutil.copy2('results/l2_single_propagation_pulse/A.cnf',OUT/'A.cnf')
 dump(OUT/'protocol.json',{'target':'C655 completed, decision827, level12, first enqueue566 by L2','stage1':'Readonly scan exact pre-enqueue state; candidate count means all live non-L2 clauses scanned; logical and native-layout counts separately','selection':'minimum monotonically assigned clause allocation ID among layout-compatible true unit clauses; observer IDs survive GC','no_layout_reordering':True,'stage2':'Only if compatible alternate exists; require identical complete target pre-state and same enqueue timing; same future-disable','fallback':'If none, no alternate route; local trace only the unique existing reason analysis conflict and its next decision','interpretation':{'alt_near174k':'L2 specific provenance is not necessary in this case','alt_near345k':'L2 provenance and analysis read important','intermediate':'partial mediation','no_alternate':'observational local analysis only; no sufficiency split conclusion'}})
 build();baseline=run('ONE_PROP_L2_REASON')
 checks=[json.loads(x) for x in (OUT/'ONE_PROP_L2_REASON.check.jsonl').read_text().splitlines()]
 check=checks[0]
 for c in check['candidates']:
  c['hash_sha256']=hashlib.sha256((' '.join(map(str,sorted(c['literals'])))+' 0\n').encode()).hexdigest()
 check['stable_id_definition']='1-based allocation order, preserved over native GC, never reused'
 check['selected']=next((c for c in check['candidates'] if c['id']==check['selected_id']),None)
 dump(OUT/'alternate_reason_check.json',check)
 dump(OUT/'summary.json',{'stage1_status':check['status'],'baseline':baseline,'existing_reason_reads':checks[1:],'alternate_route_executed':False,'fallback_pending':check['status']=='NO_COMPATIBLE_ALT_REASON'})
 print(json.dumps(check,indent=2))

if __name__=='__main__':main()
