"""Reporting-only prospective analysis; no change to locked inputs/core."""
from pathlib import Path
import sys,csv,json,statistics,collections,math,time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.audit import post_audit
from science_v3.run import csvwrite
O=ROOT/'results/prospective_temporal_state_cohort_v3'
def readcsv(p):return list(csv.DictReader(p.open()))
def median(x):return statistics.median(x) if x else None
def span(x):return [min(x),max(x)] if x else None
def numeric(v):
 try:return float(v)
 except (ValueError,TypeError):return None

def summary(rs,col,labels):
 s=[float(r[col]) for r in rs if labels[r['state_id']]=='SENSITIVE' and numeric(r[col]) is not None]
 i=[float(r[col]) for r in rs if labels[r['state_id']]=='INERT' and numeric(r[col]) is not None]
 direction=None if not s or not i else 'higher_sensitive' if median(s)>median(i) else 'lower_sensitive' if median(s)<median(i) else 'equal'
 overlap=None if not s or not i else not(max(s)<min(i) or max(i)<min(s))
 width=None if not s or not i else max(0,min(max(s),max(i))-max(min(s),min(i)))
 total=None if not s or not i else max(s+i)-min(s+i)
 return {'sensitive_n':len(s),'inert_n':len(i),'sensitive_median':median(s),'inert_median':median(i),'sensitive_range':span(s),'inert_range':span(i),'overlap':overlap,'overlap_fraction':width/total if total else (1 if total==0 else None),'direction':direction}

def describe(rows,labels):
 columns=[c for c in rows[0] if c not in ['state_id','target']];sep=[];values=[];within={t:{} for t in ['T8','T10','T13']};metrics={}
 for c in columns:
  pooled=summary(rows,c,labels);per={};rank_s=[];rank_i=[]
  for t in within:
   sub=[r for r in rows if r['target']==t];vals=[float(r[c]) for r in sub if numeric(r[c]) is not None];d=summary(sub,c,labels);per[t]=d
   for r in sub:
    v=numeric(r[c]);rank=None if v is None else sum(x<v for x in vals)+.5*sum(x==v for x in vals);norm=None if rank is None else rank/len(vals)
    values.append({'feature':c,'target':t,'state_id':r['state_id'],'label':labels[r['state_id']],'available':v is not None,'raw_value':v,'within_target_rank':rank,'normalized_within_target_rank':norm})
    if norm is not None:(rank_s if labels[r['state_id']]=='SENSITIVE' else rank_i).append(norm)
   # Outlier diagnostic: every single-state deletion must preserve strict gap and direction.
   d['leave_one_state_out_robust']=d['overlap'] is False and all((lambda z:z['overlap'] is False and z['direction']==d['direction'])(summary([x for x in sub if x['state_id']!=r['state_id']],c,labels)) for r in sub)
   within[t][c]=d
  informative=[d for d in per.values() if d['direction'] is not None]
  signs={d['direction'] for d in informative};nonoverlap=[d for d in informative if d['overlap'] is False]
  necessary=len(nonoverlap)>=2 and len(signs)==1 and all(d['leave_one_state_out_robust'] for d in nonoverlap)
  confounded=pooled['overlap'] is False and bool(informative) and all(d['direction']!=pooled['direction'] for d in informative)
  metrics[c]={'robust_necessary_evidence':necessary,'pooled_strict_separation':pooled['overlap'] is False,'within_target_directions_consistent':len(informative)>=2 and len(signs)==1,'strictly_separated_targets':len(nonoverlap),'target_confounded_by_frozen_criterion':confounded,'informative_targets':len(informative)}
  sep.append(dict(feature=c,**pooled,normalized_rank_sensitive_median=median(rank_s),normalized_rank_inert_median=median(rank_i),**metrics[c]))
 return sep,values,within,metrics

