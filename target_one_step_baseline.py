"""Predeclared conservative budget sensitivity: every target root costs one step."""
import json
from pathlib import Path
import target_local_history as run
from oracle_lemma import prepare,strip_template,objective
from replay_budget import HistoryIndex
from round4_core import decode,ancestors


def main():
    parent=run.OUT
    run.OUT=parent/'one_step'
    run.OUT.mkdir(exist_ok=True)
    (run.OUT/'protocol.json').write_text(json.dumps(dict(
        reason='Control average-cost mismatch: <=1 step/root is strictly cheaper than Gold LOCAL 57/44.',
        seeds=[17,29,43],selection='same matched_oracle; no reuse of prior winners',
        report_all_seeds=True),indent=2))
    proof=decode(json.loads((parent/'target_pool_proof.json').read_text()))
    idx=HistoryIndex(proof)
    data=prepare()
    population,_=strip_template(idx,data['cnf'],data['templates'])
    population=[i for i in population if sum(j>=idx.leaves for j in ancestors(proof,i))==1]
    td=dict(data,h=idx,population=population)
    results=[run.matched_oracle(td,'target_one_step',seed) for seed in (17,29,43)]
    run.dump('oracles.json',results)
    specs={f'targetOneStepOracle_{k}':('target',min([r['exact'][str(k)] for r in results],key=objective)['selected_ids'])
           for k in (16,32,64)}
    run.dump('selections.json',specs)
    run.timed({'target':td},specs)
    print('one step DONE',flush=True)


if __name__=='__main__': main()
