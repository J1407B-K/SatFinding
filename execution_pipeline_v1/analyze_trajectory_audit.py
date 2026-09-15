import json,hashlib,itertools,math,statistics,collections
from pathlib import Path
R=Path('results/fresh_trajectory_divergence_audit_v1'); F=Path('results/fresh_heuristic_causal_cohort_v1')
P=json.loads((R/'TRAJECTORY_DIVERGENCE_PROTOCOL_V1.json').read_text())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def scan(p,literal):
 higher={k:[] for k in ['conflict','learned','decision','backtrack','restart']};early={};milestones={};native=None;reasonless=None;enq=0;last=None; pending=[]
 with p.open() as f:
  for line in f:
   e=json.loads(line);kind=e['kind'];last=e
   if kind=='prestate':pre=e;continue
   if kind=='milestone':
    milestones[e['value']['k']]=dict(e['value'],next_decision=None,event=e['i']);pending.append(e['value']['k']);continue
   if 'state' in e:early[(e['state'],e['frontier'])]=e['i']
   if kind in higher:higher[kind].append({'value':e['value'],'event':e['i'],'conflicts':e['c']})
   if kind=='decision':
    for k in pending:milestones[k]['next_decision']=e['value']
    pending=[]
   if kind=='enqueue':
    enq+=1
    if e['value']['literal']==literal:
     n={'propagation_delay':e['p'],'enqueue_delay':enq-1,'conflict_delay':e['c'],'native_reason_clause':e['value']['reason'],'event':e['i']}
     if e['value']['reason'] is not None and native is None:native=n
     if e['value']['reason'] is None and reasonless is None:reasonless=n
 return dict(higher=higher,early=early,milestones=milestones,native=native,reasonless=reasonless,pre=pre,last=last)
def events(p):
 with p.open() as f:
  for l in f:
   e=json.loads(l)
   if e['kind'] not in ['prestate','milestone']:yield e

def first_diff(a,b):
 for offset,(x,y) in enumerate(itertools.zip_longest(a,b)):
  if x is None or y is None or x['value']!=y['value']:
   return {'offset':offset,'baseline':x,'action':y}
 return None

def compare(c):
 d=R/'routes'/c['case']/f'rank{c["rank"]}'; bp=d/'baseline/telemetry.jsonl';ap=d/'action/telemetry.jsonl'
 acts=json.loads((F/'cases'/c['case']/'action/actions.json').read_text())['selected'];act=next(a for a in acts if a['rank']==c['rank'])
 b=scan(bp,act['literal']);a=scan(ap,act['literal']);be=json.loads((d/'baseline/execution.json').read_text());ae=json.loads((d/'action/execution.json').read_text())
 first=None
 for offset,(x,y) in enumerate(itertools.zip_longest(events(bp),events(ap))):
  if x is None or y is None or (x['kind'],x['value'])!=(y['kind'],y['value']):
   first={'offset':offset,'baseline':x,'action':y};break
 higher={k:first_diff(b['higher'][k],a['higher'][k]) for k in b['higher']}
 ms=[]
 for k in [1,2,4,8,16]:
  bm=b['milestones'].get(k);am=a['milestones'].get(k);fields=['logical','learned','frontier','next_decision']
  eq={f:bm[f]==am[f] for f in fields} if bm and am else None
  ms.append({'k':k,'baseline':bm,'action':am,'equal_fields':eq,'equal':all(eq.values()) if eq else None})
 matches=set(b['early'])&set(a['early']);reconv=bool(matches)
 if first is None:cl='INERT'
 elif reconv and all(v is None for v in higher.values()) and all(m['equal'] is not False for m in ms):cl='LOCAL_TRANSIENT'
 elif all(m['equal'] is False for m in ms if m['k'] in [2,4,8,16]):cl='PERSISTENT_DIVERGENT'
 elif higher['decision'] is not None:cl='DECISION_DIVERGENT'
 elif higher['learned'] is not None:cl='LEARNED_DIVERGENT'
 else:cl='CONFLICT_DIVERGENT'
 kind=None
 if first:
  kinds={e['kind'] for e in [first['baseline'],first['action']] if e}
  kind=next((v for ks,v in [({'enqueue','dequeue'},'propagation'),({'conflict'},'conflict'),({'learned'},'learned'),({'decision'},'decision'),({'backtrack'},'backtrack'),({'restart'},'restart')] if kinds&ks),'termination')
 def samefirst(k):
  x=b['higher'][k];y=a['higher'][k]
  return x[0]['value']==y[0]['value'] if x and y else None
 n=b['native'];delta=(ae['final_counters']['analysis_resolution_steps']-be['final_counters']['analysis_resolution_steps'])/be['final_counters']['analysis_resolution_steps']*100
 r={'case':c['case'],'rank':c['rank'],'action_id':act['id'],'action_literal':act['literal'],'action_clause':act['clause'],'exact_pre_state_identity':be['identity_checkpoint_equal'] and ae['identity_checkpoint_equal'] and be['checkpoint_logical_sha256']==ae['checkpoint_logical_sha256'] and be['checkpoint_heuristic_sha256']==ae['checkpoint_heuristic_sha256'] and b['pre']['state']==a['pre']['state'],'action_verified':ae['action_verified'],'action_literal_unassigned_at_intervention':ae['action_verified'],'native_enqueue':n,'reasonless_enqueue':b['reasonless'],'never_native_enqueue_status':None if n else 'NEVER_NATURALLY_ENQUEUED_BEFORE_TERMINATION','native_before_first_divergence':n['event']<first['baseline']['i'] if n and first and first['baseline'] else None,'propagation_timing_class':'EARLY_SAME_PROPAGATION' if n and n['conflict_delay']==0 and sorted(n['native_reason_clause'])==sorted(act['clause']) else 'GENUINELY_DIFFERENT_PROPAGATION','first_divergence_kind':kind,'first_divergence_event_offset':first['offset'] if first else None,'first_divergence':first,'first_conflict_divergence':higher['conflict'],'first_learned_divergence':higher['learned'],'first_decision_divergence':higher['decision'],'first_restart_divergence':higher['restart'],'first_backtrack_divergence':higher['backtrack'],'reconverged_before_first_conflict':reconv,'reconvergence_witness':{'baseline_event':b['early'][min(matches)],'action_event':a['early'][min(matches)]} if matches else None,'same_first_conflict':samefirst('conflict'),'same_first_learned_clause':samefirst('learned'),'same_next_decision':samefirst('decision'),'milestones':ms,'persistence_class':cl,'residual_trajectory_difference':cl=='CONFLICT_DIVERGENT' and higher['conflict'] is None,'baseline_final_ops':be['final_counters']['analysis_resolution_steps'],'action_final_ops':ae['final_counters']['analysis_resolution_steps'],'delta_percent':delta,'proof_verified':be['proof_verified'] and ae['proof_verified'],'evidence':str(d)}
 (d/'comparison.json').write_text(json.dumps(r,indent=2));return r

