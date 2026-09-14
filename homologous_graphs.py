"""6-regular 3-coloring instances and degree-preserving homologous drift."""
import random

import networkx as nx

from satcache import normalize


def encode(n, edges, degree, seed=None, origin=None):
    clauses = []
    for v in range(n):
        colors = [3*v+c+1 for c in range(3)]
        clauses.append(colors)
        clauses.extend([[-colors[a], -colors[b]] for a in range(3) for b in range(a+1, 3)])
    for u, v in edges:
        clauses.extend([[-(3*u+c+1), -(3*v+c+1)] for c in range(3)])
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    graph.add_edges_from(edges)
    degrees = [d for _, d in graph.degree()]
    return dict(cnf=normalize(clauses), edges=sorted(tuple(sorted(e)) for e in edges),
                vertices=n, degree=degree, colors=3, seed=seed, origin=origin,
                connected=nx.is_connected(graph), min_degree=min(degrees), max_degree=max(degrees))


def regular(n, seed, degree=6):
    graph = nx.random_regular_graph(degree, n, seed=seed)
    return encode(n, graph.edges(), degree, seed=seed, origin='independent_regular')


def overlap(history_edges, target_edges):
    history, target = set(map(tuple, history_edges)), set(map(tuple, target_edges))
    shared = history & target
    return dict(history_edges=len(history), target_edges=len(target), shared_edges=len(shared),
                replaced_edges=len(history-target), added_edges=len(target-history),
                replace_rate=len(history-target)/len(history),
                jaccard=len(shared)/len(history|target))


def _swap(edges, n, rng):
    elist = list(edges)
    adjacent = [set() for _ in range(n)]
    for a, b in elist:
        adjacent[a].add(b)
        adjacent[b].add(a)
    for _ in range(256):
        a, b = elist[rng.randrange(len(elist))]
        c, d = elist[rng.randrange(len(elist))]
        if len({a, b, c, d}) != 4:
            continue
        if rng.randrange(2):
            pairs = ((a, c), (b, d))
        else:
            pairs = ((a, d), (b, c))
        if pairs[0][1] in adjacent[pairs[0][0]] or pairs[1][1] in adjacent[pairs[1][0]]:
            continue
        nxt = set(elist)
        nxt.remove((a, b) if a < b else (b, a))
        nxt.remove((c, d) if c < d else (d, c))
        nxt.add(tuple(sorted(pairs[0])))
        nxt.add(tuple(sorted(pairs[1])))
        return nxt
    return None


def evolve(n, base_edges, rate, seed, degree=6):
    rng = random.Random(seed)
    original = set(tuple(sorted(e)) for e in base_edges)
    edges = set(original)
    target = 0 if rate == 0 else max(1, int(round(rate * len(original))))
    swaps = attempts = rejected = 0
    while len(original - edges) < target and attempts < 100000:
        attempts += 1
        candidate = _swap(edges, n, rng)
        if candidate is None:
            rejected += 1
            continue
        graph = nx.Graph()
        graph.add_nodes_from(range(n))
        graph.add_edges_from(candidate)
        if not nx.is_connected(graph):
            rejected += 1
            continue
        edges = candidate
        swaps += 1
    instance = encode(n, edges, degree, seed=seed, origin=f'evolve_{rate}')
    instance['drift'] = dict(overlap(original, edges), target_replaced=target, swaps=swaps,
                             attempts=attempts, rejected=rejected, rate_request=rate)
    return instance
