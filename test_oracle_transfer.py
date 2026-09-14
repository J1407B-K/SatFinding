import unittest
from copy import deepcopy

from satcache import Certificate, Step, check, normalize
from oracle_transfer_run import run
from audit_oracle_transfer import audit_sessions


class OracleTests(unittest.TestCase):
    def test_complete_replay_has_zero_search_and_root_certificate(self):
        cnf = normalize([(1,), (-1,)])
        p = Certificate('UNSAT', premises=cnf, steps=(Step(1, 0, 1, ()),))
        row = run(cnf, 'ORACLE_HISTORY', p, {1: 1})
        self.assertEqual(row['status'], 'UNSAT')
        self.assertEqual(row['budget']['attempts'], 0)
        self.assertEqual(row['history']['initial_direct_inferences'], 1)

    def test_missing_leaf_not_accepted_as_input(self):
        p = Certificate('UNSAT', premises=((-1,), (1,)), steps=(Step(1, 0, 1, ()),))
        row = run(normalize([(1,)]), 'ORACLE_HISTORY', p, {1: 1})
        self.assertEqual(row['status'], 'MISS')
        self.assertIsNone(row['certificate'])
        self.assertEqual(row['history']['initial_missing_leaves'], 1)

    def test_both_routes_same_target_checked(self):
        p = Certificate('UNSAT', premises=((-1,), (1,)), steps=(Step(1, 0, 1, ()),))
        target = normalize([(1,), (-1, 2), (-2,)])
        for route in ('BLIND', 'ORACLE_HISTORY'):
            row = run(target, route, p, {1: 1})
            self.assertEqual(row['status'], 'UNSAT')
            self.assertEqual(row['budget']['attempts'], sum(len(s['trace']) for s in row['sessions']))
            self.assertEqual(sum(row['budget']['outcomes'].values()), row['budget']['attempts'])

    def test_independent_audit_accepts_complete_replay(self):
        cnf = normalize([(1,), (-1,)])
        p = Certificate('UNSAT', premises=cnf, steps=(Step(1, 0, 1, ()),))
        row = run(cnf, 'ORACLE_HISTORY', p, {1: 1})
        self.assertEqual(audit_sessions(row, cnf, p)['attempts'], 0)

    def test_independent_audit_rejects_attempt_counter_tampering(self):
        cnf = normalize([(1,), (-1,)])
        row = run(cnf, 'BLIND')
        self.assertEqual(audit_sessions(row, cnf)['attempts'], 1)
        bad = deepcopy(row)
        bad['budget']['attempts'] = 0
        with self.assertRaises(AssertionError):
            audit_sessions(bad, cnf)


if __name__ == '__main__':
    unittest.main()
