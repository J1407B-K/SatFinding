"""Fixed-budget unseen-target experiment; existing producer, checker, evaluator."""
from collections import Counter, defaultdict
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
from time import perf_counter

from evaluation_oracle_run import sha
from homologous_graphs import evolve
from homologous_template_run import load_history, encoding_leaf, NATIVE
from oracle_lemma import HISTORY, TEMPLATE, Evaluator, objective
from replay_budget import HistoryIndex
from round4_core import ProofDB, Budget
from satcache import check, normalize

OUT=Path('results/unseen_selector')
K=64
M=512
SEEDS=(9202,9203,9204)


def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2)+'\n')


def digest(value):
    return hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()


def prior_build():
    start=perf_counter()
    proof,_=load_history(HISTORY)
    assert check(proof.premises,proof)
    idx=HistoryIndex(proof)
    prior={}
    for i,score in idx.scores.items():
        c=idx.clauses[i]
        if c not in prior or score>prior[c]:prior[c]=score
    elapsed=perf_counter()-start
    payload=[[c,s.numerator,s.denominator] for c,s in sorted(prior.items())]
    dump(OUT/'history_prior.json',payload)
    start=perf_counter()
    loaded={tuple(c):Fraction(n,d) for c,n,d in json.loads((OUT/'history_prior.json').read_text())}
    load_seconds=perf_counter()-start
    assert loaded==prior
    return prior,dict(build_check_index_seconds=elapsed,prior_load_seconds=load_seconds,
        prior_entries=len(prior),prior_bytes=(OUT/'history_prior.json').stat().st_size,
        source_sha256=sha(HISTORY),prior_sha256=sha(OUT/'history_prior.json'))


def candidates(cnf,templates):
    start=perf_counter()
    occurrence=defaultdict(list)
    for i,c in enumerate(cnf):
        for lit in c:occurrence[lit].append(i)
    db=ProofDB(cnf,Budget(4096))
    seen=set(cnf)
    template_sets=[set(c) for c in templates]
    selected=[]
    order=list(range(len(cnf)))
    random.Random(17).shuffle(order)
    for i in order:
        for lit in cnf[i]:
            for j in occurrence[-lit]:
                if db.budget.attempts>=4096:raise RuntimeError('Fixed generation budget exhausted')
                r=db.resolve(i,j,lit)
                if r is None or db.nodes[r] in seen:continue
                c=db.nodes[r]
                seen.add(c)
                if encoding_leaf(cnf[i]) and encoding_leaf(cnf[j]):continue
                if any(t<=set(c) for t in template_sets if len(t)<=len(c)):continue
                selected.append(r)
                if len(selected)==M:
                    idx=HistoryIndex(db.certificate())
                    elapsed=perf_counter()-start
                    if elapsed>.1:raise RuntimeError('Fixed generation wall cap exceeded')
                    return idx,selected,dict(generation_seconds=elapsed,resolver_attempts=db.budget.attempts,
                        literal_visits=db.budget.literal_visits,candidates_examined=len(selected),
                        outputs_sha256=digest([idx.clauses[x] for x in selected]))
    raise RuntimeError('Not enough candidates; no fallback permitted')


