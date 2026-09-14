"""Frozen experiment join; all resolution/checking/search reuse repository tools."""
from collections import Counter, defaultdict
from dataclasses import asdict
from itertools import combinations
import csv
import json
from pathlib import Path
import random
from statistics import median
from time import perf_counter
import sys

from evaluation_oracle_run import sha
from homologous_template_run import encoding_leaf, NATIVE
from oracle_lemma import prepare, TARGET, HISTORY, TEMPLATE, Evaluator, objective
from oracle_lemma_evaluate import materialize
from replay_budget import HistoryIndex
from round4_core import ProofDB, Budget, ancestors
from satcache import normalize

OUT = Path('results/target_local_history')


def dump(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')


def csvout(name, rows):
    with (OUT/name).open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def cheap_pool(cnf):
    """Schedule exactly <=2 inferences through the existing proof producer."""
    start = perf_counter()
    db = ProofDB(cnf, Budget(10**8))
    occurrence = defaultdict(list)
    for i, c in enumerate(cnf):
        for lit in c:
            occurrence[lit].append(i)
    n = len(cnf)
    for i, c in enumerate(cnf):
        for lit in c:
            for j in occurrence[-lit]:
                if j > i:
                    db.resolve(i, j, lit)
    first_end = len(db.nodes)
    for i in range(n, first_end):
        for lit in db.nodes[i]:
            for j in occurrence[-lit]:
                db.resolve(i, j, lit)
    assert db.budget.attempts < db.budget.limit
    result = db.certificate()
    meta = dict(seconds=perf_counter()-start, first_step=first_end-n,
                second_step=len(db.nodes)-first_end, budget=asdict(db.budget),
                reads_history=False, reads_template=False)
    return result, meta


def matched_oracle(data, label, seed):
    start = perf_counter()
    engine = Evaluator(data, OUT/f'oracle_{label}_{seed}', workers=4)
    rng = random.Random(seed)
    try:
        singles = rng.sample(data['population'], 512)
        rr = engine.batch([[i] for i in singles], 'singletons')
        order = [r['selected_ids'][0] for r in sorted(rr, key=objective)]
        elite = order[:128]
        for k in (16,32,64):
            candidates = [order[:k]]
            candidates += [rng.sample(data['population'] if j%2==0 else elite, k)
                           for j in range(96)]
            engine.batch(candidates, f'subsets_{k}')
        current = engine.best(64, exact=True)['selected_ids']
        while len(current)>16:
            removals = rng.sample(current,8)
            rr = engine.batch([[j for j in current if j!=i] for i in removals],
                              f'backward_{len(current)}')
            current = min(rr,key=objective)['selected_ids']
        for k in (16,32,64):
            for iteration in range(4):
                current = engine.best(k,exact=True)['selected_ids']
                candidates = []
                for j in range(16):
                    remove = rng.choice(current)
                    pool = elite if j%2 else data['population']
                    add = rng.choice(pool)
                    while add in current:
                        add = rng.choice(pool)
                    candidates.append([i for i in current if i!=remove]+[add])
                engine.batch(candidates,f'swaps_{k}_{iteration}')
        result = dict(label=label, seed=seed, exact={str(k):engine.best(k,exact=True)
                      for k in (16,32,64)}, unique_evaluations=len(engine.cache),
                      wall_seconds=perf_counter()-start,
                      sum_process_seconds=sum(r['screen_process_seconds'] for r in engine.cache.values()))
        dump(f'oracle_{label}_{seed}.json',result)
        return result
    finally:
        engine.close()


def timed(data, specs):
    engines = {label:Evaluator(d,OUT/f'final_{label}',workers=1) for label,d in data.items()}
    rows = []
    jobs = [(name,rep) for name in specs for rep in range(5)]
    random.Random(20260911).shuffle(jobs)
    try:
        for name, rep in jobs:
            label, ids = specs[name]
            start = perf_counter()
            _, _, stats = materialize(data[label],dict(template=True,ids=ids))
            row = engines[label].solve(tuple(ids))
            row.update(stats, route=name, repeat=rep,total_wall_seconds=perf_counter()-start)
            assert row['status']=='UNSAT'
            rows.append(row)
        (OUT/'raw.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        summaries=[]
        for name in specs:
            rr=[r for r in rows if r['route']==name]
            assert len({(r['analysis_resolution_steps'],r['conflicts'],r['input_sha256']) for r in rr})==1
            summaries.append(dict(route=name,repeats=len(rr),**{k:median(r[k] for r in rr)
                for k in ('analysis_resolution_steps','conflicts','decisions','propagations',
                          'replay_and_check_seconds','total_wall_seconds','support_inferences')},
                time_min=min(r['total_wall_seconds'] for r in rr),
                time_max=max(r['total_wall_seconds'] for r in rr)))
        csvout('summary.csv',summaries)
    finally:
        for e in engines.values(): e.close()


def synergy(data,gold,local,nonlocal_ids):
    e=Evaluator(data,OUT/'synergy_search',workers=4)
    try:
        base,full=e.batch([[],gold],'anchors')
        b,g=base['analysis_resolution_steps'],full['analysis_resolution_steps']
        single=e.batch([[i] for i in gold],'singletons')
        drop=e.batch([[j for j in gold if j!=i] for i in gold],'leave_one_out')
        singles={i:r['analysis_resolution_steps'] for i,r in zip(gold,single)}
        drops={i:r['analysis_resolution_steps'] for i,r in zip(gold,drop)}
        csvout('marginals.csv',[dict(id=i,singleton_ops=singles[i],singleton_gain=b-singles[i],
            leave_one_out_ops=drops[i],deletion_penalty=drops[i]-g) for i in gold])
        pairs=random.Random(20260911).sample(list(combinations(gold,2)),128)
        rr=e.batch(pairs,'pairs')
        csvout('pairs.csv',[dict(a=a,b=c,ops=r['analysis_resolution_steps'],
            interaction_gain=singles[a]+singles[c]-b-r['analysis_resolution_steps'])
            for (a,c),r in zip(pairs,rr)])
        orders={'singleton_best':sorted(gold,key=lambda i:(singles[i],i)),
                'leave_one_out_best':sorted(gold,key=lambda i:(-drops[i],i)),
                'source_importance':[i for i in data['ranked'] if i in gold]}
        for seed in (17,29,43,71,97):
            orders[f'random_{seed}']=random.Random(seed).sample(gold,len(gold))
        dump('orders.json',orders)
        rows=[]
        for name,order in orders.items():
            rr=e.batch([order[:k] for k in range(65)],name)
            rows += [dict(order=name,k=k,ops=r['analysis_resolution_steps'],conflicts=r['conflicts'])
                     for k,r in enumerate(rr)]
        csvout('progressive.csv',rows)
        # Membership fixed; these controls change actual insertion order, bypassing ids_key.
        controls=[]
        for seed in (17,29,43,71,97):
            shuffled=random.Random(seed).sample(gold,len(gold))
            for name,selected in [('TEMPLATE',[]),('LOCAL',[i for i in shuffled if i in local]),
                    ('NONLOCAL',[i for i in shuffled if i in nonlocal_ids]),('Gold64',shuffled)]:
                r=e.solve(tuple(selected))
                controls.append(dict(seed=seed,route=name,ops=r['analysis_resolution_steps'],conflicts=r['conflicts']))
        csvout('insertion_controls.csv',controls)
    finally: e.close()


def main():
    OUT.mkdir(exist_ok=True)
    cnf=normalize(json.loads(TARGET.read_text())['cnf'])
    proof,poolmeta=cheap_pool(cnf)  # H and TEMPLATE have not been opened.
    dump('target_pool_proof.json',asdict(proof))
    dump('target_pool_meta.json',poolmeta)
    print('target-only pool',poolmeta,flush=True)
    target_index=HistoryIndex(proof)
    data=prepare()
    from oracle_lemma import strip_template
    population, exclusions=strip_template(target_index,cnf,data['templates'])
    td=dict(data,h=target_index,population=population)
    gold=json.loads(Path('results/oracle_lemma/gold_lemmas.json').read_text())['sets']['exact_64']['selected_ids']
    lookup={c:i for i,c in enumerate(target_index.clauses)}
    local=[i for i in gold if data['h'].clauses[i] in lookup]
    nonlocal_ids=[i for i in gold if i not in local]
    classification=[dict(id=i,clause=data['h'].clauses[i],category='LOCAL' if i in local else 'NONLOCAL',
        target_steps=(len(ancestors(proof,lookup[data['h'].clauses[i]]))-len(
            [j for j in ancestors(proof,lookup[data['h'].clauses[i]]) if j<len(cnf)])) if i in local else None)
        for i in gold]
    dump('classification.json',classification)
    sources={str(p):sha(p) for p in (TARGET,HISTORY,TEMPLATE,Path('target_local_history.py'),
        Path('docs/target-local-protocol.md'),Path('results/oracle_lemma/gold_lemmas.json'),
        Path('round4_core.py'),Path('oracle_lemma.py'),Path('replay_budget.py'),NATIVE/'counted')}
    dump('metadata.json',dict(sources=sources,poolmeta=poolmeta,target_population=len(population),
        history_population=len(data['population']),target_exclusions=exclusions,
        prepare_seconds=data['prepare_seconds'],local=local,nonlocal_ids=nonlocal_ids,
        oracle_globally_optimal=False,oracle_seeds=[17,29,43]))
    specs={'TEMPLATE':('history',[]),'LOCAL':('history',local),
           'NONLOCAL':('history',nonlocal_ids),'Gold64':('history',gold),
           'LOCAL_target_proof':('target',[lookup[data['h'].clauses[i]] for i in local])}
    # The last route preserves Gold order, changing only its validation proof.
    timed({'history':data,'target':td},specs)
    print('classification',len(local),len(nonlocal_ids),flush=True)
    synergy(data,gold,local,nonlocal_ids)
    results=[]
    for seed in (17,29,43):
        for label,d in [('target',td),('history',data)]:
            results.append(matched_oracle(d,label,seed))
    dump('oracles.json',results)
    for label in ('history','target'):
        for k in (16,32,64):
            winners=[r['exact'][str(k)] for r in results if r['label']==label]
            specs[f'{label}Oracle_{k}']=(label,min(winners,key=objective)['selected_ids'])
    dump('selections.json',specs)
    timed({'history':data,'target':td},specs)
    print('DONE',flush=True)


if __name__=='__main__': main()
