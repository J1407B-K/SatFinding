from itertools import permutations, product
import unittest

from research import CanonicalCache, ExactCache, SemanticCache, canonical
from satcache import Certificate, check, normalize, solve, transfer


class ResearchTests(unittest.TestCase):
    def test_signed_canonical_equivalence_and_transfer(self):
        for f in (normalize([[1], [-1, 2]]), normalize([[1], [-1], [2, 3]])):
            n = max(abs(x) for c in f for x in c)
            cert = solve(f)
            cache = CanonicalCache()
            cache.add(f, cert, "history")
            for perm in permutations(range(10, 10+n)):
                for signs in product((1, -1), repeat=n):
                    mapping = {i+1: v*s for i, (v, s) in enumerate(zip(perm, signs))}
                    target = normalize([[mapping[abs(x)]*(1 if x > 0 else -1) for x in c] for c in f])
                    self.assertEqual(canonical(f)[0], canonical(target)[0])
                    got = cache.lookup(target)
                    self.assertIsNotNone(got)
                    self.assertTrue(check(target, got))

    def test_strictly_more_than_exact_and_canonical(self):
        for source, query in (([[1], [2]], [[1, 2]]),
                              ([[1], [-1]], [[1], [-1], [2, 3]])):
            source, query = normalize(source), normalize(query)
            cert = solve(source)
            self.assertNotEqual(len(source), len(query))
            for cls in (ExactCache, CanonicalCache, SemanticCache):
                cache = cls()
                cache.add(source, cert, "history")
                # SAT example has no shared clause, so use structural candidate proposal.
                if cls is SemanticCache and cert.kind == "SAT":
                    cache = SemanticCache(structural_only=True)
                    cache.add(source, cert, "history")
                got = cache.lookup(query)
                if cls is SemanticCache:
                    self.assertIsNotNone(got)
                    self.assertTrue(check(query, got))
                else:
                    self.assertIsNone(got)

    def test_same_clause_count_does_not_imply_isomorphism(self):
        a = normalize([[1], [2]])
        b = normalize([[1], [-1]])
        self.assertNotEqual(canonical(a)[0], canonical(b)[0])
        a = normalize([[1, 2], [-1, -2]])
        b = normalize([[1, 2], [-1, 2]])
        self.assertNotEqual(canonical(a)[0], canonical(b)[0])

    def test_poisoned_retrieval_is_rejected(self):
        cache = SemanticCache()
        f = normalize([[1]])
        cache.add(f, solve(f), "history")
        cache.entries[0][0].assignment[1] = False
        self.assertIsNone(cache.lookup(normalize([[1], [1, 2]])))

    def test_invalid_data_fails_closed(self):
        cert = Certificate("SAT", {1: True})
        for formula in (((0,),), ((True,),), ((1, 1),), [[1]]):
            self.assertFalse(check(formula, cert))
        self.assertFalse(check(((1,),), Certificate("SAT", {True: True})))


if __name__ == "__main__":
    unittest.main()
