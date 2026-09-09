from itertools import combinations, product
from pathlib import Path
import tempfile
import unittest

from satcache import Cache, Certificate, Step, check, normalize, residual, run, solve


class SoundnessTests(unittest.TestCase):
    def test_exhaustive_two_variable_formulas(self):
        # Independent truth-table oracle, all subsets of all non-tautological clauses.
        clauses = [tuple(x for x in pair if x)
                   for pair in product((0, 1, -1), (0, 2, -2))]
        for size in range(len(clauses) + 1):
            for subset in combinations(clauses, size):
                formula = normalize(subset)
                expected = any(all(any(bits[abs(x)-1] == (x > 0) for x in c)
                                   for c in formula)
                               for bits in product((False, True), repeat=2))
                cert = solve(formula)
                self.assertIsNotNone(cert)
                self.assertTrue(check(formula, cert))
                self.assertEqual(cert.kind, "SAT" if expected else "UNSAT")

    def test_reject_bad_model(self):
        self.assertFalse(check(normalize([[1]]), Certificate("SAT", {1: False})))
        self.assertFalse(check(normalize([[1]]), Certificate("SAT", {})))

    def test_reject_wrong_context_and_forged_proof(self):
        cert = solve(normalize([[1], [-1]]))
        self.assertFalse(check(normalize([[1]]), cert))
        formula = normalize([[1, 2], [-1, 2]])
        for left, right, pivot in [(0, 1, -1), (-1, 0, 1), (99, 0, 1)]:
            forged = Certificate("UNSAT", premises=formula,
                                 steps=(Step(left, right, pivot, ()),))
            self.assertFalse(check(formula, forged))

    def test_nontrivial_resolution(self):
        f = normalize([[1, 2], [1, -2], [-1, 2], [-1, -2]])
        cert = solve(f)
        self.assertEqual(cert.kind, "UNSAT")
        self.assertGreater(len(cert.steps), 1)
        self.assertTrue(check(f, cert))

    def test_cross_instance_hits_and_persistence(self):
        cache = Cache()
        run(normalize([[1], [-1, 2]]), cache)
        self.assertTrue(run(normalize([[-7], [7, 9]]), cache)["cache_hit"])
        run(normalize([[1], [-1]]), cache)
        result = run(normalize([[7], [-7], [8, 9]]), cache)
        self.assertTrue(result["cache_hit"])
        self.assertEqual(result["status"], "UNSAT")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            cache.save(path)
            loaded = Cache.load(path)
            self.assertEqual(len(loaded.entries), len(cache.entries))
            self.assertTrue(run(normalize([[20], [-20]]), loaded)["cache_hit"])

    def test_branch_scope(self):
        f, cache = normalize([[1, 2], [1, -2]]), Cache()
        branch = run(f, cache, {1: False})
        self.assertEqual(branch["status"], "UNSAT")
        self.assertEqual(branch["assumptions"], {1: False})
        self.assertEqual(run(f, cache)["status"], "SAT")
        self.assertEqual(run(f, cache, {1: True})["assignment"][1], True)

    def test_poisoned_cache_cannot_answer(self):
        cache = Cache()
        cache.entries.append((normalize([[1]]), Certificate("UNSAT", premises=((),))))
        self.assertIsNone(cache.lookup(normalize([[1]])))

    def test_budget_and_empty_formulas(self):
        self.assertIsNone(solve(normalize([[1]]), max_assignments=0))
        self.assertIsNone(solve(normalize([[1], [-1]]), max_resolution_attempts=0))
        self.assertEqual(run((), Cache())["status"], "SAT")
        self.assertEqual(run(((),), Cache())["status"], "UNSAT")


if __name__ == "__main__":
    unittest.main()
