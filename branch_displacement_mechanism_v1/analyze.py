"""Deterministic paired mechanistic tables; no fitted cutoffs or prediction."""
import sys
from collections import Counter
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from run import *
def events(d):return list(map(json.loads,(d/'events.jsonl').read_text().splitlines()))
def csvwrite(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,keys);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def brief(e):return {k:v for k,v in e.items() if k not in ['activity_vector','heap_order']}
def key(e):
 if e['type']=='heap_activity':return (e['type'],e['heap_order'],e['activity_vector'])
 return (e['type'],e['literal'],e['clause'],e['level'])
def classify(a,b):
 kinds={a['type'],b['type']}
 if kinds <= {'decision','enqueue'}:return 'BRANCH_FIRST'
 if kinds & {'propagated_assignment','dequeue','enqueue'}:return 'PROPAGATION_FIRST'
 if kinds & {'conflict_clause','conflict_analysis'}:return 'CONFLICT_FIRST'
 return 'OTHER_FIRST'
def divergence(b,h,var,projection=None,normalize=True):
 def seq(es):
  out=[];omit_natural=normalize and not any(e['injection'] for e in es)
  for e in es:
   if e['type'] in ['checkpoint','restoration','suppression','restoration_unavailable','suppression_unavailable'] or e['injection']:continue
   if omit_natural and e['type']=='propagated_assignment' and abs(e['literal'])==var:
    omit_natural=False;continue
   if projection is None or e['type'] in projection:out.append(e)
  return out
 bs,hs=seq(b),seq(h)
 for i,(x,y) in enumerate(zip(bs,hs)):
  if key(x)!=key(y):
   return {'type':classify(x,y),'aligned_index':i,'baseline_event_index':x['index'],'treatment_event_index':y['index'],'decision_count_offset':y['decisions']-x['decisions'],'propagation_count_offset':y['dequeues']-x['dequeues'],'conflict_count_offset':y['conflicts']-x['conflicts'],'baseline':brief(x),'treatment':brief(y)}
 return {'type':'NO_CHANGE_WITHIN_OBSERVED_HORIZON','compared_events':min(len(bs),len(hs)),'censored':True}
def fate(es,var):
 stop=None
 for e in es[1:]:
  if e['type']=='decision' and abs(e['literal'])==var:stop=('A_DECISION',e);break
  if e['type']=='propagated_assignment' and abs(e['literal'])==var:stop=('B_NATURAL_PROPAGATION',e);break
  if e['type']=='enqueue' and abs(e['literal'])==var:stop=('C_OTHER_ASSIGNMENT',e);break
  if e['type']=='conflict_clause':stop=('D_CONFLICT',e);break
  if e['type']=='restart':stop=('E_RESTART',e);break
 if stop is None:stop=('F_HORIZON',es[-1])
 name,e=stop;prefix=es[:e['index']+1];cp=es[0]
 ds=[x for x in es if x['type']=='decision'][:8]
 positions=[i+1 for i,x in enumerate(ds) if abs(x['literal'])==var]
 return {'activity':cp['activity'],'activity_rank':cp['activity_rank'],'heap_rank':cp['heap_rank'],'heap_membership':cp['heap_member'],'current_top_branch_candidate':cp['top_candidate'],'fate':name,'fate_event_index':e['index'],'events_until_fate':e['index'],'dequeues_until_fate':e['dequeues'],'propagated_assignments_until_fate':sum(x['type']=='propagated_assignment' for x in prefix),'conflicts_until_fate':e['conflicts'],'decisions_until_fate':e['decision_ordinal'],'heap_rank_trajectory':[{'event_index':x['index'],'rank':x['heap_rank']} for i,x in enumerate(prefix) if i==0 or x['heap_rank']!=prefix[i-1]['heap_rank']],'activity_rank_trajectory':[{'event_index':x['index'],'rank':x['activity_rank']} for i,x in enumerate(prefix) if i==0 or x['activity_rank']!=prefix[i-1]['activity_rank']],'reaches_heap_top_before_fate':any(x['heap_rank']==1 for x in prefix),'reaches_branch_candidate_before_fate':any(x['top_candidate']==var for x in prefix),'next_decisions':[x['literal'] for x in ds],'next_decision_positions':positions,'next_decisions_observed':len(ds),'would_be_next_decision':1 in positions,**{f'next_{n}':any(i<=n for i in positions) for n in [1,2,4,8]},'branch_candidate_anytime_in_horizon':any(x['top_candidate']==var for x in es)}
