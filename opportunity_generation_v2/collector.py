"""Outcome-blind V2 inventory builder over sealed baseline telemetry."""
import json,hashlib,sys
from pathlib import Path
BUCKETS=((1,1,'BUCKET_1'),(2,4,'BUCKET_2_4'),(5,16,'BUCKET_5_16'),(17,10**18,'BUCKET_GT16'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bucket(d):
 for lo,hi,n in BUCKETS:
  if lo<=d<=hi:return n
 return 'CROSS_CONFLICT_OR_UNOBSERVED'
def build(case, telemetry, out):
 c=Path(case); st=json.loads((c/'checkpoint/state.json').read_text()); acts=json.loads((c/'action/actions.json').read_text())
 acts={'selected': acts.get('all_actions',acts.get('selected',[]))}
 ev=[json.loads(x) for x in Path(telemetry).read_text().splitlines()]
 enq={}; dq=0
 for e in ev:
  if e.get('kind')=='dequeue': dq+=1
  if e.get('kind')=='enqueue':
   v=e['value']; lit=v['literal']; enq.setdefault(lit,{'dequeue_index':dq,'event':e['i'],'reason':v['reason']})
 rows=[]
 for a in sorted(acts.get('selected',[])+[{'id':i,'literal':None,'clause':[]} for i in []],key=lambda x:x['id']):
  x=dict(a); n=enq.get(a['literal']); delay=n['dequeue_index'] if n else None
  x.update({'legal':True,'current_assignment':'UNASSIGNED','checkpoint_sha256':sha(c/'checkpoint/state.json'),'naturally_enqueued':bool(n),'native_enqueue_dequeue_delay':delay,'native_enqueue_conflict_delay':0 if n else None,'native_reason_clause':n['reason'] if n else None,'native_reason_same_source_clause':n is not None and sorted(n['reason'])==sorted(a['clause']),'before_next_conflict':bool(n),'timing_bucket':bucket(delay) if n and delay else 'CROSS_CONFLICT_OR_UNOBSERVED','selected_for_execution':False,'selection_reason':'not selected; inventory record'})
  rows.append(x)
 for x in sorted(rows,key=lambda x:hashlib.sha256((str(st.get('state_id'))+':'+str(x['id'])).encode()).hexdigest()):
  if x['timing_bucket'] in {b[2] for b in BUCKETS} and not any(y['selected_for_execution'] and y['timing_bucket']==x['timing_bucket'] for y in rows): x['selected_for_execution']=True;x['selection_reason']='deterministic stable-hash first per baseline timing bucket'
 inv={'schema':'opportunity_inventory_v2','state_id':st.get('state_id'),'checkpoint_sha256':sha(c/'checkpoint/state.json'),'all_legal_actions_count':len(rows),'actions':rows,'baseline_telemetry_sha256':sha(telemetry),'selection_outcome_blind':True}
 Path(out).write_text(json.dumps(inv,indent=2,sort_keys=True)+'\n');return inv
if __name__=='__main__': build(sys.argv[1],sys.argv[2],sys.argv[3])
