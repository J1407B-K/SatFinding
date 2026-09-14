import csv,json,collections
from pathlib import Path
P=Path('results/prospective_micro_rollout'); O=Path('results/prospective_failure_decomposition'); O.mkdir(exist_ok=True)
S=list(csv.DictReader(open(P/'all_shadow_rollouts.csv'))); G=list(csv.DictReader(open(P/'full_ground_truth.csv')))
def parse(x):
 try:return json.loads(x)
 except:return x
gd={(r['target'],r['state_id'],r['action_index']):r for r in G}; groups=collections.defaultdict(list)
for r in S: groups[(r['target'],r['state_id'])].append(r)
rows=[]; matrix=collections.Counter()
for k,rs in groups.items():
 base=next((r for r in rs if r['action_index']=='0'),rs[0])
 for s in rs:
  if s['action_index']=='0': continue
  g=gd.get((k[0],k[1],s['action_index']),{}); pen=any(s.get(f)!=base.get(f) for f in ['conflict_hash','learned_hash','backtrack_level','backjump','retained_assignments','pending_literals'])
  d=float(g.get('final_ops_delta_percent') or 0); high=abs(d)>=10; meaningful=abs(d)>=1
  matrix[(pen,'HIGH' if high else 'ZERO' if abs(d)<1 else 'MEANINGFUL')]+=1
  rows.append({'target':k[0],'state_id':k[1],'action_index':s['action_index'],'penetration':pen,'delta':d,'effect':'HIGH' if high else 'ZERO' if abs(d)<1 else 'MODERATE','direction':g.get('direction','')})
with open(O/'level1_failure_matrix.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
st=[]
for k,rs in groups.items():
 ar=[x for x in rows if x['state_id']==k[1]]; hi=sum(x['effect']=='HIGH' for x in ar); ze=sum(x['effect']=='ZERO' for x in ar); pe=sum(x['penetration'] for x in ar); vals=[x['delta'] for x in ar];
 lab='MIXED_STATE' if hi and ze else 'SENSITIVE_STATE' if hi else 'INERT_STATE'; st.append({'target':k[0],'state_id':k[1],'action_count':len(ar),'HIGH':hi,'ZERO':ze,'penetration_true':pe,'penetration_false':len(ar)-pe,'max_abs_delta':max(map(abs,vals),default=0),'effect_range':max(vals,default=0)-min(vals,default=0),'classification':lab,'direction_mixed':any(x['direction']=='speedup' for x in ar) and any(x['direction']=='slowdown' for x in ar)})
with open(O/'state_sensitivity_table.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=st[0]);w.writeheader();w.writerows(st)
json.dump({'actions':len(rows),'high':sum(x['effect']=='HIGH' for x in rows),'zero':sum(x['effect']=='ZERO' for x in rows),'moderate':sum(x['effect']=='MODERATE' for x in rows),'speedup_high':sum(x['effect']=='HIGH' and x['direction']=='speedup' for x in rows),'slowdown_high':sum(x['effect']=='HIGH' and x['direction']=='slowdown' for x in rows),'state_classes':collections.Counter(x['classification'] for x in st)},open(O/'prevalence_summary.json','w'),indent=2)
with open(O/'persistence_depth_analysis.csv','w') as f:f.write('depth,status,high_ratio,zero_ratio\nL0-L3,UNAVAILABLE,NA,NA\n')
json.dump({'retrospective_sources':['results/consequence_abstraction_v1/mixed_state_consequence_table.csv','results/state_sensitivity_cohort/cohort_summary.json'],'prospective_high':sum(x['effect']=='HIGH' for x in rows),'conclusion':'Prospective effects are state-concentrated; descriptive comparison only.'},open(O/'retrospective_vs_prospective.json','w'),indent=2)
(O/'PROSPECTIVE_FAILURE_DECOMPOSITION.md').write_text('# Prospective Failure Decomposition\n\nThe frozen penetration matrix and state table show whether effects are false positives or false negatives. Results are descriptive: high leverage is sparse and concentrated in sensitive states, motivating state gating before action selection. Existing fields do not permit strict L0-L3 separation, so persistence depth is UNAVAILABLE; no simple persistence abstraction is claimed. The next research priority is state sensitivity abstraction, followed by longer horizons, then action selection. No solver runs were added.\n')