def cases():
 rows=[]
 for rank,high in [(2,True),(1,False)]:
  act=load(PKG/'actions.json')['selected'][rank-1]
  rows.append({'target':'T10','state_id':PKG.name,'rank':rank,'action_id':act['id'],'literal':act['literal'],'clause':act['clause'],'source':act['source'],'HIGH':high,'baseline_dir':OUT/'runs'/('BASELINE' if high else 'CONTROL_BASELINE'),'action_dir':OUT/'runs'/('HIGH' if high else 'CONTROL'),'original':PKG,'historical':False})
 for target,rank,high in [('T10',1,True),('T10',2,True),('T10',5,True),('T10',3,False),('T8',4,True),('T8',1,False)]:
  sid='HIST_T10_FIXED' if target=='T10' else 'HIST_T8_S5';d=OUT/'historical_runs'/f'{sid}_R{rank}'
  meta=load(d/f'ACTION_{rank}/result.json');act=meta['action']
  rows.append({'target':target,'state_id':sid,'rank':rank,'action_id':act['stable_clause_id'],'literal':act['implied_literal'],'clause':act['clause_literals'],'source':act['source'],'HIGH':high,'baseline_dir':d/'BASELINE','action_dir':d/f'ACTION_{rank}','original':ROOT/('results/fixed_state_action_surface' if target=='T10' else 'results/multi_state_action_surface/S5'),'historical':True})
 return rows
def identity_audit(c):
 b=load(c['baseline_dir']/'result.json');h=load(c['action_dir']/'result.json');delta=100*(h['remaining_ops']/b['remaining_ops']-1)
 assert (abs(delta)>=10)==c['HIGH']
 row={k:v for k,v in c.items() if k not in ['baseline_dir','action_dir','original']}
 row.update(included=True,implied_var=abs(c['literal']),effect_percent=delta,clause_sha256=hashlib.sha256(json.dumps(sorted(c['clause'])).encode()).hexdigest(),source_artifact=str(c['original'].relative_to(ROOT)),new_replay_evidence=str((c['action_dir']/'result.json').relative_to(ROOT)),proof='VERIFIED',proof_sha256=h['proof_sha256'])
 if not c['historical']:
  st=load(PKG/'state.json');row['state_identity_evidence']=st
  row['proof_path']=str((c['action_dir']/'proof.drup').relative_to(ROOT))
  matches=[load(p) for p in (ROOT/'results/prospective_temporal_state_cohort_v3/route_results').glob('*/route_metadata.json') if load(p)['package_id']==PKG.name]
  for meta,rank in [(b,None),(h,c['rank'])]:
   orig=next(m for m in matches if m['action_rank']==rank)
   assert meta['proof_sha256']==orig['proof_sha256']
   assert all(meta['native_result'][k]==v for k,v in orig['native_result'].items())
  row['original_full_route_equivalence']=True;row['rank_identity_scope']='v3 canonical state verified'
 else:
  assert b['original_route_equivalent'] and h['original_route_equivalent']
  original=load(c['original']/'frozen_state.json');row['state_identity_evidence']=original
  row['proof_path']=str((c['action_dir'].parent/f'ACTION_{c["rank"]}.drup').relative_to(ROOT))
  row['rank_identity_scope']='native historical reconstruction; guarded operational replay + matched original binary/source + full proof/counters; no original canonical snapshot and no claim of canonical cross-build identity'
  row['original_full_route_equivalence']=True
  original_attempt=OUT/'historical_replay_attempts'/c['state_id']
  for tag in ['BASELINE',f'ACTION_{c["rank"]}']:
   orig=load(c['original']/'runs'/f'{tag}.result.json')
   assert sha(original_attempt/f'{tag}.drup')==orig['proof_sha256']
   stats=next(json.loads(x) for x in reversed((original_attempt/f'{tag}.stdout.txt').read_text().splitlines()) if x.startswith('{'))
   assert all(stats[k]==v for k,v in orig['stats'].items() if k!='seconds')
 row['proof_actual_sha256']=sha(ROOT/row['proof_path']);assert row['proof_actual_sha256']==row['proof_sha256']
 return row
