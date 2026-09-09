"""Cross-check all valid tiny certificates on all tiny current formulas."""
from itertools import combinations, product
import unittest

from satcache import Cache, Certificate, check, normalize, run, solve


class AdversarialTests(unittest.TestCase):
    def test_all_tiny_historical_certificates_on_all_current_formulas(self):
        clauses = [tuple(x for x in pair if x)
                   for pair in product((0, 1, -1), (0, 2, -2))]
        formulas = [normalize(cs) for k in range(10) for cs in combinations(clauses, k)]
        certificates = [solve(f) for f in formulas]
        for f in formulas:
            sat = any(all(any(bits[abs(x)-1] == (x > 0) for x in c) for c in f)
                      for bits in product((False, True), repeat=2))
            for cert in certificates:
                if check(f, cert):
                    self.assertEqual(cert.kind == "SAT", sat)

    def test_controller_rechecks_cache_output(self):
        class Liar(Cache):
            def lookup(self, formula):
                return Certificate("UNSAT", premises=((),))
        with self.assertRaises(ValueError):
            run(normalize([[1]]), Liar())

    def test_generator_clauses_preserve_meaning(self):
        self.assertEqual(normalize([iter([1, 2])]), ((1, 2),))


if __name__ == "__main__":
    unittest.main()
