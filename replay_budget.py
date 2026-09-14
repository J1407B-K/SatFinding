"""Budgeted, checked replay of an existing Resolution DAG (identity mapping)."""
from collections import Counter
from fractions import Fraction
import random
from time import perf_counter

from proofmodule import ProofContext, ProofModule
from satcache import Certificate, Step

BUDGETS = (0, 32, 128, 512, 2048, 8192, 32768, 'ALL')


class HistoryIndex:
    """Source-only ranking, constructed once; never observes completion outcomes.

    Cost is a cheap local literal-work proxy, not measured ancestor closure cost.
    Exact support unions are computed only for selected roots at query time.
    """
    def __init__(self, history, seeds=(17, 29, 43)):
        self.history = history
        self.leaves = len(history.premises)
        self.clauses = list(history.premises) + [s.clause for s in history.steps]
        uses = Counter(p for s in history.steps for p in (s.left, s.right))
        self.scores = {}
        for j, s in enumerate(history.steps, self.leaves):
            if not (0 <= s.left < j and 0 <= s.right < j):
                raise ValueError('Non-topological proof')
            cost = 1 + len(self.clauses[s.left]) + len(self.clauses[s.right])
            self.scores[j] = Fraction(1 + uses[j], (1 + len(s.clause)) * cost)
        ids = list(range(self.leaves, len(self.clauses)))
        self.orders = {'ranked': sorted(ids, key=lambda i: (-self.scores[i], i))}
        for seed in seeds:
            order = ids.copy()
            random.Random(seed).shuffle(order)
            self.orders[f'random_{seed}'] = order

    def select(self, cnf, budget, ordering):
        """Filter to strictly replayable unique clauses, then take a nested top-K.

        No replacement of missing historical premises by current learned clauses.
        Canonical first eligible derivation prevents duplicate clauses receiving
        extra probability in RANDOM. Ancestors are not passed to the SAT solver.
        """
        if budget == 0:
            return [], dict(eligible_lemmas=0, eligibility_nodes=0)
        available = set(cnf)
        ready = [c in available for c in self.history.premises]
        canonical = set()
        for j, s in enumerate(self.history.steps, self.leaves):
            ok = ready[s.left] and ready[s.right]
            ready.append(ok)
            if ok and s.clause not in available:
                canonical.add(j)
                available.add(s.clause)
        if budget == 'ALL':
            selected = sorted(canonical)
        else:
            selected = []
            for j in self.orders[ordering]:
                if j in canonical:
                    selected.append(j)
                    if len(selected) == budget:
                        break
            # Keep solver insertion order constant across ranking methods.
            selected.sort()
        return selected, dict(eligible_lemmas=len(canonical), eligibility_nodes=len(ready))

    def materialize(self, cnf, selected):
        """Only traverse/check the ancestor union required by selected outputs."""
        started = perf_counter()
        needed, pending = set(), list(selected)
        while pending:
            i = pending.pop()
            if i in needed:
                continue
            needed.add(i)
            if i >= self.leaves:
                s = self.history.steps[i-self.leaves]
                pending.extend((s.left, s.right))
        nodes = list(cnf)
        lookup = {c: i for i, c in enumerate(nodes)}
        bindings, steps = {}, []
        for i in sorted(needed):
            clause = self.clauses[i]
            if i < self.leaves:
                if clause not in lookup:
                    raise ValueError('Missing target premise')
                bindings[i] = lookup[clause]
            else:
                s = self.history.steps[i-self.leaves]
                # Retain even duplicate support steps, so every selected source
                # derivation is independently checked by the existing checker.
                steps.append(Step(bindings[s.left], bindings[s.right], s.pivot, clause))
                bindings[i] = len(nodes)
                nodes.append(clause)
        materialize_seconds = perf_counter()-started
        check_started = perf_counter()
        if steps:
            module = ProofModule((), (), cnf, steps[-1].clause, tuple(steps))
            if ProofContext(cnf).check(module) is None:
                raise ValueError('Selected support failed existing proof checker')
        lemmas = [nodes[bindings[i]] for i in selected]
        if len(set(lemmas)) != len(lemmas) or set(lemmas) & set(cnf):
            raise ValueError('Non-unique or original selected lemma')
        return Certificate('UNSAT', premises=cnf, steps=tuple(steps)), lemmas, dict(
            support_leaves=sum(i < self.leaves for i in needed),
            support_inferences=len(steps),
            support_literal_work=sum(1 + len(self.clauses[s.left]) + len(self.clauses[s.right])
                                     for i in needed if i >= self.leaves
                                     for s in [self.history.steps[i-self.leaves]]),
            materialize_seconds=materialize_seconds,
            checker_seconds=perf_counter()-check_started, checker='PASS')

    def replay(self, cnf, budget, ordering='ranked'):
        started = perf_counter()
        selected, selection = self.select(cnf, budget, ordering)
        selection_seconds = perf_counter()-started
        proof, lemmas, stats = self.materialize(cnf, selected)
        stats.update(selection, selected_ids=selected, selected_lemmas=len(lemmas),
                     selection_seconds=selection_seconds,
                     replay_and_check_seconds=perf_counter()-started)
        return proof, lemmas, stats
