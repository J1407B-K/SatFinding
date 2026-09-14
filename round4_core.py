"""Pure Resolution production utilities. Acceptance remains in existing checkers."""
from dataclasses import asdict, dataclass, field
import heapq

from satcache import Certificate, Step
from proofmodule import ProofModule


def decode(raw):
    return Certificate(raw['kind'], premises=tuple(map(tuple, raw['premises'])),
                       steps=tuple(Step(s['left'], s['right'], s['pivot'], tuple(s['clause']))
                                   for s in raw['steps']))


def ancestors(cert, root):
    base = len(cert.premises)
    seen, pending = set(), [root]
    while pending:
        i = pending.pop()
        if i in seen:
            continue
        if not 0 <= i < base + len(cert.steps):
            raise ValueError('Invalid proof index')
        seen.add(i)
        if i >= base:
            s = cert.steps[i-base]
            if not (0 <= s.left < i and 0 <= s.right < i):
                raise ValueError('Non-topological proof')
            pending.extend((s.left, s.right))
    return seen


def slice_proof(cert, root=None):
    nodes = list(cert.premises) + [s.clause for s in cert.steps]
    if root is None:
        root = nodes.index(())
    keep = sorted(ancestors(cert, root))
    remap = {old: new for new, old in enumerate(keep)}
    base = len(cert.premises)
    premises = tuple(nodes[i] for i in keep if i < base)
    steps = tuple(Step(remap[cert.steps[i-base].left], remap[cert.steps[i-base].right],
                       cert.steps[i-base].pivot, nodes[i]) for i in keep if i >= base)
    return Certificate('UNSAT', premises=premises, steps=steps), keep


def as_module(cert, target):
    return ProofModule((), (), cert.premises, target, cert.steps)


@dataclass
class Budget:
    limit: int
    attempts: int = 0
    outcomes: dict = field(default_factory=lambda: dict(new=0, duplicate=0, tautology=0))
    literal_visits: int = 0

    def __post_init__(self):
        if type(self.limit) is not int or self.limit < 0:
            raise ValueError('Nonnegative integral budget required')


class ProofDB:
    def __init__(self, cnf, budget):
        self.premises = tuple(cnf)
        self.nodes = list(cnf)
        self.index = {c: i for i, c in enumerate(cnf)}
        self.steps = []
        self.budget = budget
        self.trace = []

    def resolve(self, left, right, pivot):
        if self.budget.attempts >= self.budget.limit:
            return None
        a, b = self.nodes[left], self.nodes[right]
        if pivot not in a or -pivot not in b:
            raise ValueError('Producer scheduled a non-complementary pair')
        self.budget.attempts += 1
        self.budget.literal_visits += len(a) + len(b)
        clause = tuple(sorted((set(a)-{pivot}) | (set(b)-{-pivot})))
        if any(-x in clause for x in clause):
            outcome, result = 'tautology', None
        elif clause in self.index:
            outcome, result = 'duplicate', self.index[clause]
        else:
            outcome, result = 'new', len(self.nodes)
            self.nodes.append(clause)
            self.index[clause] = result
            self.steps.append(Step(left, right, pivot, clause))
        self.budget.outcomes[outcome] += 1
        self.trace.append([left, right, pivot, outcome, result])
        return result

    def certificate(self):
        return Certificate('UNSAT', premises=self.premises, steps=tuple(self.steps))

    def record(self):
        return dict(budget=asdict(self.budget), trace=self.trace,
                    full_certificate=asdict(self.certificate()))


class ResolutionSearch(ProofDB):
    """Resumable indexed saturation; all calls share the supplied global Budget.

    Each complementary parent/pivot candidate is scheduled once. Short parent
    pairs first; no width restriction, assignment enumeration or hidden hints.
    """
    def __init__(self, cnf, budget):
        super().__init__(cnf, budget)
        self.heap, self.occurrences, self.scheduled = [], {}, 0
        self._index_new()

    def _index_new(self):
        while self.scheduled < len(self.nodes):
            right = self.scheduled
            c = self.nodes[right]
            for lit in c:
                for left in self.occurrences.get(-lit, ()):
                    heapq.heappush(self.heap, (len(c)+len(self.nodes[left]), left, right, -lit))
            for lit in c:
                self.occurrences.setdefault(lit, []).append(right)
            self.scheduled += 1

    def search(self, target=(), local_limit=None):
        stop = self.budget.limit if local_limit is None else min(
            self.budget.limit, self.budget.attempts + local_limit)
        while target not in self.index and self.heap and self.budget.attempts < stop:
            _, left, right, pivot = heapq.heappop(self.heap)
            self.resolve(left, right, pivot)
            self._index_new()
        return self.index.get(target)


def preprocess(cnf, budget, bve=True, pair_cap=64):
    """CNF-only UP + no-clause-growth BVE, with explicit Resolution witnesses.

    Failed elimination probes also consume budget and remain in the trace.
    Deletions never become proof axioms. No hidden region or target is supplied.
    """
    db = ProofDB(cnf, budget)
    active = set(range(len(cnf)))
    while () not in db.index and budget.attempts < budget.limit:
        units = sorted(i for i in active if len(db.nodes[i]) == 1)
        if units:
            i = units[0]
            lit = db.nodes[i][0]
            opposing = sorted(j for j in active if -lit in db.nodes[j])
            if len(opposing) > budget.limit - budget.attempts:
                break
            results = [db.resolve(i, j, lit) for j in opposing]
            active = {j for j in active if lit not in db.nodes[j] and -lit not in db.nodes[j]}
            active.update(j for j in results if j is not None)
            continue
        if not bve:
            break
        occ = {}
        for i in sorted(active):
            for lit in db.nodes[i]:
                occ.setdefault(lit, []).append(i)
        choices = sorted((len(occ.get(v, ()))*len(occ.get(-v, ())), v)
                         for v in {abs(x) for x in occ})
        changed = False
        for pairs, v in choices:
            if pairs > pair_cap or pairs > budget.limit-budget.attempts:
                continue
            positive, negative = occ.get(v, ()), occ.get(-v, ())
            removed = set(positive) | set(negative)
            results = set()
            for a in positive:
                for b in negative:
                    result = db.resolve(a, b, v)
                    if result is not None:
                        results.add(result)
            if () in db.index:
                return db
            if len(results - (active-removed)) <= len(removed):
                active.difference_update(removed)
                active.update(results)
                changed = True
                break
        if not changed:
            break
    return db
