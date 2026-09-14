"""Compact divergence and executed implication-path analysis; no solve calls."""
from collections import defaultdict,deque
import csv
import gzip
import json
from pathlib import Path
from statistics import mean,median
from gold_mechanism_run import OUT
from unseen_selector import dump

def load(name):
    with gzip.open(OUT/(name+'.trace.jsonl.gz'),'rt') as f:rows=[json.loads(l) for l in f]
    g=defaultdict(list)
    for r in rows:g[r['t']].append(r)
    g['catalog']={r['id']:r for r in g['Q']};g['events']={r['e']:r for r in g['E']}
    return g

def clause(g,r):return g['catalog'][r]['clause'] if r>=0 else []
def label(g,r):return g['catalog'][r]['label'] if r>=0 else 'decision/root-unit'
def simple(g,r):
    out={k:v for k,v in r.items() if k not in ('mask','deps','top')}
    if 'r' in r:out.update(clause=clause(g,r['r']),label=label(g,r['r']))
    return out

def divergent(a,b,kind,fn,flt=lambda r:True):
    aa=[r for r in a[kind] if flt(r)];bb=[r for r in b[kind] if flt(r)]
    for i,(x,y) in enumerate(zip(aa,bb)):
        if fn(a,x)!=fn(b,y):return dict(ordinal=i+1,control=simple(a,x),treatment=simple(b,y))
    return dict(equal_prefix=min(len(aa),len(bb)),different_lengths=len(aa)!=len(bb))

def ancestors(g,event):
    todo=list(event.get('deps',[]));seen=set()
    while todo:
        e=todo.pop()
        if e in seen:continue
        seen.add(e);todo.extend(g['events'][e]['deps'])
    return seen

def paths(g,event):
    """Shortest executed edge path from each Gold reason to the selected event."""
    pending=deque((e,[]) for e in event.get('deps',[]));seen=set();found={}
    if event['t']=='E':pending=deque([(event['e'],[])])
    while pending:
        e,tail=pending.popleft()
        if e in seen:continue
        seen.add(e);r=g['events'][e];path=[e]+tail
        if r['r']>=0:
            gold=g['catalog'][r['r']]['gold']
            if gold>=0 and gold not in found:found[gold]=path
        pending.extend((p,path) for p in r['deps'])
    return found

def check_graph(g):
    for e in g['E']:
        if e['r']<0:assert not e['deps'];continue
        assert all(0<d<e['e'] for d in e['deps'])
        assert all(g['events'][d]['dl']<=e['dl'] for d in e['deps'])
        assert set(clause(g,e['r']))-{e['lit']}=={-g['events'][d]['lit'] for d in e['deps']}
        assert e['lit'] in clause(g,e['r'])
    for c in g['C']:
        if 'deps' in c:assert set(clause(g,c['r']))=={-g['events'][d]['lit'] for d in c['deps']}

