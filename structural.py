"""Round-two retrieval and matching. No dataset names or ground truth enter here."""
from collections import Counter, defaultdict
from hashlib import blake2b
from math import log, sqrt
import random
import multiprocessing
from time import perf_counter

from research import canonical
from satcache import Certificate, check, normalize, transfer, variables


def digest(value):
    return blake2b(repr(value).encode(), digest_size=16).hexdigest()


def incidence(formula):
    """Literal-pair / clause graph, typed by polarity and clause width."""
    vs = variables(formula)
    index = {v: i for i, v in enumerate(vs)}
    adj = [[] for _ in range(2*len(vs)+len(formula))]
    colors = [p for _ in vs for p in ("positive", "negative")]
    colors += [f"clause:{len(c)}" for c in formula]
    for i in range(len(vs)):
        adj[2*i].append(2*i+1)
        adj[2*i+1].append(2*i)
    for j, c in enumerate(formula):
        node = 2*len(vs)+j
        for x in c:
            literal = 2*index[abs(x)]+(x < 0)
            adj[node].append(literal)
            adj[literal].append(node)
    return adj, colors, vs


def wl(formula, rounds=2):
    adj, colors, _ = incidence(formula)
    result = Counter()
    for depth in range(rounds+1):
        result.update((depth, c) for c in colors)
        colors = [digest((colors[i], tuple(sorted(colors[j] for j in neighbors))))
                  for i, neighbors in enumerate(adj)]
    return result


def dot_rank(query, documents):
    # Useful independently of the corpus-level retriever (e.g. local proof motifs).
    norm = sqrt(sum(v*v for v in query.values())) or 1
    return [sum(query[k]*v for k, v in d.items()) /
            (norm*(sqrt(sum(v*v for v in d.values())) or 1)) for d in documents]


class Retriever:
    def __init__(self, formulas, method):
        self.formulas = formulas
        self.method = method
        self.documents = [wl(f) if method == "wl" else Counter(f) for f in formulas]
        self.postings = defaultdict(list)
        self.lengths = [sum(d.values()) for d in self.documents]
        self.average = sum(self.lengths)/max(1, len(formulas))
        self.idf = {}
        for i, d in enumerate(self.documents):
            for term, frequency in d.items():
                self.postings[term].append((i, frequency))
        n = len(formulas)
        for term, posting in self.postings.items():
            self.idf[term] = log((1+n)/(1+len(posting)))+1
        self.norms = [sqrt(sum((v*self.idf[t])**2 for t, v in d.items())) or 1
                      for d in self.documents]
        self.keys = [canonical(f)[0] for f in formulas] if method == "canonical" else None
        self.signatures = [self.minhash(d) for d in self.documents] if method == "minhash" else None

    @staticmethod
    def minhash(document, count=64):
        prime = 2**61-1
        values = [int(digest(t), 16) % prime for t in document]
        rng = random.Random(914)
        return tuple(min(((a*x+b) % prime for x in values), default=prime)
                     for a, b in ((rng.randrange(1, prime), rng.randrange(prime)) for _ in range(count)))

    def rank(self, formula):
        n = len(self.formulas)
        rng = random.Random(int(digest(formula), 16))
        tie_order = list(range(n))
        rng.shuffle(tie_order)
        priority = {idx: k for k, idx in enumerate(tie_order)}
        scores = [0.0]*n
        if self.method == "random":
            return tie_order, scores
        if self.method in ("exact", "canonical"):
            key = formula if self.method == "exact" else canonical(formula)[0]
            hits = [i for i, f in enumerate(self.formulas if self.keys is None else self.keys) if f == key]
            return hits, [float(i in hits) for i in range(n)]
        query = wl(formula) if self.method == "wl" else Counter(formula)
        if self.method == "minhash":
            signature = self.minhash(query)
            scores = [sum(a == b for a, b in zip(signature, s))/len(signature) for s in self.signatures]
        elif self.method == "jaccard":
            for term in query:
                for i, _ in self.postings.get(term, ()):
                    scores[i] += 1
            scores = [x/(len(query)+len(d)-x) if len(query)+len(d)-x else 1.0
                      for x, d in zip(scores, self.documents)]
        elif self.method in ("tfidf", "wl"):
            qnorm = sqrt(sum((v*self.idf.get(t, log(1+n)+1))**2 for t, v in query.items())) or 1
            for term, qf in query.items():
                for i, df in self.postings.get(term, ()):
                    scores[i] += qf*df*self.idf[term]**2
            scores = [v/(qnorm*self.norms[i]) for i, v in enumerate(scores)]
        elif self.method == "bm25":
            for term, qf in query.items():
                postings = self.postings.get(term, ())
                weight = log(1+(n-len(postings)+0.5)/(len(postings)+0.5))
                for i, df in postings:
                    scores[i] += qf*weight*(df*2.2)/(df+1.2*(0.25+0.75*self.lengths[i]/self.average))
        else:
            raise ValueError(self.method)
        return sorted(range(n), key=lambda i: (-scores[i], priority[i])), scores


