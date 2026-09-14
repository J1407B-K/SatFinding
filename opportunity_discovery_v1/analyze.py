import sys,csv,json,collections,statistics,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from opportunity_discovery_v1.extract import R,O,V,sha,load,dump,csvwrite

def rows(p):
 out=[]
 for r in csv.DictReader(p.open()):
  x={}
  for k,v in r.items():
   if v=='':x[k]=None
   elif v in ['True','False']:x[k]=v=='True'
   else:
    try:x[k]=json.loads(v)
    except (ValueError,TypeError):x[k]=v
  out.append(x)
 return out

def main():
 freeze=load(O/'FEATURE_ARTIFACT_FREEZE.json')
 for n,h in freeze['files'].items():assert sha(O/n)==h
 va=rows(O/'opportunity_action_features.csv');vs=rows(O/'opportunity_state_features.csv');ha=rows(O/'historical_action_features.csv');hs=rows(O/'historical_state_features.csv')
 gt=rows(V/'state_action_ground_truth.csv');lookup={(r['state_id'],r['action_rank']):r for r in gt};ho=load(O/'historical_outcomes.json');hl={(r['state_id'],r['action_rank']):r for r in ho}
 for r in va:r['HIGH']=lookup[r['state_id'],r['action_rank']]['HIGH_LEVERAGE'];r['delta_percent']=lookup[r['state_id'],r['action_rank']]['final_ops_delta_percent']
 for r in ha:r['HIGH']=hl[r['state_id'],r['action_rank']]['HIGH_LEVERAGE'];r['delta_percent']=hl[r['state_id'],r['action_rank']]['delta_percent']
 allstates={s['state_id']:s for s in vs+hs};by=collections.defaultdict(list)
 for r in va+ha:by[r['state_id']].append(r)
 sensitive={sid:any(a['HIGH'] for a in aa) for sid,aa in by.items()}
 for s in vs+hs:s['SENSITIVE']=sensitive[s['state_id']]
 # Every registered natural predicate and only the two registered conjunctions.
 def predicates(a):
  v=a['newest_antecedent_relative_to_qhead'];q=allstates[a['state_id']]['pending_queue_length']
  return {'pending_antecedent_count > 0':a['pending_antecedent_count']>0,'all_antecedents_processed':a['all_antecedents_processed'],'distinct_implied_literal_count > 1':a['distinct_implied_literal_count']>1,'same_implied_literal_multiplicity > 1':a['same_implied_literal_multiplicity']>1,'pending_queue_length > 0':q>0,'newest_antecedent_relative_to_qhead == 0':None if v is None else v==0,'newest_antecedent_relative_to_qhead > 0':None if v is None else v>0,'watched_false_pending_count > 0':a['watched_false_pending_count']>0}
 protocol=load(O/'OPPORTUNITY_FEATURE_PROTOCOL_V1.json');names=list(protocol['bounded_predicates'])
 for pair in protocol['permitted_conjunctions']:names.append(' AND '.join(pair))
 def value(a,name):
  p=predicates(a)
  if name in p:return p[name]
  pair=name.split(' AND ');return None if any(p[n] is None for n in pair) else all(p[n] for n in pair)
 results=[]
 for name in names:
  vpass=[a for a in va if value(a,name) is True];hpass=[a for a in ha if value(a,name) is True]
  passed={sid:any(value(a,name) is True for a in aa) for sid,aa in by.items()}
  valid={sid:all(value(a,name) is not None for a in aa) for sid,aa in by.items()}
  positive_ids={sid for sid in by if sensitive[sid]};covered={sid for sid in positive_ids if passed[sid]};excluded=[s['state_id'] for s in vs if not sensitive[s['state_id']] and valid[s['state_id']] and not passed[s['state_id']]]
  targets={allstates[sid]['target'] for sid in covered}
  candidate=len(covered)>=2 and covered==positive_ids and len(targets)>1 and len(excluded)>0
  results.append({'predicate':'exists frozen action: '+name,'v3_HIGH_pass':sum(a['HIGH'] for a in vpass),'v3_HIGH_total':sum(a['HIGH'] for a in va),'v3_NON_HIGH_pass':sum(not a['HIGH'] for a in vpass),'v3_NON_HIGH_total':sum(not a['HIGH'] for a in va),'historical_HIGH_pass':sum(a['HIGH'] for a in hpass),'historical_HIGH_total':sum(a['HIGH'] for a in ha),'positive_states_covered':len(covered),'positive_states_total':len(positive_ids),'positive_targets_covered':sorted(targets),'v3_inert_states_excluded':len(excluded),'v3_inert_states_total':sum(not s['SENSITIVE'] for s in vs),'excluded_state_ids':excluded,'candidate_criteria_met':candidate})
 csvwrite(O/'bounded_predicate_analysis.csv',results)
 # Complete-case distributions, kept separate for prospective-v3 discovery and historical ascertainment.
 description=[];rankrows=[]
 def describe(dataset,level,rs,labelkey):
  for feature in rs[0]:
   if feature in ['action_rank','action_id','clause_id','state_identity','state_id','target','HIGH','SENSITIVE','delta_percent','dataset','partial_historical_snapshot']:continue
   values=[r.get(feature) for r in rs if isinstance(r.get(feature),(float,int,bool))]
   for group in [True,False]:
    sub=[r for r in rs if r[labelkey]==group];nums=[r[feature] for r in sub if isinstance(r.get(feature),(float,int,bool))]
    if values:
     description.append({'dataset':dataset,'level':level,'feature':feature,'group':('HIGH' if group else 'NON_HIGH') if level=='action' else ('SENSITIVE' if group else 'INERT within frozen tested-action budget'),'total':len(sub),'available':len(nums),'median':statistics.median(nums) if nums else None,'min':min(nums) if nums else None,'max':max(nums) if nums else None,'raw_values':nums})
     for r in sub:
      v=r.get(feature)
      if isinstance(v,(float,int,bool)):rankrows.append({'dataset':dataset,'level':level,'state_id':r['state_id'],'action_id':r.get('action_id'),'feature':feature,'raw_value':v,'rank':1+sum(x<v for x in values)+.5*(sum(x==v for x in values)-1),'label':group})
    elif feature=='source':
     description.append({'dataset':dataset,'level':level,'feature':feature,'group':'HIGH' if group else 'NON_HIGH','total':len(sub),'available':len(sub),'median':None,'min':None,'max':None,'raw_values':dict(collections.Counter(r[feature] for r in sub))})
 describe('V3_DISCOVERY','action',va,'HIGH');describe('HISTORICAL_DISCOVERY_POSITIVES','action',ha,'HIGH');describe('V3_DISCOVERY','state',vs,'SENSITIVE');describe('HISTORICAL_DISCOVERY_POSITIVES','state',hs,'SENSITIVE')
 csvwrite(O/'opportunity_feature_analysis.csv',description);csvwrite(O/'opportunity_feature_ranks.csv',rankrows)
 positive=[a for a in va+ha if a['HIGH']]
 fields=['dataset','target','state_id','action_id','implied_literal','clause_length','source','pending_antecedent_count','pending_antecedent_fraction','newest_antecedent_age','newest_antecedent_relative_to_qhead','all_antecedents_processed','watched_false_pending_count','same_implied_literal_multiplicity','distinct_implied_literal_count','implied_var_activity_rank','implied_var_heap_rank','delta_percent']
 csvwrite(O/'positive_mechanism_comparison.csv',[{f:a[f] for f in fields} for a in positive])
 sid=next(a['state_id'] for a in va if a['HIGH']);pair=by[sid];assert len(pair)==2
 high=next(a for a in pair if a['HIGH']);non=next(a for a in pair if not a['HIGH'])
 def show(v):return 'UNAVAILABLE' if v is None else json.dumps(v,ensure_ascii=False)
 pairlines=['# V3 sensitive-state action pair — exploratory only','',f'State `{sid}`. Same sealed canonical logical/heuristic state; two frozen actions. The sealed v3 conclusion B is unchanged.','',f'HIGH action #{high["action_id"]}: {high["delta_percent"]:.6f}% remaining ops. NON-HIGH action #{non["action_id"]}: {non["delta_percent"]:.6f}%.','', '| Frozen relational field | HIGH | same-state NON-HIGH | Equal? |','|---|---|---|---|']
 for f in high:
  if f in ['dataset','state_id','target','state_identity','HIGH','delta_percent']:continue
  pairlines.append(f'| {f} | {show(high[f])} | {show(non[f])} | {high[f]==non[f]} |')
 pairlines+=['','Both actions share exactly the same queue head and newest antecedent frontier. Their clauses differ in length/source, older antecedents and implied variable activity/heap position. These differences are observed contrasts, not identified causes. The natural pending/frontier booleans cannot distinguish this HIGH/NON-HIGH pair. No continuous-value cutoff or action-selection rule was fitted.']
 (O/'V3_SENSITIVE_STATE_ACTION_PAIR.md').write_text('\n'.join(pairlines)+'\n')
 candidates=[r for r in results if r['candidate_criteria_met']]
 decision='A' if candidates else 'B' if len(hs)>=1 else 'C'
 result={'A':'CANDIDATE_INTERVENTION_OPPORTUNITY_DESCRIPTOR','B':'NO_OBVIOUS_INTERVENTION_OPPORTUNITY_DESCRIPTOR_V1','C':'HISTORICAL_POSITIVES_NOT_AUDITABLE_ENOUGH'}[decision]
 # If this fires, inspect the mechanism and freeze an exact prospective test before any new run.
 summary={'scope':'EXPLORATORY_HYPOTHESIS_GENERATION','result':decision,'classification':result,'auditable_positive_states':sum(sensitive.values()),'auditable_HIGH_actions':len(positive),'v3_positive_states':1,'v3_HIGH_actions':1,'historical_positive_states':len(hs),'historical_HIGH_actions':sum(a['HIGH'] for a in ha),'v3_states':18,'v3_actions':85,'historical_actions_including_same_state_controls':len(ha),'candidate_predicates':[r['predicate'] for r in candidates],'predicates_examined':len(results),'new_native_interventions':0,'prospective_validation_run':False,'v3_scientific_result_unchanged':'B — NO_SIMPLE_TEMPORAL_STATE_ABSTRACTION','READY_FOR_MICRO_ROLLOUT_ACTION_SELECTION':False,'pair_HIGH_action_id':high['action_id'],'pair_NON_HIGH_action_id':non['action_id'],'pair_differences':{f:{'HIGH':high[f],'NON_HIGH':non[f]} for f in fields if high[f]!=non[f] and f not in ['delta_percent','dataset','target','state_id']}}
 dump(O/'DISCOVERY_RESULT.json',summary)
 print(json.dumps(summary),flush=True)
 if candidates:print(json.dumps(candidates),flush=True)
 report=['# Intervention opportunity discovery v1','',f'**{decision}. {result}**','', 'Exploratory hypothesis generation only. The sealed temporal v3 conclusion is not modified or reinterpreted. No native solver was run, no intervention was executed and no package or label was changed. Existing canonical snapshots supplied all v3 fields; historical proof rechecks were the only new external executions.','',
 f'Discovery includes 18 v3 states/85 actions (1 HIGH), plus {len(hs)} audited historical positive states/{len(ha)} actions including controls ({sum(a["HIGH"] for a in ha)} HIGH). Thus {len(positive)} HIGH actions occur across {sum(sensitive.values())} distinct positive states on T8 and T10. Historical observations are selected discovery positives, not prospective validation or an unbiased prevalence estimate.','',
 'Historical exactness is same-parent OS fork identity with matching operational/raw-object/heap fingerprints inside one run, legal action and enqueue records, full continuation counters, and newly reverified proofs. No legacy hash is used to assert cross-run canonical equality. Complete pending queue positions are recovered from the baseline FIFO dequeue prefix; historical activity and semantic heap rank are unavailable and not imputed. Original/Gold is excluded from feature/label comparisons because an exact matched baseline pre-snapshot was not established; its existing mechanism finding is not disputed.','',
 'The opportunity protocol was frozen before new feature/label association. V3 and historical feature artifacts were hashed before joining outcomes. Eight listed natural predicates and two explicitly listed conjunctions were tested; no extra predicate, weighted score, continuous cutoff sweep, regression or classifier was tried.','',
 '## Exact within-state contrast','',f'HIGH #{high["action_id"]} versus NON-HIGH #{non["action_id"]} is fully tabulated in V3_SENSITIVE_STATE_ACTION_PAIR.md. Pending-antecedent status alone does not distinguish them. Clause source/length, older antecedent positions and implied-variable search-control ranks differ, but this single pair cannot identify which difference caused the continuation effect.','',
 '## Bounded opportunity tests','', '| Predicate (state has such a frozen action) | HIGH states covered | V3 inert states excluded | Meets candidate criteria |','|---|---:|---:|---|']
 for r in results:report.append(f'| {r["predicate"]} | {r["positive_states_covered"]}/{r["positive_states_total"]} | {r["v3_inert_states_excluded"]}/{r["v3_inert_states_total"]} | {r["candidate_criteria_met"]} |')
 report+=['','These are descriptive discovery counts, not gate validation. Continuous features are reported as complete-case distributions and ranks only, separately for v3 and historical data. Correlated actions from one state are not independent positive replications.','',
 'The common frontier relationship is not sufficient to explain intervention leverage: positive and zero-effect actions can occupy the same pending frontier, including within the exact same state. The evidence supports asking how a particular enqueue interacts with subsequent propagation/learning, but this feature family does not establish that mechanism or supply a promotable opportunity rule. Equal final analysis ops do not by themselves prove bit-exact trajectory identity.','',
 'No opportunity gate is promoted, no held-out test is run under B/C, and no controller, Level-1 selector, direction predictor or micro-rollout is validated. The appropriate next step is further bounded mechanism discovery, not deployment or action selection.']
 (O/'INTERVENTION_OPPORTUNITY_DISCOVERY_V1.md').write_text('\n'.join(report)+'\n')
if __name__=='__main__':main()
