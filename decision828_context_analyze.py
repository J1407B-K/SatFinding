import gzip,json
from pathlib import Path
from collections import defaultdict
P=Path('results/decision828_context')
NAMES=['A','B','A_FORCED','B_FORCED']
def load(n):
 rows=[];cat={}
 for l in gzip.open(P/f'{n}.events.jsonl.gz','rt'):
  r=json.loads(l)
  if r['t']=='Q':cat[r['id']]=r['clause']
  else:rows.append(r)
 return rows,cat
def snap(n,t):return json.loads((P/f'{n}.{t}.snapshot.json').read_text())
def first(a,b,t,keys):
 aa=[r for r in a if r['t']==t];bb=[r for r in b if r['t']==t]
 for i,(x,y) in enumerate(zip(aa,bb)):
  if any(x[k]!=y[k] for k in keys):return dict(ordinal=i+1,A=x,B=y)
 return dict(equal_prefix=min(len(aa),len(bb)),lengths=[len(aa),len(bb)])
def main():
 data={};cats={};post={};start={};summ={};cases={};checkpoints=[]
 for n in NAMES:
  data[n],cats[n]=load(n);start[n]=next(r for r in data[n] if r['t']=='D' and r['d']==828)
  post[n]=[r for r in data[n] if r.get('g',-1)>start[n]['g']]
  summ[n]=[]
  for N in [1,5,10,20,50]:
   c=657+N;end=next(r for r in post[n] if r['t']=='L' and r['c']==c)
   rr=[r for r in post[n] if r.get('g',0)<=end['g']]
   conflicts=[]
   for ci in range(658,c+1):
    cc=next(r for r in rr if r['t']=='C' and r['c']==ci);ll=next(r for r in rr if r['t']=='L' and r['c']==ci)
    conflicts.append(dict(conflict=ci,event=cc,clause=cats[n][cc['r']],UIP=[dict(r,clause=cats[n][r['r']]) for r in rr if r['t']=='A' and r['c']==ci],learned=dict(ll,clause=cats[n][ll['r']]),backjump=next(r for r in post[n] if r['t']=='BACK' and r['c']==ci),activity_updates=[r for r in rr if r['t']=='U' and r['c']==ci]))
   es=[r for r in rr if r['t']=='E'];ds=[r for r in rr if r['t']=='D']
   # D enqueues carry reason0. Subtract the branch828 enqueue and later D events.
   summ[n].append(dict(N=N,native_propagations=end['props']-start[n]['props'],enqueues=len(es),successful_nondecision_enqueues=len(es)-1-len(ds),analysis_ops=end['ops']-start[n]['ops'],next_decisions=ds,conflicts=conflicts))
 for x,y in [('A_FORCED','B'),('A','B_FORCED'),('A','B'),('A','A_FORCED'),('B','B_FORCED')]:
  c={}
  for t,k,label in [('E',['v'],'literal'),('E',['v','r'],'reason'),('C',['r'],'conflict'),('A',['v','r'],'UIP'),('L',['r'],'learned'),('D',['v'],'next_decision')]:
   d=first(post[x],post[y],t,k)
   for side,n in [('A',x),('B',y)]:
    if side in d:d[side]['clause']=cats[n].get(d[side]['r'])
   c[label]=d
  cases[f'{x}_vs_{y}']=c
 for tag in ['boundary_600','boundary_650','boundary_656','boundary_657','decision828_before_pick','boundary_700','boundary_750','boundary_800']:
  a=snap('A',tag);b=snap('B',tag)
  diff={k:[i+1 for i,(x,y) in enumerate(zip(a[k],b[k])) if x!=y] for k in ['assignment','reasons','activity','phase','eligible']}
  diff['heap_positions']={k:sum(x!=y for x,y in zip(a['heap'][k],b['heap'][k])) for k in a['heap']}
  diff['learned_content_positions']=[i+1 for i,(x,y) in enumerate(zip(a['learned'],b['learned'])) if x[0]!=y[0]]
  diff['learned_counts']=[len(a['learned']),len(b['learned'])]
  diff['restart_different_fields']=[k for k in a['restart'] if a['restart'][k]!=b['restart'][k]]
  checkpoints.append(dict(checkpoint=tag,A={k:a[k] for k in ['c','d','e','dl']},B={k:b[k] for k in ['c','d','e','dl']},differences=diff))
 # Precisely locate direct usages of context-specific clauses present before828.
 ingredients={}
 for n in NAMES:
  s=snap(n,'decision828_before_pick');ids={r[0] for r in s['learned'][-2:]};ids.add('15289423184524811497')
  ingredients[n]={h:dict(clause=cats[n].get(h),uses=[r for r in post[n] if r.get('r')==h and r['t'] in ['E','A','M','C']]) for h in ids}
 out=dict(checkpoints=checkpoints,first_responses=cases,ingredients=ingredients)
 (P/'context_analysis.json').write_text(json.dumps(out,indent=2))
 (P/'branch_responses.json').write_text(json.dumps(summ,indent=2))
 print('first responses',json.dumps(cases['A_FORCED_vs_B'],indent=2))
 print('ingredients', {n:{h:dict(clause=r['clause'],count=len(r['uses']),first=r['uses'][:1]) for h,r in v.items()} for n,v in ingredients.items()})
 print('budgets',{n:[{k:r[k] for k in ['N','native_propagations','successful_nondecision_enqueues','analysis_ops']} for r in v] for n,v in summ.items()})
if __name__=='__main__':main()