def select(instance,idx,population,prior=None):
    start=perf_counter()
    cnf=instance['cnf']
    adjacency=defaultdict(set)
    for a,b in instance['edges']:
        adjacency[a].add(b);adjacency[b].add(a)
    jw=defaultdict(float)
    for c in cnf:
        for x in c:jw[x]+=2.0**(-len(c))
    feature=[]
    for i in population:
        c=idx.clauses[i]
        vertices=sorted({(abs(x)-1)//3 for x in c})
        assert len(vertices)==2
        a,b=vertices
        target=(len(c),-len(adjacency[a]&adjacency[b]),-sum(jw[-x] for x in c),digest(c))
        score=prior.get(c,Fraction(0)) if prior is not None else Fraction(0)
        feature.append(((-score,)+target,i,score,target))
    feature.sort(key=lambda x:x[0])
    ids=sorted(r[1] for r in feature[:K])
    elapsed=perf_counter()-start
    if elapsed>.05:raise RuntimeError('Fixed selection wall cap exceeded')
    return ids,dict(selection_seconds=elapsed,feature_evaluations=len(feature),
        prior_lookups=len(feature) if prior is not None else 0,sorts=1,
        prior_hits=sum(r[2]>0 for r in feature),selected_prior_hits=sum(r[2]>0 for r in feature[:K]),
        target_feature_histogram=dict(Counter(str(r[3][:-1]) for r in feature)),
        selected_sha256=digest([idx.clauses[i] for i in ids]))


def template_data():
    start=perf_counter()
    proof,_=load_history(TEMPLATE)
    assert check(proof.premises,proof)
    idx=HistoryIndex(proof)
    frozen=json.loads(Path('results/oracle_lemma/metadata.json').read_text())
    ids=frozen['template_ids']
    clauses=[tuple(c) for c in frozen['template_lemmas']]
    assert [idx.clauses[i] for i in ids]==clauses and len(clauses)==67
    return idx,ids,clauses,perf_counter()-start


def oracle(data,online,name):
    e=Evaluator(data,OUT/name/'oracle',workers=4)
    start=perf_counter()
    rng=random.Random(17)
    try:
        proposals=[online['TARGET'],online['HISTORY']]+[rng.sample(data['population'],K) for _ in range(96)]
        e.batch(proposals,'fixed_sets')
        for step in range(4):
            current=e.best(K,exact=True)['selected_ids']
            proposals=[]
            for _ in range(16):
                remove=rng.choice(current)
                add=rng.choice(data['population'])
                while add in current:add=rng.choice(data['population'])
                proposals.append([i for i in current if i!=remove]+[add])
            e.batch(proposals,f'fixed_swaps_{step}')
        result=dict(best=e.best(K,exact=True),unique_calls=len(e.cache),proposals=162,
                    discovery_seconds=perf_counter()-start,
                    sum_process_seconds=sum(r['screen_process_seconds'] for r in e.cache.values()),
                    globally_optimal=False)
        dump(OUT/name/'oracle.json',result)
        return result
    finally:e.close()


def run():
    OUT.mkdir(exist_ok=True)
    if (OUT/'online_frozen.json').exists():raise RuntimeError('Already frozen; do not retune/re-run into same directory')
    prior,prior_meta=prior_build()
    t,tids,templates,template_prepare=template_data()
    base=json.loads(Path('results/oracle_transfer_6regular/n200_H_s6202.json').read_text())
    old_hashes=set()
    for directory in ('results/homologous_template','results/oracle_transfer_6regular'):
        for path in Path(directory).glob('*.json'):
            content=json.loads(path.read_text())
            if isinstance(content,dict) and 'cnf' in content:
                assert content.get('seed') not in SEEDS
                old_hashes.add(digest(normalize(content['cnf'])))
    instances={};data={};frozen={}
    for number,seed in enumerate(SEEDS,2):
        name=f'T{number}'
        instance=evolve(200,base['edges'],.01,seed)
        instance['cnf']=normalize(instance['cnf'])
        assert digest(instance['cnf']) not in old_hashes
        assert all(digest(instance['cnf'])!=digest(other['cnf']) for other in instances.values())
        instances[name]=instance
        (OUT/name).mkdir(exist_ok=True)
        dump(OUT/name/'target.json',instance)
        _,checked,_=t.materialize(instance['cnf'],tids)
        assert checked==templates
        idx,pop,gen=candidates(instance['cnf'],templates)
        a,sa=select(instance,idx,pop)
        b,sb=select(instance,idx,pop,prior)
        frozen[name]=dict(seed=seed,cnf_sha256=digest(instance['cnf']),population=pop,
            online={'TARGET':a,'HISTORY':b},generation=gen,target_selection=sa,history_selection=sb,
            candidate_clauses=[idx.clauses[i] for i in pop],proof=asdict(idx.history),
            drift=instance['drift'])
        data[name]=dict(cnf=instance['cnf'],templates=templates,h=idx,population=pop)
    sources={str(p):sha(p) for p in [Path(__file__),Path('docs/unseen-selector-protocol.md'),HISTORY,TEMPLATE,
             Path('homologous_graphs.py'),Path('replay_budget.py'),Path('round4_core.py'),Path('oracle_lemma.py'),NATIVE/'counted']}
    dump(OUT/'online_frozen.json',frozen)
    dump(OUT/'metadata.json',dict(prior=prior_meta,template_prepare_seconds=template_prepare,
        sources=sources,online_frozen_sha256=sha(OUT/'online_frozen.json'),
        targets_frozen_before_any_target_completion=True,K=K,M=M,seeds=SEEDS,
        solver=dict(binary=str(NATIVE/'counted'),conflict_budget=1000000,timeout=30)))
    print('All online selections frozen before any target completion',flush=True)
    oracle_results={name:oracle(data[name],frozen[name]['online'],name) for name in instances}
    engines={name:Evaluator(d,OUT/name/'timing',workers=1) for name,d in data.items()}
    jobs=[(name,route,rep) for name in instances for route in ['TEMPLATE','TARGET','HISTORY','ORACLE'] for rep in range(5)]
    random.Random(20260911).shuffle(jobs)
    rows=[]
    try:
        for name,route,rep in jobs:
            start=perf_counter()
            instance=instances[name]
            generation={};selection={}
            if route=='TEMPLATE':
                ids=[]
                idx=data[name]['h']
            else:
                idx,pop,generation=candidates(instance['cnf'],templates)
                assert pop==frozen[name]['population']
                if route=='ORACLE':
                    pick_start=perf_counter()
                    ids=oracle_results[name]['best']['selected_ids']
                    selection=dict(selection_seconds=perf_counter()-pick_start)
                else:
                    ids,selection=select(instance,idx,pop,prior if route=='HISTORY' else None)
                    assert ids==frozen[name]['online'][route]
            validation_start=perf_counter()
            _,tc,ts=t.materialize(instance['cnf'],tids)
            if ids:
                _,clauses,stats=idx.materialize(instance['cnf'],ids)
                assert stats['support_inferences']==K and len(clauses)==K
            else:stats=dict(support_inferences=0)
            assert tc==templates
            validation=perf_counter()-validation_start
            # Engines write target + TEMPLATE + selected clauses to a temporary file.
            row=engines[name].solve(tuple(ids))
            assert row['status']=='UNSAT', (name,route,row['status'])
            row.update(target=name,route=route,repeat=rep,**generation,**selection,
                validation_seconds=validation,solver_seconds=row['seconds'],
                total_seconds=perf_counter()-start,validation_steps=stats['support_inferences'],
                template_steps=ts['support_inferences'])
            rows.append(row)
        (OUT/'raw.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    finally:
        for e in engines.values():e.close()
    print('DONE 60 sequential final measurements',flush=True)


if __name__=='__main__':run()
