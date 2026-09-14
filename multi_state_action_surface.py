"""First5 distinct cohort pre-states, selected without reading effects."""
import csv,gzip,json,subprocess,shutil,os,statistics
from pathlib import Path
from collections import Counter
from build_native_cdcl import replace_once
import conflict_frontier_discovery as cf
ROOT=OUT=Path('results/multi_state_action_surface').resolve()
BUILD=Path('/private/tmp/satfinding-multi-state-action-surface')
OLD=Path('results/high_leverage_discovery').resolve()
sha=cf.sha;dump=cf.dump;chash=cf.chash;events=cf.events
def build():
 prior=Path('/private/tmp/satfinding-high-leverage-discovery');root=BUILD/'glucose-3.0';shutil.copytree(prior/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void hc_boundary();','    void hc_boundary();\n    void fs_surface();\n    void cf_dequeue(Lit);\n    void cf_conflict(CRef);\n    void cf_analysis(const vec<Lit>&);\n    void cf_decision(Lit);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(Path('high_leverage_discovery.inc').resolve()),str(Path('multi_state_action_surface.inc').resolve()))
 for anchor,extra in [("        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.",'\n        cf_dequeue(p);'),('\t  conflicts++; conflictC++;conflictsRestarts++;','\n          cf_conflict(confl);'),('            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);','\n            cf_analysis(learnt_clause);')]:s=replace_once(s,anchor,anchor+extra)
 s=replace_once(s,"            // Increase decision level and enqueue 'next'","            cf_decision(next);\n            // Increase decision level and enqueue 'next'");cc.write_text(s)
 shutil.copy2(prior/'driver.cc',BUILD/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('multi_state_action_surface.inc'),h,cc,BUILD/'driver.cc']},'base_build':json.loads((OLD/'build.json').read_text())})



