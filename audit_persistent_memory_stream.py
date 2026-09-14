"""Full stream soundness/amendment/frozen-selection audit, no completion calls."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import tempfile

from persistent_memory_stream import prior_load,source_check
from unseen_selector import candidates,select,template_data,digest
from evaluation_oracle_run import sha,dimacs
from proofmodule import ProofContext,ProofModule
from satcache import normalize

P=Path('results/persistent_memory_stream')


def load(name):return json.loads((P/name).read_text())


def main():
    source_check();prior,_=prior_load()
    meta=load('metadata.json');amend=load('protocol_amendment.json');execution=load('execution_start.json')
    frozen=load('online_frozen.json');validity=load('template_validity.json');policy=load('measurement_policy.json')
    assert sha(P/'online_frozen.json')==meta['online_frozen_sha256']==amend['online_frozen_sha256']
    assert sha(P/'seeds.json')==amend['seeds_sha256']
    for path,h in meta['sources'].items():
        checked=(P/'pre_amendment_driver.py.txt' if Path(path).name=='persistent_memory_stream.py' else P/'pre_amendment_protocol.md' if Path(path).name=='persistent-memory-stream-protocol.md' else Path(path))
        assert sha(checked)==h,path
    for path,h in (meta['frozen_sources']|amend['amended_sources']|amend['originals']|amend['target_input_hashes']).items():assert sha(path)==h,path
    assert datetime.fromisoformat(amend['recorded_utc'])<datetime.fromisoformat(execution['utc'])
    for name in ['protocol_amendment','template_validity','measurement_policy']:
        assert sha(P/(name+'.json'))==execution[name+'_sha256']
    assert policy['baseline_description']=='frozen TEMPLATE-67 source set with per-target soundness filtering'
    assert not policy['failures'] and policy['template_policy']=='valid-subset'
    seeds=load('seeds.json')['targets']
    assert list(seeds)==[f'T{i}' for i in range(5,55)] and list(seeds.values())==list(range(9205,9255))
    assert list(frozen)==list(seeds) and len(validity)==50
    raw=[json.loads(l) for l in (P/'raw.jsonl').read_text().splitlines()]
    assert len(raw)==750 and len({(r['target'],r['route'],r['repeat']) for r in raw})==750
    failed=[r for r in raw if r['status']!='UNSAT']
    assert failed==load('analysis_failure_policy.json')['failures'] and len(failed)==1
    assert sha(P/'raw.jsonl')==load('analysis_failure_policy.json')['raw_sha256']
    assert [(r['target'],r['route'],r['repeat']) for r in raw]==[tuple(j) for j in load('jobs.json')]
    t,tids,templates,_=template_data();new_hashes=set();checks=[]
    with tempfile.TemporaryDirectory(prefix='satfinding-stream-audit-') as tmp:
        input_path=Path(tmp)/'expected.cnf'
        for target,fr in frozen.items():
            instance=load(f'{target}/target.json');instance['cnf']=normalize(instance['cnf'])
            assert instance['seed']==seeds[target]==fr['seed']
            h=digest(instance['cnf']);assert h==fr['cnf_sha256']
            assert h not in new_hashes and h not in meta['old_target_hashes'];new_hashes.add(h)
            active=[];invalid=[]
            for i in tids:
                try:t.materialize(instance['cnf'],[i]);active.append(i)
                except ValueError as exc:
                    assert str(exc)=='Missing target premise'
                    invalid.append(i)
            _,tc,ts=t.materialize(instance['cnf'],active)
            assert active==policy['active_template_ids'][target]
            assert validity[target]==dict(template_valid_count=len(tc),invalid_template_ids=invalid,valid_template_hash=digest(tc))
            idx,pop,gen=candidates(instance['cnf'],templates)
            assert pop==fr['population'] and [idx.clauses[i] for i in pop]==[tuple(c) for c in fr['candidate_clauses']]
            assert gen['outputs_sha256']==fr['generation']['outputs_sha256'] and gen['resolver_attempts']==fr['generation']['resolver_attempts']
            assert ProofContext(instance['cnf']).check(ProofModule((),(),instance['cnf'],idx.history.steps[-1].clause,idx.history.steps)) is not None
            assert all(s.left<idx.leaves and s.right<idx.leaves for s in idx.history.steps)
            for route,p in [('TEMPLATE',None),('TARGET',None),('HISTORY',prior)]:
                if route=='TEMPLATE':ids=[]
                else:
                    ids,_=select(instance,idx,pop,p)
                    assert ids==fr['online'][route] and len(ids)==64
                    _,_,s=idx.materialize(instance['cnf'],ids);assert s['support_inferences']==64
                cnf=list(instance['cnf'])+tc+[idx.clauses[i] for i in ids]
                dimacs(input_path,cnf);expected_hash=sha(input_path)
                rr=[r for r in raw if r['target']==target and r['route']==route]
                assert len(rr)==5 and {r['repeat'] for r in rr}==set(range(5))
                rr=[r for r in rr if r['status']=='UNSAT']
                assert len(rr)>=4
                assert all(r['input_sha256']==expected_hash and r['selected_ids']==ids for r in rr)
                assert len({(r['analysis_resolution_steps'],r['conflicts'],r['decisions'],r['propagations']) for r in rr})==1
                assert all(all(r[k]==v for k,v in validity[target].items()) for r in rr)
                assert all(r['template_steps']==ts['support_inferences'] and r['total_seconds']>=r['solver_seconds'] for r in rr)
                if route!='TEMPLATE':
                    assert all(r['candidates_examined']==512 and r['feature_evaluations']==512 and r['sorts']==1 and r['validation_steps']==64 for r in rr)
                    assert all(r['generation_seconds']<=.1 and r['selection_seconds']<=.05 and r['resolver_attempts']==gen['resolver_attempts'] for r in rr)
            checks.append(dict(target=target,template_valid_count=len(active),invalid_template_ids=invalid,valid_template_hash=digest(tc),proof_check='PASS',selection_check='PASS'))
    result=dict(status='PASS',targets=50,runs=750,source_hashes_match=True,amendment_precedes_solves=True,
        all_template_roots_individually_revalidated=50*67,all_routes_same_template_hash=True,
        all_original_candidate_pools_and_selected_ids_preserved=True,all749_completed_input_hashes_reconstructed=True,
        no_duplicate_or_old_targets=True,completed_budget_guards_pass=True,budget_failures=failed,all_completed_counters_repeat=True,
        template_count_distribution=dict(Counter(r['template_valid_count'] for r in checks)),targets_checked=checks)
    (P/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='targets_checked'}))


if __name__=='__main__':main()