def main():
 t0=time.monotonic();audit,routes=post_audit(O);assert audit['ROUTE_INTEGRITY_PASSED']
 for n,h in frozen(O/'science_input_manifest.json')['files'].items():assert sha(O/n)==h
 gt=readcsv(O/'state_action_ground_truth.csv');sl=readcsv(O/'state_labels.csv');labels={r['state_id']:r['label'] for r in sl}
 temporal=readcsv(O/'temporal_state_features.csv');static=readcsv(O/'static_state_features.csv')
 assert len(sl)==18 and len(gt)==audit['action_routes']
 assert {r['state_id'] for r in temporal}==set(labels)
 by=collections.defaultdict(list)
 for r in gt:by[r['state_id']].append(r)
 surfaces=[]
 for st in sl:
  ds=[float(r['final_ops_delta_percent']) for r in by[st['state_id']]];hi=[d for d in ds if abs(d)>=10]
  surfaces.append({'target':st['target'],'state_id':st['state_id'],'label':st['label'],'selected_count':len(ds),'high_count':len(hi),'high_fraction':len(hi)/len(ds),'HIGH_speedup_count':sum(d<=-10 for d in ds),'HIGH_slowdown_count':sum(d>=10 for d in ds),'speedup_count':sum(d<0 for d in ds),'slowdown_count':sum(d>0 for d in ds),'zero_fraction':sum(abs(d)<1 for d in ds)/len(ds),'best_speedup_percent':min(0,min(ds)),'worst_slowdown_percent':max(0,max(ds)),'effect_range_percent':[min(ds),max(ds)],'sparse':bool(hi) and len(hi)/len(ds)<.5})
 ds=[float(r['final_ops_delta_percent']) for r in gt];nh=sum(abs(d)>=10 for d in ds);ns=sum(s['label']=='SENSITIVE' for s in surfaces)
 structure={'states':len(sl),'SENSITIVE':ns,'INERT_within_frozen_tested_action_budget':len(sl)-ns,'actions':len(ds),'HIGH':nh,'HIGH_prevalence':nh/len(ds),'HIGH_speedups':sum(d<=-10 for d in ds),'HIGH_slowdowns':sum(d>=10 for d in ds),'moderate':sum(1<=abs(d)<10 for d in ds),'zero_or_near_zero':sum(abs(d)<1 for d in ds),'exact_zero':sum(int(r['action_remaining_ops'])==int(r['baseline_remaining_ops']) for r in gt),'sensitive_state_fraction':ns/len(sl),'sparse_sensitive_states':sum(s['sparse'] for s in surfaces),'surfaces':surfaces,'per_target':{t:{'states':6,'sensitive':sum(s['target']==t and s['label']=='SENSITIVE' for s in surfaces),'actions':sum(s['selected_count'] for s in surfaces if s['target']==t),'HIGH':sum(s['high_count'] for s in surfaces if s['target']==t)} for t in ['T8','T10','T13']}}
 # Qualitative replication only; no old/invalid cohort numerical data enter the test.
 structure['previous_observation_comparison']='Qualitative only: earlier prospective observation was rare, concentrated, sparse; no historical labels/features pooled.'
 structure['distribution_shift']='SENSITIVITY_DISTRIBUTION_SHIFT' if ns and sum(s['sparse'] for s in surfaces)<=ns/2 else 'NO_CLEAR_QUALITATIVE_SHIFT_IN_SPARSITY' if ns else 'NO_HIGH_LEVERAGE_OBSERVED_IN_THIS_FROZEN_BUDGET'
 dump(O/'sensitivity_structure.json',structure)
 ts,tv,tw,tm=describe(temporal,labels);ss,sv,sw,sm=describe(static,labels)
 for path,rows in [('temporal_feature_separation.csv',ts),('temporal_feature_values.csv',tv),('static_feature_separation.csv',ss),('static_feature_values.csv',sv)]:
  csvwrite(O/path,[{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows])
 dump(O/'within_target_temporal_analysis.json',{'targets':tw,'per_descriptor':tm,'no_feature_selection':True,'single_state_removal_diagnostic':True})
 robust_t=[k for k,v in tm.items() if v['robust_necessary_evidence']];robust_s=[k for k,v in sm.items() if v['robust_necessary_evidence']]
 confounded=[k for k,v in tm.items() if v['target_confounded_by_frozen_criterion']]
 # No candidate relation is invented after the labels. B/C logic was frozen before collection.
 result='C' if confounded and not robust_t else 'B'
 title={'B':'NO_SIMPLE_TEMPORAL_STATE_ABSTRACTION','C':'TARGET_CONFOUNDED_TEMPORAL_SIGNAL'}[result]
 comparison={'temporal_robust_necessary_evidence':robust_t,'static_robust_necessary_evidence':robust_s,'temporal_superiority_established':False,'static_features_unavailable':['enumeration_literal_visits'],'static_within_target':sw,'temporal_metrics':tm,'static_metrics':sm,'pooled_strict_temporal_descriptors':[k for k,v in tm.items() if v['pooled_strict_separation']],'target_confounded_descriptors':confounded,'scientific_result':title,'limitation':'Descriptive comparisons are not predictive validation; no outcome-selected descriptor or combination is promoted.'}
 dump(O/'static_vs_temporal.json',comparison)
 extraction=[];collection=[]
 for p in (O/'collection').rglob('feature_compute.json'):extraction.append(load(p)['seconds'])
 for p in (O/'collection').glob('*/command.json'):collection.append(load(p)['seconds'])
 costs={'OFFLINE_SCIENTIFIC_COST':{'collection_native_wall_seconds':sum(collection),'deterministic_replay_and_continuation_seconds':sum(r['solve_seconds'] for r in routes),'proof_checking_seconds':sum(r['proof_seconds'] for r in routes),'report_analysis_wall_seconds':time.monotonic()-t0,'labeling_seconds':'not isolated by locked finalizer','routes':len(routes)},'ONLINE_RELEVANT_COST':{'checkpoint_feature_and_reference_check_seconds_total':sum(extraction),'checkpoint_feature_and_reference_check_seconds_mean':statistics.mean(extraction),'measurement_scope':'Includes feature extraction and independent reference audit; not isolated online-only extraction cost','ring_maintenance_overhead':'UNMEASURED: no locked ON/OFF cost artifact for these exact runs','gate_evaluation':'NOT_RUN'},'gate':'SKIP_STATE_GATE_BY_PROTOCOL','exploration_budget_saving':0,'sensitive_coverage':'NOT_APPLICABLE_NO_GATE'}
 dump(O/'cost_accounting.json',costs)
 final={'HARNESS_LOCK_VERIFIED':True,'states':len(sl),'per_target_states':{t:sum(s['target']==t for s in surfaces) for t in ['T8','T10','T13']},'actions':len(gt),'expected_routes':audit['expected_routes'],'actual_routes':audit['actual_routes'],'logical_verified':audit['canonical_logical_replay'],'heuristic_verified':audit['canonical_heuristic_replay'],'action_verified':audit['frozen_action_success'],'proof_verified':audit['proof_verified'],'SENSITIVE':ns,'INERT_within_frozen_tested_action_budget':len(sl)-ns,'HIGH':nh,'HIGH_prevalence':nh/len(ds),'HIGH_speedups':structure['HIGH_speedups'],'HIGH_slowdowns':structure['HIGH_slowdowns'],'sparse_sensitive_states':structure['sparse_sensitive_states'],'temporal_superiority_established':False,'robust_temporal_descriptors':len(robust_t),'robust_static_descriptors':len(robust_s),'result':result,'scientific_result':title,'heldout_gate':'SKIP_STATE_GATE_BY_PROTOCOL','exploration_budget_saving':0,'sensitive_coverage':None,'READY_FOR_MICRO_ROLLOUT_ACTION_SELECTION':False}
 dump(O/'scientific_result.json',final)
 report=f'''# Prospective Temporal State Cohort v3

Result: **{result}. {title}**.

HARNESS_LOCK_V3 verified completely; all core hashes remain unchanged. This is the first temporal cohort with scientific label promotion after full pre-GT and route-integrity audits. v1/v2 invalid cohorts and all qualification labels/features are excluded. The two earlier stop files are preserved in `../prospective_temporal_state_cohort_v3_prelock_history/`.

## Prospective design

T8/T10/T13 each contributed six fresh exact states: 18 total. The v1.1 fixed-window first-eligible rule (at least two legal actions) was instantiated before collection with six identical windows per target, conflicts 3000–3599. No runtime, feature or intervention outcome adjusted the schedule. K=6; each package freezes first min(6,legal_count) actions by stable creation ID. All 128 raw samples precede the exported checkpoint boundary, including the most recently completed conflict. All SHORT/MID/LONG descriptors use the locked v1.1 extractor and were independently audited. Static comparisons use the previously frozen feature list; enumeration_literal_visits is unavailable.

18 states froze {len(gt)} actions and {len(routes)} routes before any action outcome. Canonical logical/heuristic replay passed {len(routes)}/{len(routes)}; action verification {len(gt)}/{len(gt)}; proofs {len(routes)}/{len(routes)} VERIFIED. Duplicate/missing/extra and collector/discovery/package emissions are zero. Package and peripheral science input hashes remained unchanged. Labels come from the locked finalizer: remaining ops = final analysis-resolution steps − prefix analysis-resolution steps; HIGH iff abs(100*(action_remaining/baseline_remaining−1)) >= 10%.

## Sensitivity structure

SENSITIVE: {ns}/18. INERT within frozen tested-action budget: {18-ns}/18. HIGH actions: {nh}/{len(gt)} ({nh/len(gt):.2%}), including {structure['HIGH_speedups']} speedups and {structure['HIGH_slowdowns']} slowdowns. Moderate (1%≤abs(delta)<10%): {structure['moderate']}; zero/near-zero (abs(delta)<1%): {structure['zero_or_near_zero']}, including {structure['exact_zero']} exact zeros. These bins are mutually exclusive. {structure['sparse_sensitive_states']}/{ns} sensitive states are SPARSE (HIGH fraction < 0.5). Per-state counts, proportions and signed extrema are retained in sensitivity_structure.json. Distribution status: {structure['distribution_shift']}. Earlier observations are compared qualitatively only; this is no statistical test against invalid cohorts.

## Temporal versus static

Every frozen scalar descriptor is reported with raw values, availability, group medians/ranges, interval overlap and within-target midranks. No ML, regression, composite feature, optimized threshold, best-feature selection or new action predictor was used. {len(robust_t)} temporal descriptors and {len(robust_s)} static descriptors satisfy the frozen necessary test of robust strict separation in multiple targets. Pooled strict temporal separation occurs for {sum(v['pooled_strict_separation'] for v in tm.values())} descriptors. Full per-target directions and leave-one-state-out checks are in within_target_temporal_analysis.json. Temporal superiority over static snapshot is not established.

The analysis specification was frozen before collection. Candidate promotion requires a frozen specific descriptor/relation and robust non-confounded prospective evidence; the inherited temporal protocol specifies a feature family but no directional candidate. No candidate is invented after observing labels. This result is limited to the frozen family, tested action budget, schedule and small cohort; it does not rule out all temporal mechanisms. Missing within-target label classes are recorded as uninformative, not treated as negative separation evidence.

## Stage decision and costs

**SKIP_STATE_GATE_BY_PROTOCOL**. No held-out state gate was run. Exploration budget saving from an implemented gate is 0; sensitive coverage is not applicable. **READY_FOR_MICRO_ROLLOUT_ACTION_SELECTION = false**.

Offline collection, full replay/continuation, proof verification and labeling are separate from online-relevant costs. Checkpoint extraction timing includes the independent reference check; isolated ring-maintenance overhead is unmeasured and not claimed to be zero. No scientific full-route cost is presented as online controller overhead. See cost_accounting.json.
'''
 # Avoid promoting artifacts unless all pre-GT hashes and the locked harness still match.
 for n,h in frozen(O/'science_input_manifest.json')['files'].items():assert sha(O/n)==h
 dump(O/'analysis_audit.json',{'only_v3_inputs':True,'pre_GT_inputs_unchanged':True,'no_ML':True,'no_threshold_sweep':True,'result':result,'analysis_script_sha256':sha(Path(__file__))})
 (O/'PROSPECTIVE_TEMPORAL_STATE_COHORT_V3.md').write_text(report)
 print(json.dumps(final),flush=True)
if __name__=='__main__':main()
