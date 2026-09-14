"""Round 3: bounded complementary-pair discovery and a syntactic two-layer checker.

No SAT solver, graph metadata, hidden split variables, or history in this module.
"""
from collections import defaultdict, deque
from itertools import product
from time import perf_counter


def clause(c):
    if not isinstance(c, (list, tuple)) or any(type(x) is not int or x == 0 for x in c):
        raise ValueError('Invalid clause')
    if len(set(c)) != len(c) or any(-x in c for x in c):
        raise ValueError('Duplicate/tautological clause')
    return tuple(sorted(c))


def canonical(scope, rhs):
    if (not isinstance(scope, (list, tuple)) or not 1 <= len(scope) <= 8
            or any(type(v) is not int or v <= 0 for v in scope)
            or list(scope) != sorted(set(scope)) or type(rhs) is not int or rhs not in (0, 1)):
        raise ValueError('Invalid parity')
    return [tuple(sorted(-v if b else v for v, b in zip(scope, bits)))
            for bits in product((0, 1), repeat=len(scope)) if sum(bits) % 2 != rhs]


def register(nodes, proposal):
    """Only exact canonical clauses, with explicit already-checked node IDs."""
    try:
        expected = canonical(proposal['vars'], proposal['rhs'])
        refs = proposal['clauses']
        return (isinstance(refs, list) and len(refs) == len(expected)
                and all(type(i) is int and 0 <= i < len(nodes) and nodes[i] == c
                        for i, c in zip(refs, expected)))
    except (ValueError, TypeError, KeyError):
        return False


def check(cnf, cert):
    """Deterministic resolution -> canonical registration -> GF(2) replay."""
    times = dict(resolution_check_time=0., parity_registration_time=0., GF2_check_time=0.)
    try:
        start = perf_counter()
        nodes = [clause(c) for c in cnf]
        for step in cert['resolution']:
            a, b, p = step['left'], step['right'], step['pivot']
            if any(type(i) is not int or not 0 <= i < len(nodes) for i in (a, b)):
                raise ValueError('Invalid parent')
            if type(p) is not int or p <= 0 or p not in nodes[a] or -p not in nodes[b]:
                raise ValueError('Invalid pivot')
            result = clause(step['clause'])
            expected = (set(nodes[a])-{p}) | (set(nodes[b])-{-p})
            if set(result) != expected:
                raise ValueError('Incorrect resolvent')
            nodes.append(result)
        times['resolution_check_time'] = perf_counter()-start
        start = perf_counter()
        equations = []
        for proposal in cert['parities']:
            if not register(nodes, proposal):
                raise ValueError('Missing canonical clause')
            equations.append((set(proposal['vars']), proposal['rhs']))
        times['parity_registration_time'] = perf_counter()-start
        start = perf_counter()
        for a, b in cert['gf2']['steps']:
            if any(type(i) is not int or not 0 <= i < len(equations) for i in (a, b)):
                raise ValueError('Invalid GF2 parent')
            x, u = equations[a]
            y, v = equations[b]
            equations.append((x ^ y, u ^ v))
        end = cert['gf2']['conclusion']
        if end is not None and (type(end) is not int or not 0 <= end < len(equations)):
            raise ValueError('Invalid conclusion')
        unsat = end is not None and equations[end] == (set(), 1)
        if end is not None and not unsat:
            raise ValueError('Conclusion is not a contradiction')
        times['GF2_check_time'] = perf_counter()-start
        return dict(valid=True, unsat=unsat, recovered_parities=len(cert['parities']), **times)
    except (ValueError, TypeError, KeyError, IndexError):
        return dict(valid=False, unsat=False, recovered_parities=0, **times)


