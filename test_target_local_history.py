import unittest
from target_local_history import cheap_pool
from satcache import normalize
from proofmodule import ProofContext, ProofModule
from round4_core import ancestors


class CheapPoolTests(unittest.TestCase):
    def test_two_steps_not_two_levels(self):
        cnf=normalize([(1,2),(-1,3),(-3,4),(-4,5)])
        proof,meta=cheap_pool(cnf)
        clauses=list(cnf)+[s.clause for s in proof.steps]
        self.assertIn((2,4),clauses)
        self.assertNotIn((2,5),clauses)  # Requires three inferences.
        self.assertIsNotNone(ProofContext(cnf).check(
            ProofModule((),(),cnf,clauses[-1],proof.steps)))
        for i in range(len(cnf),len(clauses)):
            self.assertLessEqual(sum(j>=len(cnf) for j in ancestors(proof,i)),2)

    def test_tautology_and_duplicate_handling(self):
        cnf=normalize([(1,2),(-1,-2),(1,3),(-1,3)])
        proof,_=cheap_pool(cnf)
        clauses=list(cnf)+[s.clause for s in proof.steps]
        self.assertEqual(len(clauses),len(set(clauses)))
        self.assertIn((2,3),clauses)
        self.assertTrue(all(not any(-x in c for x in c) for c in clauses))


if __name__=='__main__': unittest.main()
