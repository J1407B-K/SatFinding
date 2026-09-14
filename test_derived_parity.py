import copy
import itertools
import unittest

from derived_parity import canonical, check, discover, register, sharing
from round3_inputs import check_projection, split


class DerivedParityTests(unittest.TestCase):
    def formula(self, odd=True):
        return canonical([1,2],0)+canonical([2,3],0)+canonical([1,3],int(odd))

    def test_depth_ladder_and_budget(self):
        for depth in range(4):
            cnf,witness = split(self.formula(),depth)
            self.assertTrue(check_projection(self.formula(),cnf,witness))
            cert,stats = discover(cnf)
            self.assertTrue(check(cnf,cert)['unsat'])
            self.assertEqual(len(cert['resolution']),6*(2**depth-1))
            self.assertEqual(sharing(cnf,cert)['proof_sharing_ratio'],1)
            empty,_ = discover(cnf,step_budget=0)
            self.assertEqual(check(cnf,empty)['unsat'],depth==0)

    def test_sat_and_false_rhs(self):
        for depth in range(4):
            cnf,_ = split(self.formula(False),depth)
            cert,_ = discover(cnf)
            result = check(cnf,cert)
            self.assertTrue(result['valid'])
            self.assertFalse(result['unsat'])
            bad = copy.deepcopy(cert)
            bad['parities'][0]['rhs'] ^= 1
            self.assertFalse(check(cnf,bad)['valid'])

    def test_tampered_certificates(self):
        cnf,_ = split(self.formula(),2)
        cert,_ = discover(cnf)
        for key,value in [('left',-1),('right',len(cnf)+len(cert['resolution'])),
                          ('pivot',True),('clause',[])]:
            bad = copy.deepcopy(cert)
            bad['resolution'][0][key] = value
            self.assertFalse(check(cnf,bad)['valid'])
        bad = copy.deepcopy(cert)
        bad['parities'][0]['clauses'].pop()
        self.assertFalse(check(cnf,bad)['valid'])
        bad = copy.deepcopy(cert)
        bad['gf2']['steps'][0] = [-1,0]
        self.assertFalse(check(cnf,bad)['valid'])
        self.assertFalse(check(cnf[1:],cert)['valid'])

    def test_registration_has_no_semantic_inference(self):
        # Units imply x1 XOR x2=0, but the explicit canonical block is absent.
        self.assertFalse(register([(1,),(2,)],dict(vars=[1,2],rhs=0,clauses=[0,1])))
        with self.assertRaises(ValueError):
            canonical(list(range(1,10)),0)

    def test_projection_exhaustive(self):
        cnf = [(1,2)]
        for depth in range(4):
            hidden,witness = split(cnf,depth)
            nv = max(abs(x) for c in hidden for x in c)
            for bits in itertools.product((False,True),repeat=nv):
                actual = all(any(bits[abs(x)-1]==(x>0) for x in c) for c in hidden)
                self.assertEqual(actual,bits[0] or bits[1])
            if witness:
                witness[0]['pivot'] = 1
                self.assertFalse(check_projection(cnf,hidden,witness))


if __name__ == '__main__':
    unittest.main()
