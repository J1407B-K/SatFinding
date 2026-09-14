"""Stream orchestration around frozen unseen_selector functions; no new selector."""
import argparse
from dataclasses import asdict
from fractions import Fraction
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import random
from time import perf_counter

from unseen_selector import candidates, select, template_data, digest, dump
from homologous_graphs import evolve
from oracle_lemma import Evaluator
from evaluation_oracle_run import sha
from satcache import normalize
from round4_core import ancestors

OUT=Path('results/persistent_memory_stream')
OLD=Path('results/unseen_selector')


def prior_load():
    start=perf_counter()
    with gzip.open(OLD/'history_prior.json.gz','rb') as f:blob=f.read()
    old=json.loads((OLD/'metadata.json').read_text())
    assert hashlib.sha256(blob).hexdigest()==old['prior']['prior_sha256']
    prior={tuple(c):Fraction(n,d) for c,n,d in json.loads(blob)}
    return prior,perf_counter()-start


def source_check():
    old=json.loads((OLD/'metadata.json').read_text())
    for path,expected in old['sources'].items():assert sha(path)==expected,path
    return old


def prepare():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'online_frozen.json').exists(),'Do not overwrite frozen stream'
    old=source_check()
    seeds=json.loads((OUT/'seeds.json').read_text())['targets']
    assert list(seeds)==[f'T{i}' for i in range(5,55)]
    assert list(seeds.values())==list(range(9205,9255))
    prior,load_seconds=prior_load()
    t,tids,templates,template_seconds=template_data()
    base=json.loads(Path('results/oracle_transfer_6regular/n200_H_s6202.json').read_text())
    old_hashes=set();old_seeds=set()
    paths=list(Path('results/homologous_template').glob('*.json'))+list(Path('results/oracle_transfer_6regular').glob('*.json'))+list(OLD.glob('T*/target.json'))
    for path in paths:
        obj=json.loads(path.read_text())
        if isinstance(obj,dict) and 'cnf' in obj:
            old_hashes.add(digest(normalize(obj['cnf'])))
            old_seeds.add(obj.get('seed'))
    frozen={};new_hashes=set()
    for name,seed in seeds.items():
        assert seed not in old_seeds
        instance=evolve(200,base['edges'],.01,seed)
        instance['cnf']=normalize(instance['cnf'])
        h=digest(instance['cnf'])
        assert h not in old_hashes|new_hashes
        new_hashes.add(h)
        folder=OUT/name;folder.mkdir(exist_ok=True)
        dump(folder/'target.json',instance)
        idx,pop,gen=candidates(instance['cnf'],templates)
        a,sa=select(instance,idx,pop)
        b,sb=select(instance,idx,pop,prior)
        for ids in (a,b):
            _,_,stats=idx.materialize(instance['cnf'],ids)
            assert stats['support_inferences']==64
        try:
            _,tc,_=t.materialize(instance['cnf'],tids)
            assert tc==templates
            error=None
        except ValueError as exc:error=str(exc)
        frozen[name]=dict(seed=seed,cnf_sha256=h,population=pop,online={'TARGET':a,'HISTORY':b},
            generation=gen,target_selection=sa,history_selection=sb,
            candidate_clauses=[idx.clauses[i] for i in pop],template_error=error)
    dump(OUT/'online_frozen.json',frozen)
    dump(OUT/'metadata.json',dict(frozen_sources=old['sources'],
        sources={str(p):sha(p) for p in [Path(__file__),Path('docs/persistent-memory-stream-protocol.md'),OUT/'seeds.json']},
        online_frozen_sha256=sha(OUT/'online_frozen.json'),prior_sha256=old['prior']['prior_sha256'],
        current_archive_load_seconds=load_seconds,template_prepare_seconds=template_seconds,
        frozen_prior_load_seconds=old['prior']['prior_load_seconds'],frozen_prior_build_seconds=old['prior']['build_check_index_seconds'],
        load_line_seconds=.82,build_line_seconds=3.87,old_target_hashes=sorted(old_hashes),
        old_target_seeds=sorted(s for s in old_seeds if s is not None),
        targets=50,all_online_selections_frozen_before_any_completion=True))
    print('Frozen all50 inputs/selectors; template failures:',sum(bool(r['template_error']) for r in frozen.values()),flush=True)


