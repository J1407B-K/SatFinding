"""COW-fork local discovery, capped500 per target; full solve only first conflict change."""
import csv,gzip,json,shutil,subprocess
from collections import Counter
from pathlib import Path
import high_leverage_discovery as utils
from build_native_cdcl import replace_once
OUT=Path('results/conflict_frontier_discovery').resolve()
BUILD=Path('/private/tmp/satfinding-conflict-frontier')
OLD=Path('results/high_leverage_discovery').resolve()
sha=utils.sha;dump=utils.dump;chash=utils.chash

def build():
 prior=Path('/private/tmp/satfinding-high-leverage-discovery');root=BUILD/'glucose-3.0';shutil.copytree(prior/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void hc_boundary();','    void hc_boundary();\n    void cf_dequeue(Lit);\n    void cf_conflict(CRef);\n    void cf_analysis(const vec<Lit>&);\n    void cf_decision(Lit);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(Path('high_leverage_discovery.inc').resolve()),str(Path('conflict_frontier_discovery.inc').resolve()))
 for anchor,extra in [("        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.",'\n        cf_dequeue(p);'),('\t  conflicts++; conflictC++;conflictsRestarts++;','\n          cf_conflict(confl);'),('            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);','\n            cf_analysis(learnt_clause);')]:s=replace_once(s,anchor,anchor+extra)
 s=replace_once(s,"            // Increase decision level and enqueue 'next'","            cf_decision(next);\n            // Increase decision level and enqueue 'next'");cc.write_text(s)
 shutil.copy2(prior/'driver.cc',BUILD/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('conflict_frontier_discovery.inc'),h,cc,BUILD/'driver.cc']},'base_build':json.loads((OLD/'build.json').read_text())})

def events(path):return [json.loads(l) for l in path.read_text().splitlines()]
def run_parent(t,d,index):
 d.mkdir(exist_ok=False)
 cmd=[str(BUILD/'run'),str(OLD/t/'input.cnf'),str(d/'prefix.drup'),'1000000',str(d),str(index)]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
 (d/'parent.stdout.txt').write_text(p.stdout+p.stderr);dump(d/'command.json',{'command':cmd,'returncode':p.returncode})
 if p.returncode!=0:raise RuntimeError(f'{t} parent failed: {p.stdout} {p.stderr}')
 es=events(d/'opportunities.jsonl');return es

def traces(d,index):
 pair=[]
 for role in ['BASELINE','EARLY']:
  es=events(d/f'P{index}_{role}.trace.jsonl');pre=next(e for e in es if e['event']=='PRE_STATE');loc=next(e for e in es if e['event']=='LOCAL_RESULT')
  loc['conflict_canonical_sha256']=chash(loc['conflict_clause_literals']);loc['learned_canonical_sha256']=chash(loc['learned_clause_literals'])
  assert pre['hash']==pre['fork_parent_hash']
  pair.append({'pre':pre,'local':loc,'events':es})
 assert pair[0]['pre']==pair[1]['pre']
 return pair

