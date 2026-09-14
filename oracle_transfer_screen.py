"""Readiness screen for independently generated graph-coloring CNFs.

No planted proof, retained core, leaf replacement, retrieval or mapping search.
Worker input consists solely of a CNF. Proofs are exported only by Glucose.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

from satcache import Certificate, check, normalize

PAIRS = ((80, 6100, 6101), (120, 6102, 6103), (160, 6104, 6105))


def coloring(n, seed, degree=5):
    import networkx as nx
    graph = nx.random_regular_graph(degree, n, seed=seed)
    edges = sorted(tuple(sorted(e)) for e in graph.edges())
    clauses = []
    for v in range(n):
        colors = [3*v+c+1 for c in range(3)]
        clauses.append(colors)
        clauses.extend([[-colors[a], -colors[b]] for a in range(3) for b in range(a+1, 3)])
    for u, v in edges:
        clauses.extend([[-(3*u+c+1), -(3*v+c+1)] for c in range(3)])
    return dict(cnf=normalize(clauses), edges=edges, vertices=n, degree=degree, colors=3,
                seed=seed, connected=nx.is_connected(graph))


def worker(cnf, method):
    cnf = normalize(cnf)
    if method == 'PREPROCESS':
        from pysat.process import Processor
        started = perf_counter()
        with Processor(bootstrap_with=cnf) as processor:
            result = processor.process(rounds=3)
            return dict(status='UNSAT' if not result.status else 'UNRESOLVED',
                        seconds=perf_counter()-started, remaining_clauses=len(result.clauses),
                        checker='SOLVER_REPORTED_ONLY')
    from pysat.solvers import Cadical195, Glucose3
    cls = Glucose3 if method == 'PROOF' else Cadical195
    started = perf_counter()
    options = dict(with_proof=True) if method == 'PROOF' else {}
    with cls(bootstrap_with=cnf, **options) as solver:
        status = solver.solve()
        seconds = perf_counter()-started
        assignment = {abs(x): x > 0 for x in solver.get_model()} if status else None
        if status:
            assert check(cnf, Certificate('SAT', assignment=assignment))
        proof = solver.get_proof() if method == 'PROOF' and not status else None
        return dict(status='SAT' if status else 'UNSAT', seconds=seconds,
                    assignment=assignment, stats=solver.accum_stats(), drup=proof,
                    checker='MODEL_PASS' if status else 'AWAITING_RESOLUTION_RECONSTRUCTION')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', choices=['PREPROCESS', 'SOLVE', 'PROOF'])
    ap.add_argument('--output', default='results/oracle_transfer')
    ap.add_argument('--unsat-candidates', action='store_true')
    args = ap.parse_args()
    if args.worker:
        print(json.dumps(worker(json.load(sys.stdin)['cnf'], args.worker)))
        return
    import networkx as nx
    import pysat
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=True)
    degree = 6 if args.unsat_candidates else 5
    pairs = ((120, 6200, 6201), (200, 6202, 6203), (320, 6204, 6205)) if args.unsat_candidates else PAIRS
    manifest = dict(phase='natural_family_readiness', family=f'independent_random_{degree}_regular_3_coloring',
                    pairs=pairs, degree=degree, cases=[], networkx=nx.__version__, pysat=pysat.__version__,
                    python=sys.version, platform=platform.platform(), watchdog_seconds=15,
                    sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                             for p in ('oracle_transfer_screen.py', 'docs/oracle-transfer-protocol.md', 'satcache.py')})
    for n, hs, ts in pairs:
        pair = []
        for role, seed in (('H', hs), ('T', ts)):
            data = coloring(n, seed, degree)
            pair.append(set(data['cnf']))
            key = f'n{n}_{role}_s{seed}'
            case_path = directory / f'{key}.json'
            case_path.write_text(json.dumps(data))
            row = dict(key=key, role=role, n=n, seed=seed, path=str(case_path),
                       sha256=hashlib.sha256(case_path.read_bytes()).hexdigest(), methods={})
            for method in ('PREPROCESS', 'SOLVE', 'PROOF'):
                started = perf_counter()
                try:
                    process = subprocess.run([sys.executable, __file__, '--worker', method],
                        input=json.dumps(dict(cnf=data['cnf'])), text=True,
                        capture_output=True, check=True, timeout=15)
                    result = json.loads(process.stdout)
                except subprocess.TimeoutExpired:
                    result = dict(status='TIMEOUT')
                except subprocess.CalledProcessError as exc:
                    result = dict(status='ERROR', error=exc.stderr[-2000:])
                result['process_seconds'] = perf_counter()-started
                proof = result.pop('drup', None)
                if proof is not None:
                    proof_path = directory/f'{key}.drup'
                    proof_path.write_text('\n'.join(proof)+'\n')
                    result.update(drup_path=str(proof_path), drup_lines=len(proof),
                                  drup_sha256=hashlib.sha256(proof_path.read_bytes()).hexdigest())
                row['methods'][method] = result
                print(key, method, result['status'], result.get('seconds'), flush=True)
            manifest['cases'].append(row)
            (directory/'screen.json').write_text(json.dumps(manifest, indent=2))
        assert not pair[0] <= pair[1] and not pair[1] <= pair[0]
    manifest['complete'] = True
    (directory/'screen.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
