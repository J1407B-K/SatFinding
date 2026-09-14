"""Independent frozen experiment: only resolver exploration order varies."""
from collections import defaultdict
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import random
from time import perf_counter

from evaluation_oracle_run import sha
from homologous_graphs import evolve
from homologous_template_run import load_history, encoding_leaf, NATIVE
from oracle_lemma import HISTORY, TEMPLATE, Evaluator
from replay_budget import HistoryIndex
from round4_core import ProofDB, Budget
from satcache import normalize, check
from unseen_selector import digest, dump, select, template_data

OUT = Path('results/history_guided_generation')
SEEDS = tuple(range(19201,19221))
BUDGETS = (64,128,256,512,1024)
ROUTES = ('TARGET-GEN','HISTORY-GEN')
PROTOCOL = Path('docs/history-guided-generation-protocol.md')


def key(i,j,p):
    return (i,j,p) if i<j else (j,i,-p)


def build_hints():
    start=perf_counter()
    proof,_=load_history(HISTORY)
    assert check(proof.premises,proof)
    idx=HistoryIndex(proof)
    hints=[]; seen=set()
    for node in idx.orders['ranked']:
        s=proof.steps[node-idx.leaves]
        if s.left>=idx.leaves or s.right>=idx.leaves: continue
        k=key(s.left,s.right,s.pivot)
        if k in seen: continue
        seen.add(k)
        i,j,p=k
        hints.append((proof.premises[i],proof.premises[j],p))
    build=perf_counter()-start
    dump(OUT/'hints.json',hints)
    start=perf_counter()
    hints=[(tuple(a),tuple(b),p) for a,b,p in json.loads((OUT/'hints.json').read_text())]
    return hints,dict(build_seconds=build,load_seconds=perf_counter()-start,
                      hint_pairs=len(hints),sha256=sha(OUT/'hints.json'))


def generate(instance,templates,budget,hints=None):
    start=perf_counter(); cnf=instance['cnf']
    occurrence=defaultdict(list)
    for i,c in enumerate(cnf):
        for p in c: occurrence[p].append(i)
    enc=[encoding_leaf(c) for c in cnf]
    order=list(range(len(cnf)));random.Random(17).shuffle(order)
    schedule=[];seen_pairs=set()
    for i in order:
        for p in cnf[i]:
            for j in occurrence[-p]:
                if enc[i] and enc[j]:continue
                k=key(i,j,p)
                if k not in seen_pairs:
                    schedule.append(k);seen_pairs.add(k)
    retrieval_start=perf_counter(); hits=[]
    if hints is not None:
        lookup={c:i for i,c in enumerate(cnf)}; used=set()
        for a,b,p in hints:
            if a not in lookup or b not in lookup:continue
            k=key(lookup[a],lookup[b],p)
            if k in seen_pairs and k not in used:
                hits.append(k);used.add(k)
        schedule=hits+[k for k in schedule if k not in used]
    retrieval=perf_counter()-retrieval_start
    schedule_hash=digest(schedule)
    db=ProofDB(cnf,Budget(budget)); seen=set(cnf);population=[];unique=0
    ts=[set(t) for t in templates]
    for i,j,p in schedule[:budget]:
        if perf_counter()-start>.1:raise RuntimeError('Frozen generation wall guard breached')
        r=db.resolve(i,j,p)
        if r is None or db.nodes[r] in seen:continue
        c=db.nodes[r];seen.add(c)
        if any(t<=set(c) for t in ts if len(t)<=len(c)):continue
        unique+=1
        if len(population)<512:population.append(r)
    idx=HistoryIndex(db.certificate())
    elapsed=perf_counter()-start
    assert elapsed<=.1 and db.budget.attempts==budget
    return idx,population,dict(resolver_attempts=db.budget.attempts,
        unique_candidates_generated=unique,candidates_retained=len(population),
        generation_seconds=elapsed,retrieval_seconds=retrieval,
        hint_pairs_available=len(hits),hint_attempts=min(budget,len(hits)),
        schedule_sha256=schedule_hash,pair_universe_sha256=digest(sorted(seen_pairs)),
        pool_sha256=digest([idx.clauses[i] for i in population]))


def identity_audit():
    """Read only identities from historical artifacts, never fit to outcomes."""
    seeds=set();hashes=set();files=0
    def visit(x):
        if isinstance(x,dict):
            if isinstance(x.get('seed'),int):seeds.add(x['seed'])
            for name in ('cnf_sha256','input_sha256','target_sha256'):
                if isinstance(x.get(name),str):hashes.add(x[name])
            if 'cnf' in x and isinstance(x['cnf'],list):
                hashes.add(digest(normalize(x['cnf'])))
            for k,v in x.items():
                if k not in ('cnf','steps','premises','candidate_clauses','proof'):
                    if isinstance(v,(dict,list)):visit(v)
        elif isinstance(x,list):
            for v in x:
                if isinstance(v,(dict,list)):visit(v)
    for path in Path('results').rglob('*'):
        if OUT in path.parents or not path.is_file():continue
        if path.suffix not in ('.json','.jsonl') and not path.name.endswith('.json.gz'):continue
        opener=gzip.open if path.suffix=='.gz' else open
        with opener(path,'rt') as f:
            if path.suffix=='.jsonl':
                for line in f:
                    if line.strip():visit(json.loads(line))
            else:visit(json.load(f))
        files+=1
    assert not set(SEEDS)&seeds, 'Reused seed'
    return hashes,dict(files_scanned=files,known_seeds=len(seeds),known_hashes=len(hashes))


