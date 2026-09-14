import unittest

from pysat.solvers import Glucose3
from pysat.examples.genhard import PHP
from satcache import check, normalize
from resolution_import import RUPImporter, convert


class ImportTests(unittest.TestCase):
    def test_real_glucose_drup_and_ancestor_slice(self):
        cnf = normalize(PHP(nof_holes=3).clauses)
        with Glucose3(bootstrap_with=cnf, with_proof=True) as solver:
            self.assertFalse(solver.solve())
            proof, stats = convert(cnf, solver.get_proof())
        self.assertTrue(check(cnf, proof))
        self.assertGreater(stats['sliced_inference_nodes'], 0)

    def test_rup_strengthening_has_no_weakening_axiom(self):
        producer = RUPImporter(normalize([(1,), (-1, 2)]))
        i = producer.add((2, 3))
        self.assertLessEqual(set(producer.nodes[i]), {2, 3})
        self.assertNotIn(3, producer.nodes[i])

    def test_unsupported_addition_rejected(self):
        with self.assertRaises(ValueError):
            convert(normalize([(1, 2)]), ['1 0', '0'])

    def test_deletion_is_not_an_axiom(self):
        proof, _ = convert(normalize([(1,), (-1,)]), ['d 1 0', '0'])
        self.assertTrue(check(normalize([(1,), (-1,)]), proof))


if __name__ == '__main__':
    unittest.main()