def measure(policy):
    source_check()
    amendment=json.loads((OUT/'protocol_amendment.json').read_text())
    assert policy=='valid-subset'
    for path,h in amendment['amended_sources'].items():assert sha(path)==h,path
    meta=json.loads((OUT/'metadata.json').read_text())
    assert sha(OUT/'online_frozen.json')==meta['online_frozen_sha256']
    frozen=json.loads((OUT/'online_frozen.json').read_text())
    prior,_=prior_load()
    t,tids,templates,_=template_data()
    supports={i:{t.clauses[j] for j in ancestors(t.history,i) if j<t.leaves} for i in tids}
    inputs={};engines={};active={};failures={};validity={}
    for name,fr in frozen.items():
        instance=json.loads((OUT/name/'target.json').read_text())
        instance['cnf']=normalize(instance['cnf'])
        if policy=='strict' and fr['template_error']:
            failures[name]=fr['template_error'];continue
        available=set(instance['cnf'])
        chosen=tids if policy=='strict' else [i for i in tids if supports[i]<=available]
        _,tc,_=t.materialize(instance['cnf'],chosen)
        validity[name]=dict(template_valid_count=len(tc),
            invalid_template_ids=[i for i in tids if i not in chosen],
            valid_template_hash=digest(tc))
        idx,pop,_=candidates(instance['cnf'],templates)  # Original exclusion list unchanged.
        assert pop==fr['population']
        inputs[name]=instance;active[name]=chosen
        engines[name]=Evaluator(dict(cnf=instance['cnf'],templates=tc,h=idx,population=pop),OUT/name/'timing',workers=1)
    settings=dict(template_policy=policy,active_template_ids=active,failures=failures,
        unchanged_candidate_exclusion_count=len(templates),online_frozen_sha256=sha(OUT/'online_frozen.json'),
        baseline_description='frozen TEMPLATE-67 source set with per-target soundness filtering',
        protocol_amendment_sha256=sha(OUT/'protocol_amendment.json'),template_validity=validity)
    manifest=OUT/'measurement_policy.json'
    if manifest.exists():assert json.loads(manifest.read_text())==settings
    else:dump(manifest,settings)
    dump(OUT/'template_validity.json',validity)
    jobs=[(name,route,rep) for name in frozen for route in ['TEMPLATE','TARGET','HISTORY'] for rep in range(5)]
    random.Random(20260911).shuffle(jobs)
    dump(OUT/'jobs.json',jobs)
    existing={}
    raw_path=OUT/'raw.jsonl'
    if raw_path.exists():
        for line in raw_path.read_text().splitlines():
            row=json.loads(line);existing[row['target'],row['route'],row['repeat']]=row
    if not (OUT/'execution_start.json').exists():
        dump(OUT/'execution_start.json',dict(utc=datetime.now(timezone.utc).isoformat(),
            protocol_amendment_sha256=sha(OUT/'protocol_amendment.json'),
            template_validity_sha256=sha(OUT/'template_validity.json'),
            measurement_policy_sha256=sha(OUT/'measurement_policy.json')))
    try:
        with raw_path.open('a') as stream:
            for name,route,rep in jobs:
                if (name,route,rep) in existing:continue
                start=perf_counter()
                if name in failures:
                    row=dict(target=name,route=route,repeat=rep,status='PROTOCOL_FAILURE',error=failures[name])
                else:
                    instance=inputs[name];gen={};sel={}
                    try:
                        if route=='TEMPLATE':ids=[];idx=None
                        else:
                            idx,pop,gen=candidates(instance['cnf'],templates)
                            assert gen['outputs_sha256']==frozen[name]['generation']['outputs_sha256']
                            ids,sel=select(instance,idx,pop,prior if route=='HISTORY' else None)
                            assert ids==frozen[name]['online'][route]
                        begin=perf_counter()
                        available=set(instance['cnf'])
                        chosen=tids if policy=='strict' else [i for i in tids if supports[i]<=available]
                        assert chosen==active[name]
                        _,tc,ts=t.materialize(instance['cnf'],chosen)
                        assert digest(tc)==validity[name]['valid_template_hash']
                        if ids:
                            _,_,stats=idx.materialize(instance['cnf'],ids)
                            assert stats['support_inferences']==64
                        else:stats={'support_inferences':0}
                        validation=perf_counter()-begin
                        row=engines[name].solve(tuple(ids))
                        row.update(**gen,**sel,validation_seconds=validation,solver_seconds=row.get('seconds'),
                            total_seconds=perf_counter()-start,validation_steps=stats['support_inferences'],
                            template_steps=ts['support_inferences'],template_outputs=len(tc),**validity[name])
                    except (ValueError,RuntimeError,AssertionError) as exc:
                        row=dict(status='PROTOCOL_FAILURE',error=repr(exc),total_seconds=perf_counter()-start)
                    row.update(target=name,route=route,repeat=rep)
                stream.write(json.dumps(row)+'\n');stream.flush()
                existing[name,route,rep]=row
                if len(existing)%50==0:print(f'{len(existing)}/750 runs recorded',flush=True)
    finally:
        for engine in engines.values():engine.close()
    print('DONE',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','measure'])
    ap.add_argument('--template-policy',choices=['strict','valid-subset'],default='strict')
    args=ap.parse_args()
    prepare() if args.phase=='prepare' else measure(args.template_policy)
