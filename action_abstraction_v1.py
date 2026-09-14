"""Pre-action descriptors from existing artifacts only; no solver or intervention runs."""
import csv,json,hashlib
from pathlib import Path
from collections import Counter
OUT=Path('results/action_abstraction_v1')
U='UNAVAILABLE'
SOURCES={'T10':Path('results/fixed_state_action_surface'),'T8':Path('results/multi_state_action_surface/S5')}
NUM=['clause_length','implied_literal_activity','implied_literal_heap_rank','active_clause_occurrence_count','binary_occurrence_count','ternary_occurrence_count','long_occurrence_count','same_literal_almost_unit_neighbor_count','opposite_literal_almost_unit_neighbor_count','local_clause_fanout','antecedent_level_min','antecedent_level_max','antecedent_level_mean','antecedent_level_distinct_count']
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writecsv(p,rows):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def readcnf(p):
 clauses=[];cur=[]
 for line in p.read_text().splitlines():
  if not line or line[0] in 'cp':continue
  for lit in map(int,line.split()):
   if lit:cur.append(lit)
   else:clauses.append(cur);cur=[]
 assert not cur
 return clauses

def main():
 OUT.mkdir(exist_ok=False)
 protocol={'states':{t:str(p) for t,p in SOURCES.items()},'features':NUM+['original_or_learned'],'stage_order':'Write all pre-action features and rankings before loading action-run labels. No performance-dependent feature computation.','rank':'Ascending raw value,1-based average ranks for ties; normalized rank=(rank-1)/(N-1). All-tied feature has normalized rank0.5. Higher numeric value => higher normalized rank; heap smaller position means nearer array front.','missing':'UNAVAILABLE; if any action lacks a feature, all ranks for that feature/state are UNAVAILABLE. No partial-population rankings or substitution features.','almost_unit':'Active clause contains the specified signed literal, no true literals, exactly2 unassigned. Keep literal/opposite counts separate. Only infer when existing pre-state assignment facts completely determine membership.','occurrence':'Active clauses containing implied variable, counted once per clause; binary2/ternary3/long>3. Fanout is same active occurrence count, not a new derived feature.','antecedents':'Decision levels of all false non-implied literals in action clause; summaries from exact-hash descriptors only.','consistent_discrimination':'For every fixed numeric feature with complete data in both states, test strict ordered separation: all HIGH greater than all ZERO in both states, or all HIGH less than all ZERO in both. Ties crossing classes fail. Rank equivalent. No fitted cutoffs or feature combinations. Categorical source requires consistent disjoint category membership.','labels':'Existing abs(delta)>=10% vs existing exact-zero labels; sign is not analyzed.','scope':'Only existing files and fixed solver initialization invariants; no rerun/new instrumentation/new action.'}
 dump(OUT/'protocol.json',protocol)
 features=[];provenance={};snapshots={};hashes={}
 for t,src in SOURCES.items():
  snapshot=json.loads((src/'frozen_state.json').read_text());snapshots[t]=snapshot;assert snapshot['conflict']==0 and snapshot['analysis_ops_at_snapshot']==0
  actions=list(csv.DictReader((src/'legal_actions.csv').open()));cnf=Path('results/high_leverage_discovery')/t/'input.cnf';clauses=readcnf(cnf)
  assert len(clauses)==2600 and min(map(len,clauses))>=2
  assert all(len(c)==len(set(c)) and not any(-x in c for x in c) for c in clauses)
  # Both fixed C0 snapshots precede all analysis; initial CNF has no units/tautologies.
  # No root assignments => initial simplify removes no clauses; no learned/deletion before conflict1.
  # Glucose activity initializes0 (rnd-init false; thin driver doesn't override it), bumps only in analyze.
  solver=Path('/private/tmp/satfinding-fixed-state-action-surface/glucose-3.0/core/Solver.cc').read_text()
  assert 'activity .push(rnd_init_act ? drand(random_seed) * 0.00001 : 0)' in solver
  assert 'Randomize the initial activity", false)' in solver
  logfile=Path('results/state_sensitivity_cohort')/t/'local/opportunities.jsonl';logs=[json.loads(x) for x in logfile.read_text().splitlines()]
  opps={e['opportunity']:e for e in logs if e['event']=='OPPORTUNITY' and e['pre_state_fnv64']==snapshot['pre_state_hash']}
  descriptors={}
  for e in logs:
   if e['event']=='DESCRIPTORS' and e['opportunity'] in opps:
    o=opps[e['opportunity']];descriptors[(o['reason_id'],o['literal'])]=e
  facts={}
  for a in actions:
   for lit,status in zip(json.loads(a['clause_literals']),json.loads(a['literal_values'])):
    value=None if status=='UNASSIGNED' else lit<0
    if abs(lit) in facts:assert facts[abs(lit)]==value
    facts[abs(lit)]=value
  def signed_almost(lit):
   count=0
   for c in clauses:
    if lit not in c:continue
    unset=0;sat=False;unknown=0
    for x in c:
     if abs(x) not in facts:unknown+=1
     elif facts[abs(x)] is None:unset+=1
     elif facts[abs(x)]==(x>0):sat=True
    if sat or unset>2 or unset+unknown<2:continue
    if unknown:return U
    count+=unset==2
   return count
  for a in actions:
   cid=int(a['stable_clause_id']);lit=int(a['implied_literal']);lits=json.loads(a['clause_literals']);key=(cid,lit);desc=descriptors.get(key)
   assert sorted(lits)==sorted(clauses[cid-1])
   neighborhood=[c for c in clauses if any(abs(x)==abs(lit) for x in c)]
   levels=[]
   if desc:
    assert float.fromhex(desc['candidate_activity_hex'])==0 and desc['local_clause_fanout']==len(neighborhood)
    for lev,n in desc['antecedent_level_distribution'].items():levels.extend([int(lev)]*n)
    assert len(levels)==len(lits)-1
   r={'state':t,'pre_state_hash':snapshot['pre_state_hash'],'action_id':'ACTION_'+a['action_index'],'clause_id':cid,'implied_literal':lit,'clause_length':len(lits),'original_or_learned':a['source'],'implied_literal_activity':0.0,'implied_literal_heap_rank':desc['heap_array_position'] if desc else U,'active_clause_occurrence_count':len(neighborhood),'binary_occurrence_count':sum(len(c)==2 for c in neighborhood),'ternary_occurrence_count':sum(len(c)==3 for c in neighborhood),'long_occurrence_count':sum(len(c)>3 for c in neighborhood),'same_literal_almost_unit_neighbor_count':signed_almost(lit),'opposite_literal_almost_unit_neighbor_count':signed_almost(-lit),'local_clause_fanout':len(neighborhood),'antecedent_level_min':min(levels) if levels else U,'antecedent_level_max':max(levels) if levels else U,'antecedent_level_mean':sum(levels)/len(levels) if levels else U,'antecedent_level_distinct_count':len(set(levels)) if levels else U}
   features.append(r)
  provenance[t]={'active_db_reason':'C0, no initial units/tautologies/duplicates, no root assignment; no learned or clause removal before first conflict. Clause literal order may change, membership does not. Original CNF is valid for occurrence counts.','activity_reason':'rnd-init=false default with no driver override, initialization0, bumps only in analyze; snapshot conflict0 and analysis_ops0.','exact_descriptor_actions':[{'clause_id':k[0],'literal':k[1]} for k in descriptors],'missing_reason':'No full serialized assignment/heap/levels. Existing variable-level almost-unit total is not used as signed count. Hashes are not invertible snapshots.','snapshot_is_manifest':True}
  for p in [src/'frozen_state.json',src/'legal_actions.csv',cnf,logfile]:hashes[str(p)]=sha(p)
 writecsv(OUT/'action_features.csv',features)
 rankings=[]
 for t in SOURCES:
  rr=[r for r in features if r['state']==t];n=len(rr)
  for field in NUM:
   vals=[r[field] for r in rr];complete=all(v!=U for v in vals)
   for r in rr:
    v=r[field];rank=1+sum(x<v for x in vals)+0.5*(sum(x==v for x in vals)-1) if complete else U
    norm=(rank-1)/(n-1) if complete else U
    rankings.append({'state':t,'action_id':r['action_id'],'feature':field,'raw_value':v,'rank_ascending_among_all_actions':rank,'normalized_rank':norm,'legal_action_count':n,'known_raw_values':sum(x!=U for x in vals),'complete_state_feature':complete})
 writecsv(OUT/'within_state_rankings.csv',rankings)
 # Labels are joined only after the pre-action dataset and all rankings are written.
 labels={}
 for t,src in SOURCES.items():
  for r in csv.DictReader((src/'all_action_runs.csv').open()):
   high=r['HIGH_LEVERAGE']=='True';zero=float(r['relative_ops_delta_percent'])==0
   assert high!=zero
   labels[(t,r['action_id'])]='HIGH_LEVERAGE' if high else 'ZERO'
 comparisons={};candidate=[]
 for field in NUM:
  states={}
  for t in SOURCES:
   rr=[r for r in features if r['state']==t];groups={label:[r[field] for r in rr if labels[(t,r['action_id'])]==label] for label in ['HIGH_LEVERAGE','ZERO']}
   complete=all(v!=U for vs in groups.values() for v in vs);relation='UNAVAILABLE'
   if complete:
    h,z=groups['HIGH_LEVERAGE'],groups['ZERO'];relation='HIGH_STRICTLY_GREATER' if min(h)>max(z) else 'HIGH_STRICTLY_LESS' if max(h)<min(z) else 'OVERLAP_OR_TIES'
   states[t]={'raw_values_by_class':groups,'rank_values_by_class':{label:[r['normalized_rank'] for r in rankings if r['state']==t and r['feature']==field and labels[(t,r['action_id'])]==label] for label in groups},'complete':complete,'relation':relation}
  relations=[v['relation'] for v in states.values()];consistent=len(set(relations))==1 and relations[0] in ['HIGH_STRICTLY_GREATER','HIGH_STRICTLY_LESS']
  comparisons[field]={'states':states,'consistent_discrimination':consistent}
  if consistent:candidate.append(field)
 comparisons['original_or_learned']={'states':{t:{label:sorted(set(r['original_or_learned'] for r in features if r['state']==t and labels[(t,r['action_id'])]==label)) for label in ['HIGH_LEVERAGE','ZERO']} for t in SOURCES},'consistent_discrimination':False}
 assert all(r['original_or_learned']=='original' for r in features)
 summary={'classification':'CANDIDATE_ACTION_ABSTRACTION' if candidate else 'NO_SIMPLE_ACTION_LOCAL_ABSTRACTION','candidate_features':candidate,'feature_comparisons':comparisons,'label_counts':{t:dict(Counter(label for (state,_),label in labels.items() if state==t)) for t in SOURCES},'action_labels':[{'state':t,'action_id':a,'label':v} for (t,a),v in labels.items()],'provenance':provenance,'input_sha256':hashes,'preaction_features_sha256':sha(OUT/'action_features.csv'),'rankings_sha256':sha(OUT/'within_state_rankings.csv'),'protocol_sha256':sha(OUT/'protocol.json'),'missing_data_limits_conclusion':True,'solver_runs':0,'prospective_test_performed':False}
 dump(OUT/'cross_cnf_comparison.json',summary)
 print(summary['classification'])
 for f,x in comparisons.items():
  if f!='original_or_learned':print(f,{t:(v['complete'],v['relation']) for t,v in x['states'].items()})
if __name__=='__main__':main()