def _lad_worker(connection, host, pattern, domains):
    try:
        connection.send(("ok", host.subisomorphic_lad(pattern, domains=domains,
                                                      induced=False, return_mapping=True)))
    except Exception as exc:
        connection.send(("error", repr(exc)))
    finally:
        connection.close()


def match(pattern, host, seconds=1):
    """Inject pattern clauses into host, with a subprocess LAD time budget.

    Search uses polarity-preserving variable permutations. Exact clause containment
    is checked after graph matching, so graph-library output is only a proposal.
    """
    import igraph
    if not isinstance(seconds, (float, int)) or seconds <= 0:
        raise ValueError("A positive search time budget is required")
    start = perf_counter()
    pa, pc, pv = incidence(pattern)
    ha, hc, hv = incidence(host)
    def graph(adj):
        return igraph.Graph(n=len(adj), edges=[(i, j) for i, ns in enumerate(adj) for j in ns if i < j])
    domains = [[j for j in range(len(ha)) if pc[i] == hc[j] and len(pa[i]) <= len(ha[j])]
               for i in range(len(pa))]
    if len(pa) > len(ha) or any(not d for d in domains):
        return None, "incompatible", perf_counter()-start
    # igraph 1.0 retains a stale time_limit docstring but rejects the keyword.
    # Bound actual native search in a disposable process; never let a timeout
    # become an UNSAT answer. Linux fork is the explicit execution requirement.
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_lad_worker, args=(child, graph(ha), graph(pa), domains))
    process.start()
    child.close()
    try:
        if not parent.poll(seconds):
            return None, "timeout", perf_counter()-start
        try:
            state, payload = parent.recv()
        except EOFError:
            return None, "worker_error", perf_counter()-start
        if state != "ok":
            raise RuntimeError(payload)
        found, node_map = payload
    finally:
        parent.close()
        process.join(0.02)
        if process.is_alive():
            process.terminate()
            process.join()
    if not found:
        return None, "no_match", perf_counter()-start
    mapping = {v: hv[node_map[2*i]//2] for i, v in enumerate(pv)}
    transported = normalize([[mapping[abs(x)]*(1 if x > 0 else -1) for x in c] for c in pattern])
    if len(set(mapping.values())) != len(mapping) or not set(transported) <= set(host):
        return None, "invalid_mapping", perf_counter()-start
    return mapping, "mapped", perf_counter()-start


def reuse_sat(history, certificate, query, seconds=1):
    mapping, status, elapsed = match(query, history, seconds)
    if mapping is None:
        return None, mapping, status, elapsed
    candidate = Certificate("SAT", assignment={v: certificate.assignment[w] for v, w in mapping.items()})
    if not check(query, candidate):
        return None, mapping, "rejected", elapsed
    return candidate, mapping, "verified", elapsed


def reuse_unsat(certificate, query, seconds=1):
    mapping, status, elapsed = match(certificate.premises, query, seconds)
    if mapping is None:
        return None, mapping, status, elapsed
    candidate = transfer(certificate, mapping)
    if not check(query, candidate):
        return None, mapping, "rejected", elapsed
    return candidate, mapping, "verified", elapsed
