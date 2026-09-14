"""Compare direct parity CNF with an XOR-chain extension (heuristic width)."""
from __future__ import annotations
import argparse, random, itertools
import statistics, csv, heapq, subprocess, tempfile, pathlib, time

_native = None

def native_width(adj, method):
    global _native
    if _native is None:
        _native = tempfile.TemporaryDirectory(prefix='satfinding-width-')
        source = pathlib.Path(__file__).with_name('extension_minfill.cpp')
        subprocess.run(['clang++', '-O3', '-std=c++17', str(source), '-o',
                        str(pathlib.Path(_native.name) / 'width')], check=True)
    ids = {v:i for i,v in enumerate(adj)}
    edges = [(ids[v],ids[u]) for v,ns in adj.items() for u in ns if ids[v]<ids[u]]
    data = '{} {}\n'.format(len(ids),len(edges)) + ''.join('{} {}\n'.format(*e) for e in edges)
    result = subprocess.run([str(pathlib.Path(_native.name)/'width'), method],
                            input=data, text=True, capture_output=True, check=True)
    return int(result.stdout)

def minfill_width(adj):
    ids={v:i for i,v in enumerate(adj)}; n=len(ids)
    g=[0]*n
    for v,ns in adj.items():
        m=0
        for u in ns: m |= 1<<ids[u]
        g[ids[v]]=m
    alive=(1<<n)-1; width=0
    while alive:
        best=None; bestkey=None; bits=alive
        while bits:
            lb=bits & -bits; v=lb.bit_length()-1; bits-=lb
            ns=g[v]&alive; deg=ns.bit_count() if hasattr(ns,'bit_count') else bin(ns).count('1'); missing=0; a=ns
            while a:
                la=a&-a; i=la.bit_length()-1; a-=la
                z=ns & ~g[i]; missing += z.bit_count() if hasattr(z,'bit_count') else bin(z).count('1')
            key=(missing,deg)
            if bestkey is None or key<bestkey: best,bestkey=v,key
        v=best; ns=g[v]&alive; width=max(width,ns.bit_count() if hasattr(ns,'bit_count') else bin(ns).count('1'))
        a=ns
        while a:
            la=a&-a; u=la.bit_length()-1; a-=la
            g[u] |= ns & ~(1<<u)
            g[u] &= ~(1<<v)
        alive &= ~(1<<v)
    return width

