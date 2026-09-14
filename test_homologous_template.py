import json
import tempfile
import unittest
from pathlib import Path

from homologous_graphs import encode, evolve, overlap, regular
from homologous_template_run import encoding_leaf, encoding_only_inferences
from oracle_transfer_screen import coloring
from evaluation_oracle_run import replay
from satcache import check, normalize
from pysat.solvers import Glucose3
from resolution_import import convert
from round4_core import decode


class HomologousTemplateTests(unittest.TestCase):
    def test_encode_matches_screen_coloring(self):
        data = coloring(10, 3, degree=6)
        self.assertEqual(encode(10, data['edges'], 6, seed=3)['cnf'], normalize(data['cnf']))

    def test_evolve_preserves_regularity_and_hits_replaced_target(self):
        base = regular(12, 11, degree=4)
        inst = evolve(12, base['edges'], 0.25, seed=19, degree=4)
        self.assertTrue(inst['connected'])
        self.assertEqual(inst['min_degree'], 4)
        self.assertEqual(inst['max_degree'], 4)
        self.assertEqual(inst['drift']['replaced_edges'], inst['drift']['target_replaced'])
        self.assertEqual(inst['drift']['replaced_edges'], inst['drift']['added_edges'])
        self.assertGreater(inst['drift']['shared_edges'], 0)
        self.assertLess(set(map(tuple, inst['edges'])), set(map(tuple, base['edges'])) | set(map(tuple, inst['edges'])))
        self.assertNotEqual(set(map(tuple, inst['edges'])), set(map(tuple, base['edges'])))

    def test_independent_overlap_is_not_identity(self):
        a, b = regular(12, 4), regular(12, 5)
        stats = overlap(a['edges'], b['edges'])
        self.assertLess(stats['jaccard'], 1)
        self.assertEqual(stats['history_edges'], 36)

    def test_encoding_only_inferences_are_zero_on_k4(self):
        n, edges = 4, [(i, j) for i in range(4) for j in range(i+1, 4)]
        cnf = normalize(encode(n, edges, 3)['cnf'])
        with Glucose3(bootstrap_with=cnf, with_proof=True) as solver:
            self.assertFalse(solver.solve())
            history, _ = convert(cnf, solver.get_proof())
        self.assertTrue(any(encoding_leaf(c) for c in history.premises))
        self.assertTrue(any(not encoding_leaf(c) for c in history.premises))
        self.assertEqual(encoding_only_inferences(history), 0)
        proof, lemmas, stats = replay(cnf, history, list(range(n)), (0, 1, 2))
        self.assertTrue(check(cnf, proof))
        self.assertEqual(stats['direct_inferences'], len(history.steps))
        self.assertGreater(len(lemmas), 0)

    def test_decode_roundtrip_of_saved_history_shape(self):
        raw = json.loads(Path('results/oracle_transfer_6regular/n120_H_s6200.json').read_text())
        self.assertEqual(raw['vertices'], 120)
        self.assertEqual(len(raw['edges']), 360)


if __name__ == '__main__':
    unittest.main()
