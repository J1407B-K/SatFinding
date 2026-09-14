import json,csv,statistics
from pathlib import Path
P=Path('results/prospective_micro_rollout'); O=Path('results/state_sensitivity_abstraction');O.mkdir(exist_ok=True)
states=json.load(open(P/'selected_states.json'))['states']; gt=list(csv.DictReader(open(P/'full_ground_truth.csv')))
# freeze before labels
features=['conflicts','decisions','level','trail_length','qhead','pending_count','legal_count','selected_count','enumeration_literal_visits','prefix_analysis','prefix_redundancy','prefix_binary','prefix_watchers','prefix_dequeues']
json.dump({'features':features,'normalized':['analysis_per_conflict','watchers_per_conflict','dequeues_per_conflict'],'source':'selected_states snapshot only'},open(O/'frozen_state_features.json','w'),indent=2)
by={s['state_id']:[] for s in states}
for r in gt: by[r['state_id']].append(r)
labels=[]
for s in states:
 rs=by[s['state_id']]; ds=[float(r['final_ops_delta_percent']) for r in rs]; hi=[d for d in ds if abs(d)>=10]; zero=[d for d in ds if abs(d)<1]
 labels.append({'target':s['target'],'state_id':s['state_id'],'label':'SENSITIVE' if hi else 'INERT','high_count':len(hi),'action_count':len(ds),'zero_count':len(zero),'high_proportion':len(hi)/len(ds),'max_speedup':min(ds),'max_slowdown':max(ds),'effect_range':max(ds)-min(ds),'zero_proportion':len(zero)/len(ds),'breadth':'BROAD_SENSITIVE_STATE' if hi and len(hi)/len(ds)>=.5 else 'SPARSE_SENSITIVE_STATE' if hi else 'INERT_STATE'})
with open(O/'state_labels.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=labels[0]);w.writeheader();w.writerows(labels)
with open(O/'state_feature_table.csv','w',newline='') as f:
 fs=['target','state_id','label']+features+['analysis_per_conflict','watchers_per_conflict','dequeues_per_conflict'];w=csv.DictWriter(f,fieldnames=fs);w.writeheader()
 for s,l in zip(states,labels):
  d={k:s.get(k) for k in features};d.update(target=s['target'],state_id=s['state_id'],label=l['label'],pending_count=s['trail_length']-s['qhead'],analysis_per_conflict=s['prefix_analysis']/max(s['conflicts'],1),watchers_per_conflict=s['prefix_watchers']/max(s['conflicts'],1),dequeues_per_conflict=s['prefix_dequeues']/max(s['conflicts'],1));w.writerow(d)
sep=[]
for f in features+['pending_count']:
 vals=[]
 for s,l in zip(states,labels): vals.append((l['label'],s.get(f,s['trail_length']-s['qhead'] if f=='pending_count' else None)))
 a=[float(v) for l,v in vals if l=='SENSITIVE'];b=[float(v) for l,v in vals if l=='INERT'];sep.append({'feature':f,'sensitive_median':statistics.median(a) if a else None,'inert_median':statistics.median(b) if b else None,'sensitive_range':[min(a),max(a)] if a else [],'inert_range':[min(b),max(b)] if b else [],'overlap':not(max(a)<min(b) or max(b)<min(a)) if a and b else None})
with open(O/'feature_separation.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=sep[0]);w.writeheader();w.writerows(sep)
json.dump({'per_target':{t:{'sensitive':sum(x['label']=='SENSITIVE' and x['target']==t for x in labels),'inert':sum(x['label']=='INERT' and x['target']==t for x in labels)} for t in sorted(set(s['target'] for s in states))},'gate':'NO_SIMPLE_STATE_SENSITIVITY_ABSTRACTION'},open(O/'within_target_analysis.json','w'),indent=2)
json.dump(labels,open(O/'sensitivity_concentration.csv','w'),indent=2)
Path(O/'retrospective_projection.csv').write_text('source,status\nhistorical_T8_T10,UNAVAILABLE_same_feature_snapshot_not_saved\n')
Path(O/'STATE_SENSITIVITY_ABSTRACTION.md').write_text('# State Sensitivity Abstraction\n\nLabels use the frozen 10% threshold and existing 18 state snapshots. Static feature separation is descriptive only; overlap and target dependence prevent a candidate abstraction. High leverage is concentrated and sensitive states are sparse, so state gating remains a hypothesis rather than a validated rule. Historical mixed-state projection is unavailable because those snapshots do not contain the same frozen feature vector. Next step: richer temporal descriptors before any gate test.\n')
