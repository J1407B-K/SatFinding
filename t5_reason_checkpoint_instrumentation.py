"""Offline reason/checkpoint instrumentation for frozen T5 CONTROL/TREATMENT."""
import gzip,json,hashlib
from pathlib import Path
P=Path('results/persistent_imprint_replication'); OUT=P/'T5_instrumentation'; OUT.mkdir(exist_ok=True)
def h(vals):
 x=1469598103934665603
 for v in sorted(vals):
  for b in int(v).to_bytes(4,'little',signed=True): x=((x^b)*1099511628211)&((1<<64)-1)
 return str(x)
def load(p):return [json.loads(x) for x in gzip.open(p,'rt')]
def main():
 cert=json.load(open(P/'T5_lemmas/certificates.json')); lem={h(c):i+1 for i,c in enumerate(cert['lemmas'])}; rows=load(P/'T5_treatment/TREATMENT.events.jsonl.gz'); control=load(P/'T5_smoke/CONTROL.events.jsonl.gz')
 uses=[]
 for r in rows:
  if r.get('t') in ('E','A','M') and r.get('r') in lem: uses.append(dict(clause_id=lem[r['r']],event=r['t'],hash=r['r'],conflict=r['c'],decision=r['d'],level=r['dl'],literal=r['v'],global_event=r['g']))
 def first(kind):
  for a,b in zip([r for r in control if r.get('t')==kind],[r for r in rows if r.get('t')==kind]):
   if a.get('v')!=b.get('v') or a.get('r')!=b.get('r'):return dict(kind=kind,control=a,treatment=b)
  return None
 alignment=[]
 for c in [600,650,656,657,658,662,667,677,700,707,750,800]:
  a=json.load(open(P/f'T5_smoke/CONTROL.boundary_{c}.snapshot.json'));b=json.load(open(P/f'T5_treatment/TREATMENT.boundary_{c}.snapshot.json'))
  alignment.append(dict(conflict=c,assignment_equal=a['assignment']==b['assignment'],trail_equal=a['trail']==b['trail'],level_equal=a['dl']==b['dl'],decision_level=[a['d'],b['d']],eligible_equal=a['eligible']==b['eligible'],activity_diffs=sum(x!=y for x,y in zip(a['activity'],b['activity'])),heap_array_diffs=sum(x!=y for x,y in zip(a['heap']['array'],b['heap']['array']))))
 eligible=[x for x in alignment if x['assignment_equal'] and x['trail_equal'] and x['level_equal'] and uses]
 out=dict(target='T5',stable_clause_ids={str(i+1):list(c) for i,c in enumerate(cert['lemmas'])},lemma_reason_uses=uses,first_divergence={k:first(k) for k in ['E','A','M','L','D']},alignment=alignment,eligible_checkpoint_candidates=[],eligibility_rule={'abs_relative_ops_gap':True,'reason_use':True,'assignment_trail_level_equal':True,'native_conflict_end_pre_decision':True},decision='NO_ALIGNED_CHECKPOINT' if not eligible else 'INSTRUMENTATION_ONLY')
 (OUT/'ledger.json').write_text(json.dumps(out,indent=2)); print(dict(lemma_reason_uses=len(uses),eligible=len(eligible),decision=out['decision']))
if __name__=='__main__':main()