def writecsv(path,rows):
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def run_state(state):
 OUT=ROOT/state['state_id'];OUT.mkdir(exist_ok=False)
 t=state['target'];o=state['opportunity'];d=OUT/'runs';cf.BUILD=BUILD
 os.environ['MS_STATE_HASH']=o['pre_state_fnv64']
 try:es=cf.run_parent(t,d,o['opportunity'])
 finally:os.environ.pop('MS_STATE_HASH',None)
 assert next(e for e in es if e['event']=='STOP')['status']=='ACTION_SURFACE_COMPLETED'
 snapshot=next(e for e in es if e['event']=='FROZEN_STATE');actions=[e for e in es if e['event']=='LEGAL_ACTION'];selected=[a for a in actions if a['selected']]
 assert snapshot['pre_state_hash']==o['pre_state_fnv64'] and len(actions)==snapshot['legal_action_count'] and len(selected)==min(len(actions),32)
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
  proof=d/(tag+'.drup');check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OLD/t/'input.cnf'),str(proof)],capture_output=True,text=True,timeout=240);(d/(tag+'.proof_check.txt')).write_text(check.stdout+check.stderr);assert stats['status']=='UNSAT' and check.returncode==0 and 's VERIFIED' in check.stdout
  with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
  result={'route':tag,'stats':stats,'local':local,'next_decision':decision,'trace':trace,'proof_validation':'VERIFIED','proof_sha256':sha(proof),'same_parent_pre_state':True};dump(d/(tag+'.result.json'),result);results[tag]=result
 base=results['BASELINE'];old=json.loads((OLD/t/'BASELINE.result.json').read_text());assert all(base['stats'][k]==v for k,v in old['stats'].items() if k!='seconds') and base['proof_sha256']==old['proof_sha256']
 rows=[];locals=[];reproduced=[]
 for a in selected:
  tag=f"ACTION_{a['action_index']}";r=results[tag];ops=r['stats']['analysis_resolution_steps'];remaining=ops-snapshot['analysis_ops_at_snapshot'];denom=base['stats']['analysis_resolution_steps']-snapshot['analysis_ops_at_snapshot'];delta=100*(remaining/denom-1)
  flags={'propagation_diverged':r['local']['dequeue_literals']!=base['local']['dequeue_literals'],'conflict_diverged':r['local']['conflict_hash']!=base['local']['conflict_hash'],'learned_diverged':r['local']['learned_hash']!=base['local']['learned_hash'],'decision_diverged':r['next_decision']!=base['next_decision']}
  cls='NO_LOCAL_CHANGE'
  for key,name in zip(flags,['PROPAGATION_ONLY','CONFLICT_CHANGING','LEARNED_CHANGING','DECISION_CHANGING']):
   if flags[key]:cls=name
  row={'action_id':tag,'selection_index':a['action_index'],'implied_literal':a['implied_literal'],'clause_id':a['stable_clause_id'],'clause_hash':a['clause_canonical_sha256'],'ops':ops,'remaining_analysis_ops_from_S':remaining,'baseline_remaining_ops_from_S':denom,'conflicts':r['stats']['conflicts'],'decisions':r['stats']['decisions'],'propagations':r['stats']['propagations'],'relative_ops_delta_percent':delta,'sign':'speedup' if delta<0 else 'slowdown' if delta>0 else 'zero','magnitude_abs_percent':abs(delta),'HIGH_LEVERAGE':abs(delta)>=10,'status':r['stats']['status'],'proof_validation':r['proof_validation'],'same_snapshot_S':True,'local_classification':cls};rows.append(row)
  locals.append({'action_id':tag,**flags,'classification':cls,'propagation_sequence':r['local']['dequeue_literals'],'next_conflict_hash':r['local']['conflict_hash'],'learned_hash':r['local']['learned_hash'],'next_decision_literal':r['next_decision'],'baseline_next_conflict_hash':base['local']['conflict_hash'],'baseline_learned_hash':base['local']['learned_hash'],'baseline_next_decision_literal':base['next_decision']})
  if a['stable_clause_id']==o['reason_id'] and a['implied_literal']==o['literal']:
   prior=json.loads((Path('results/state_sensitivity_cohort')/t/f"event_{o['opportunity']}"/'full_result.json').read_text())['full_runs'][1]
   assert all(r['stats'][k]==v for k,v in prior['stats'].items() if k!='seconds') and r['proof_sha256']==prior['proof_sha256'];reproduced.append(o['opportunity'])
 rows.sort(key=lambda r:(r['relative_ops_delta_percent'],r['selection_index']))
 writecsv(OUT/'all_action_runs.csv',rows);writecsv(OUT/'local_effects.csv',locals)
 summary={'snapshot':snapshot,'legal_action_count':len(actions),'tested_action_count':len(selected),'baseline':base,'rows_sorted_by_effect_after_selection':rows,'local_effects':locals,'effect_min_percent':min(r['relative_ops_delta_percent'] for r in rows),'effect_max_percent':max(r['relative_ops_delta_percent'] for r in rows),'sign_counts':dict(Counter(r['sign'] for r in rows)),'high_leverage_count':sum(r['HIGH_LEVERAGE'] for r in rows),'local_classification_counts':dict(Counter(r['classification'] for r in locals)),'prior_actions_reproduced':reproduced,'proofs_verified':len(routes),'selection_rule_unchanged':True}
 summary['state_id']=state['state_id'];summary['target']=t;summary['source_event']=o['opportunity'];summary['previously_studied_surface']=state['previously_studied_surface']
 assert reproduced==[o['opportunity']]
 assert all(snapshot[k]==o[k] for k in ['conflict','decision','level','global_enqueue'])
 dump(OUT/'response_surface_summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ['snapshot','baseline','rows_sorted_by_effect_after_selection','local_effects']},indent=2),flush=True)

 return summary

def main():
 ROOT.mkdir(exist_ok=False)
 protocol={'selection_order':'Existing frozen cohort order: T8,T10,T13 then original opportunity index; first5 distinct(target,pre-state hash) with validated conflict change and existing successful OS-fork restore. Never use final cost.','state_count':5,'actions':'All live legal native-layout-compatible true-unit clause actions at each S; stable clause ID ascending; if>32 take first32, otherwise all. Freeze list before any branch.','snapshot':'Same paused parent memory/stack OS fork for baseline and all actions; validate old operational hash, raw Solver object and heap+inverse hashes.','high_leverage_percent':10,'mixed_criteria':['high-leverage + exact0','speedup + slowdown'],'scope':'Distinct exact states need not be independent CNFs or independent trajectory prefixes. Report coarse context sharing explicitly.','no_new_feature_or_prediction':True}
 dump(ROOT/'protocol.json',protocol)
 source=Path('results/state_sensitivity_cohort/frozen_cohort.json');cohort=json.loads(source.read_text());chosen=[];seen=set();previous=json.loads(Path('results/fixed_state_action_surface/frozen_state.json').read_text())['pre_state_hash']
 order={'T8':0,'T10':1,'T13':2};assert cohort==sorted(cohort,key=lambda e:(order[e['target']],e['opportunity']['opportunity']))
 for e in cohort:
  t=e['target'];o=e['opportunity'];key=(t,o['pre_state_fnv64'])
  if key in seen:continue
  assert e['local_pair'][0]['local']['conflict_canonical_sha256']!=e['local_pair'][1]['local']['conflict_canonical_sha256']
  result=json.loads((Path('results/state_sensitivity_cohort')/t/f"event_{o['opportunity']}"/'full_result.json').read_text())
  assert result['same_pre_state_by_os_fork'] and result['full_local_replay_matches']
  seen.add(key);chosen.append({'state_id':f'S{len(chosen)+1}','target':t,'opportunity':o,'previously_studied_surface':t=='T10' and o['pre_state_fnv64']==previous,'snapshot_restore_evidence':'Existing cohort full_result same_pre_state_by_os_fork and matching local replay','descriptors':e['descriptors']})
  if len(chosen)==5:break
 assert len(chosen)==5
 selection={'source_frozen_cohort_sha256':sha(source),'protocol_sha256':sha(ROOT/'protocol.json'),'states':chosen,'previous_state_included':any(e['previously_studied_surface'] for e in chosen)}
 dump(ROOT/'selected_states.json',selection);selection_hash=sha(ROOT/'selected_states.json')
 build();summaries=[];rows=[];per=[]
 for state in chosen:
  ss=run_state(state);summaries.append(ss)
  local={r['action_id']:r for r in ss['local_effects']}
  for r in ss['rows_sorted_by_effect_after_selection']:
   rows.append({'state_id':state['state_id'],'target':state['target'],'state_hash':ss['snapshot']['pre_state_hash'],**r,**{k:local[r['action_id']][k] for k in ['propagation_diverged','conflict_diverged','learned_diverged','decision_diverged']}})
  rs=ss['rows_sorted_by_effect_after_selection'];deltas=[r['relative_ops_delta_percent'] for r in rs];counts=ss['sign_counts'];high=ss['high_leverage_count']
  per.append({'state_id':state['state_id'],'target':state['target'],'source_opportunity':state['opportunity']['opportunity'],'state_hash':ss['snapshot']['pre_state_hash'],'previously_studied_surface':state['previously_studied_surface'],'legal_action_count':ss['legal_action_count'],'tested_action_count':ss['tested_action_count'],'zero_count':counts.get('zero',0),'speedup_count':counts.get('speedup',0),'slowdown_count':counts.get('slowdown',0),'high_leverage_count':high,'delta_min_percent':min(deltas),'delta_max_percent':max(deltas),'delta_median_percent':statistics.median(deltas),'effect_range_percentage_points':max(deltas)-min(deltas),'high_leverage_plus_zero':high>0 and counts.get('zero',0)>0,'speedup_plus_slowdown':counts.get('speedup',0)>0 and counts.get('slowdown',0)>0,'all_actions_same_sign':len(counts)==1,'proofs_verified':ss['proofs_verified']})
  writecsv(ROOT/'all_action_runs.csv',rows);writecsv(ROOT/'per_state_summary.csv',per)
 assert sha(ROOT/'selected_states.json')==selection_hash
 summary={'selection_sha256':selection_hash,'states_tested':len(per),'new_exact_states':sum(not r['previously_studied_surface'] for r in per),'old_studied_states':sum(r['previously_studied_surface'] for r in per),'targets_tested':sorted(set(r['target'] for r in per)),'decision_context_groups':len(set((e['target'],e['opportunity']['conflict'],e['opportunity']['decision'],e['opportunity']['level']) for e in chosen)),'total_actions_tested':len(rows),'proofs_verified':sum(r['proofs_verified'] for r in per),'states_high_plus_zero':sum(r['high_leverage_plus_zero'] for r in per),'states_speedup_plus_slowdown':sum(r['speedup_plus_slowdown'] for r in per),'per_state':per,'all_actions':rows,'stopped':True}
 dump(ROOT/'response_surface_summary.json',summary)
 print('AGGREGATE',json.dumps({k:v for k,v in summary.items() if k not in ['per_state','all_actions']}),flush=True)

if __name__=='__main__':main()
