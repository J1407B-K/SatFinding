from pathlib import Path
import json,csv,hashlib,statistics,collections,subprocess,sys
R=Path.cwd();O=R/'results/intervention_opportunity_discovery_v1';V=R/'results/prospective_temporal_state_cohort_v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def csvwrite(p,rs):
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rs)
def events(p):return [json.loads(l) for l in p.read_text().splitlines() if l]
def ranks(activity):
 vals=list(activity.values());return {v:1+sum(x>a for x in vals)+.5*(sum(x==a for x in vals)-1) for v,a in activity.items()}
def extract(st,actions,positions,assignment,activity,heap,partial=False):
 rank=ranks(activity);heapr={v:i+1 for i,v in enumerate(heap)};state=dict(st)
 state.update(pending_queue_length=st['trail_length']-st['qhead'],selected_action_count=len(actions),heap_head_var=heap[0] if heap else None,heap_head_activity_rank=rank.get(heap[0]) if heap else None)
 rows=[];sets=[set(map(abs,a['clause'])) for a in actions];distinct=len({a['literal'] for a in actions})
 for idx,a in enumerate(actions):
  implied=a['literal'];var=abs(implied);ants=[l for l in a['clause'] if l!=implied];assert ants
  if assignment:
   assert assignment[var]==2
   assert all(assignment[abs(l)]==(1 if l>0 else 0) for l in ants)
  pp=[positions.get(abs(l)) for l in ants];known=all(x is not None for x in pp)
  # In a recovered pending-prefix map, absent vars are processed only if prefix is complete.
  pending=sum(x is not None and x>=st['qhead'] for x in pp)
  lengths=[len(sets[idx]&other) for j,other in enumerate(sets) if j!=idx]
  jac=[len(sets[idx]&other)/len(sets[idx]|other) for j,other in enumerate(sets) if j!=idx]
  watches=a['clause'][:2];wp=[positions.get(abs(l)) for l in watches]
  watchpend=sum(l!=implied and pos is not None and pos>=st['qhead'] for l,pos in zip(watches,wp))
  row={k:st[k] for k in ['dataset','state_id','target','state_identity']}
  row.update(action_rank=a['rank'],action_id=a['id'],clause_id=a['id'],clause=a['clause'],clause_length=len(a['clause']),source=a['source'],implied_literal=implied,implied_var=var,antecedent_trail_positions=pp,antecedent_min_trail_pos=min(pp) if known else None,antecedent_max_trail_pos=max(pp) if known else None,antecedent_mean_trail_pos=statistics.mean(pp) if known else None,newest_antecedent_age=st['trail_length']-1-max(pp) if known else None,pending_antecedent_count=pending,pending_antecedent_fraction=pending/len(ants),newest_antecedent_relative_to_qhead=max(pp)-st['qhead'] if known else None,all_antecedents_processed=pending==0,implied_var_activity_hex=float.hex(activity[var]) if var in activity else None,implied_var_activity=activity.get(var),implied_var_activity_rank=rank.get(var),implied_var_heap_rank=heapr.get(var),implied_var_in_heap=(var in heapr) if heap else None,same_implied_literal_multiplicity=sum(b['literal']==implied for b in actions),distinct_implied_literal_count=distinct,has_competing_implied_literals=distinct>1,max_variable_overlap=max(lengths) if lengths else 0,mean_variable_overlap=statistics.mean(lengths) if lengths else 0,max_jaccard=max(jac) if jac else 0,mean_jaccard=statistics.mean(jac) if jac else 0,watched_literals=watches,watched_literal_trail_positions=wp,watched_false_pending_count=watchpend,partial_historical_snapshot=partial)
  rows.append(row)
 return state,rows

