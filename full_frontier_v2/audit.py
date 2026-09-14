import gzip,json,hashlib,collections
from build import ROOT,OUT,dump,sha

def audit(path):
 checks=0;counts=collections.Counter();assigned={};reasons={};trail=[];qhead=0;front=None;chains={};steps=collections.Counter();root=[];checkpoint=False
 def check(v,reason):
  nonlocal checks
  checks+=1
  if not v:raise AssertionError((str(path),checks,counts,reason))
 with gzip.open(path,'rt') as f:
  for ordinal,line in enumerate(f):
   e=json.loads(line);k=e['type'];counts[k]+=1
   check(e['event']==ordinal,'ordinal');aid=e['analysis_id']
   if k=='checkpoint':
    trail=e['trail'];assigned={abs(x):x for x in trail};reasons={abs(x['literal']):x['reason'] for x in e['assigned']};qhead=e['qhead'];checkpoint=True
   if k=='enqueue':
    p=e['literal'];rs=e['reason'];check(abs(p) not in assigned,'enqueue unassigned');check(e['trail_position']==len(trail),'enqueue position')
    if rs:check(p in rs and all(assigned.get(abs(x))==-x for x in rs if x!=p),'unit reason');check(e['reason_id']==hashlib.sha256(json.dumps(rs,separators=(',',':')).encode()).hexdigest(),'reason digest')
    else:check(e['reason_id'] in ['ROOT','DECISION'],'reason sentinel')
    assigned[abs(p)]=p;reasons[abs(p)]=rs;trail.append(p)
   if k=='frontier':
    check(e['trail']==trail,'frontier reconstructed trail');check(e['pending_ordered']==trail[e['qhead']:],'pending slice');check(bool(e['pending_ordered']),'nonempty');check(e['native_next_literal']==e['pending_ordered'][0],'next candidate');front=e;qhead=e['qhead']
   if k=='step_end':
    check(front is not None and front['step']==e['step'],'step pairing');check(e['processed_literal']==front['native_next_literal']==e['native_next_literal'],'processed');check(e['trail']==trail,'post trail');check(e['newly_enqueued']==trail[len(front['trail']):],'new enqueues');check(e['qhead_before']==front['qhead'],'qhead before');check(e['qhead_after']==front['qhead']+1 or bool(e['conflict_clause']) and e['qhead_after']==len(trail),'qhead after');check(e['pending_ordered']==trail[e['qhead']:],'post pending')
    if e['conflict_clause']:check(all(assigned.get(abs(x))==-x for x in e['conflict_clause']),'step conflict falsified')
    front=None;qhead=e['qhead']
   if k=='conflict_detected':
    check(bool(e['clause']) and all(assigned.get(abs(x))==-x for x in e['clause']),'conflict falsified');check(aid not in chains,'unique conflict');chains[aid]={'conflict_detected':e}
    if e['decision_level']==0:root.append(aid)
   if k in ['analysis_begin','first_uip','learned_clause','analysis_backtrack_complete']:
    check(aid in chains,'known conflict');check(k not in chains[aid],'unique chain type');chains[aid][k]=e
    if k=='analysis_begin':check(e['clause']==chains[aid]['conflict_detected']['clause'],'analysis conflict')
    if k=='first_uip':check(e['asserting_literal']==-e['first_uip_trail_literal'],'UIP sign');check(trail[e['trail_position']]==e['first_uip_trail_literal'] and e['path_count']==0,'native UIP position')
    if k=='learned_clause':
     u=chains[aid]['first_uip'];check(e['native_literals'][0]==u['asserting_literal']==e['asserting_literal'],'asserting identity');check(sorted(e['native_literals'])==e['canonical_literals'],'learned copy');check(len(e['native_literals'])==e['length'],'length')
    if k=='analysis_backtrack_complete':check(e['target_level']==chains[aid]['learned_clause']['backtrack_level']==e['level'],'backtrack target')
   if k=='analysis_step':check(aid in chains and 'analysis_begin' in chains[aid],'step in analysis');steps[aid]+=1
   if k in ['backtrack','analysis_backtrack_complete']:
    check(trail[:len(e['trail'])]==e['trail'],'backtrack prefix');trail=e['trail'];assigned={abs(x):x for x in trail};reasons={v:reasons[v] for v in assigned};qhead=e['qhead']
 complete=0
 for aid,c in chains.items():
  if aid in root:check(set(c)=={'conflict_detected'},'root conflict no analysis')
  else:check(set(c)=={'conflict_detected','analysis_begin','first_uip','learned_clause','analysis_backtrack_complete'} and steps[aid]>0,'complete chain');complete+=1
 return {'checks_total':checks,'checks_pass':checks,'checks_fail':0,'counts':dict(counts),'complete_chains':complete,'root_conflicts':len(root),'PASS':True}

def main():
 audits={};nonpert={};stable={}
 for target in ['T8','T10']:
  ds=[OUT/'runs'/target/m for m in ['OFF','ON1','ON2']];ss=[json.loads((d/'summary.json').read_text()) for d in ds]
  nonpert[target]={'exact_summary_equal':ss[0]==ss[1]==ss[2],'decision_sequence_equal':len(set(s['sequences']['decision_sha256'] for s in ss))==1,'enqueue_sequence_equal':len(set(s['sequences']['enqueue_sha256'] for s in ss))==1}
  assert all(nonpert[target].values())
  # gzip includes no timestamps with gzopen; compare decompressed canonical bytes explicitly.
  hs=[]
  for d in ds[1:]:
   h=hashlib.sha256()
   with gzip.open(d/'trace.jsonl.gz','rb') as f:
    for b in iter(lambda:f.read(1048576),b''):h.update(b)
   hs.append(h.hexdigest())
   audits[str(d.relative_to(OUT))]=audit(d/'trace.jsonl.gz');print(target,d.name,'AUDITED',flush=True)
  stable[target]={'canonical_sha256':hs,'PASS':hs[0]==hs[1]};assert stable[target]['PASS']
 dump(OUT/'OBSERVER_SELF_CONSISTENCY.json',audits);dump(OUT/'OBSERVER_NONPERTURBATION.json',nonpert);dump(OUT/'OBSERVER_CROSS_RUN_STABILITY.json',stable)
if __name__=='__main__':main()
