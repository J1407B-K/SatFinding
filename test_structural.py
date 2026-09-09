import unittest
from unittest.mock import patch
import time

from satcache import check, normalize, solve
from structural import Retriever, match, reuse_sat, reuse_unsat, wl


def slow_worker(connection, host, pattern, domains):
    time.sleep(1)


class StructuralTests(unittest.TestCase):
    def test_wl_is_variable_permutation_invariant(self):
        a = normalize([[1, -2], [2, 3], [-1]])
        b = normalize([[17, -9], [9, 22], [-17]])
        self.assertEqual(wl(a), wl(b))

    def test_sat_partial_source_model_projection(self):
        history = normalize([[1], [2], [3], [-1, 2]])
        query = normalize([[7], [-7, 8]])
        cert, mapping, status, _ = reuse_sat(history, solve(history), query)
        self.assertEqual(status, "verified")
        self.assertTrue(check(query, cert))
        self.assertEqual(set(mapping), {7, 8})

    def test_unsat_proof_mapped_into_unrelated_context(self):
        core = normalize([[1, 2], [1, -2], [-1, 2], [-1, -2]])
        query = normalize([[8, 9], [8, -9], [-8, 9], [-8, -9], [8, 20, 21]])
        cert, _, status, _ = reuse_unsat(solve(core), query)
        self.assertEqual(status, "verified")
        self.assertTrue(check(query, cert))

    def test_nonmatch_and_budget(self):
        self.assertIsNone(match(normalize([[1]]), normalize([[-7]]))[0])
        with self.assertRaises(ValueError):
            match((), (), seconds=0)

    def test_sparse_retrieval_baselines(self):
        documents = [normalize([[1, 2], [-1, 3]]), normalize([[7, 8], [-7, 9]])]
        for method in ("jaccard", "minhash", "tfidf", "bm25", "exact"):
            ranked, _ = Retriever(documents, method).rank(documents[1])
            self.assertEqual(ranked[0], 1)

    def test_native_timeout_is_not_a_logical_answer(self):
        with patch('structural._lad_worker', slow_worker):
            mapping, status, _ = match(normalize([[1]]), normalize([[2]]), seconds=0.01)
        self.assertIsNone(mapping)
        self.assertEqual(status, 'timeout')


if __name__ == "__main__":
    unittest.main()
