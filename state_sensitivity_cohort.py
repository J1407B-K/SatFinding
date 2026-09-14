"""First5 conflict-changing events among first500 opportunities on each fixed target."""
import csv,gzip,json,subprocess,shutil
from pathlib import Path
from collections import Counter
from build_native_cdcl import replace_once
import conflict_frontier_discovery as cf
OUT=Path('results/state_sensitivity_cohort').resolve()
BUILD=Path('/private/tmp/satfinding-state-sensitivity-cohort')
OLD=Path('results/high_leverage_discovery').resolve()
sha=cf.sha;dump=cf.dump;chash=cf.chash;events=cf.events;traces=cf.traces
def build():
 prior=Path('/private/tmp/satfinding-high-leverage-discovery');root=BUILD/'glucose-3.0';shutil.copytree(prior/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void hc_boundary();','    void hc_boundary();\n    void cf_dequeue(Lit);\n    void cf_conflict(CRef);\n    void cf_analysis(const vec<Lit>&);\n    void cf_decision(Lit);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(Path('high_leverage_discovery.inc').resolve()),str(Path('state_sensitivity_cohort.inc').resolve()))
 for anchor,extra in [("        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.",'\n        cf_dequeue(p);'),('\t  conflicts++; conflictC++;conflictsRestarts++;','\n          cf_conflict(confl);'),('            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);','\n            cf_analysis(learnt_clause);')]:s=replace_once(s,anchor,anchor+extra)
 s=replace_once(s,"            // Increase decision level and enqueue 'next'","            cf_decision(next);\n            // Increase decision level and enqueue 'next'");cc.write_text(s)
 shutil.copy2(prior/'driver.cc',BUILD/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('state_sensitivity_cohort.inc'),h,cc,BUILD/'driver.cc']},'base_build':json.loads((OLD/'build.json').read_text())})


def run_parent(t,d,index):
 cf.BUILD=BUILD
 return cf.run_parent(t,d,index)

