import csv,json,hashlib,os
from pathlib import Path
P=Path('results/prospective_micro_rollout')
def loadj(n): return json.loads((P/n).read_text())
def rows(n): return list(csv.DictReader((P/n).open()))
sh=rows('all_shadow_rollouts.csv'); gt=rows('full_ground_truth.csv')
# one row per action (shadow may include records; retain horizon/first)
def key(r): return (r['target'],r['state_id'],r['action_index'])
sd={key(r):r for r in sh}; gd={key(r):r for r in gt}
# determine penetration from shadow tag/event/hash fields
out=[]
for k,g in gd.items():
 s=sd.get(k,{})
 pen= str(s.get('tag','')).upper() in ('PENETRATING','TRUE','LOCAL_PENETRATION') or s.get('event','').upper()=='HORIZON'
 try: d=float(g.get('final_ops_delta_percent','nan'))
 except: d=float('nan')
 out.append({'target':g['target'],'state_id':g['state_id'],'action_index':g['action_index'],'local_penetration':pen,'delta_percent':d,'high_leverage':abs(d)>=10 if d==d else False,'direction':g.get('direction',''),'proof_validation':g.get('proof_validation')})
neg=[x for x in out if not x['local_penetration']]; pos=[x for x in out if x['local_penetration']]
def bins(a): return {'action_count':len(a),'zero_or_negligible':sum(abs(x['delta_percent'])<1 for x in a if x['delta_percent']==x['delta_percent']),'high_leverage':sum(x['high_leverage'] for x in a),'speedup':sum(x['delta_percent']<0 for x in a if x['delta_percent']==x['delta_percent']),'slowdown':sum(x['delta_percent']>0 for x in a if x['delta_percent']==x['delta_percent'])}
lev1={'definition':'Frozen protocol LOCAL_PENETRATION','negative':bins(neg),'positive':bins(pos),'coverage_fraction':len(out)/111,'label':'LEVEL1_NOT_VALIDATED'}
# apply frozen thresholds
if len(neg)>=6 and len(pos)>=6 and lev1['negative']['zero_or_negligible']/max(1,len(neg))>=.95 and lev1['negative']['high_leverage']==0 and sum(abs(x['delta_percent'])>=1 for x in pos)/len(pos)>=.5 and lev1['positive']['high_leverage']/len(pos)>=.2: lev1['label']='LEVEL1_PROSPECTIVELY_VALIDATED'
(P/'level1_validation.json').write_text(json.dumps(lev1,indent=2)+'\n')
l2={'population':'LOCAL_PENETRATION=true','rules':{},'label':'LEVEL2_UNRESOLVED','candidate_rule':None}
(P/'level2_analysis.json').write_text(json.dumps(l2,indent=2)+'\n')
(P/'controller_eval.json').write_text(json.dumps({'status':'SKIP_CONTROLLER_BY_PROTOCOL','reason':'No frozen Level2 candidate'},indent=2)+'\n')
# integrity
prot=hashlib.sha256((P/'frozen_protocol.json').read_bytes()).hexdigest(); audit={'protocol_sha256':prot,'selected_states_protocol_match':loadj('selected_states.json').get('protocol_sha256')==prot,'full_route_count':len(gt),'shadow_route_count':len(sh),'status_counts':{},'proof_validation_counts':{}}
from collections import Counter
audit['status_counts']=dict(Counter(r['status'] for r in gt));audit['proof_validation_counts']=dict(Counter(r['proof_validation'] for r in gt));(P/'integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# costs
fields=['analysis_resolution_steps','search_watchers','search_dequeues','child_cpu_seconds','child_wall_seconds']
cost={'search_only':{f:sum(float(r.get(f) or 0) for r in gt) for f in fields},'total_with_rollout':{'actions':len(sh),'shadow_analysis_ops':sum(float(r.get('analysis_ops') or 0) for r in sh),'shadow_watcher_visits':sum(float(r.get('watcher_visits') or 0) for r in sh),'shadow_dequeues':sum(float(r.get('dequeues') or 0) for r in sh)}};(P/'cost_accounting.json').write_text(json.dumps(cost,indent=2)+'\n')
print(json.dumps(audit));print(json.dumps(lev1))
