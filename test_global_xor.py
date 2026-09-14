import copy
import itertools
import unittest

from global_xor import check, discover, extract, oracle, parity_clauses


class GlobalXorTests(unittest.TestCase):
    def test_all_small_parities(self):
        for width in range(1, 5):
            for rhs in (0, 1):
                scope = tuple(range(1, width+1))
                cnf = parity_clauses(scope, rhs)
                self.assertEqual(extract(cnf), [(scope, rhs)])
                for bits in itertools.product((False, True), repeat=width):
                    sat = all(any(bits[abs(v)-1] == (v > 0) for v in c) for c in cnf)
                    self.assertEqual(sat, sum(bits) % 2 == rhs)
                self.assertFalse(check(cnf, discover(cnf)))

    def test_global_contradiction_and_tampering(self):
        equations = [((1, 2), 0), ((2, 3), 0), ((1, 3), 1)]
        cnf = sum((parity_clauses(s, r) for s, r in equations), [])
        for cert in (discover(cnf), oracle(equations)):
            self.assertTrue(check(cnf, cert))
            self.assertFalse(check(cnf[1:], cert))
            bad = copy.deepcopy(cert)
            bad['steps'][0] = (-1, 0)
            self.assertFalse(check(cnf, bad))
            bad = copy.deepcopy(cert)
            bad['steps'][0] = (len(cert['equations'])+len(cert['steps']), 0)
            self.assertFalse(check(cnf, bad))

    def test_sat_control_and_partial_parity(self):
        cnf = parity_clauses((1, 2), 0)+parity_clauses((2, 3), 0)+parity_clauses((1, 3), 0)
        self.assertFalse(check(cnf, discover(cnf)))
        self.assertEqual(extract(parity_clauses((1, 2, 3), 1)[:-1]), [])


if __name__ == '__main__':
    unittest.main()
