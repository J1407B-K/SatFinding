import unittest

from evaluation_oracle_run import replay
from replay_budget import HistoryIndex
from satcache import Certificate, Step, normalize


class BudgetTests(unittest.TestCase):
    def setUp(self):
        # Two branches, one has a premise absent from the target. Duplicate
        # derivations must not consume output budget or bias random sampling.
        self.cnf = normalize([(1, 2), (-1,), (-2, 3)])
        self.history = Certificate('UNSAT', premises=((1, 2), (-1,), (-2, 3), (-3,)), steps=(
            Step(0, 1, 1, (2,)), Step(4, 2, 2, (3,)),
            Step(5, 3, 3, ()), Step(0, 1, 1, (2,))))
        self.index = HistoryIndex(self.history)

    def test_all_equals_legacy_and_excludes_missing_branch(self):
        _, old, _ = replay(self.cnf, self.history, [0], [0, 1, 2])
        _, new, stats = self.index.replay(self.cnf, 'ALL')
        self.assertEqual(new, old)
        self.assertEqual(stats['selected_lemmas'], 2)
        self.assertEqual(stats['support_inferences'], 2)

    def test_budget_nested_unique_and_zero(self):
        for order in self.index.orders:
            one, _ = self.index.select(self.cnf, 1, order)
            two, _ = self.index.select(self.cnf, 2, order)
            self.assertEqual(len(one), 1)
            self.assertTrue(set(one) <= set(two))
            self.assertEqual(len(two), 2)
        _, lemmas, stats = self.index.replay(self.cnf, 0)
        self.assertEqual(lemmas, [])
        self.assertEqual(stats['support_inferences'], 0)

    def test_support_is_checked_but_not_injected(self):
        _, lemmas, stats = self.index.materialize(self.cnf, [5])
        self.assertEqual(lemmas, [(3,)])
        self.assertEqual(stats['support_inferences'], 2)
        with self.assertRaisesRegex(ValueError, 'Missing target premise'):
            self.index.materialize(self.cnf, [6])

    def test_corrupt_selected_derivation_rejected(self):
        bad = Certificate('UNSAT', premises=self.history.premises,
                          steps=(Step(0, 1, 1, (3,)),))
        with self.assertRaisesRegex(ValueError, 'checker'):
            HistoryIndex(bad).replay(self.cnf, 'ALL')


if __name__ == '__main__':
    unittest.main()
