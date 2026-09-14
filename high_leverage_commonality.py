"""Frozen first-five unit episodes on T8/T10/T13; keep every outcome."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/high_leverage_commonality').resolve()
BUILD=Path('/private/tmp/satfinding-high-leverage-commonality')
BASE=Path('/private/tmp/satfinding-native-cdcl')
TARGETS=['T8','T10','T13']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def chash(c):return hashlib.sha256((' '.join(map(str,sorted(c)))+' 0\n').encode()).hexdigest()

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 for rel in ['mtl/Heap.h','core/BoundedQueue.h']:
  shutil.copy2(Path('/private/tmp/satfinding-l1-l2-latent/glucose-3.0')/rel,root/rel)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void     uncheckedEnqueue',
  '    void hc_register(CRef);\n    void hc_gc();\n    unsigned long long hc_state_hash();\n    void hc_before_enqueue();\n    void hc_dequeue(Lit);\n    void hc_conflict(CRef);\n    void hc_observe();\n    void     uncheckedEnqueue');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text();s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include "'+str(Path('high_leverage_commonality.inc').resolve())+'"')
 for anchor in ['CRef cr = ca.alloc(ps, false);','CRef cr = ca.alloc(learnt_clause, true);']:s=replace_once(s,anchor,anchor+'\n        hc_register(cr);')
 s=replace_once(s,'void Solver::removeClause(CRef cr) {','void Solver::removeClause(CRef cr) {\n    hc_ids.erase(cr);')
 s=replace_once(s,'    relocAll(to);','    relocAll(to);\n    hc_gc();')
 s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    hc_before_enqueue();\n    assigns[var(p)] = lbool(!sign(p));')
 s=replace_once(s,'    trail.push_(p);','    trail.push_(p);\n    hc_observe();')
 s=replace_once(s,"        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.","        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.\n        hc_dequeue(p);")
 s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;','\t  conflicts++; conflictC++;conflictsRestarts++;\n          hc_conflict(confl);');cc.write_text(s)
 driver=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {',
  '#include <stdexcept>\n#include <string>\nextern void hc_init(const char*,int);\nextern void hc_finish();\nint main(int argc, char **argv) {')
 driver=driver.replace('argc != 4','argc != 6').replace('    auto start =','    hc_init(argv[4],atoi(argv[5]));\n    auto start =')
 driver=driver.replace('    Glucose::lbool result = solver.solveLimited(assumptions);','    Glucose::lbool result;std::string failure;\n    try{result=solver.solveLimited(assumptions);}catch(const std::runtime_error& e){failure=e.what();}')
 driver=driver.replace('    printf("{','    if(!failure.empty())status=failure.c_str();\n    printf("{').replace('    return 0;','    hc_finish();\n    return failure.empty()?0:42;');(BUILD/'driver.cc').write_text(driver)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('high_leverage_commonality.inc'),cc,h,BUILD/'driver.cc']},'base_build':json.loads((BASE/'build.json').read_text())})

def run(target,index):
 d=OUT/target;tag='BASELINE' if index==0 else f'INTERVENTION_{index}';proof=d/(tag+'.drup')
 cmd=[str(BUILD/'run'),str(d/'input.cnf'),str(proof),'1000000',str(d/(tag+'.events.jsonl')),str(index)]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=240);(d/(tag+'.stdout.txt')).write_text(p.stdout+p.stderr)
 events=[json.loads(x) for x in (d/(tag+'.events.jsonl')).read_text().splitlines()] if (d/(tag+'.events.jsonl')).exists() else []
 try:stats=json.loads(next(x for x in reversed(p.stdout.splitlines()) if x.startswith('{')))
 except StopIteration:stats={'status':'PROCESS_FAILURE','returncode':p.returncode}
 verified=False
 if stats['status']=='UNSAT':
  c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(d/'input.cnf'),str(proof)],capture_output=True,text=True,timeout=240);(d/(tag+'.proof_check.txt')).write_text(c.stdout+c.stderr);verified=c.returncode==0 and 's VERIFIED' in c.stdout
 if proof.exists():
  with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
 for e in events:
  if 'reason_literals' in e:e['reason_hash_sha256']=chash(e['reason_literals'])
  if 'clause_literals' in e:e['clause_hash_sha256']=chash(e['clause_literals'])
 result={'target':target,'route':tag,'stats':stats,'proof_validation':'VERIFIED' if verified else 'NOT_VERIFIED','proof_sha256':sha(proof) if proof.exists() else None,'events':events,'command':cmd}
 dump(d/(tag+'.result.json'),result);print(target,tag,json.dumps(stats),verified,flush=True);return result

def main():
 OUT.mkdir(exist_ok=False)
 inputs={}
 for t in TARGETS:
  d=OUT/t;d.mkdir();src=Path('results/persistent_imprint_replication/T6_T14')/t/'CONTROL.cnf';shutil.copy2(src,d/'input.cnf');inputs[t]={'source':str(src),'sha256':sha(d/'input.cnf')}
 dump(OUT/'protocol.json',{'targets':TARGETS,'inputs':inputs,'selection':'First5 newly native-layout-eligible true-unit clause/literal episodes observed after each completed native enqueue. At a shared state, ascending stable allocation ID. A continuously eligible pair is counted once; rearm only after an observed ineligible state. No conflict/literal/feature filtering.','stable_ids':'1-based clause allocation order, never reused, updated across GC','intervention':'One native uncheckedEnqueue at its baseline episode; afterward ordinary deterministic solver. No heuristic changes.','frozen_pre_features':['pending queue length','almost-unit neighbors','clause fanout','binary implication fanout','antecedent levels','literal activity','heap array position','conflict/decision/level/trail/qhead','literal and reason ID/hash/length'],'frozen_post_features':['dequeued before next conflict','dequeue ordinal','horizon after dequeue','direct enqueues during candidate processing','all enqueues after candidate dequeue','first conflict changed'],'definitions':{'high_leverage':'abs((ops/base_ops)-1)>=0.10','almost_unit':'clause contains candidate variable, no true literals, exactly2 unassigned','clause_fanout':'active clauses containing candidate variable','binary_implication_fanout':'active binary clauses containing negation of candidate signed literal','horizon':'observed dequeue count from after candidate dequeue to first conflict, excluding candidate itself; null if not dequeued','direct_downstream':'enqueue calls during processing candidate, before next dequeue','default_action_position':'after fully completed enqueue; earliest selected event no ordinary pending enqueue invalidated','invalid':'retain failures and absent opportunities; never replace a slot'},'post_features_never_used_for_selection':True,'no_adaptation':True})
 build();rows=[]
 for t in TARGETS:
  b=run(t,0);old=json.loads((Path('results/persistent_imprint_replication/T6_T14')/t/'summary.json').read_text())['control']['stats']
  assert b['proof_validation']=='VERIFIED' and all(b['stats'][k]==v for k,v in old.items() if k!='seconds')
  ops={e['opportunity']:e for e in b['events'] if e['event']=='OPPORTUNITY'};futures={e['opportunity']:e for e in b['events'] if e['event']=='NEXT_CONFLICT'}
  dump(OUT/t/'selected_opportunities.json',list(ops.values()))
  for i in range(1,6):
   if i not in ops:rows.append({'target':t,'opportunity':i,'valid':False,'status':'NO_OPPORTUNITY'});continue
   r=run(t,i);observed=next((e for e in r['events'] if e['event']=='OPPORTUNITY' and e['opportunity']==i),None)
   future=next((e for e in r['events'] if e['event']=='NEXT_CONFLICT' and e['opportunity']==i),None)
   total=next((e for e in r['events'] if e['event']=='TOTAL'),{})
   valid=r['proof_validation']=='VERIFIED' and observed==ops[i] and total.get('interventions')==1
   delta=(r['stats']['analysis_resolution_steps']/b['stats']['analysis_resolution_steps']-1) if valid else None
   row={'target':t,'opportunity':i,'valid':valid,'status':r['stats']['status'],'baseline_ops':b['stats']['analysis_resolution_steps'],'ops':r['stats'].get('analysis_resolution_steps'),'conflicts':r['stats'].get('conflicts'),'decisions':r['stats'].get('decisions'),'propagations':r['stats'].get('propagations'),'proof_validation':r['proof_validation'],'relative_ops_delta_percent':None if delta is None else 100*delta,'HIGH_LEVERAGE':None if delta is None else abs(delta)>=.1,'same_deterministic_pre_state':observed==ops[i],**{k:v for k,v in ops[i].items() if k not in ['event','opportunity']}}
   row.update({k:v for k,v in (future or {}).items() if k not in ['event','opportunity','conflict','clause_literals']});row['first_conflict_changed']=future['clause_hash_sha256']!=futures[i]['clause_hash_sha256'] if future and i in futures else None
   rows.append(row);dump(OUT/t/(f'INTERVENTION_{i}.comparison.json'),row)
  dump(OUT/'partial_results.json',rows)
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/'all_interventions.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})
 dump(OUT/'summary.json',{'rows':rows,'targets':TARGETS,'high_leverage_threshold_percent':10,'checker_sha256':sha('/private/tmp/satfinding-drat-trim')})

if __name__=='__main__':main()
