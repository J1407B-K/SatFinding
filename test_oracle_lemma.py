import json
import gzip
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from oracle_lemma import Evaluator, ids_key, objective, strip_template
from oracle_lemma_evaluate import certify, materialize
from replay_budget import HistoryIndex
from round4_core import decode
from satcache import Certificate, Step, check, normalize


class OracleTests(unittest.TestCase):
    def test_template_duplicates_and_subsumed_outputs_are_excluded(self):
        premises = ((1, 2), (-1,), (1, 2, 4), (-2, 3))
        proof = Certificate('UNSAT', premises=premises, steps=(
            Step(0, 1, 1, (2,)), Step(2, 1, 1, (2, 4)), Step(4, 3, 2, (3,))))
        ids, stats = strip_template(HistoryIndex(proof), normalize(premises), [(2,)])
        self.assertEqual(ids, [6])
        self.assertEqual(stats['exact_template_duplicates'], 1)
        self.assertEqual(stats['template_subsumed'], 1)

    def test_objective_uses_ops_then_conflicts_never_seconds(self):
        a = dict(status='UNSAT', analysis_resolution_steps=10, conflicts=2, selected_ids=[5], seconds=100)
        b = dict(a, conflicts=3, seconds=0)
        self.assertLess(objective(a), objective(b))
        self.assertLess(objective(b), objective(dict(a, status='TIMEOUT')))

    def test_canonical_selection_ignores_request_order(self):
        self.assertEqual(ids_key([9, 2, 9, 5]), (2, 5, 9))

    def test_resume_future_cache_cannot_bias_earlier_stage(self):
        data = dict(cnf=normalize([(1,), (-1,)]), templates=[], population=[2, 3],
                    h=SimpleNamespace(clauses=[(), (), (2,), (3,)]))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            future = dict(status='UNSAT', analysis_resolution_steps=1, conflicts=1,
                          selected_ids=[3], screen_process_seconds=0)
            (path/'search.jsonl').write_text(json.dumps(future)+'\n')
            engine = Evaluator(data, path, workers=1)
            try:
                def solve(ids):
                    return dict(status='UNSAT', analysis_resolution_steps=100, conflicts=10,
                                selected_ids=list(ids), screen_process_seconds=0)
                engine.solve = solve
                engine.batch([[2]], 'early')
                self.assertEqual(engine.best(1)['selected_ids'], [2])
                engine.batch([[3]], 'later')
                self.assertEqual(engine.best(1)['selected_ids'], [3])
                with self.assertRaises(ValueError):
                    engine.batch([[99]], 'invalid')
            finally:
                engine.close()

    def test_conditional_supports_and_completion_discharge_to_original_target(self):
        cnf = normalize([(1, 2), (-1,), (-2,)])
        lookup = {c: i for i, c in enumerate(cnf)}
        t = HistoryIndex(Certificate('UNSAT', premises=cnf, steps=(
            Step(lookup[(1, 2)], lookup[(-1,)], 1, (2,)),)))
        h = HistoryIndex(Certificate('UNSAT', premises=cnf, steps=(
            Step(lookup[(1, 2)], lookup[(-2,)], 2, (1,)),)))
        data = dict(cnf=cnf, t=t, h=h, template_ids=[3])
        spec = dict(template=True, ids=[3])
        augmented, _, stats = materialize(data, spec)
        self.assertEqual(augmented, list(cnf)+[(2,), (1,)])
        self.assertEqual(stats['support_inferences'], 2)
        with tempfile.TemporaryDirectory() as d:
            proof_path = Path(d)/'completion.drup'
            proof_path.write_text('0\n')
            out = Path(d)/'certificate.json.gz'
            result = certify(data, spec, dict(proof_path=str(proof_path), input_sha256='test'), out)
            self.assertEqual(result['status'], 'PASS')
            with gzip.open(out, 'rt') as f:
                certificate = decode(json.load(f)['certificate'])
            self.assertTrue(check(cnf, certificate))


if __name__ == '__main__':
    unittest.main()
