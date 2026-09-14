"""Compare bounded natural event ledgers and exact logical snapshots."""
from collections import defaultdict
import gzip
import json
from pathlib import Path
from l1_l2_latent import OUT
from unseen_selector import dump
from evaluation_oracle_run import sha

def load(name):
    groups=defaultdict(list);catalog={}
    with gzip.open(OUT/(name+'.events.jsonl.gz'),'rt') as f:
        for l in f:
            r=json.loads(l)
            if r['t']=='Q':catalog[r['id']]=r['clause']
            else:groups[r['t']].append(r)
    return groups,catalog

def first(a,b,kind,fields):
    aa=a[kind];bb=b[kind]
    for i,(x,y) in enumerate(zip(aa,bb)):
        if any(x[f]!=y[f] for f in fields):return dict(ordinal=i+1,A=x,B=y,fields=fields)
    return dict(equal_prefix=min(len(aa),len(bb)),length_A=len(aa),length_B=len(bb))

def compare_snap(name):
    a=json.loads((OUT/('A.'+name+'.snapshot.json')).read_text());b=json.loads((OUT/('B.'+name+'.snapshot.json')).read_text())
    fields={}
    for k in a:
        if k in ('global',):continue
        if a[k]==b[k]:fields[k]=dict(equal=True)
        elif isinstance(a[k],list) and len(a[k])==len(b[k]):fields[k]=dict(equal=False,differing_positions=[i for i,(x,y) in enumerate(zip(a[k],b[k])) if x!=y])
        else:fields[k]=dict(equal=False)
    return dict(name=name,A_time={k:a[k] for k in ('c','d','e','global')},B_time={k:b[k] for k in ('c','d','e','global')},fields=fields,
        sha256={n:sha(OUT/(n+'.'+name+'.snapshot.json')) for n in ('A','B')})

def main():
    a,ac=load('A');b,bc=load('B')
    diffs=dict(reason=first(a,b,'E',['v','r']),propagation_literal=first(a,b,'E',['v']),
        conflict_clause=first(a,b,'C',['r']),conflict_trail=first(a,b,'C',['trail']),
        analysis=first(a,b,'A',['r','v']),minimization=first(a,b,'M',['r']),
        activity_bump=first(a,b,'U',['a']),heap_at_bump=first(a,b,'U',['h']),
        learned_content=first(a,b,'L',['r']),decision=first(a,b,'D',['v']),
        restart_queue=first(a,b,'QT',['restart']),restart_after_learning=first(a,b,'QL',['restart']))
    for r in diffs.values():
        for name,cat in [('A',ac),('B',bc)]:
            if name in r:r[name]['clause']=cat.get(r[name]['r'])
    dump(OUT/'first_divergences.json',diffs)
    l2={k:[r for r in b[k] if r['l2']] for k in ('W','W_AFTER','E','A','M','C')}
    dump(OUT/'l2_all_uses.json',l2)
    dump(OUT/'restart_actions.json',dict(A=a['RESTART'],B=b['RESTART']))
    snaps=[compare_snap(n) for n in ('initialized','first_reason_before','first_reason_after','L_199_1','ANALYZE_PRE_656_1','D_PRE_657_1')]
    dump(OUT/'snapshot_comparison.json',snaps)
    changes=[]
    for conflict in (199,291,656):
        # Actual visited clauses/pivots; these are the executed implication proof.
        for n,g,cat in [('A',a,ac),('B',b,bc)]:
            changes.append(dict(run=n,conflict=conflict,
                analysis=[dict(r,clause=cat[r['r']]) for r in g['A'] if r['c']==conflict],
                bumps=[r for r in g['U'] if r['c']==conflict],
                minimization=[dict(r,clause=cat[r['r']]) for r in g['M'] if r['c']==conflict],
                conflict_event=next(r for r in g['C'] if r['c']==conflict),
                learned=next(dict(r,clause=cat[r['r']]) for r in g['L'] if r['c']==conflict)))
    dump(OUT/'critical_analysis_paths.json',changes)
    print(json.dumps(dict(first_l2={k:rr[0] if rr else None for k,rr in l2.items()},counts={k:len(v) for k,v in l2.items()},diffs=diffs,
        snapshots=[dict(name=s['name'],different=[k for k,v in s['fields'].items() if not v['equal']]) for s in snaps]),indent=2))

if __name__=='__main__':main()
