import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from oracle_transfer_screen import coloring
from satcache import check, normalize
from pysat.solvers import Glucose3
from resolution_import import convert
from evaluation_oracle_run import oracle_input, replay, dimacs
from audit_evaluation_oracle import replayed_clauses


class EvaluationOracleTests(unittest.TestCase):
    def test_strict_replay_and_optimizer_bound_on_complete_graph(self):
        # K4 non-3-colorability is a correctness control, never a research case.
        n=4
        edges=[(i,j) for i in range(n) for j in range(i+1,n)]
        cnf=[]
        for v in range(n):
            cs=[3*v+c+1 for c in range(3)]
            cnf.append(cs)
            cnf.extend([[-cs[a],-cs[b]] for a in range(3) for b in range(a+1,3)])
        cnf.extend([[-(3*u+c+1),-(3*v+c+1)] for u,v in edges for c in range(3)])
        cnf=normalize(cnf)
        with Glucose3(bootstrap_with=cnf,with_proof=True) as solver:
            self.assertFalse(solver.solve())
            history,_=convert(cnf,solver.get_proof())
        with tempfile.TemporaryDirectory() as tmp:
            ip,op=Path(tmp)/'input',Path(tmp)/'output'
            oracle_input(ip,n,history,dict(edges=edges))
            subprocess.run(['/private/tmp/satfinding-evaluation-oracle',str(ip),'.02',str(op)],check=True)
            result=json.loads(op.read_text())
        self.assertTrue(result['global_optimality_proven'])
        for candidate in result['candidates']:
            proof,lemmas,stats=replay(cnf,history,candidate['permutation'],(2,0,1))
            self.assertTrue(check(cnf,proof))
            self.assertEqual(stats['direct_inferences'],len(history.steps))
            self.assertEqual(replayed_clauses(cnf,history,candidate['permutation'],(2,0,1))[2],lemmas)

    def test_native_counter_disabled_preserves_small_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            cnf=Path(tmp)/'input.cnf'
            dimacs(cnf,normalize([(1,2),(1,-2),(-1,2),(-1,-2)]))
            rows=[]
            proofs=[]
            for mode in ('counted','control'):
                out=Path(tmp)/mode
                result=subprocess.check_output(['/private/tmp/satfinding-native-cdcl/'+mode,str(cnf),str(out),'1000000'],text=True)
                rows.append(json.loads(result.splitlines()[-1]))
                proofs.append(out.read_bytes())
            self.assertEqual(proofs[0],proofs[1])
            self.assertEqual(rows[0]['status'],'UNSAT')
            self.assertEqual(rows[0]['conflicts'],rows[1]['conflicts'])


if __name__=='__main__':
    unittest.main()
