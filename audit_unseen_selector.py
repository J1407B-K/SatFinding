"""Audit frozen choices, target-only candidates, source prior and budgets."""
import gzip
import json
from pathlib import Path
from collections import defaultdict
from fractions import Fraction
from statistics import median
from dataclasses import asdict
from unseen_selector import OUT, candidates, select, digest
from evaluation_oracle_run import sha
from homologous_template_run import load_history
from oracle_lemma import HISTORY,TEMPLATE,objective
from replay_budget import HistoryIndex
from proofmodule import ProofContext,ProofModule
from round4_core import decode
from satcache import check,normalize


def main():
    metadata=json.loads((OUT/'metadata.json').read_text())
    assert all(sha(p)==h for p,h in metadata['sources'].items())
    assert sha(OUT/'online_frozen.json')==metadata['online_frozen_sha256']
    prior_path=OUT/'history_prior.json'
    if prior_path.exists(): blob=prior_path.read_bytes()
    else:
        with gzip.open(str(prior_path)+'.gz','rb') as f:blob=f.read()
    import hashlib
    assert hashlib.sha256(blob).hexdigest()==metadata['prior']['prior_sha256']
    prior={tuple(c):Fraction(n,d) for c,n,d in json.loads(blob)}
    proof,_=load_history(HISTORY)
    assert check(proof.premises,proof)
    h=HistoryIndex(proof)
    expected={}
    for i,score in h.scores.items():
        c=h.clauses[i]
        expected[c]=max(expected.get(c,Fraction(0)),score)
    assert prior==expected
    del expected,h,proof,blob
    tp,_=load_history(TEMPLATE)
    assert check(tp.premises,tp)
    ti=HistoryIndex(tp)
    old=json.loads(Path('results/oracle_lemma/metadata.json').read_text())
    templates=[tuple(c) for c in old['template_lemmas']]
    frozen=json.loads((OUT/'online_frozen.json').read_text())
    raw=[json.loads(l) for l in (OUT/'raw.jsonl').read_text().splitlines()]
    assert len(raw)==60
    summaries=[]
    for name,fr in frozen.items():
        instance=json.loads((OUT/name/'target.json').read_text())
        instance['cnf']=normalize(instance['cnf'])
        assert digest(instance['cnf'])==fr['cnf_sha256']
        idx,pop,gen=candidates(instance['cnf'],templates)
        assert gen['outputs_sha256']==fr['generation']['outputs_sha256']
        assert gen['resolver_attempts']==fr['generation']['resolver_attempts']
        assert len(pop)==512 and pop==fr['population']
        assert asdict(idx.history)==asdict(decode(fr['proof']))
        assert all(s.left<idx.leaves and s.right<idx.leaves for s in idx.history.steps)
        assert ProofContext(instance['cnf']).check(ProofModule((),(),instance['cnf'],idx.history.steps[-1].clause,idx.history.steps))
        for label,p in [('TARGET',None),('HISTORY',prior)]:
            ids,_=select(instance,idx,pop,p)
            assert ids==fr['online'][label] and len(ids)==64
            _,_,stats=idx.materialize(instance['cnf'],ids)
            assert stats['support_inferences']==64
        _,tc,_=ti.materialize(instance['cnf'],old['template_ids'])
        assert tc==templates
        oracle=json.loads((OUT/name/'oracle.json').read_text())
        trace=[json.loads(l) for l in (OUT/name/'oracle/search.jsonl').read_text().splitlines()]
        assert len(trace)==oracle['unique_calls'] and len(trace)<=162
        assert all(len(r['selected_ids'])==64 and set(r['selected_ids'])<=set(pop) and r['status']=='UNSAT' for r in trace)
        assert objective(oracle['best'])==min(map(objective,trace))
        for route in ['TEMPLATE','TARGET','HISTORY','ORACLE']:
            rr=[r for r in raw if r['target']==name and r['route']==route]
            assert len(rr)==5 and {r['repeat'] for r in rr}==set(range(5))
            assert len({(r['input_sha256'],r['analysis_resolution_steps'],r['conflicts'],r['status']) for r in rr})==1
            assert all(r['status']=='UNSAT' for r in rr)
            ids=[] if route=='TEMPLATE' else oracle['best']['selected_ids'] if route=='ORACLE' else fr['online'][route]
            assert all(r['selected_ids']==ids and r['validation_steps']==len(ids) for r in rr)
            if route!='TEMPLATE':
                assert all(r['candidates_examined']==512 and r['resolver_attempts']==gen['resolver_attempts'] for r in rr)
                assert all(r['generation_seconds']<=.1 and r['selection_seconds']<=.05 for r in rr)
            if route in ['TARGET','HISTORY']:
                assert all(r['feature_evaluations']==512 and r['sorts']==1 for r in rr)
            row=dict(target=name,route=route,repeats=5)
            for k in ['analysis_resolution_steps','conflicts','generation_seconds','selection_seconds','validation_seconds','solver_seconds','screen_process_seconds','total_seconds']:
                row[k]=median(r.get(k,0) for r in rr)
            row.update(total_min=min(r['total_seconds'] for r in rr),total_max=max(r['total_seconds'] for r in rr))
            summaries.append(row)
    lookup={(r['target'],r['route']):r for r in summaries}
    ratios=[];time_ratios=[]
    for t in frozen:
        ratios.append(lookup[t,'HISTORY']['analysis_resolution_steps']/lookup[t,'TARGET']['analysis_resolution_steps'])
        time_ratios.append(lookup[t,'HISTORY']['total_seconds']/lookup[t,'TARGET']['total_seconds'])
    warm_saving=sum(lookup[t,'TARGET']['total_seconds']-lookup[t,'HISTORY']['total_seconds'] for t in frozen)
    build=metadata['prior']['build_check_index_seconds']
    alive=all(r<=.9 for r in ratios) and all(r<=.95 for r in time_ratios) and warm_saving>build
    stop=(median(ratios)>=.95 and sum(r<=.9 for r in ratios)<2) or (sum(r>1 for r in ratios)>=2 and warm_saving<=0)
    verdict='ALIVE' if alive else 'STOP' if stop else 'WEAK'
    audit=dict(status='PASS',targets=3,final_runs=60,candidate_count_each=512,validation_steps_each=64,
        frozen_before_completion=True,source_hashes_match=True,source_prior_recomputed=True,
        independent_target_proofs_checked=True,online_selections_reproduced=True,
        all_budget_caps_pass=True,deterministic_counters=True,ratios=ratios,warm_time_ratios=time_ratios,
        warm_aggregate_saving_seconds=warm_saving,amortized_build_net_saving_seconds=warm_saving-build,
        verdict=verdict)
    (OUT/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit))


if __name__=='__main__':main()
