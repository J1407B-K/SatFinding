"""Isolated shortcut worker. Input is ONLY a CNF and public configuration."""
import argparse
from dataclasses import asdict
import json
import sys
from time import perf_counter

from satcache import Certificate, check, normalize
from round4_core import Budget, preprocess, slice_proof


def run(cnf, method, limit):
    cnf = normalize(cnf)
    started = perf_counter()
    if method in ('UP', 'BVE'):
        db = preprocess(cnf, Budget(limit), bve=method == 'BVE')
        search_seconds = perf_counter()-started
        cert = None
        if () in db.index:
            cert, _ = slice_proof(db.certificate())
        check_start = perf_counter()
        accepted = cert is not None and check(cnf, cert)
        checker_seconds = perf_counter()-check_start
        if cert is not None and not accepted:
            raise ValueError('Invalid shortcut certificate')
        return dict(method=method, status='UNSAT' if accepted else 'MISS',
                    checker='PASS' if accepted else 'NOT_APPLICABLE',
                    search_seconds=search_seconds, checker_seconds=checker_seconds,
                    end_to_end_seconds=perf_counter()-started,
                    certificate=asdict(cert) if cert else None, **db.record())
    if method == 'CADICAL_PREPROCESS':
        from pysat.process import Processor
        with Processor(bootstrap_with=cnf) as processor:
            result = processor.process(rounds=3)
            return dict(method=method, status='UNSAT' if not result.status else 'UNRESOLVED',
                        remaining_clauses=len(result.clauses), checker='SOLVER_REPORTED_ONLY',
                        end_to_end_seconds=perf_counter()-started)
    if method == 'CADICAL_SOLVE':
        from pysat.solvers import Cadical195
        with Cadical195(bootstrap_with=cnf) as solver:
            solved = solver.solve()
            assignment = {abs(x): x > 0 for x in solver.get_model()} if solved else None
            if solved and not check(cnf, Certificate('SAT', assignment=assignment)):
                raise ValueError('Invalid solver model')
            return dict(method=method, status='SAT' if solved else 'UNSAT',
                        solver_stats=solver.accum_stats(), assignment=assignment,
                        checker='MODEL_PASS' if solved else 'SOLVER_REPORTED_ONLY',
                        end_to_end_seconds=perf_counter()-started)
    raise ValueError(method)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('method', choices=['UP', 'BVE', 'CADICAL_PREPROCESS', 'CADICAL_SOLVE'])
    ap.add_argument('--budget', type=int, default=100000)
    args = ap.parse_args()
    print(json.dumps(run(json.load(sys.stdin)['cnf'], args.method, args.budget)))