def run():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'online_manifest.json').exists() and not (OUT/'raw.jsonl').exists(),'No overwrite'
    resuming=(OUT/'frozen.json').exists()
    old,identity=identity_audit()
    base=json.loads(Path('results/oracle_transfer_6regular/n200_H_s6202.json').read_text())
    instances={};identities={}
    for seed in SEEDS:
        obj=evolve(200,base['edges'],.01,seed);obj['cnf']=normalize(obj['cnf'])
        h=digest(obj['cnf']);assert h not in old;old.add(h)
        instances[str(seed)]=obj;identities[str(seed)]=h
    if resuming:
        assert json.loads((OUT/'frozen.json').read_text())['cnf_hashes']==identities
    else:dump(OUT/'targets.json',instances)
    sources={str(p):sha(p) for p in (Path(__file__),PROTOCOL,HISTORY,TEMPLATE,
        Path('unseen_selector.py'),Path('round4_core.py'),Path('replay_budget.py'),
        Path('oracle_lemma.py'),Path('homologous_graphs.py'),Path('satcache.py'),NATIVE/'counted')}
    dump(OUT/('amendment.json' if resuming else 'frozen.json'),dict(seeds=SEEDS,cnf_hashes=identities,budgets=BUDGETS,
        sources=sources,identity_audit=identity,targets_sha256=sha(OUT/'targets.json'),
        frozen_before_generation_and_solving=True))
    print('FROZEN 20 new target identities and protocol',flush=True)
    hints,meta=build_hints();templates=[]
    dump(OUT/'history_cost.json',dict(**meta,common_template_prepare_seconds=0))
    frozen={}
    for name,obj in instances.items():
        for b in BUDGETS:
            for route in ROUTES:
                idx,pop,g=generate(obj,templates,b,hints if route=='HISTORY-GEN' else None)
                ids,s=select(obj,idx,pop) # shared existing target rank; NO history score
                ids.sort(key=lambda i:idx.clauses[i])
                assert len(ids)==min(64,len(pop))
                _,clauses,vs=idx.materialize(obj['cnf'],ids)
                assert vs['support_inferences']==len(ids)
                frozen[f'{name}/{b}/{route}']=dict(generation=g,selection=s,
                    selected_clauses=clauses,population=pop,proof=asdict(idx.history))
            a=frozen[f'{name}/{b}/TARGET-GEN']['generation']
            c=frozen[f'{name}/{b}/HISTORY-GEN']['generation']
            assert a['pair_universe_sha256']==c['pair_universe_sha256']
    with gzip.open(OUT/'online_frozen.json.gz','wt') as f:json.dump(frozen,f)
    dump(OUT/'online_manifest.json',dict(sha256=sha(OUT/'online_frozen.json.gz'),
        frozen_before_any_target_solve=True,cells=len(frozen)))
    print('FROZEN all 200 candidate pools, selections and short proofs',flush=True)
    jobs=[(name,b,route,rep) for name in instances for b in BUDGETS for route in ROUTES for rep in range(3)]
    random.Random(20260911).shuffle(jobs)
    with (OUT/'raw.jsonl').open('w') as stream:
        for n,(name,b,route,rep) in enumerate(jobs,1):
            start=perf_counter();obj=instances[name]
            idx,pop,g=generate(obj,templates,b,hints if route=='HISTORY-GEN' else None)
            ids,s=select(obj,idx,pop);ids.sort(key=lambda i:idx.clauses[i])
            expected=frozen[f'{name}/{b}/{route}']
            assert g['pool_sha256']==expected['generation']['pool_sha256']
            assert [list(idx.clauses[i]) for i in ids]==[list(c) for c in expected['selected_clauses']]
            begin=perf_counter()
            _,clauses,vs=idx.materialize(obj['cnf'],ids)
            assert vs['support_inferences']==len(ids)
            validation=perf_counter()-begin
            e=Evaluator(dict(cnf=obj['cnf'],templates=templates,h=idx,population=pop),OUT/'timing',workers=1)
            try:row=e.solve(tuple(ids))
            finally:e.close()
            total=perf_counter()-start
            assert row['status']=='UNSAT',(name,b,route,row)
            row.update(target=name,budget=b,route=route,repeat=rep,**g,**s,
                selected_K=len(ids),validation_seconds=validation,
                validation_steps=vs['support_inferences'],template_steps=0,
                solver_seconds=row['seconds'],total_warm_seconds=total)
            stream.write(json.dumps(row)+'\n');stream.flush()
            if n%50==0:print(f'{n}/600 sequential timed runs',flush=True)
    print('DONE',flush=True)


if __name__=='__main__':run()
