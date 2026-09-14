"""Reproduce selected runs and retain stronger CNF-only timing references."""
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter

from pysat.process import Processor
from pysat.solvers import Cadical195
from satcache import normalize
from evaluation_oracle_run import dimacs, METRICS


def main():
    directory=Path('results/evaluation_oracle_native')
    data=json.loads((directory/'results.json').read_text())
    rows, repeated=[],[]
    binary='/private/tmp/satfinding-native-cdcl/counted'
    for pair in data['pairs']:
        best=pair['best_found']
        proof=directory/f'n{pair["n"]}_selected_recheck.drup'
        output=subprocess.check_output([binary,best['input_path'],str(proof),'1000000'],text=True,timeout=30)
        run=json.loads(output.splitlines()[-1])
        assert all(run[k]==best[k] for k in METRICS)
        assert hashlib.sha256(proof.read_bytes()).hexdigest()==best['proof_sha256']
        repeated.append(dict(n=pair['n'],status='PASS',counters_identical=True,drup_identical=True,run=run))
        cnf=normalize(json.loads(Path(pair['target_path']).read_text())['cnf'])
        started=perf_counter()
        with Cadical195(bootstrap_with=cnf) as solver:
            solved=solver.solve()
            statistics=solver.accum_stats()
        direct=dict(status='SAT' if solved else 'UNSAT',seconds=perf_counter()-started,
                    stats=statistics,checker='SOLVER_REPORTED_ONLY')
        started=perf_counter()
        with Processor(bootstrap_with=cnf) as processor:
            result=processor.process(rounds=3)
        preprocessing_seconds=perf_counter()-started
        path=directory/f'n{pair["n"]}_preprocessed.cnf'
        dimacs(path,result.clauses)
        proof=directory/f'n{pair["n"]}_preprocessed.drup'
        output=subprocess.check_output([binary,str(path),str(proof),'1000000'],text=True,timeout=30)
        run=json.loads(output.splitlines()[-1])
        rows.append(dict(n=pair['n'],cadical_direct=direct,preprocess_seconds=preprocessing_seconds,
            preprocess_status=result.status,processed_clauses=len(result.clauses),preprocessed_native=run,
            combined_worker_seconds=preprocessing_seconds+run['seconds'],
            checker='PREPROCESSED_FORMULA_ONLY_NOT_ROOT_CERTIFIED',
            input_path=str(path),input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            drup_path=str(proof),drup_sha256=hashlib.sha256(proof.read_bytes()).hexdigest()))
    (directory/'selected_reexecution.json').write_text(json.dumps(repeated,indent=2))
    (directory/'modern_references.json').write_text(json.dumps(rows,indent=2))
    paths=['evaluation_oracle_references.py','evaluation_oracle_run.py','satcache.py',binary]
    (directory/'reference_metadata.json').write_text(json.dumps(dict(
        sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        artifacts={str(directory/p):hashlib.sha256((directory/p).read_bytes()).hexdigest()
                   for p in ('selected_reexecution.json','modern_references.json')},
        role='Secondary references, not optimization feedback; candidates and winners unchanged.'),indent=2))
    print(json.dumps(rows))


if __name__=='__main__':
    main()