def percentile(xs,q):
 xs=sorted(xs)
 if not xs:return None
 p=(len(xs)-1)*q;i=int(p);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(p-i)
def dist(xs):
 if not xs:return {'n':0}
 return {'n':len(xs),'min':min(xs),'max':max(xs),'median':percentile(xs,.5),'p90':percentile(xs,.9),'p95':percentile(xs,.95),'p99':percentile(xs,.99)}
def summary(rows):
 ds=[x['delta_percent'] for x in rows];absds=list(map(abs,ds));classes=collections.Counter(x['persistence_class'] for x in rows)
 decision='A' if classes['INERT']>68 else 'B' if classes['LOCAL_TRANSIENT']>68 else 'C' if classes['PERSISTENT_DIVERGENT']>68 and not any(x>=10 for x in absds) else 'D'
 s={'audited':len(rows),'identity_pass':sum(x['exact_pre_state_identity'] for x in rows),'action_verified':sum(x['action_verified'] for x in rows),'naturally_enqueued':sum(x['native_enqueue'] is not None for x in rows),'never_enqueued':sum(x['native_enqueue'] is None for x in rows),'native_delay_propagation':dist([x['native_enqueue']['propagation_delay'] for x in rows if x['native_enqueue']]),'native_delay_conflict':dist([x['native_enqueue']['conflict_delay'] for x in rows if x['native_enqueue']]),'propagation_timing_class':dict(collections.Counter(x['propagation_timing_class'] for x in rows)),'first_divergence':dict(collections.Counter(x['first_divergence_kind'] or 'no_semantic_divergence' for x in rows)),'reconverged_before_first_conflict':sum(x['reconverged_before_first_conflict'] for x in rows),'classes':dict(classes),'signed_effect_distribution':dist(ds),'absolute_effect_distribution':dist(absds),'effect_counts':{},'class_effect_distribution':{k:{'signed':dist([x['delta_percent'] for x in rows if x['persistence_class']==k]),'absolute':dist([abs(x['delta_percent']) for x in rows if x['persistence_class']==k])} for k in ['INERT','LOCAL_TRANSIENT','CONFLICT_DIVERGENT','LEARNED_DIVERGENT','DECISION_DIVERGENT','PERSISTENT_DIVERGENT']},'top10':[{k:x[k] for k in ['case','rank','delta_percent','persistence_class']} for x in sorted(rows,key=lambda x:-abs(x['delta_percent']))[:10]],'strongest_speedup':min(ds),'strongest_slowdown':max(ds),'proof_verified_pairs':sum(x['proof_verified'] for x in rows),'proof_verified_executions':sum(json.loads((Path(x['evidence'])/mode/'execution.json').read_text())['proof_verified'] for x in rows for mode in ['baseline','action']),'proof_failed':sum(not x['proof_verified'] for x in rows),'final_decision':decision}
 for name,pred in [('abs_eq_0',lambda v:v==0),('abs_between_0_1',lambda v:0<v<1)]+[(f'abs_ge_{k}',lambda v,k=k:v>=k) for k in [1,2,5,10]]:
  s['effect_counts'][name]={'all':sum(pred(abs(v)) for v in ds),'speedup':sum(v<0 and pred(abs(v)) for v in ds),'slowdown':sum(v>0 and pred(abs(v)) for v in ds)}
 (R/'AUDIT_SUMMARY.json').write_text(json.dumps(s,indent=2));return s
if __name__=='__main__':
 rows=[]
 for i,c in enumerate(P['cohort']):
  d=R/'routes'/c['case']/f'rank{c["rank"]}'/'comparison.json'
  r=json.loads(d.read_text()) if d.exists() else compare(c);rows.append(r);print(i+1,r['case'],r['rank'],r['persistence_class'],flush=True)
 (R/'ROUTE_COMPARISONS.json').write_text(json.dumps(rows,indent=2));print(json.dumps(summary(rows),indent=2))