def eliminate(parities):
    basis, steps = {}, []
    for i, q in enumerate(parities):
        row, rhs, node = sum(1 << (v-1) for v in q['vars']), q['rhs'], i
        while row:
            pivot = row.bit_length()-1
            if pivot not in basis:
                basis[pivot] = (row, rhs, node)
                break
            other, bit, parent = basis[pivot]
            steps.append([node, parent])
            node = len(parities)+len(steps)-1
            row ^= other
            rhs ^= bit
        if not row and rhs:
            return dict(steps=steps, conclusion=node)
    return dict(steps=steps, conclusion=None)


def discover(cnf, step_budget=200000, attempt_budget=2000000):
    start = perf_counter()
    nodes = [clause(c) for c in cnf]
    active = {i:c for i,c in enumerate(nodes)}
    occurrences = defaultdict(set)
    for i,c in active.items():
        for lit in c:
            occurrences[abs(lit)].add(i)
    pending = deque(sorted(v for v, ids in occurrences.items() if len(ids) == 2))
    queued = set(pending)
    steps, attempts, misses = [], 0, 0
    while pending and len(steps) < step_budget and attempts < attempt_budget:
        v = pending.popleft()
        queued.discard(v)
        ids = occurrences[v]
        if len(ids) != 2:
            continue
        attempts += 1
        a,b = sorted(ids)
        ca,cb = active[a],active[b]
        if v not in ca:
            a,b,ca,cb = b,a,cb,ca
        if v not in ca or -v not in cb:
            misses += 1
            continue
        result = tuple(x for x in ca if x != v)
        if result != tuple(x for x in cb if x != -v):
            misses += 1
            continue
        index = len(nodes)
        steps.append(dict(left=a, right=b, pivot=v, clause=result))
        nodes.append(result)
        del active[a],active[b]
        touched = {abs(x) for x in ca+cb}
        for x in ca:
            occurrences[abs(x)].discard(a)
        for x in cb:
            occurrences[abs(x)].discard(b)
        active[index] = result
        for x in result:
            occurrences[abs(x)].add(index)
        for x in sorted(touched):
            if len(occurrences[x]) == 2 and x not in queued:
                queued.add(x)
                pending.append(x)
    groups = defaultdict(dict)
    # Include every proved clause, even those subsequently eliminated.
    for i,c in enumerate(nodes):
        if 1 <= len(c) <= 8:
            groups[tuple(sorted(abs(x) for x in c))][c] = i
    parities, candidate_attempts, rejects = [], 0, 0
    for scope, available in sorted(groups.items()):
        # Incomplete scopes still count as two attempted registrations, but
        # cannot contain either full block, avoiding exponential enumeration.
        candidate_attempts += 2
        if len(available) < 2**(len(scope)-1):
            rejects += 2
            continue
        for rhs in (0, 1):
            block = canonical(scope, rhs)
            if all(c in available for c in block):
                parities.append(dict(vars=list(scope), rhs=rhs, clauses=[available[c] for c in block]))
            else:
                rejects += 1
    discovery_time = perf_counter()-start
    start = perf_counter()
    gf2 = eliminate(parities)
    gf2_time = perf_counter()-start
    cert = dict(version=1, resolution=steps, parities=parities, gf2=gf2)
    return cert, dict(discovery_time=discovery_time, GF2_time=gf2_time,
        resolution_candidate_attempts=attempts, resolution_candidate_misses=misses,
        candidate_attempts=candidate_attempts, candidate_accepts=len(parities),
        candidate_rejects=rejects, search_budget_exhausted=bool(pending))


def sharing(cnf, cert):
    """Count input and derived ancestors; per-parity sets vs their union."""
    base = len(cnf)
    union, independent = set(), 0
    for q in cert['parities']:
        seen, stack = set(), list(q['clauses'])
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            if i >= base:
                s = cert['resolution'][i-base]
                stack.extend((s['left'],s['right']))
        independent += len(seen)
        union.update(seen)
    return dict(sum_of_independent_proof_nodes=independent, shared_DAG_nodes=len(union),
                proof_sharing_ratio=independent/len(union) if union else None)
