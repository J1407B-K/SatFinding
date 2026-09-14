from pathlib import Path
import sys,json,hashlib,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from prospective_temporal_schema import feature_schema_sha256
O=ROOT/'results/prospective_temporal_state_cohort_v3'
Q=ROOT/'results/harness_qualification_v3'
lock=load(Q/'HARNESS_LOCK_V3.json');checks=[]
def check(p,h):
 actual=sha(p) if p.is_file() else None;checks.append({'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'expected':h,'actual':actual,'match':actual==h})
check(Q/'HARNESS_LOCK_V3.json',(Q/'HARNESS_LOCK_V3.sha256').read_text().strip())
for n,h in lock['components'].items():check(ROOT/n,h)
for n,h in lock['evidence'].items():check(Q/n,h)
check(Path(lock['checker']['path']),lock['checker']['sha256'])
assert feature_schema_sha256()==lock['canonical_schema_sha256']
assert all(c['match'] for c in checks)
# Preserve the earlier pre-V3-lock stop report, which contains no scientific cohort.
if O.exists():
 assert set(p.name for p in O.iterdir())=={'HARNESS_LOCK_VERIFICATION.json','PROSPECTIVE_TEMPORAL_STATE_COHORT_V3.md'}
 O.rename(ROOT/'results/prospective_temporal_state_cohort_v3_prelock_history')
O.mkdir()
dump(O/'HARNESS_LOCK_VERIFICATION.json',{'LOCK_VERIFIED':True,'time':stamp(),'lock_sha256':sha(Q/'HARNESS_LOCK_V3.json'),'checks':checks,'canonical_schema_sha256':feature_schema_sha256(),'core_modified':False})
freeze(O/'build_manifest.json',{'components':lock['components'],'checker':lock['checker'],'harness_lock_sha256':sha(Q/'HARNESS_LOCK_V3.json')})
inputs=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['inputs']
plan={'purpose':'PROSPECTIVE_TEMPORAL_STATE_COHORT_V3','rule_source':'frozen temporal protocol v1.1: fixed conflict checkpoints, >=2 legal actions, outcome-blind; locked first_eligible_per_window collector','numeric_schedule':'six consecutive 100-conflict windows starting at 3000, identical for all targets; frozen before collection, without feature/outcome inspection','collections':[{'target':t,'input':inputs[t]['path'],'input_sha256':inputs[t]['sha256'],'requested_state_count':6,'K':6,'checkpoint_rule':{'kind':'first_eligible_per_window','windows':[[b,b+99] for b in range(3000,3600,100)],'minimum_legal_count':2}} for t in ['T8','T10','T13']]}
freeze(O/'collection_plan.json',plan)
static=ROOT/'results/state_sensitivity_abstraction/frozen_state_features.json'
# These decisions describe reporting/evidence only, not features or solver behavior.
freeze(O/'analysis_specification.json',{
 'time':stamp(),'protocol_sha256':sha(PROTOCOL),'schema_sha256':feature_schema_sha256(),'static_feature_spec':str(static.relative_to(ROOT)),'static_feature_spec_sha256':sha(static),
 'inputs':'Only this prospective v3 cohort; no v1/v2 or qualification feature/label data',
 'feature_policy':'Report every scalar leaf of the frozen temporal schema in schema order; no fitted model, feature selection, composite, optimized direction or threshold search',
 'ranking':'midrank=(count_less+0.5*count_equal), normalized=midrank/n; ties preserved',
 'overlap':'intersection width / pooled range width for group intervals; boundary contact counts as overlap; unavailable when one group absent',
 'candidate_necessary_evidence':'For a single frozen descriptor, strict nonoverlap in at least two informative targets with same sensitive direction, no opposite direction in any other informative target, direction/nonoverlap preserved after deleting any single state, and no static descriptor with equal evidence. Report all descriptors, never select a best descriptor post hoc. A requires an already frozen specific descriptor/relation in addition to these necessary tests.',
 'A_policy':'No specific directional candidate relation is present in the inherited protocol. Do not invent one after outcomes. Descriptive feature separation alone cannot justify A.',
 'C_policy':'C only if strict pooled temporal separation exists but its direction is opposite or absent in every informative within-target comparison; mere overlap is insufficient to assert target confounding.',
 'B_policy':'Otherwise B: no simple abstraction satisfying the requested frozen candidate and robust within-target criteria within this feature family/cohort; not a claim about all possible temporal mechanisms.',
 'effect_bins':{'HIGH':'abs(delta)>=10','ZERO_OR_NEAR_ZERO':'abs(delta)<1','MODERATE':'1<=abs(delta)<10','EXACT_ZERO':'remaining_ops equal'},
 'sparse':'sensitive high_fraction < 0.5, matching previous frozen reporting definition',
 'rare_reporting':'Report fractions without newly tuned rare/concentration thresholds',
 'static_missing':'enumeration_literal_visits is not exported by the locked collector; mark unavailable, do not invent it',
 'cost':'offline collection/routes/proofs/labels separate from online-relevant measured checkpoint extraction; isolated ring overhead unavailable without a locked ON/OFF measurement',
 'gate':'B/C skip by protocol; no post hoc candidate or gate'
})
print(json.dumps({'LOCK_VERIFIED':True,'checks':len(checks),'plan_frozen':True,'ground_truth_routes_started':0}))
