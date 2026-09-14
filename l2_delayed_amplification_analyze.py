import gzip,json,csv
from pathlib import Path
from collections import defaultdict
from evaluation_oracle_run import sha
P=Path('results/l2_delayed_amplification')
def load(p):
 g=defaultdict(list);cat={}
 for l in gzip.open(p,'rt'):
  r=json.loads(l)
  if r['t']=='Q':cat[r['id']]=r['clause']
  else:g[r['t']].append(r)
 return g,cat
def read(p):return json.loads(p.read_text())
def first(x,y,t,key):
 for i,(a,b) in enumerate(zip(x[t],y[t])):
  if a[key]!=b[key]:return dict(ordinal=i+1,reference=a,run=b)
 return None
def logical(x):return {k:v for k,v in x.items() if k!='global'}
def main():
 runs=read(P/'runs.json');A,ac=load(P/'A.events.jsonl.gz');B,bc=load(P/'B.events.jsonl.gz')
 audits={};rows=[]
 for n in ['B','I100','I150','I180','I190','I198','I200','I220','I250','I300','I400','I600']:
  g,cat=load(P/f'{n}.events.jsonl.gz');s=runs[n]['stats']
  inj=g['INJECT'][0] if g['INJECT'] else None
  fd=first(A,g,'D','v');fl=first(A,g,'L','r')
  row=dict(name=n,point=0 if n=='B' else int(n[1:]),stats=s,first_l2=g['E'][0],first_decision_vs_A=fd,first_learned_vs_A=fl,first_decision_vs_B=first(B,g,'D','v'),first_learned_vs_B=first(B,g,'L','r'),injection=inj)
  rows.append(row)
  if inj:
   a=read(P/f'A.boundary_{n[1:]}.snapshot.json');pre=read(P/f'{n}.injection_before.snapshot.json');post=read(P/f'{n}.injection_after.snapshot.json')
   assert logical(a)==logical(pre),(n,'pre mismatch')
   different=[k for k in pre if pre[k]!=post[k] and k!='global']
   assert set(different)=={'watches','clauses_literals'},(n,different)
   assert inj['dl_before']==inj['dl_after'] and not inj['unit_assert'] and not inj['conflict']
   assert [(r['c'],r['r']) for r in A['L'] if r['c']<=inj['c']]==[(r['c'],r['r']) for r in g['L'] if r['c']<=inj['c']]
   assert [(r['d'],r['v']) for r in A['D'] if r['d']<=inj['d']]==[(r['d'],r['v']) for r in g['D'] if r['d']<=inj['d']]
   audits[n]=dict(pre_snapshot_matches_A=True,post_changed_fields=different,no_backjump=True,pre_sha256=sha(P/f'{n}.injection_before.snapshot.json'),reference_sha256=sha(P/f'A.boundary_{n[1:]}.snapshot.json'))
 # All natural D/L events through frozen ledger bound reproduce prior experiment.
 for n,g in [('A',A),('B',B)]:
  old,_=load(Path('results/l1_l2_latent')/f'{n}.events.jsonl.gz')
  for t,fields in [('D',['c','d','v']),('L',['c','r'])]:
   assert [[r[k] for k in fields] for r in old[t] if r['c']<=900]==[[r[k] for k in fields] for r in g[t] if r['c']<=900]
 # Ghost states are monitored across full A; first opportunity and transient expiry.
 ghost={}
 for state,name in [(0,'satisfied'),(1,'inactive'),(2,'unit'),(3,'conflict')]:
  rr=[r for r in A['GHOST'] if r['state']==state];ghost[name]=dict(transitions=len(rr),first=rr[0] if rr else None)
 firstunit=ghost['unit']['first'];gi=A['GHOST'].index(firstunit);ghost['first_unit_interval']=A['GHOST'][gi:gi+2]
 ghost['around_first_real_reason']=[r for r in A['GHOST'] if r['c']==198]
 # Existing compact literal ledger identifies the original clause that wins the
 # transient ghost-unit race. Read only; no new run or intervention.
 nearby={}
 for n in ['A','B']:
  old,cat=load(Path('results/l1_l2_latent')/f'{n}.events.jsonl.gz')
  nearby[n]=[dict(r,clause=cat.get(r['r'])) for r in old['E'] if 23430<=r['e']<=23445]
 ghost['native_enqueues_around_first_unit']=nearby
 fp=P/'forced_valid';fr=read(fp/'runs.json');forced={}
 for natural,n in [('A','A_FORCED'),('B','B_FORCED')]:
  g,_=load(fp/f'{n}.events.jsonl.gz');ref,_=load(fp/f'{natural}.events.jsonl.gz')
  assert {k:v for k,v in fr[natural]['stats'].items() if k!='seconds'}=={k:v for k,v in runs[natural]['stats'].items() if k!='seconds'}
  pre=read(fp/f'{n}.decision828_before_pick.snapshot.json');reference=read(fp/f'{natural}.decision828_before_pick.snapshot.json');post=read(fp/f'{n}.decision828_after_override.snapshot.json')
  assert pre==reference and pre==post
  assert [(r['c'],r['d'],r['v']) for r in ref['D'][:827]]==[(r['c'],r['d'],r['v']) for r in g['D'][:827]]
  assert [(r['c'],r['r']) for r in ref['L'] if r['c']<=pre['c']]==[(r['c'],r['r']) for r in g['L'] if r['c']<=pre['c']]
  fe=g['FORCED'][0];ne=ref['NATIVE_PICK'][0]
  assert fe['seed_before']==ne['seed_before'] and fe['seed_after']==ne['seed_after']
  forced[n]=dict(stats=fr[n]['stats'],forced=fe,first_decision=first(ref,g,'D','v'),first_learned=first(ref,g,'L','r'),pre_matches_own_natural=True,override_snapshot_unchanged=True,same_native_rng_step=True,pre_sha256=sha(fp/f'{n}.decision828_before_pick.snapshot.json'),post_sha256=sha(fp/f'{n}.decision828_after_override.snapshot.json'),proof_verified=fr[n]['proof_verified'])
 out=dict(injections=rows,ghost=ghost,forced=forced,audits=audits,natural_prefix_matches_previous=True)
 (P/'analysis.json').write_text(json.dumps(out,indent=2))
 with (P/'injection_summary.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['point','ops','conflicts','decisions','first_l2_c','first_l2_d','first_l2_e','first_learned_c_vs_A','first_decision_d_vs_A','all_D_equal_B','all_L_equal_B'])
  for r in rows:w.writerow([r['point'],r['stats']['analysis_resolution_steps'],r['stats']['conflicts'],r['stats']['decisions'],r['first_l2']['c'],r['first_l2']['d'],r['first_l2']['e'],r['first_learned_vs_A']['run']['c'],r['first_decision_vs_A']['run']['d'],r['first_decision_vs_B'] is None,r['first_learned_vs_B'] is None])
 print('Ghost',ghost['first_unit_interval'],ghost['conflict']['first'])
 print('Forced',json.dumps(forced,indent=2))
 print((P/'injection_summary.csv').read_text())
if __name__=='__main__':main()
