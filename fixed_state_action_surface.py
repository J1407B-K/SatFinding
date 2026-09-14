"""All legal actions at the single frozen T10 P226/P227 state."""
import csv,gzip,json,subprocess,shutil
from pathlib import Path
from collections import Counter
from build_native_cdcl import replace_once
import conflict_frontier_discovery as cf
OUT=Path('results/fixed_state_action_surface').resolve()
BUILD=Path('/private/tmp/satfinding-fixed-state-action-surface')
OLD=Path('results/high_leverage_discovery').resolve()
sha=cf.sha;dump=cf.dump;chash=cf.chash;events=cf.events
def build():
 prior=Path('/private/tmp/satfinding-high-leverage-discovery');root=BUILD/'glucose-3.0';shutil.copytree(prior/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void hc_boundary();','    void hc_boundary();\n    void fs_surface();\n    void cf_dequeue(Lit);\n    void cf_conflict(CRef);\n    void cf_analysis(const vec<Lit>&);\n    void cf_decision(Lit);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(Path('high_leverage_discovery.inc').resolve()),str(Path('fixed_state_action_surface.inc').resolve()))
 for anchor,extra in [("        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.",'\n        cf_dequeue(p);'),('\t  conflicts++; conflictC++;conflictsRestarts++;','\n          cf_conflict(confl);'),('            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);','\n            cf_analysis(learnt_clause);')]:s=replace_once(s,anchor,anchor+extra)
 s=replace_once(s,"            // Increase decision level and enqueue 'next'","            cf_decision(next);\n            // Increase decision level and enqueue 'next'");cc.write_text(s)
 shutil.copy2(prior/'driver.cc',BUILD/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('fixed_state_action_surface.inc'),h,cc,BUILD/'driver.cc']},'base_build':json.loads((OLD/'build.json').read_text())})



