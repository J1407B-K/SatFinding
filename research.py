"""Benchmark caches; every returned certificate is checked on the query."""
from collections import Counter, defaultdict
from copy import deepcopy
from math import sqrt

from satcache import Certificate, check, embedding, similarity, transfer, variables


class ExactCache:
    def __init__(self):
        self.exact = {}
        self.last_source = None

    def add(self, formula, cert, name):
        if not check(formula, cert):
            raise ValueError("Invalid certificate on insertion")
        self.exact[formula] = (deepcopy(cert), name)

    def lookup(self, formula):
        self.last_source = None
        entry = self.exact.get(formula)
        if entry and check(formula, entry[0]):
            self.last_source = entry[1]
            return entry[0]
        return None


def canonical(formula):
    """Exact colored-graph canonicalization under signed variable permutation."""
    import pynauty
    vs = variables(formula)
    n, m = len(vs), len(formula)
    index = {v: i for i, v in enumerate(vs)}
    adjacency = {i: [] for i in range(2*n + m)}
    for i in range(n):
        adjacency[2*i].append(2*i+1)
        adjacency[2*i+1].append(2*i)
    for j, c in enumerate(formula):
        node = 2*n+j
        for x in c:
            literal = 2*index[abs(x)] + (x < 0)
            adjacency[node].append(literal)
            adjacency[literal].append(node)
    if not adjacency:
        return (0, 0, b""), (), vs
    colors = [s for s in (set(range(2*n)), set(range(2*n, 2*n+m))) if s]
    graph = pynauty.Graph(2*n+m, adjacency_dict=adjacency, vertex_coloring=colors)
    return (n, m, pynauty.certificate(graph)), tuple(pynauty.canon_label(graph)), vs


class CanonicalCache(ExactCache):
    def __init__(self):
        super().__init__()
        self.index = {}
        self.pending = None

    def lookup(self, formula):
        cert = super().lookup(formula)
        if cert is not None:
            return cert
        key, order, vs = canonical(formula)
        self.pending = (formula, key, order, vs)
        entry = self.index.get(key)
        if entry is None:
            return None
        cert, source_order, source_vs, name = entry
        inverse = {node: i for i, node in enumerate(source_order)}
        mapping = {}
        for i, v in enumerate(source_vs):
            target_node = order[inverse[2*i]]
            mapping[v] = vs[target_node//2] * (-1 if target_node % 2 else 1)
        candidate = transfer(cert, mapping)
        if check(formula, candidate):
            self.last_source = name
            return candidate
        return None

    def add(self, formula, cert, name):
        super().add(formula, cert, name)
        if self.pending is not None and self.pending[0] == formula:
            _, key, order, vs = self.pending
        else:
            key, order, vs = canonical(formula)
        self.index[key] = (deepcopy(cert), order, vs, name)
        self.pending = None


class SemanticCache(ExactCache):
    """Sparse clause-incidence embedding with an inverted dot-product index.

    This baseline assumes aligned variable identities. Similarity only proposes
    candidates; even containment is not trusted as an acceptance condition.
    """
    def __init__(self, top_k=8, structural_only=False, prefilter=True):
        super().__init__()
        self.entries = []
        self.postings = defaultdict(list)
        self.top_k = top_k
        self.structural_only = structural_only
        self.prefilter = prefilter

    def add(self, formula, cert, name):
        super().add(formula, cert, name)
        idx = len(self.entries)
        self.entries.append((deepcopy(cert), name, sqrt(len(formula)),
                             embedding(formula) if self.structural_only else None))
        for c in formula:
            self.postings[c].append(idx)

    def lookup(self, formula):
        cert = super().lookup(formula)
        if cert is not None:
            return cert
        if self.structural_only:
            query = embedding(formula)
            ranked = sorted(range(len(self.entries)),
                            key=lambda i: similarity(query, self.entries[i][3]), reverse=True)
        else:
            scores = Counter()
            for c in formula:
                scores.update(self.postings.get(c, ()))
            # Query norm is common to all candidates and need not be computed.
            ranked = sorted(scores, key=lambda i: scores[i]/self.entries[i][2], reverse=True)
        for idx in ranked[:self.top_k]:
            candidate, name, _, _ = self.entries[idx]
            # Untrusted cheap rejection only: do not traverse/validate a whole CNF
            # for models typically falsified by one of its first few clauses.
            if self.prefilter and candidate.kind == "SAT":
                model = candidate.assignment or {}
                if not all(any(model.get(abs(x)) == (x > 0) for x in c) for c in formula):
                    continue
            if check(formula, candidate):
                self.last_source = name
                return candidate
        return None


def glucose_sat(formula):
    """SAT-only adapter. An UNSAT solver status is NOT accepted without a proof."""
    from pysat.solvers import Glucose3
    with Glucose3(bootstrap_with=formula) as solver:
        if not solver.solve():
            return None
        model = solver.get_model()
    cert = Certificate("SAT", assignment={abs(x): x > 0 for x in model})
    if not check(formula, cert):
        raise ValueError("Invalid Glucose model")
    return cert