def cf(c,mode):
 if c['historical']:
  d=c['action_dir'].parent.with_name(c['action_dir'].parent.name+'_'+mode)
  d=d/(f'ACTION_{c["rank"]}' if mode=='restore' else 'BASELINE')
 else:d=OUT/'runs'/('HIGH_RESTORE1' if mode=='restore' else 'SUPPRESS_BRANCH1')
 meta=load(d/'result.json');es=events(d);be=events(c['baseline_dir']);he=events(c['action_dir'])
 hits=[e for e in es if e['type']==('restoration' if mode=='restore' else 'suppression')]
 assert len(hits)==1,(c,mode,hits)
 b=load(c['baseline_dir']/'result.json');h=load(c['action_dir']/'result.json')
 bc,hc,cc=b['remaining_ops'],h['remaining_ops'],meta['remaining_ops']
 att=1-abs(cc-bc)/abs(hc-bc);ratio=(cc-bc)/(hc-bc)
 bd=[e['literal'] for e in be if e['type']=='decision'][:8];hd=[e['literal'] for e in he if e['type']=='decision'][:8];cd=[e['literal'] for e in es if e['type']=='decision'][:8]
 firstlearn=lambda ee: next(e['clause'] for e in ee if e['type']=='learned_clause')
 bl,hl,cl=[[e['clause'] for e in ee if e['type']=='learned_clause'] for ee in [be,he,es]]
 changed=next(i for i,(x,y) in enumerate(zip(bl,hl)) if x!=y)
 return {'state_id':c['state_id'],'action_id':c['action_id'],'mode':mode,'performed':True,'depth':1,'branch_ordinal':hits[0]['decision_ordinal'],'baseline_branch_literal':hits[0]['literal'],'branch_is_implied_variable':abs(hits[0]['literal'])==abs(c['literal']),'intervention_event':brief(hits[0]),'baseline_remaining_ops':bc,'high_remaining_ops':hc,'counterfactual_remaining_ops':cc,'high_effect_percent':100*(hc/bc-1),'counterfactual_effect_percent':100*(cc/bc-1),'attenuation_fraction':att,'signed_high_shift_reproduced':ratio,'substantial_attenuation':att>=.5,'partial_same_direction_cost_reproduction':ratio>=.5,'baseline_conflicts':b['native_result']['conflicts'],'high_conflicts':h['native_result']['conflicts'],'counterfactual_conflicts':meta['native_result']['conflicts'],'baseline_next8':bd,'high_next8':hd,'counterfactual_next8':cd,'next8_equal_baseline':bd==cd,'next8_equal_high':hd==cd,'baseline_first_learned':firstlearn(be),'high_first_learned':firstlearn(he),'counterfactual_first_learned':firstlearn(es),'first_learned_equal_high':firstlearn(es)==firstlearn(he),'high_first_changed_learned_ordinal':changed+1,'counterfactual_reproduces_first_high_changed_learned':cl[changed]==hl[changed],'first_divergence_from_baseline':divergence(be,es,abs(c['literal'])),'proof':'VERIFIED','proof_sha256':meta['proof_sha256'],'route_evidence':str(d.relative_to(ROOT))}