def writecsv(path,rows):
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def main():
 OUT.mkdir(exist_ok=False)
 dump(OUT/'protocol.json',{'target':'T10','fixed_pre_state_hash':'422271443557180589','existing_events':['T10_P226','T10_P227'],'state_gate':'Original episode226, conflicts0 decisions18 level18 trail263 qhead252 global enqueue263; exact old operational fingerprint required.','snapshot':'One paused parent state. All baseline/action children fork its same memory and stack; verify unchanged operational hash + raw Solver object hash before each fork and in every child, including existing heap+inverse hash. No state reconstruction.','enumeration':'All active original/learned true-unit clauses with unassigned implied literal and compatible native reason layout at S; includes continuously eligible clauses, not only newly eligible episodes.','selection':'Ascending stable clause ID; all if<=32, else first32. Freeze full list before first fork.','action':'One original native uncheckedEnqueue, same literal/reason audit repeated online. No other search changes.','local':'Dequeues to first conflict, conflict+learned canonical hash, then first actual next decision. Deepest changed layer classification, all flags retained.','high_leverage':'abs(delta)>=10%','cost_denominator':'Baseline remaining analysis ops from S; record full counters and prefix ops. Here S is before first conflict, expected prefix analysis ops0.','no_new_state_or_feature':True})
 build();d=OUT/'runs';cf.BUILD=BUILD;es=cf.run_parent('T10',d,226)
 assert next(e for e in es if e['event']=='STOP')['status']=='ACTION_SURFACE_COMPLETED'
 snapshot=next(e for e in es if e['event']=='FROZEN_STATE');actions=[e for e in es if e['event']=='LEGAL_ACTION'];selected=[a for a in actions if a['selected']]
 assert snapshot['pre_state_hash']=='422271443557180589' and len(actions)==snapshot['legal_action_count'] and len(selected)==min(len(actions),32)
 assert [a['stable_clause_id'] for a in actions]==sorted(a['stable_clause_id'] for a in actions)
 for a in actions:a['clause_canonical_sha256']=chash(a['clause_literals'])
 writecsv(OUT/'legal_actions.csv',actions)
 snapshot.update({'snapshot_kind':'OS fork COW in-memory snapshot; this JSON is its manifest, not a serialized checkpoint','fixed_components':['assignments','trail','decision levels','qhead','activity vector','heap and inverse indices','original and learned DB','watches','phases','restart state','counters','RNG/seed','native call stack'],'all_forks_from_one_paused_parent':True,'hash_scope':'Operational fingerprint plus raw Solver object bytes/pointers; heap hash includes inverse indices. Fork inherits all dynamically allocated memory as well.','native_selection_log_sha256':sha(d/'opportunities.jsonl')})
 dump(OUT/'frozen_state.json',snapshot)
 routes=['BASELINE']+[f"ACTION_{a['action_index']}" for a in selected];results={}
 for tag in routes:
  out=(d/(tag+'.stdout.txt')).read_text();stats=next(json.loads(x) for x in reversed(out.splitlines()) if x.startswith('{'))
  trace=events(d/(tag+'.trace.jsonl'));pre=next(e for e in trace if e['event']=='PRE_STATE')
  assert pre['hash']==snapshot['pre_state_hash'] and pre['raw_solver_object_hash']==snapshot['raw_solver_object_hash'] and pre['heap_including_inverse_hash']==snapshot['heap_including_inverse_hash']
  assert next(e for e in es if e['event']=='CHILD_EXIT' and e['route']==tag)['wait_status']==0
  expected=0 if tag=='BASELINE' else 1;assert next(e for e in trace if e['event']=='FINISH')['interventions']==expected
  ee=[e for e in trace if e['event']=='EARLY_ENQUEUE'];assert len(ee)==expected
  if expected:
   a=next(a for a in selected if tag==f"ACTION_{a['action_index']}");assert ee[0]['literal']==a['implied_literal'] and ee[0]['reason_id']==a['stable_clause_id'] and ee[0]['global_enqueue']==snapshot['global_enqueue']+1
  local=next(e for e in trace if e['event']=='LOCAL_RESULT');local['conflict_hash']=chash(local['conflict_clause_literals']);local['learned_hash']=chash(local['learned_clause_literals']);decision=next((e['literal'] for e in trace if e['event']=='NEXT_DECISION'),None)
  proof=d/(tag+'.drup');check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OLD/'T10/input.cnf'),str(proof)],capture_output=True,text=True,timeout=240);(d/(tag+'.proof_check.txt')).write_text(check.stdout+check.stderr);assert stats['status']=='UNSAT' and check.returncode==0 and 's VERIFIED' in check.stdout
  with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
  result={'route':tag,'stats':stats,'local':local,'next_decision':decision,'trace':trace,'proof_validation':'VERIFIED','proof_sha256':sha(proof),'same_parent_pre_state':True};dump(d/(tag+'.result.json'),result);results[tag]=result
 base=results['BASELINE'];old=json.loads((OLD/'T10/BASELINE.result.json').read_text());assert all(base['stats'][k]==v for k,v in old['stats'].items() if k!='seconds') and base['proof_sha256']==old['proof_sha256']
 rows=[];locals=[];reproduced=[]
 for a in selected:
  tag=f"ACTION_{a['action_index']}";r=results[tag];ops=r['stats']['analysis_resolution_steps'];remaining=ops-snapshot['analysis_ops_at_snapshot'];denom=base['stats']['analysis_resolution_steps']-snapshot['analysis_ops_at_snapshot'];delta=100*(remaining/denom-1)
  flags={'propagation_diverged':r['local']['dequeue_literals']!=base['local']['dequeue_literals'],'conflict_diverged':r['local']['conflict_hash']!=base['local']['conflict_hash'],'learned_diverged':r['local']['learned_hash']!=base['local']['learned_hash'],'decision_diverged':r['next_decision']!=base['next_decision']}
  cls='NO_LOCAL_CHANGE'
  for key,name in zip(flags,['PROPAGATION_ONLY','CONFLICT_CHANGING','LEARNED_CHANGING','DECISION_CHANGING']):
   if flags[key]:cls=name
  row={'action_id':tag,'selection_index':a['action_index'],'implied_literal':a['implied_literal'],'clause_id':a['stable_clause_id'],'clause_hash':a['clause_canonical_sha256'],'ops':ops,'remaining_analysis_ops_from_S':remaining,'baseline_remaining_ops_from_S':denom,'conflicts':r['stats']['conflicts'],'decisions':r['stats']['decisions'],'propagations':r['stats']['propagations'],'relative_ops_delta_percent':delta,'sign':'speedup' if delta<0 else 'slowdown' if delta>0 else 'zero','magnitude_abs_percent':abs(delta),'HIGH_LEVERAGE':abs(delta)>=10,'status':r['stats']['status'],'proof_validation':r['proof_validation'],'same_snapshot_S':True,'local_classification':cls};rows.append(row)
  locals.append({'action_id':tag,**flags,'classification':cls,'propagation_sequence':r['local']['dequeue_literals'],'next_conflict_hash':r['local']['conflict_hash'],'learned_hash':r['local']['learned_hash'],'next_decision_literal':r['next_decision'],'baseline_next_conflict_hash':base['local']['conflict_hash'],'baseline_learned_hash':base['local']['learned_hash'],'baseline_next_decision_literal':base['next_decision']})
  if a['stable_clause_id'] in [831,833]:
   i=226 if a['stable_clause_id']==831 else 227;prior=json.loads((Path('results/state_sensitivity_cohort/T10')/f'event_{i}/full_result.json').read_text())['full_runs'][1]
   assert all(r['stats'][k]==v for k,v in prior['stats'].items() if k!='seconds') and r['proof_sha256']==prior['proof_sha256'];reproduced.append(i)
 rows.sort(key=lambda r:(r['relative_ops_delta_percent'],r['selection_index']))
 writecsv(OUT/'all_action_runs.csv',rows);writecsv(OUT/'local_effects.csv',locals)
 summary={'snapshot':snapshot,'legal_action_count':len(actions),'tested_action_count':len(selected),'baseline':base,'rows_sorted_by_effect_after_selection':rows,'local_effects':locals,'effect_min_percent':min(r['relative_ops_delta_percent'] for r in rows),'effect_max_percent':max(r['relative_ops_delta_percent'] for r in rows),'sign_counts':dict(Counter(r['sign'] for r in rows)),'high_leverage_count':sum(r['HIGH_LEVERAGE'] for r in rows),'local_classification_counts':dict(Counter(r['classification'] for r in locals)),'prior_actions_reproduced':reproduced,'proofs_verified':len(routes),'selection_rule_unchanged':True}
 dump(OUT/'response_surface_summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ['snapshot','baseline','rows_sorted_by_effect_after_selection','local_effects']},indent=2),flush=True)

if __name__=='__main__':main()