def main():
 assert sha(O/'OPPORTUNITY_FEATURE_PROTOCOL_V1.json')==(O/'OPPORTUNITY_FEATURE_PROTOCOL_V1.sha256').read_text().strip()
 states=[];actions=[];audit=[];outcomes=[]
 co=load(V/'cohort_manifest.json')
 for e in co['packages']:
  p=V/e['path'];m=load(p/'package_manifest.json');assert sha(p/'package_manifest.json')==e['package_manifest_sha256']
  for n,h in m['files'].items():assert sha(p/n)==h
  s=load(p/'state.json');assert sha(p/'logical.txt')==s['canonical_logical_state_hash'] and sha(p/'heuristic.txt')==s['canonical_heuristic_state_hash']
  logical=(p/'logical.txt').read_text().splitlines();trail=list(map(int,next(l[6:] for l in logical if l.startswith('trail ')).split()));assignment={int(l.split()[1]):int(l.split()[2]) for l in logical if l.startswith('var ')}
  assert len(trail)==s['trail_length'];positions={abs(l):i for i,l in enumerate(trail)};assert len(positions)==len(trail)
  heuristic=(p/'heuristic.txt').read_text().splitlines();activity={int(l.split()[1]):float.fromhex(l.split()[2]) for l in heuristic if l.startswith('var ')};heap=json.loads(next(l.split(' ',1)[1] for l in heuristic if l.startswith('heap_pop_order ')))
  clauses={}
  for l in heuristic:
   if l.startswith('clause '):
    fields=l.split();cid,learned,mark=map(int,fields[1:4]);clauses[cid]=(list(map(int,fields[4:-3] if learned else fields[4:])),learned,mark)
  aa=load(p/'actions.json')['selected']
  for a in aa:assert clauses[a['id']]==(a['clause'],int(a['source']=='learned'),0)
  st=dict(dataset='V3_DISCOVERY',state_id=s['state_id'],target=s['target'],state_identity=s['canonical_logical_state_hash']+':'+s['canonical_heuristic_state_hash'],decision_level=s['level'],trail_length=s['trail_length'],qhead=s['qhead'],conflicts=s['conflicts'],decisions=s['decisions'],propagations=s['propagations'],enqueues=s['enqueues'])
  state,ar=extract(st,aa,positions,assignment,activity,heap);states.append(state);actions+=ar;audit.append({'state_id':s['state_id'],'included':True,'source':'sealed_v3','identity':'canonical logical and heuristic preimages match package manifest','actions_verified':len(aa),'interventions_executed':0})
 csvwrite(O/'opportunity_state_features.csv',states);csvwrite(O/'opportunity_action_features.csv',actions)
 dump(O/'V3_FEATURE_FREEZE.json',{'protocol_sha256':sha(O/'OPPORTUNITY_FEATURE_PROTOCOL_V1.json'),'artifacts':{n:sha(O/n) for n in ['opportunity_state_features.csv','opportunity_action_features.csv']},'states':len(states),'actions':len(actions),'feature_label_association_started':False,'source_snapshot_audits':audit})
 # Historical experiments are audited as same-parent exact forks, never matched via legacy cross-run hash.
 hist=[];hs=[];ha=[];included=[]
 candidates=[('HIST_T10_FIXED','T10',R/'results/fixed_state_action_surface')]+[(f'HIST_T8_{i}','T8',R/f'results/multi_state_action_surface/{i}') for i in ['S1','S2','S3','S4','S5']]
 checker=load(R/'results/harness_qualification_v3/HARNESS_LOCK_V3.json')['checker'];assert sha(Path(checker['path']))==checker['sha256']
 (O/'historical_proof_checks').mkdir()
 for sid,target,p in candidates:
  ev=events(p/'runs/opportunities.jsonl');fr=load(p/'frozen_state.json');parent=next(e for e in ev if e['event']=='FROZEN_STATE');base=load(p/'runs/BASELINE.result.json');baseline=base['stats']['analysis_resolution_steps'];prefix=fr['analysis_ops_at_snapshot']
  aa=[e for e in ev if e['event']=='LEGAL_ACTION' and e['selected']];rr=[load(p/'runs'/f'ACTION_{a["action_index"]}.result.json') for a in aa]
  ds=[100*((r['stats']['analysis_resolution_steps']-prefix)/(baseline-prefix)-1) for r in rr]
  high=sum(abs(d)>=10 for d in ds)
  item={'state_id':sid,'target':target,'state_identity':fr['pre_state_hash'],'identity_scope':'same-parent OS-fork experimental state only; not cross-run canonical','HIGH_actions':high,'included':False,'actions':[]}
  if not high:item['reason']='Audited summary has no >=10% action; not a historical discovery positive';hist.append(item);continue
  assert sha(p/'runs/opportunities.jsonl')==fr['native_selection_log_sha256']
  assert all(fr[k]==v for k,v in parent.items())
  assert [a['stable_clause_id'] for a in aa]==sorted(a['stable_clause_id'] for a in aa)
  assert all(e['wait_status']==0 for e in ev if e['event']=='CHILD_EXIT')
  assert len([e for e in ev if e['event']=='CHILD_EXIT'])==len(aa)+1
  inputpath=R/f'results/high_leverage_discovery/{target}/input.cnf'
  # Every retained action and its baseline have a proof hash and are independently rechecked.
  for tag,result in [('BASELINE',base)]+[(f'ACTION_{a["action_index"]}',r) for a,r in zip(aa,rr)]:
   proof=p/'runs'/(tag+'.drup');assert sha(proof)==result['proof_sha256'] and result['proof_validation']=='VERIFIED' and result['stats']['status']=='UNSAT'
   trace=events(p/'runs'/(tag+'.trace.jsonl'));pre=next(x for x in trace if x['event']=='PRE_STATE')
   assert pre['hash']==fr['pre_state_hash'] and pre['raw_solver_object_hash']==fr['raw_solver_object_hash'] and pre['heap_including_inverse_hash']==fr['heap_including_inverse_hash'] and pre['same_parent_snapshot']
   assert result['same_parent_pre_state']
   c=subprocess.run([checker['path'],str(inputpath),str(proof)],capture_output=True,text=True,timeout=240);(O/'historical_proof_checks'/(sid+'_'+tag+'.txt')).write_text(c.stdout+c.stderr);assert c.returncode==0 and 's VERIFIED' in c.stdout
   if tag!='BASELINE':
    a=aa[int(tag.split('_')[1])-1];enq=next(x for x in trace if x['event']=='EARLY_ENQUEUE');assert enq['literal']==a['implied_literal'] and enq['reason_id']==a['stable_clause_id']
    assert a['unit_verified'] and a['native_reason_layout_compatible']
    assert a['literal_values']==['UNASSIGNED' if l==a['implied_literal'] else 'FALSE' for l in a['clause_literals']]
  pending=fr['trail_length']-fr['qhead'];deq=base['local']['dequeue_literals'];assert len(deq)>=pending,'INCOMPLETE_PENDING_PREFIX'
  initial=deq[:pending];positions={abs(l):fr['qhead']+i for i,l in enumerate(initial)};assert len(positions)==pending
  converted=[{'rank':a['action_index'],'id':a['stable_clause_id'],'literal':a['implied_literal'],'clause':a['clause_literals'],'source':a['source']} for a in aa]
  # If an antecedent is in the pending prefix, its assigned sign must be opposite.
  for a in converted:
   for lit in a['clause']:
    if lit!=a['literal'] and abs(lit) in positions:assert initial[positions[abs(lit)]-fr['qhead']]==-lit
  st=dict(dataset='HISTORICAL_DISCOVERY_POSITIVES',state_id=sid,target=target,state_identity=fr['pre_state_hash'],decision_level=fr['level'],trail_length=fr['trail_length'],qhead=fr['qhead'],conflicts=fr['conflict'],decisions=fr['decision'],propagations=None,enqueues=fr['global_enqueue'])
  state,ar=extract(st,converted,positions,{}, {},[],True);hs.append(state);ha+=ar
  for a,r,delta in zip(converted,rr,ds):
   outcome={'dataset':'HISTORICAL_DISCOVERY_POSITIVES','state_id':sid,'action_rank':a['rank'],'action_id':a['id'],'HIGH_LEVERAGE':abs(delta)>=10,'delta_percent':delta,'proof_sha256':r['proof_sha256']};outcomes.append(outcome);item['actions'].append(outcome)
  item.update(included=True,reason='Exact same-parent fork and action logs matched; all continuation proofs independently reverified; frontier positions recovered from complete baseline initial FIFO dequeue prefix',full_canonical_snapshot_available=False,partial_fields=['activity','semantic_heap_rank','positions_of_processed_antecedents'],recovered_pending_literals=initial,evidence_hashes={str(f.relative_to(R)):sha(f) for f in [p/'frozen_state.json',p/'runs/opportunities.jsonl',p/'runs/BASELINE.result.json']});hist.append(item);included.append(sid)
 # Gold/original case retains exact ORIGINAL-vs-L2 preimages, but the baseline counterfactual's preimage is absent.
 gold=R/'results/original_clause_early_prop'
 hist.append({'state_id':'GOLD_ORIGINAL_CRITICAL','target':'not treated as T8/T10 original CNF','included':False,'reason':'Original early-prop and L2 pre-snapshots align, but BEFORE_PROP_BASELINE has no matched pre-snapshot and uses REMOVE@655. Cannot align the baseline effect to a common exact opportunity snapshot without additional historical reconstruction. Retain as mechanistic context, not discovery feature/label row.','evidence':[str((gold/'event_audit.json').relative_to(R)),str((gold/'ORIGINAL_EARLY_PROP/local.TARGET_PRE.snapshot.json').relative_to(R))]})
 csvwrite(O/'historical_state_features.csv',hs);csvwrite(O/'historical_action_features.csv',ha)
 dump(O/'historical_positive_audit.json',{'candidates':hist,'included_states':len(hs),'included_actions':len(ha),'positive_actions':sum(x['HIGH_LEVERAGE'] for x in outcomes),'independent_proofs_reverified':len(ha)+len(hs)})
 dump(O/'historical_outcomes.json',outcomes)
 dump(O/'DISCOVERY_DATASET_AUDIT.json',{'v3':{'included':True,'states':18,'actions':85,'source_manifest_sha256':sha(V/'SCIENCE_RESULT_MANIFEST.json'),'usage':'discovery only; sealed v3 conclusion unchanged'},'historical':hist,'excluded':[{'source':'temporal_v1','reason':'COHORT_V1_INVALID_FOR_SENSITIVITY_LABELING'},{'source':'temporal_v2','reason':'INVALID_FOR_SCIENTIFIC_PROMOTION'},{'source':'old_qualification','reason':'invalid cross-run identity'},{'source':'qualification_v2/v3','reason':'infrastructure data excluded; not needed for mechanistic discovery'}],'no_new_native_runs':True,'only_proof_checker_runs':len(ha)+len(hs)})
 dump(O/'FEATURE_ARTIFACT_FREEZE.json',{'protocol_sha256':sha(O/'OPPORTUNITY_FEATURE_PROTOCOL_V1.json'),'features_label_association_started':False,'files':{n:sha(O/n) for n in ['opportunity_state_features.csv','opportunity_action_features.csv','historical_state_features.csv','historical_action_features.csv']}})
 print(json.dumps({'v3_features':[len(states),len(actions)],'historical_features':[len(hs),len(ha)],'historical_HIGH':sum(x['HIGH_LEVERAGE'] for x in outcomes),'feature_freeze_complete':True}))
if __name__=='__main__':main()
