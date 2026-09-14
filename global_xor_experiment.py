"""Oracle vs CNF-only global parity discovery vs budgeted Glucose3."""
import csv
import hashlib
import json
import platform
import random
import statistics
import threading
from pathlib import Path
from time import perf_counter

import networkx as nx
import pysat
from pysat.solvers import Glucose3

from global_xor import check, discover, oracle, parity_clauses, trace_stats


def instance(n, seed):
    graph = nx.random_regular_graph(6, n, seed=seed)
    assert nx.is_connected(graph) and all(d == 6 for _, d in graph.degree())
    edges = sorted(tuple(sorted(e)) for e in graph.edges())
    rng = random.Random(100000+seed)
    names = list(range(1, len(edges)+1))
    rng.shuffle(names)
    planted = {v:rng.randrange(2) for v in names}
    scopes = [tuple(sorted(names[i] for i, edge in enumerate(edges) if v in edge)) for v in range(n)]
    charges = [sum(planted[x] for x in s) % 2 for s in scopes]
    sat = list(zip(scopes, charges))
    charges[0] ^= 1
    unsat = list(zip(scopes, charges))
    def encode(equations):
        cnf = sum((parity_clauses(s, r) for s, r in equations), [])
        rng.shuffle(cnf)
        return cnf
    return encode(unsat), unsat, encode(sat), planted


def baseline(cnf):
    start = perf_counter()
    with Glucose3(bootstrap_with=cnf) as solver:
        timer = threading.Timer(2., solver.interrupt)
        timer.start()
        try:
            result = solver.solve_limited(expect_interrupt=True)
        finally:
            timer.cancel()
            timer.join()
        stats = solver.accum_stats()
    return dict(status='UNKNOWN' if result is None else ('SAT' if result else 'UNSAT'),
                seconds=perf_counter()-start, **stats)


def main():
    prefix = Path('results/global_xor')
    proofs = Path('results/global_xor_certificates')
    proofs.mkdir(exist_ok=True)
    rows = []
    metadata = dict(sizes=[80,160,320,640], seeds=list(range(10)), degree=6,
        baseline='Glucose3', conflict_budget=None, wall_seconds=2,
        python=platform.python_version(), networkx=nx.__version__, pysat=pysat.__version__,
        sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
                 for p in ('global_xor.py','global_xor_experiment.py')})
    Path(str(prefix)+'_metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    with open(str(prefix)+'_raw.csv', 'w', newline='') as f:
        writer = None
        for n in metadata['sizes']:
            for seed in metadata['seeds']:
                cnf, equations, sat_cnf, planted = instance(n, seed)
                assert all(any(planted[abs(v)] == (v > 0) for v in c) for c in sat_cnf)
                assert not check(sat_cnf, discover(sat_cnf))
                # Alternate execution order to reduce fixed ordering effects.
                results = {}
                modes = ['baseline','oracle','discovered']
                if seed % 2:
                    modes.reverse()
                for mode in modes:
                    if mode == 'baseline':
                        results[mode] = baseline(cnf)
                        assert results[mode]['status'] != 'SAT'
                        continue
                    start = perf_counter()
                    cert = oracle(equations) if mode == 'oracle' else discover(cnf)
                    discovery_seconds = perf_counter()-start
                    start = perf_counter()
                    accepted = check(cnf, cert)
                    check_seconds = perf_counter()-start
                    assert accepted
                    results[mode] = dict(seconds=discovery_seconds+check_seconds,
                        discovery_seconds=discovery_seconds, check_seconds=check_seconds,
                        **trace_stats(cert))
                    (proofs/f'n{n}_s{seed}_{mode}.json').write_text(json.dumps(cert)+'\n')
                row = dict(n=n,seed=seed,variables=3*n,clauses=len(cnf),
                    cnf_sha256=hashlib.sha256(json.dumps(cnf).encode()).hexdigest(),sat_control=True)
                for mode, result in results.items():
                    row.update({mode+'_'+k:v for k,v in result.items()})
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=row.keys())
                    writer.writeheader()
                writer.writerow(row)
                f.flush()
                rows.append(row)
                print(f'n={n} seed={seed} base={results["baseline"]["status"]} '
                      f'discovery+check={results["discovered"]["seconds"]:.4f}s', flush=True)
    lines = ['# Global XOR pilot', '',
        '| n | CDCL UNSAT / 10 | oracle+check median s | discovery+check median s | CDCL observed median s | discovered XOR steps median |',
        '|---:|---:|---:|---:|---:|---:|']
    for n in metadata['sizes']:
        rs = [r for r in rows if r['n']==n]
        med = lambda k: statistics.median(r[k] for r in rs)
        solved = sum(r['baseline_status']=='UNSAT' for r in rs)
        lines.append(f'| {n} | {solved} | {med("oracle_seconds"):.4f} | {med("discovered_seconds"):.4f} | {med("baseline_seconds"):.4f} | {med("discovered_xor_steps"):.0f} |')
    lines += ['', 'All 40 discovered refutations and 40 oracle refutations passed the independent CNF/GF(2) checker. All 40 planted SAT controls were checked by their assignments and produced no accepted refutation.', '',
        'CDCL UNKNOWN is censored, not a completed runtime; no exact speedup or proof-size ratio is inferred. Budget: 2 seconds for the solver call, no conflict cap; actual counters and total time (including loading) are recorded. Discovery timing includes parity extraction and Gaussian elimination; total includes certificate checking. Formula generation, imports, diagnostic trace statistics and file serialization are excluded for all modes. Oracle has privileged equation/group information; discovery receives CNF only.', '',
        'This pilot recognizes explicit parity blocks of width at most 8 and uses a separate GF(2) proof checker. It does not discover the XOR operation, learn from CDCL history, or produce extended-resolution proofs. Recorded DAGs are algebraic elimination histories. It establishes neither low primal treewidth nor a general SAT algorithm. No learned parameters or train/test claim; seeds 0–9 overlap earlier width experiments.', '',
        'Baseline API: [PySAT solver documentation](https://pysathq.github.io/docs/api/solvers.html).']
    Path(str(prefix)+'_report.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