def main():
    names=[r['name'] for r in json.loads((OUT/'runs.json').read_text())]
    data={n:load(n) for n in names}
    for g in data.values():check_graph(g)
    a,b=data['CONTROL'],data['TREATMENT']
    diffs=dict(
        propagation_literal=divergent(a,b,'E',lambda g,r:r['lit'],lambda r:r['bcp']),
        propagation_reason=divergent(a,b,'E',lambda g,r:(r['lit'],clause(g,r['r'])),lambda r:r['bcp']),
        all_enqueue=divergent(a,b,'E',lambda g,r:(r['lit'],clause(g,r['r']))),
        decision=divergent(a,b,'D',lambda g,r:r['lit']),
        conflict_clause=divergent(a,b,'C',lambda g,r:clause(g,r['r'])),
        conflict_state=divergent(a,b,'C',lambda g,r:(clause(g,r['r']),r['dl'],r['trail'],r['enqueues'])),
        learned=divergent(a,b,'L',lambda g,r:clause(g,r['r'])))
    dump(OUT/'divergence.json',diffs)
    existing={int(r['id']):{k:int(v) for k,v in r.items()} for r in csv.DictReader(open('results/target_local_history/marginals.csv'))}
    usages=[]
    for r in b['Q']:
        if r['gold']<0:continue
        u=dict(id=r['gold'],clause=r['clause'],bcp=r['bcp'],reason=r['reason'],analysis=r['analysis'],
            minimization=r['minimize'],conflict=r['conflict'],first_completed_conflicts=r['first_reason'],
            first_analysis_conflict=r['first_analysis'],first_direct_conflict=r['first_conflict'],
            first_effect=(f"propagation after {r['first_reason']} completed conflicts" if
                r['first_conflict']<0 or r['first_reason']<r['first_conflict'] else f"conflict {r['first_conflict']}"),
            never_direct=(r['reason']+r['analysis']+r['minimize']+r['conflict']==0),
            **{k:v for k,v in existing[r['gold']].items() if k!='id'})
        usages.append(u)
    usages.sort(key=lambda r:r['id']);assert len(usages)==64
    with (OUT/'lemma_usage.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(usages[0]));w.writeheader();w.writerows(usages)
    dump(OUT/'lemma_usage.json',usages)
    qcontrol={(r['label'],tuple(r['clause'])):r for r in a['Q']}
    cases=[]
    for c in b['C'][:64]:
        pp=paths(b,c)
        if not pp:continue
        learned=next((r for r in b['L'] if r['c']==c['c']),None)
        cc=a['C'][c['c']-1]
        record=dict(conflict=simple(b,c),control_same_ordinal=simple(a,cc),
            gold_ancestors=sorted(pp),learned=simple(b,learned) if learned else None,paths=[])
        for gold,path in sorted(pp.items(),key=lambda kv:len(kv[1]))[:3]:
            nodes=[]
            for e in path:
                node=simple(b,b['events'][e]);r=b['catalog'].get(node['r'])
                if r:
                    other=qcontrol.get((r['label'],tuple(r['clause'])))
                    node['first_reason_conflict_T']=r['first_reason']
                    node['first_reason_conflict_C']=other['first_reason'] if other else None
                nodes.append(node)
            record['paths'].append(dict(gold=gold,nodes=nodes))
        cases.append(record)
        if len(cases)==6:break
    dump(OUT/'case_studies.json',cases)
    joint={}
    for name in ('TREATMENT','L1_L2','L1_L2_L3'):
        g=data[name];found=[]
        for e in g['E']:
            if e['r']<0 or g['catalog'][e['r']]['gold']>=0:continue
            pp=paths(g,e)
            if len(pp)>=2:
                found.append(dict(event=simple(g,e),gold_ancestors=sorted(pp),
                    paths=[dict(gold=k,nodes=[simple(g,g['events'][v]) for v in p]) for k,p in sorted(pp.items())]))
                break
        for c in g['C'][:64]:
            pp=paths(g,c)
            if len(pp)>=2:
                found.append(dict(event=simple(g,c),gold_ancestors=sorted(pp),
                    paths=[dict(gold=k,nodes=[simple(g,g['events'][v]) for v in p]) for k,p in sorted(pp.items())]))
                break
        joint[name]=found
    dump(OUT/'joint_activation.json',joint)
    state={}
    for name in ('CONTROL','TREATMENT'):
        g=data[name];learn=g['L'];
        state[name]=dict(conflicts=len(g['C']),mean_width=mean(r['width'] for r in learn),
            mean_lbd=mean(r['lbd'] for r in learn),mean_dl=mean(r['dl'] for r in learn),
            mean_backjump=mean(r['dl']-r['bt'] for r in learn),restarts=[r['c'] for r in g['R']],
            actual_dequeues=g['END'][0]['dequeues'],enqueues=g['END'][0]['enqueues'])
    end=b['C'][-1]['c'];control_at=next(r for r in a['L'] if r['c']==end)['ops']
    state['accounting']=dict(common_conflicts=end,control_ops_at_common=control_at,
        treatment_final_ops=b['C'][-1]['ops'],control_final_ops=a['C'][-1]['ops'],
        prefix_savings=control_at-b['C'][-1]['ops'],
        extra_control_tail=a['C'][-1]['ops']-control_at)
    dump(OUT/'state_summary.json',state)
    dump(OUT/'graph_audit.json',dict(status='PASS',configurations=len(data),
        checked_reason_events=sum(len(g['E']) for g in data.values()),
        checked_early_conflicts=sum(min(64,len(g['C'])) for g in data.values())))
    print(json.dumps(dict(divergence=diffs,state=state,joint={n:[(r['event'],r['gold_ancestors']) for r in rr] for n,rr in joint.items()}),indent=2))

if __name__=='__main__':main()