def main():
 OUT.mkdir(exist_ok=False)
 dump(OUT/'protocol.json',{'targets':['T8','T10','T13'],'max_opportunities_per_target':500,'inputs':{t:{'path':str(OLD/t/'input.cnf'),'sha256':sha(OLD/t/'input.cnf')} for t in ['T8','T10','T13']},'enumeration':'After completed enqueue and at search-loop entry, scan active original+learned clauses read-only. Enumerate newly eligible clause/literal episodes in observation order; simultaneous candidates ascending stable allocation ID. Continuously eligible episode counted once, rearm after observed ineligible state. No clause/literal/feature filtering.','eligibility':'True unit with unassigned implied literal; binary native layout either index, longer clause implied at index0. No clause reorder.','fork':'Two sequential OS fork children from identical paused baseline parent state and call stack. Parent waits without solver mutation; local output streams differ only. Observer/child metadata excluded from solver state. Each child rechecks pre-state fingerprint; perturbation child audits unit reason before sole uncheckedEnqueue.','local_stop':'Immediately after analyze returns learned clause for next conflict; no backtracking/next decision/full UNSAT search in local children. Parent resumes unchanged baseline solely to enumerate next episode.','selection':'First conflict canonical-literal change; L3 if learned canonical also differs. Freeze before inspecting any full-run cost.','classification':'L0 if dequeue/conflict/learned identical; L1 dequeue differs with same conflict and learned; L2 conflict differs with same learned; L3 learned differs, all flags retained. Stop criterion requires conflict difference.','full':'Only first selected event; rerun shared deterministic prefix then OS fork full baseline+one early enqueue children. Copy exact proof prefix, preserve certifiedUNSAT code path.','high_leverage':'abs(ops/base_ops-1)>=0.10','no_extension':True})
 build();rows=[];selected=None;target_results={}
 for t in ['T8','T10','T13']:
  d=OUT/t;es=run_parent(t,d,0);ops=[e for e in es if e['event']=='OPPORTUNITY'];stop=next((e for e in es if e['event']=='STOP'),{'status':'TRAJECTORY_EXHAUSTED'})
  assert len(ops)<=500
  for o in ops:
   i=o['opportunity'];assert i==len([r for r in rows if r['target']==t])+1
   o['reason_canonical_sha256']=chash(o['reason_literals']);pair=traces(d,i);a,b=[x['local'] for x in pair]
   assert pair[0]['pre']['hash']==o['pre_state_fnv64']
   assert len([e for e in pair[0]['events'] if e['event']=='EARLY_ENQUEUE'])==0
   ee=[e for e in pair[1]['events'] if e['event']=='EARLY_ENQUEUE'];assert len(ee)==1 and ee[0]['global_enqueue']==o['global_enqueue']+1
   pd=a['dequeue_literals']!=b['dequeue_literals'];cd=a['conflict_canonical_sha256']!=b['conflict_canonical_sha256'];ld=a['learned_canonical_sha256']!=b['learned_canonical_sha256']
   cls='L3' if ld else 'L2' if cd else 'L1' if pd else 'L0'
   row={'target':t,'opportunity':i,'conflict':o['conflict'],'decision':o['decision'],'level':o['level'],'global_enqueue':o['global_enqueue'],'literal':o['literal'],'reason_id':o['reason_id'],'reason_hash':o['reason_canonical_sha256'],'pre_state_hash':o['pre_state_fnv64'],'propagation_diverged':pd,'conflict_diverged':cd,'learned_diverged':ld,'classification':cls,'baseline_conflict_hash':a['conflict_canonical_sha256'],'early_conflict_hash':b['conflict_canonical_sha256'],'baseline_learned_hash':a['learned_canonical_sha256'],'early_learned_hash':b['learned_canonical_sha256']}
   rows.append(row);dump(d/f'P{i}.comparison.json',{'row':row,'opportunity':o,'baseline':pair[0],'early':pair[1]})
   if cd:
    assert i==len(ops);selected={'target':t,'opportunity':o,'local_pair':pair,'classification':cls,'selection_reason':'FIRST_NEXT_CONFLICT_CANONICAL_CHANGE'}
  target_results[t]={'count':len(ops),'stop':stop,'classifications':dict(Counter(r['classification'] for r in rows if r['target']==t))}
  print(t,target_results[t],flush=True)
  with (OUT/'local_probe_summary.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  if selected:
   assert stop['status']=='SECOND_CONFLICT_PERTURBATION_CASE';dump(OUT/'frozen_event.json',selected);break
 for t in ['T8','T10','T13']:
  if t not in target_results:target_results[t]={'status':'NOT_RUN_STOP_RULE'}
 summary={'targets':target_results,'local_probe_count':len(rows),'selected_event':selected,'stage1_used_final_ops':False,'protocol_sha256':sha(OUT/'protocol.json')}
 dump(OUT/'discovery_summary.json',summary)
 if selected:
  t=selected['target'];o=selected['opportunity'];i=o['opportunity'];d=OUT/'full';es=run_parent(t,d,i)
  assert next(e for e in es if e['event']=='STOP')['status']=='FULL_PAIR_COMPLETED'
  replay=next(e for e in es if e['event']=='OPPORTUNITY');assert all(replay[k]==v for k,v in o.items() if k!='reason_canonical_sha256')
  pair=traces(d,i);runs=[]
  for role,trace,priortrace in zip(['BASELINE','EARLY'],pair,selected['local_pair']):
   tag=f'P{i}_{role}';stdout=(d/(tag+'.stdout.txt')).read_text();stats=next(json.loads(x) for x in reversed(stdout.splitlines()) if x.startswith('{'))
   assert trace['local']==priortrace['local'] and trace['pre']==priortrace['pre']
   proof=d/(tag+'.drup');c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OLD/t/'input.cnf'),str(proof)],capture_output=True,text=True,timeout=240);(d/(tag+'.proof_check.txt')).write_text(c.stdout+c.stderr)
   verified=c.returncode==0 and 's VERIFIED' in c.stdout;assert stats['status']=='UNSAT' and verified
   with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
   runs.append({'route':'BASELINE_FULL' if role=='BASELINE' else 'EARLY_PROP_FULL','stats':stats,'trace':trace,'next_decision':next((e for e in trace['events'] if e['event']=='NEXT_DECISION'),None),'proof_validation':'VERIFIED','proof_sha256':sha(proof)})
  old=json.loads((OLD/t/'BASELINE.result.json').read_text())['stats'];assert all(runs[0]['stats'][k]==v for k,v in old.items() if k!='seconds')
  delta=100*(runs[1]['stats']['analysis_resolution_steps']/runs[0]['stats']['analysis_resolution_steps']-1)
  full={'frozen_event_sha256':sha(OUT/'frozen_event.json'),'target':t,'opportunity':o,'baseline':runs[0],'early':runs[1],'baseline_matches_original_counters':True,'same_pre_state_by_os_fork':True,'local_replay_matches_stage1':True,'relative_ops_delta_percent':delta,'HIGH_LEVERAGE':abs(delta)>=10}
  dump(OUT/'full_run_summary.json',full);summary['stage2']={'relative_ops_delta_percent':delta,'HIGH_LEVERAGE':abs(delta)>=10,'proofs_verified':2};dump(OUT/'discovery_summary.json',summary)
  print('FULL',json.dumps(summary['stage2']),flush=True)

if __name__=='__main__':main()