def eliminate_width(adj, scorer='degree', shortlist=64):
    ids={v:i for i,v in enumerate(adj)}; n=len(ids); g=[0]*n
    for v,ns in adj.items():
        for u in ns: g[ids[v]] |= 1<<ids[u]
    alive=(1<<n)-1; width=0
    heap=[(bin(g[v]).count('1'),v) for v in range(n)]; heapq.heapify(heap)
    while alive:
        if scorer=='degree':
            while True:
                d,v=heapq.heappop(heap)
                cur=bin(g[v]&alive).count('1')
                if (alive>>v)&1 and d==cur: break
            ns=g[v]&alive; width=max(width,bin(ns).count('1')); a=ns
            while a:
                z=a&-a; u=z.bit_length()-1; a-=z; g[u]|=ns&~(1<<u); g[u]&=~(1<<v)
                heapq.heappush(heap,(bin(g[u]&alive).count('1'),u))
            alive&=~(1<<v); continue
        cand=[]; b=alive
        while b:
            z=b&-b; v=z.bit_length()-1; b-=z; d=bin(g[v]&alive).count('1')
            cand.append((d,v))
        cand.sort(); cand=cand[:shortlist] if scorer=='sampled' else cand
        if scorer=='degree': v=cand[0][1]
        else:
            best=None
            for _,v0 in cand:
                ns=g[v0]&alive; miss=0; a=ns
                while a:
                    z=a&-a; i=z.bit_length()-1; a-=z
                    miss += bin(ns & ~g[i]).count('1')
                degree=bin(ns).count('1')
                key=((miss-degree)//2,degree,v0)
                if best is None or key<best[0]: best=(key,v0)
            v=best[1]
        ns=g[v]&alive; width=max(width,bin(ns).count('1')); a=ns
        while a:
            z=a&-a; u=z.bit_length()-1; a-=z; g[u]|=ns&~(1<<u); g[u]&=~(1<<v)
        alive&=~(1<<v)
    return width

def add_clause(adj, clause):
    clause=[x[1] if isinstance(x,tuple) else x for x in clause]
    for x in clause: adj.setdefault(x,set())
    for i,x in enumerate(clause):
        for y in clause[i+1:]: adj[x].add(y); adj[y].add(x)

def build(n, d, extended, seed=0, method='full', edges=None):
    if edges is None:
        edges = legacy_edges(n, d, seed)
    return encode_width(n, edges, extended, method)

def legacy_edges(n, d, seed):
    rng=random.Random(seed); edges=[]
    for i in range(n):
        for k in range(d//2):
            j=(i + 1 + rng.randrange(n-1))%n
            if i<j: edges.append((i,j))
            else: edges.append((j,i))
    return list(dict.fromkeys(edges))

def encode_width(n, edges, extended, method):
    adj={}
    # parity constraints are represented by a local chain encoding of XOR.
    for v in range(n):
        inc=[k for k,e in enumerate(edges) if v in e]
        if not inc: continue
        cur=inc[0]
        if not extended:
            # Every direct parity clause has exactly this variable scope.
            # Build the identical primal graph without enumerating assignments.
            add_clause(adj,inc)
            continue
        if len(inc)==1: add_clause(adj,inc); continue
        for k in inc[1:-1]:
            if extended:
                y=f"y{v}_{k}"
                for c in ((cur,k,('!',y)),(cur,('!',k),y),(('!',cur),k,y),(('!',cur),('!',k),('!',y))): add_clause(adj,list(c))
                cur=y
        # final parity equation cur XOR last = 1, encoded as two clauses
        if len(inc)>1: add_clause(adj,[cur,inc[-1]]); add_clause(adj,[('!',cur),('!',inc[-1])])
    w=native_width(adj,method) if method in ('degree','full','sampled') else eliminate_width(adj,method,64)
    return len(edges), len(adj), w

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--seeds',type=int,default=20); ap.add_argument('--output',default='extension_width_results.csv'); ap.add_argument('--method',choices=('degree','sampled','full'),default='degree')
    ap.add_argument('--sizes', type=int, nargs='+', default=[20,40,80,160,320,640,1280,2560])
    a=ap.parse_args()
    if a.seeds<1 or any(n<2 for n in a.sizes): ap.error('seeds >= 1 and sizes >= 2 required')
    output=pathlib.Path(a.output)
    rawpath=output.with_name(output.stem+'_raw.csv')
    rawfile=rawpath.open('w',newline='')
    raw=csv.DictWriter(rawfile,fieldnames=['n','seed','method','extended','width','original_vars','total_vars','extension_vars','width_per_original','width_per_total','seconds'])
    raw.writeheader()
    rows=[]
    for n in a.sizes:
      vals={False:[],True:[]}
      for s in range(a.seeds):
        for ext in (False,True):
          start=time.perf_counter()
          e,v,w=build(n,6,ext,s,a.method); vals[ext].append((w,e,v))
          raw.writerow(dict(n=n,seed=s,method=a.method,extended=ext,width=w,original_vars=e,total_vars=v,extension_vars=v-e,width_per_original=w/e,width_per_total=w/v,seconds=time.perf_counter()-start))
          rawfile.flush()
        print(f'n={n} seed={s+1}/{a.seeds} complete',flush=True)
      for ext in (False,True):
        data=vals[ext]; ws=sorted(x[0] for x in data)
        q=lambda p:quantile(ws,p)
        med=statistics.median(ws); med_e=statistics.median(x[1] for x in data); med_v=statistics.median(x[2] for x in data)
        rows.append(dict(n=n,method=a.method,seeds=a.seeds,extended=ext,median=med,p25=q(.25),p75=q(.75),width_per_original=statistics.median(w/e for w,e,v in data),width_per_total=statistics.median(w/v for w,e,v in data),extension_vars=statistics.median(v-e for w,e,v in data)))
      with open(a.output,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    rawfile.close()
    print('n ext median p25 p75 width/original width/total ext-vars')
    for r in rows: print(r['n'],int(r['extended']),r['median'],r['p25'],r['p75'],f"{r['width_per_original']:.4f}",f"{r['width_per_total']:.4f}",r['extension_vars'])
def quantile(values,p):
    values=sorted(values); pos=(len(values)-1)*p; i=int(pos)
    return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(pos-i)

if __name__=='__main__': main()
