import unittest
from copy import deepcopy

from satcache import Certificate, Step, check, normalize
from proofmodule import ProofContext
from round4_core import Budget, ProofDB, ResolutionSearch, as_module, preprocess, slice_proof
from audit_round4 import audit_trace


class Round4Tests(unittest.TestCase):
    def test_slice_removes_unused_inputs_and_search_nodes(self):
        cnf = normalize([(1,), (-1, 2), (-2,), (3, 4), (-3, 4)])
        db = ProofDB(cnf, Budget(10))
        db.resolve(db.index[(3, 4)], db.index[(-3, 4)], 3)
        i = db.resolve(db.index[(1,)], db.index[(-1, 2)], 1)
        db.resolve(i, db.index[(-2,)], 2)
        cert, keep = slice_proof(db.certificate())
        self.assertTrue(check(cnf, cert))
        self.assertEqual((len(cert.premises), len(cert.steps)), (3, 2))
        self.assertNotIn(db.index[(4,)], keep)
        self.assertEqual(db.budget.attempts, 3)

    def test_slice_keeps_shared_parent_once(self):
        cnf = ((1,), (-1, 2), (-2, 3), (-3, -2))
        cert = Certificate('UNSAT', premises=cnf, steps=(
            Step(0, 1, 1, (2,)), Step(4, 2, 2, (3,)),
            Step(4, 3, 2, (-3,)), Step(5, 6, 3, ())))
        sliced, keep = slice_proof(cert)
        self.assertTrue(check(cnf, sliced))
        self.assertEqual(keep.count(4), 1)
        self.assertEqual(len(sliced.steps), 4)

    def test_global_budget_survives_calls_and_search_instances(self):
        budget = Budget(2)
        cnf = normalize([(1,), (-1, 2), (-2,)])
        a = ResolutionSearch(cnf, budget)
        a.search(local_limit=1)
        self.assertEqual(budget.attempts, 1)
        b = ResolutionSearch(cnf, budget)
        b.search(local_limit=100)
        a.search(local_limit=100)
        self.assertEqual(budget.attempts, 2)
        self.assertEqual(len(a.trace)+len(b.trace), 2)

    def test_rejected_results_are_charged(self):
        cnf = normalize([(1, 2), (-1, -2), (-1, 2), (2,)])
        db = ProofDB(cnf, Budget(2))
        db.resolve(db.index[(1, 2)], db.index[(-2, -1)], 1)
        db.resolve(db.index[(1, 2)], db.index[(-1, 2)], 1)
        self.assertEqual(db.budget.outcomes, dict(new=0, duplicate=1, tautology=1))
        self.assertEqual(db.budget.attempts, 2)

    def test_exact_lemma_without_assumption_or_extension(self):
        cnf = normalize([(1, 2, 3), (-1, 2, 3)])
        search = ResolutionSearch(cnf, Budget(10))
        root = search.search((2, 3))
        cert, _ = slice_proof(search.certificate(), root)
        self.assertIsNotNone(ProofContext(cnf).check(as_module(cert, (2, 3))))
        self.assertFalse(check(cnf, cert))

    def test_preprocessing_refutation_and_sat_control(self):
        cnf = normalize([(1, 2), (1, -2), (-1, 2), (-1, -2)])
        self.assertNotIn((), preprocess(cnf, Budget(100), bve=False).index)
        db = preprocess(cnf, Budget(100))
        cert, _ = slice_proof(db.certificate())
        self.assertTrue(check(cnf, cert))
        self.assertNotIn((), preprocess(normalize([(1, 2), (-1, 2)]), Budget(100)).index)

    def test_audit_rejects_uncharged_attempt(self):
        search = ResolutionSearch(normalize([(1,), (-1,)]), Budget(10))
        search.search()
        record = deepcopy(search.record())
        self.assertEqual(audit_trace(record)['attempts'], 1)
        record['budget']['attempts'] = 0
        with self.assertRaises(AssertionError):
            audit_trace(record)

    def test_audit_rejects_future_parent_and_false_outcome(self):
        search = ResolutionSearch(normalize([(1,), (-1,)]), Budget(10))
        search.search()
        record = deepcopy(search.record())
        record['trace'][0][0] = 2
        with self.assertRaises(AssertionError):
            audit_trace(record)
        record = deepcopy(search.record())
        record['trace'][0][3] = 'duplicate'
        with self.assertRaises(AssertionError):
            audit_trace(record)


if __name__ == '__main__':
    unittest.main()
