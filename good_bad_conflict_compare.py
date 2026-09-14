"""Fixed four-outcome comparison, same historical interventions."""
import json,os,shutil,subprocess,gzip,csv
from pathlib import Path
from build_native_cdcl import replace_once
from high_leverage_discovery import sha,dump,chash
OUT=Path('results/good_bad_conflict_compare').resolve();BUILD=Path('/private/tmp/satfinding-good-bad-compare')

def build(kind,base):
 dest=BUILD/kind;root=dest/'glucose-3.0';shutil.copytree(base/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'core/Solver.h';s=h.read_text();anchor='    void     uncheckedEnqueue';s=replace_once(s,anchor,'    void gb_enqueue();\n    void gb_dequeue();\n    void gb_visit(Var);\n    void gb_bump(Var);\n    void gb_before(CRef);\n    void gb_heuristic(const char*);\n    void gb_analysis(const vec<Lit>&,int,unsigned);\n    void gb_backtrack(const vec<Lit>&);\n    void gb_end();\n    void gb_decision(Lit);\n'+anchor)
 s=replace_once(s,'inline void Solver::varBumpActivity(Var v, double inc) {','inline void Solver::varBumpActivity(Var v, double inc) {\n    gb_bump(v);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text();anchor='//=================================================================================================';pos=s.index(anchor,s.index('using namespace Glucose;'))
 s=s[:pos]+('\n#define GB_FORK\n' if kind=='bad' else '\n')+'#include "'+str(Path('good_bad_conflict_compare.inc').resolve())+'"\n'+s[pos:]
 for anchor,extra in [('    assigns[var(p)] = lbool(!sign(p));','    gb_enqueue();\n'),("        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.",'')]:
  if extra:s=replace_once(s,anchor,extra+anchor)
  else:s=replace_once(s,anchor,anchor+'\n        gb_dequeue();')
 s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;','\t  conflicts++; conflictC++;conflictsRestarts++;\n          gb_before(confl);')
 s=replace_once(s,'            Lit q = c[j];','            Lit q = c[j];\n            gb_visit(var(q));')
 anchor='            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);';s=replace_once(s,anchor,anchor+'\n            gb_analysis(learnt_clause,backtrack_level,nblevels);')
 s=replace_once(s,'            cancelUntil(backtrack_level);','            cancelUntil(backtrack_level);\n            gb_backtrack(learnt_clause);')
 s=replace_once(s,'            claDecayActivity();','            claDecayActivity();\n            gb_end();')
 s=replace_once(s,"            // Increase decision level and enqueue 'next'","            gb_decision(next);\n            // Increase decision level and enqueue 'next'");cc.write_text(s)
 shutil.copy2(base/'driver.cc',dest/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(dest/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(dest/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/(kind+'.build.log')).write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/(kind+'.build.json'),{'command':cmd,'binary_sha256':sha(dest/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('good_bad_conflict_compare.inc'),h,cc,dest/'driver.cc']}})
 return dest/'run'

def verify(d,stdout,proof,cnf,old):
 stats=next(json.loads(x) for x in reversed(stdout.splitlines()) if x.startswith('{'))
 assert all(stats[k]==v for k,v in old['stats'].items() if k!='seconds'),(stats,old)
 c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(cnf),str(proof)],capture_output=True,text=True,timeout=180);(d/'proof_check.txt').write_text(c.stdout+c.stderr);assert c.returncode==0 and 's VERIFIED' in c.stdout
 with gzip.open(d/'proof.drup.gz','wb') as f:f.write(proof.read_bytes())
 assert sha(proof)==old['proof_sha256']
 return {'stats':stats,'original_counters_match':True,'original_proof_hash_match':True,'proof_validation':'VERIFIED','proof_sha256':sha(proof)}

def main():
 OUT.mkdir(exist_ok=False)
 dump(OUT/'protocol.json',{'routes':{'GOOD_BASELINE':'original_clause_early_prop BEFORE_PROP_BASELINE / REMOVE@655','GOOD_PERTURBED':'original_clause_early_prop ORIGINAL_EARLY_PROP','BAD_BASELINE':'T8 #181 baseline fork','BAD_PERTURBED':'T8 #181 early fork'},'first_changed_conflicts':{'GOOD':656,'BAD':1},'prior_conflict_gate':'Compare rolling canonical conflict sequence hash before selected conflict. Selected conflict canonical hash must differ.','window':'Exactly10 subsequent conflicts, excluding selected conflict. Counts from prior conflict end to current conflict detection.','visited':'Distinct variables inspected in main analyze resolution loop; sequence hash preserves all inspections including repetitions. Excludes minimization traversal.','bumps':'Distinct variables passed to actual varBumpActivity during whole analyze, including native UPDATEVARACTIVITY path.','immediate_propagation':'New enqueue count after selected conflict completes (excluding its own asserting enqueue) until next actual decision. Subsequent learned-unit assertions included.','heuristic':'Activity vector FNV64 and heap hash; K10 native heap array positions, not sorted activity rank; before analysis and after assertion+decay.','subsume_strengthen':'UNAVAILABLE: no existing direct indicator used.','threshold_unchanged':0.10,'no_new_intervention':True})
 good=build('good',Path('/private/tmp/satfinding-original-early-prop'));bad=build('bad',Path('/private/tmp/satfinding-conflict-frontier'))
 good_old=json.loads(Path('results/original_clause_early_prop/summary.json').read_text())['routes'];results={}
 for label,name,tag in [('GOOD_BASELINE','BEFORE_PROP_BASELINE','REMOVE@655'),('GOOD_PERTURBED','ORIGINAL_EARLY_PROP','ORIGINAL_EARLY_PROP')]:
  d=OUT/label;d.mkdir();cnf=Path('results/original_clause_early_prop/A.cnf').resolve();proof=d/'proof.drup'
  cmd=[str(good),str(cnf),str(proof),'1000000',tag,str(d/'pulse.jsonl'),str(d/'events.jsonl'),str(d/'audit.jsonl'),'0',str(d),'0']
  env=dict(os.environ,GB_START='656',GB_OUT=str(d/'metrics.jsonl'));p=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=180);(d/'stdout.txt').write_text(p.stdout+p.stderr);assert p.returncode==0
  results[label]=verify(d,p.stdout,proof,cnf,next(x for x in good_old if x['route']==name));print(label,results[label]['stats'],flush=True)
 d=OUT/'bad_fork';d.mkdir();cnf=Path('results/high_leverage_discovery/T8/input.cnf').resolve();cmd=[str(bad),str(cnf),str(d/'prefix.drup'),'1000000',str(d),'181'];env=dict(os.environ,GB_START='1',GB_OUT=str(d/'metrics'))
 p=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=180);(d/'parent.stdout.txt').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
 old=json.loads(Path('results/conflict_frontier_discovery/full_run_summary.json').read_text())
 for label,role,key in [('BAD_BASELINE','BASELINE','baseline'),('BAD_PERTURBED','EARLY','early')]:
  rd=OUT/label;rd.mkdir();shutil.copy2(d/('metrics.'+role+'.jsonl'),rd/'metrics.jsonl')
  stdout=(d/f'P181_{role}.stdout.txt').read_text();results[label]=verify(rd,stdout,d/f'P181_{role}.drup',cnf,old[key]);print(label,results[label]['stats'],flush=True)
 dump(OUT/'run_validation.json',results)

if __name__=='__main__':main()