def main():
 assert sha(OUT/'BRANCH_DISPLACEMENT_PROTOCOL_V1.json')==(OUT/'BRANCH_DISPLACEMENT_PROTOCOL_V1.sha256').read_text().strip()
 cs=cases();audits=[identity_audit(c) for c in cs]
 old=load(ROOT/'results/intervention_opportunity_discovery_v1/historical_positive_audit.json')
 audit={'study':'exploratory mechanistic causal','included_high_states':len(set(c['state_id'] for c in cs if c['HIGH'])),'included_high_actions':sum(c['HIGH'] for c in cs),'included_matched_controls':sum(not c['HIGH'] for c in cs),'included':audits,'excluded_candidates':[c for c in old['candidates'] if not c['included']],'historical_identity_limit':'Historical reconstruction is tied to archived native build/guard and byte-identical full routes. It does not upgrade old operational hashes to canonical identity. Canonical_cross_build_rank fields remain unavailable.'}
 dump(OUT/'MECHANISM_DATASET_AUDIT.json',audit)
 fates=[];divs=[];rest=[];supp=[];pairs=[]
 for c in cs:
  base=events(c['baseline_dir']);high=events(c['action_dir']);var=abs(c['literal'])
  row={'state_id':c['state_id'],'action_id':c['action_id'],'HIGH':c['HIGH'],'implied_literal':c['literal'],'implied_var':var,**fate(base,var)}
  firstbranch=next((e for e in base if e['type']=='decision' and abs(e['literal'])==var and e['decision_ordinal']<=8),None)
  row.update(first_branch_event_index=firstbranch['index'] if firstbranch else None,time_to_first_decision_dequeues=firstbranch['dequeues'] if firstbranch else None,time_to_first_decision_conflicts=firstbranch['conflicts'] if firstbranch else None,reaches_heap_top_within_next8_window=any(e['heap_rank']==1 for e in base if e['decision_ordinal']<=8))
  hd=[x['literal'] for x in high if x['type']=='decision'][:8]
  row['high_or_control_next8']=hd;row['implied_branch_displaced_positions']=[i for i in row['next_decision_positions'] if abs(hd[i-1])!=var];row['historical_native_rank']=c['historical'];row['canonical_cross_build_rank']='unavailable' if c['historical'] else 'v3 verified'
  fates.append(row)
  divs.append({'state_id':c['state_id'],'action_id':c['action_id'],'HIGH':c['HIGH'],'first_downstream':divergence(base,high,var),'raw_after_injection_omitted':divergence(base,high,var,normalize=False),'other_assignment_divergence':divergence(base,high,var,{'propagated_assignment'}),'first_decision_divergence':divergence(base,high,var,{'decision'}),'first_conflict_divergence':divergence(base,high,var,{'conflict_clause'}),'first_learned_divergence':divergence(base,high,var,{'learned_clause'}),'first_heap_activity_divergence':divergence(base,high,var,{'heap_activity'})})
  if c['HIGH']:rest.append(cf(c,'restore'));supp.append(cf(c,'suppress'))
 for h in [f for f in fates if f['HIGH']]:
  c=next(f for f in fates if not f['HIGH'] and f['state_id']==h['state_id'])
  pairs.append({'state_id':h['state_id'],'high_action':h['action_id'],'control_action':c['action_id'],**{f'{group}_{key}':row[key] for group,row in [('high',h),('control',c)] for key in ['activity','activity_rank','heap_rank','fate','dequeues_until_fate','next_decision_positions','implied_branch_displaced_positions','first_branch_event_index','time_to_first_decision_dequeues','time_to_first_decision_conflicts']},**{f'{group}_first_downstream_divergence':next(d['first_downstream']['type'] for d in divs if d['state_id']==row['state_id'] and d['action_id']==row['action_id']) for group,row in [('high',h),('control',c)]}})
 csvwrite('baseline_fate_tracking.csv',[f for f in fates if f['HIGH']]);csvwrite('matched_control_fate_tracking.csv',[f for f in fates if not f['HIGH']]);csvwrite('branch_displacement_observation.csv',fates)
 csvwrite('historical_positive_branch_context.csv',[f for f in fates if f['historical_native_rank']]);csvwrite('high_vs_nonhigh_pairs.csv',pairs)
 dump(OUT/'FIRST_DIVERGENCE.json',divs)
 flat=[]
 for d in divs:
  first=d['first_downstream'];flat.append({'state_id':d['state_id'],'action_id':d['action_id'],'HIGH':d['HIGH'],'first_downstream_divergence_type':first['type'],**{k:v for k,v in first.items() if k!='type'}})
 csvwrite('first_divergence.csv',flat);csvwrite('branch_restoration_results.csv',rest);csvwrite('branch_suppression_results.csv',supp)
 hs=[f for f in fates if f['HIGH']]
 result={'result':'B','verdict':'BRANCH_DISPLACEMENT_NOT_PRIMARY_MECHANISM','scope':'Direct removal of a high-priority imminent branch is not the primary initiating carrier in these five actions; downstream branch choices can still mediate cost. Not a universal rejection of branch mediation.','auditable_high_states':audit['included_high_states'],'auditable_high_actions':len(hs),'next_decision_counts':{str(n):sum(f[f'next_{n}'] for f in hs) for n in [1,2,4,8]},'high_initial_fates':dict(Counter(f['fate'] for f in hs)),'first_downstream_distribution':dict(Counter(d['first_downstream']['type'] for d in divs if d['HIGH'])),'restoration_performed':len(rest),'restoration_substantial_attenuation_count':sum(r['substantial_attenuation'] for r in rest),'suppression_action_comparisons':len(supp),'suppression_unique_interventions':len(set((r['state_id'],r['branch_ordinal'],r['baseline_branch_literal']) for r in supp)),'suppression_partial_cost_reproduction_count':sum(r['partial_same_direction_cost_reproduction'] for r in supp),'historical_high_initial_activity':[f['activity'] for f in hs if f['historical_native_rank']],'next_mechanism':'PROPAGATION_ORDER / IMPLICATION_GRAPH BIFURCATION','causal_interpretation':'All first downstream divergences precede the first new decision; historical checkpoint priorities do not replicate v3 high activity. Counterfactuals intervene on later changed branches, not the already naturally implied variable at the checkpoint; cost similarity alone is not channel identification.'}
 result.update(suppression_reproduces_first_high_changed_learned_count=sum(r['counterfactual_reproduces_first_high_changed_learned'] for r in supp),suppression_next8_equal_high_count=sum(r['next8_equal_high'] for r in supp))
 assert result['first_downstream_distribution']=={'PROPAGATION_FIRST':5}
 dump(OUT/'MECHANISM_RESULT.json',result)
 print(json.dumps(result,indent=2));print('RESTORATION',[(r['action_id'],r['counterfactual_effect_percent'],r['attenuation_fraction']) for r in rest]);print('SUPPRESSION',[(r['action_id'],r['counterfactual_effect_percent'],r['signed_high_shift_reproduced']) for r in supp]);print('FATES',[(r['action_id'],r['activity_rank'],r['heap_rank'],r['fate'],r['dequeues_until_fate'],r['next_decision_positions']) for r in fates])
if __name__=='__main__':main()