def main():
 OUT.mkdir(exist_ok=False)
 protocol={'targets':['T8','T10','T13'],'max_opportunities_per_target':500,'events_per_target':5,'selection':'First5 canonical-next-conflict-changing events in fixed baseline opportunity order; stop at fifth or opportunity500. All targets selected before any full runs.','enumeration':'Unchanged Conflict-Frontier Discovery: completed enqueue and search-loop entry; newly eligible true-unit native-layout-compatible clause/literal episodes; simultaneous candidates ordered by stable allocation ID; rearm only after observed ineligible state.','fork':'Unchanged OS COW fork pair at identical pre-state; local children stop after next conflict analysis; full pair only after selection frozen.','descriptors':['current conflict','decision','level','trail length','qhead','pending propagation count','restart epoch','conflicts since restart','candidate activity','heap array position','clause length','antecedent level distribution','almost-unit neighbor count','local clause fanout'],'definitions':{'restart_epoch':'native starts counter','conflicts_since_restart':'native conflictsRestarts counter','heap_rank':'zero-based native heap array position; -1 absent; not sorted activity rank','almost_unit':'active clause containing candidate variable, no true literals, exactly2 unassigned','fanout':'number of active clauses containing candidate variable','antecedents':'histogram of assigned-false reason literals decision levels','high_leverage':'abs(relative_ops_delta)>=10%','effect_bins':'exact0; nonzero abs<1% (near0); 1<=abs<5%; 5<=abs<10%; abs>=10%. Descriptive bins only, HIGH_LEVERAGE unchanged.'},'no_feature_selection':True,'inputs':{t:{'path':str(OLD/t/'input.cnf'),'sha256':sha(OLD/t/'input.cnf')} for t in ['T8','T10','T13']}}
 dump(OUT/'protocol.json',protocol);build();selected=[];target_summaries={}
 for t in protocol['targets']:
  td=OUT/t;td.mkdir();es=run_parent(t,td/'local',0)
  os={e['opportunity']:e for e in es if e['event']=='OPPORTUNITY'};ds={e['opportunity']:e for e in es if e['event']=='DESCRIPTORS'}
  hits=[e['opportunity'] for e in es if e['event']=='CONFLICT_CHANGING_EVENT'];assert len(os)<=500 and len(hits)<=5 and list(os)==list(range(1,len(os)+1))
  stop=next(e for e in es if e['event']=='STOP');assert (stop['status']=='FIVE_EVENTS_COLLECTED' and len(hits)==5) or (stop['status']=='CAP_REACHED' and len(os)==500)
  localrows=[];ts=[]
  for i,o in os.items():
   pair=traces(td/'local',i);a,b=[x['local'] for x in pair];assert pair[0]['pre']['hash']==o['pre_state_fnv64']
   assert sum(e['event']=='EARLY_ENQUEUE' for e in pair[0]['events'])==0
   ee=[e for e in pair[1]['events'] if e['event']=='EARLY_ENQUEUE'];assert len(ee)==1 and ee[0]['global_enqueue']==o['global_enqueue']+1 and ee[0]['literal']==o['literal']
   pd=a['dequeue_literals']!=b['dequeue_literals'];cd=a['conflict_canonical_sha256']!=b['conflict_canonical_sha256'];ld=a['learned_canonical_sha256']!=b['learned_canonical_sha256'];assert cd==(i in hits)
   localrows.append({'opportunity':i,'propagation_diverged':pd,'conflict_diverged':cd,'learned_diverged':ld,'classification':'L3' if ld else 'L2' if cd else 'L1' if pd else 'L0'})
   if cd:
    event={'target':t,'opportunity':o,'descriptors':ds[i],'local_pair':pair,'selected_rank':hits.index(i)+1};selected.append(event);ts.append(event)
  dump(td/'frozen_events.json',ts);dump(td/'all_local_probes.json',localrows)
  target_summaries[t]={'opportunities_scanned':len(os),'conflict_changing_events':len(hits),'selected_indices':hits,'stop':stop['status'],'local_classifications':dict(Counter(r['classification'] for r in localrows))}
  print('FROZEN',t,target_summaries[t],flush=True)
 dump(OUT/'frozen_cohort.json',selected)
 # Selection of all3 targets is immutable before any full cost is inspected.
 selection_hash=sha(OUT/'frozen_cohort.json');rows=[];fullresults=[]
 for event in selected:
  t=event['target'];o=event['opportunity'];i=o['opportunity'];d=OUT/t/f'event_{i}';es=run_parent(t,d,i)
  assert next(e for e in es if e['event']=='STOP')['status']=='FULL_PAIR_COMPLETED'
  assert next(e for e in es if e['event']=='OPPORTUNITY')==o
  assert next(e for e in es if e['event']=='DESCRIPTORS')==event['descriptors']
  pair=traces(d,i);runs=[]
  for role,trace,prior in zip(['BASELINE','EARLY'],pair,event['local_pair']):
   assert trace['pre']==prior['pre'] and trace['local']==prior['local']
   tag=f'P{i}_{role}';stats=next(json.loads(x) for x in reversed((d/(tag+'.stdout.txt')).read_text().splitlines()) if x.startswith('{'))
   proof=d/(tag+'.drup');check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OLD/t/'input.cnf'),str(proof)],capture_output=True,text=True,timeout=240);(d/(tag+'.proof_check.txt')).write_text(check.stdout+check.stderr)
   assert stats['status']=='UNSAT' and check.returncode==0 and 's VERIFIED' in check.stdout
   with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
   runs.append({'route':role,'stats':stats,'proof_validation':'VERIFIED','proof_sha256':sha(proof),'next_decision':next((e['literal'] for e in trace['events'] if e['event']=='NEXT_DECISION'),None),'trace':trace})
  baseline_old=json.loads((OLD/t/'BASELINE.result.json').read_text())
  assert all(runs[0]['stats'][k]==v for k,v in baseline_old['stats'].items() if k!='seconds')
  assert runs[0]['proof_sha256']==baseline_old['proof_sha256']
  a,b=runs;delta=100*(b['stats']['analysis_resolution_steps']/a['stats']['analysis_resolution_steps']-1)
  da=abs(delta);bin='exact0' if da==0 else 'nonzero_abs_lt1pct' if da<1 else 'abs_1_to5pct' if da<5 else 'abs_5_to10pct' if da<10 else 'HIGH_LEVERAGE'
  row={'event':f'{t}_P{i}','target':t,'opportunity_index':i,'selected_rank':event['selected_rank'],'conflict':o['conflict'],'decision':o['decision'],'level':o['level'],'clause_id':o['reason_id'],'clause_hash':chash(o['reason_literals']),'clause_literals':o['reason_literals'],'implied_literal':o['literal'],'pre_state_hash':o['pre_state_fnv64'],**{k:v for k,v in event['descriptors'].items() if k not in ['event','opportunity','current_conflict','decision','level']},'baseline_next_conflict_hash':a['trace']['local']['conflict_canonical_sha256'],'perturb_next_conflict_hash':b['trace']['local']['conflict_canonical_sha256'],'baseline_learned_hash':a['trace']['local']['learned_canonical_sha256'],'perturb_learned_hash':b['trace']['local']['learned_canonical_sha256'],'conflict_changed':True,'learned_changed':a['trace']['local']['learned_canonical_sha256']!=b['trace']['local']['learned_canonical_sha256'],'baseline_next_decision':a['next_decision'],'perturb_next_decision':b['next_decision'],'decision_changed':a['next_decision']!=b['next_decision'],'baseline_ops':a['stats']['analysis_resolution_steps'],'perturb_ops':b['stats']['analysis_resolution_steps'],'relative_ops_delta_percent':delta,'HIGH_LEVERAGE':da>=10,'effect_bin':bin,'direction':'speedup' if delta<0 else 'slowdown' if delta>0 else 'unchanged'}
  for prefix,r in [('baseline',a),('perturb',b)]:
   for k in ['conflicts','decisions','propagations','status']:row[prefix+'_'+k]=r['stats'][k]
   row[prefix+'_proof_validation']=r['proof_validation']
  result={'event':event,'full_runs':runs,'row':row,'selection_hash':selection_hash,'same_pre_state_by_os_fork':True,'full_local_replay_matches':True};dump(d/'full_result.json',result);fullresults.append(result);rows.append(row)
  print('FULL',row['event'],row['perturb_ops'],delta,bin,flush=True)
  with (OUT/'all_conflict_changing_events.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerows({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
 assert sha(OUT/'frozen_cohort.json')==selection_hash
 summary={'target_summaries':target_summaries,'event_count':len(rows),'effect_bins':dict(Counter(r['effect_bin'] for r in rows)),'directions':dict(Counter(r['direction'] for r in rows)),'HIGH_LEVERAGE_count':sum(r['HIGH_LEVERAGE'] for r in rows),'verified_full_proofs':2*len(rows),'frozen_cohort_sha256':selection_hash,'protocol_sha256':sha(OUT/'protocol.json'),'rows':rows,'selection_completed_before_full_runs':True}
 dump(OUT/'cohort_summary.json',summary)

if __name__=='__main__':main()
