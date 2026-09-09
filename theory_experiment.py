"""Finite check of the ordered-DPLL recurrence in docs/complexity.md."""
import json
from pathlib import Path
from time import perf_counter

from research import SemanticCache
from satcache import check, normalize, residual, solve, variables


CORE = normalize([[1, 2], [1, -2], [-1, 2], [-1, -2]])


def padded(n):
    return normalize(list(CORE) + [(3+i, 3+n+i) for i in range(n)])


def dpll(formula, order):
    while True:
        if () in formula:
            return False, 0
        if not formula:
            return True, 0
        unit = next((c[0] for c in formula if len(c) == 1), None)
        if unit is None:
            break
        formula = residual(formula, {abs(unit): unit > 0})
    remaining = set(variables(formula))
    v = next(v for v in order if v in remaining)
    nodes = 1
    for b in (False, True):
        sat, child_nodes = dpll(residual(formula, {v: b}), order)
        nodes += child_nodes
        if sat:
            return True, nodes
    return False, nodes


def main():
    cache = SemanticCache()
    start = perf_counter()
    cache.add(CORE, solve(CORE), "constant-core")
    seed_seconds = perf_counter()-start
    rows = []
    for n in (0, 2, 4, 6, 8, 10, 12, 14):
        formula = padded(n)
        order = list(range(3, 3+2*n)) + [1, 2]
        start = perf_counter()
        sat, nodes = dpll(formula, order)
        dpll_seconds = perf_counter()-start
        assert not sat and nodes == 2**(n+1)-1
        start = perf_counter()
        cert = cache.lookup(formula)
        assert cert is not None and check(formula, cert)
        cache_seconds = perf_counter()-start
        rows.append(dict(n=n, decision_nodes=nodes, dpll_seconds=dpll_seconds,
                         cache_seconds=cache_seconds))
    result = dict(seed_seconds=seed_seconds, rows=rows)
    Path("results").mkdir(exist_ok=True)
    Path("results/theory.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
