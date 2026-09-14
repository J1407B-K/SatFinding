"""Frozen 250-conflict trajectory-wide discovery; no feature-based selection."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once
OUT=Path('results/high_leverage_discovery').resolve()
BUILD=Path('/private/tmp/satfinding-high-leverage-discovery')
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
  '    void hc_register(CRef);\n    void hc_gc();\n    unsigned long long hc_state_hash();\n    void hc_before_enqueue();\n    void hc_boundary();\n    void hc_observe();\n    void     uncheckedEnqueue');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text();s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include "'+str(Path('high_leverage_discovery.inc').resolve())+'"')
 for anchor in ['CRef cr = ca.alloc(ps, false);','CRef cr = ca.alloc(learnt_clause, true);']:s=replace_once(s,anchor,anchor+'\n        hc_register(cr);')
 s=replace_once(s,'void Solver::removeClause(CRef cr) {','void Solver::removeClause(CRef cr) {\n    hc_ids.erase(cr);')
 s=replace_once(s,'    relocAll(to);','    relocAll(to);\n    hc_gc();')
 s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    hc_before_enqueue();\n    assigns[var(p)] = lbool(!sign(p));')
 s=replace_once(s,'    trail.push_(p);','    trail.push_(p);\n    hc_observe();')
 s=replace_once(s,'        CRef confl = propagate();','        hc_boundary();\n        CRef confl = propagate();');cc.write_text(s)
 driver=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {',
  '#include <stdexcept>\n#include <string>\nextern void hc_init(const char*,int);\nextern void hc_finish();\nint main(int argc, char **argv) {')
 driver=driver.replace('argc != 4','argc != 6').replace('    auto start =','    hc_init(argv[4],atoi(argv[5]));\n    auto start =')
 driver=driver.replace('    Glucose::lbool result = solver.solveLimited(assumptions);','    Glucose::lbool result;std::string failure;\n    try{result=solver.solveLimited(assumptions);}catch(const std::runtime_error& e){failure=e.what();}')
 driver=driver.replace('    printf("{','    if(!failure.empty())status=failure.c_str();\n    printf("{').replace('    return 0;','    hc_finish();\n    return failure.empty()?0:42;');(BUILD/'driver.cc').write_text(driver)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('high_leverage_discovery.inc'),cc,h,BUILD/'driver.cc']},'base_build':json.loads((BASE/'build.json').read_text())})

def run(target,bucket):
 d=OUT/target;tag='BASELINE' if bucket==0 else f'EARLY_PROP_C{bucket}';proof=d/(tag+'.drup');log=d/(tag+'.events.jsonl')
 cmd=[str(BUILD/'run'),str(d/'input.cnf'),str(proof),'1000000',str(log),str(bucket)]
 failure=None;rc=None
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=240);stdout=p.stdout;stderr=p.stderr;rc=p.returncode
 except subprocess.TimeoutExpired as e:
  stdout=e.stdout or b'';stderr=e.stderr or b'';failure='RUN_TIMEOUT'
  if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
  if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
 (d/(tag+'.stdout.txt')).write_text(stdout+stderr)
 events=[]
 if log.exists():
  for line in log.read_text().splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:failure=failure or 'TRUNCATED_EVENT_LOG'
 stats=next((json.loads(x) for x in reversed(stdout.splitlines()) if x.startswith('{')),{'status':failure or 'PROCESS_FAILURE'})
 if rc!=0:failure=failure or 'PROCESS_FAILURE'
 verified=False;checker=None
 if stats['status']=='UNSAT':
  try:
   c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(d/'input.cnf'),str(proof)],capture_output=True,text=True,timeout=240)
   (d/(tag+'.proof_check.txt')).write_text(c.stdout+c.stderr);verified=c.returncode==0 and 's VERIFIED' in c.stdout;checker=c.returncode
  except subprocess.TimeoutExpired:failure=failure or 'PROOF_TIMEOUT'
 if proof.exists():
  with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
 for e in events:
  if 'reason_literals' in e:e['reason_hash_sha256']=chash(e['reason_literals'])
 result={'target':target,'route':tag,'stats':stats,'failure':failure,'returncode':rc,'proof_validation':'VERIFIED' if verified else 'NOT_VERIFIED','checker_returncode':checker,'proof_sha256':sha(proof) if proof.exists() else None,'events':events,'command':cmd}
 dump(d/(tag+'.result.json'),result);print(target,tag,json.dumps(stats),verified,flush=True);return result

def write_csv(rows,path):
 fields=['target','sample_conflict_bucket','actual_conflict','decision','level','global_enqueue','clause_id','clause_hash','implied_literal','baseline_ops','intervention_ops','relative_ops_delta_percent','HIGH_LEVERAGE','conflicts','decisions','propagations','status','proof_validation','valid','same_deterministic_pre_state','failure']
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
 OUT.mkdir(exist_ok=False);inputs={}
 for t in TARGETS:
  src=Path('results/persistent_imprint_replication/T6_T14')/t/'CONTROL.cnf';inputs[t]={'source':str(src),'sha256':sha(src)}
 protocol={'targets_in_order':TARGETS,'inputs':inputs,'spacing':250,'buckets':'Every positive multiple of250 <= final baseline conflicts, frozen by baseline trajectory before any intervention results.','boundary':'Activate bucket at first search-loop entry after the bucket conflict completes, before propagate. Thereafter inspect after every completed enqueue.','selection':'First observed live true-unit native-layout-compatible clause, implied literal unassigned; tie lowest stable allocation ID. All original and learned clauses eligible. No features or literal filters.','native_layout':'Binary either position (native binary reason handling); nonbinary implied literal must be index0. Never reorder.','overlapping_buckets':'If several buckets await a first opportunity, same first eligible state serves all; retain separate reruns.','missing':'If no opportunity before baseline termination, record NO_OPPORTUNITY; never replace bucket.','stable_id':'Monotonic clause allocation ID, remapped across GC, never reused.','intervention':'One native uncheckedEnqueue at matched baseline event and state fingerprint; afterward ordinary solver. Watch/heap/qhead/heuristic unchanged by observer.','threshold':'abs(intervention_ops / baseline_ops - 1) >= 0.10','stop':'Complete all baseline-selected buckets for a target; if any valid high-leverage event stop before next target. Choose earliest qualifying bucket, never largest effect.','limits':{'solver_conflict_budget':1000000,'solver_wall_timeout_seconds':240,'proof_wall_timeout_seconds':240},'failure':'Retain process, proof, state mismatch failures; no replacement events.','features_added':False}
 dump(OUT/'protocol.json',protocol);build();rows=[];targets={};selected=None
 for t in TARGETS:
  d=OUT/t;d.mkdir();shutil.copy2(inputs[t]['source'],d/'input.cnf')
  b=run(t,0);old=json.loads((Path('results/persistent_imprint_replication/T6_T14')/t/'summary.json').read_text())['control']['stats']
  matches=all(b['stats'].get(k)==v for k,v in old.items() if k!='seconds')
  if b['failure'] or b['proof_validation']!='VERIFIED' or not matches:
   targets[t]={'status':'BASELINE_FAILURE','baseline_matches':matches,'baseline':b};dump(d/'summary.json',targets[t]);continue
  opportunities={e['bucket']:e for e in b['events'] if e['event']=='OPPORTUNITY'}
  grid=list(range(250,b['stats']['conflicts']+1,250))
  dump(d/'frozen_samples.json',[{'bucket':i,'opportunity':opportunities.get(i),'status':'SELECTED' if i in opportunities else 'NO_OPPORTUNITY'} for i in grid])
  targetrows=[]
  for i in grid:
   o=opportunities.get(i);row={'target':t,'sample_conflict_bucket':i,'baseline_ops':b['stats']['analysis_resolution_steps'],'status':'NO_OPPORTUNITY','valid':False}
   if o:
    r=run(t,i);seen=next((e for e in r['events'] if e['event']=='OPPORTUNITY' and e['bucket']==i),None);total=next((e for e in r['events'] if e['event']=='TOTAL'),{})
    valid=not r['failure'] and r['proof_validation']=='VERIFIED' and seen==o and total.get('interventions')==1
    op=r['stats'].get('analysis_resolution_steps');delta=100*(op/row['baseline_ops']-1) if valid else None
    row.update({'actual_conflict':o['conflict'],'decision':o['decision'],'level':o['level'],'global_enqueue':o['global_enqueue'],'clause_id':o['reason_id'],'clause_hash':o['reason_hash_sha256'],'implied_literal':o['literal'],'intervention_ops':op,'relative_ops_delta_percent':delta,'HIGH_LEVERAGE':abs(delta)>=10 if delta is not None else None,'conflicts':r['stats'].get('conflicts'),'decisions':r['stats'].get('decisions'),'propagations':r['stats'].get('propagations'),'status':r['stats']['status'],'proof_validation':r['proof_validation'],'valid':valid,'same_deterministic_pre_state':seen==o,'failure':r['failure'] or (None if valid else 'VALIDATION_FAILURE')})
   rows.append(row);targetrows.append(row);dump(d/f'C{i}.comparison.json',row)
   write_csv(rows,OUT/'all_samples.csv')
  hits=[r for r in targetrows if r.get('HIGH_LEVERAGE')];targets[t]={'status':'COMPLETE','baseline':b['stats'],'baseline_matches_prior':matches,'baseline_proof':b['proof_validation'],'sample_count':len(grid),'valid_count':sum(r['valid'] for r in targetrows),'high_leverage_count':len(hits),'rows':targetrows}
  write_csv(targetrows,d/'samples.csv');dump(d/'summary.json',targets[t])
  if hits:selected=hits[0];break
 for t in TARGETS:
  if t not in targets:targets[t]={'status':'NOT_RUN_STOP_RULE'}
 summary={'protocol_sha256':sha(OUT/'protocol.json'),'checker_sha256':sha('/private/tmp/satfinding-drat-trim'),'targets':targets,'selected_second_case':selected,'sample_count':len(rows),'valid_count':sum(r['valid'] for r in rows),'high_leverage_count':sum(bool(r.get('HIGH_LEVERAGE')) for r in rows),'complete':all(x['status']!='BASELINE_FAILURE' for x in targets.values())}
 dump(OUT/'discovery_summary.json',summary)

if __name__=='__main__':main()
