"""Isolated CNF-only baseline worker. Never receives original XOR groups."""
import argparse
import json
import pickle
import threading
from collections import defaultdict
from time import perf_counter

from pysat.process import Processor
from pysat.solvers import Glucose3
import pycryptosat


def explicit_parities(cnf):
    groups = defaultdict(lambda: [set(),set()])
    for c in cnf:
        if 1 <= len(c) <= 8 and len({abs(x) for x in c}) == len(c):
            scope = tuple(sorted(abs(x) for x in c))
            groups[scope][sum(x<0 for x in c)%2].add(tuple(sorted(c)))
    return [[list(scope),1-forbidden] for scope,sets in sorted(groups.items())
            for forbidden,clauses in enumerate(sets) if len(clauses)==2**(len(scope)-1)]


def solve(cnf, mode, seconds):
    started = perf_counter()
    preprocess_time = 0.
    processor = None
    original = cnf
    processed_parities = None
    try:
        if mode == 'C':
            processor = Processor(bootstrap_with=cnf)
            processed = processor.process(rounds=3)
            cnf = processed.clauses
            preprocess_time = perf_counter()-started
            processed_parities = explicit_parities(cnf)
            if not processed.status:
                return dict(status='UNSAT',total_time=perf_counter()-started,
                            preprocess_time=preprocess_time,processed_clauses=len(cnf),model_checked=False,
                            processed_parities=processed_parities)
        if mode == 'A':
            with Glucose3(bootstrap_with=cnf) as solver:
                timer = threading.Timer(seconds,solver.interrupt)
                timer.start()
                try:
                    status = solver.solve_limited(expect_interrupt=True)
                finally:
                    timer.cancel()
                    timer.join()
                stats = solver.accum_stats()
                model = solver.get_model() if status else None
        else:
            solver = pycryptosat.Solver(threads=1,time_limit=seconds)
            for c in cnf:
                solver.add_clause(c)
            status, values = solver.solve(time_limit=seconds)
            model = [i if x else -i for i,x in enumerate(values) if i] if status else None
            stats = {}
        elapsed = perf_counter()-started
        verified = False
        if status:
            if processor is not None:
                model = processor.restore(model)
            assignment = {abs(x):x>0 for x in model}
            verified = all(any(assignment.get(abs(x)) == (x>0) for x in c) for c in original)
            if not verified:
                raise ValueError('Invalid baseline SAT model')
        return dict(status='UNKNOWN' if status is None else ('SAT' if status else 'UNSAT'),
                    total_time=elapsed,preprocess_time=preprocess_time,processed_clauses=len(cnf),
                    model_checked=verified,processed_parities=processed_parities,**stats)
    finally:
        if processor is not None:
            processor.delete()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode',choices=['A','B','C'])
    ap.add_argument('input')
    ap.add_argument('--seconds',type=float,default=2.)
    args = ap.parse_args()
    with open(args.input,'rb') as f:
        cnf = pickle.load(f)
    print(json.dumps(solve(cnf,args.mode,args.seconds)))
