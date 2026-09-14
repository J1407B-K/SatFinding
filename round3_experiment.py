"""Depth ladder with CNF-only baselines and replayable two-layer certificates."""
import argparse
import csv
import gzip
import hashlib
import json
import pickle
import platform
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter

import networkx
import pycryptosat
import pysat

from derived_parity import check, clause, discover, eliminate, register, sharing
from global_xor import check as check_oracle
from global_xor import oracle
from round3_inputs import dimacs, make


def encode(cert):
    return json.dumps(cert,separators=(',',':')).encode()


def native(cnf, mode, seconds):
    with tempfile.TemporaryDirectory(prefix='round3-') as d:
        path = Path(d)/'input.pkl'
        path.write_bytes(pickle.dumps(cnf))
        start = perf_counter()
        try:
            result = subprocess.run([sys.executable,'round3_solver.py',mode,str(path),
                                     '--seconds',str(seconds)],capture_output=True,text=True,
                                    timeout=seconds+10,check=True)
            value = json.loads(result.stdout)
            value['worker_wall_time'] = perf_counter()-start
            return value
        except subprocess.TimeoutExpired:
            return dict(status='TIMEOUT',total_time=perf_counter()-start,
                        worker_wall_time=perf_counter()-start)


def run_case(n, seed, depth, kind, args, directory):
    cnf,equations,original,model = make(n,seed,depth,kind)
    data = dimacs(cnf)
    common = dict(n=n,seed=seed,kind=kind,planted_depth=depth,
        total_input_vars=len(model),total_input_clauses=len(cnf),input_bytes=len(data),
        input_sha256=hashlib.sha256(data).hexdigest(),total_parities=len(equations))
    if kind == 'SAT':
        assert all(any(model[abs(x)] == (x>0) for x in c) for c in cnf)
    # Randomize all modes reproducibly; no simultaneous solver timing.
    modes = list('ABCDE')
    random.Random(seed+100*depth).shuffle(modes)
    rows = []
    for mode in modes:
        row = dict(common,mode=mode)
        if mode in 'ABC':
            result = native(cnf,mode,args.seconds)
            assert result['status'] != ('SAT' if kind == 'UNSAT' else 'UNSAT'), result
            if result.get('processed_parities') is not None:
                found = {(tuple(s),r) for s,r in result.pop('processed_parities')}
                truth = {(tuple(s),r) for s,r in equations}
                result['recovered_parities'] = len(found & truth)
                result['recovered_fraction'] = len(found & truth)/len(truth)
            row.update(result)
        elif mode == 'D':
            cert,stats = discover(cnf,args.step_budget,args.attempt_budget)
            checked = check(cnf,cert)
            assert checked['valid']
            assert not checked['unsat'] or kind == 'UNSAT'
            payload = encode(cert)
            path = directory/f'n{n}_s{seed}_d{depth}_{kind}.json.gz'
            with gzip.open(path,'wb') as f:
                f.write(payload)
            recovered = {(tuple(p['vars']),p['rhs']) for p in cert['parities']}
            truth = {(tuple(s),r) for s,r in equations}
            matched = len(recovered & truth)
            assert matched == len(recovered), 'Unexpected extra parity: inspect separately'
            res_steps = len(cert['resolution'])
            row.update(stats)
            row.update(checked)
            row.update(sharing(cnf,cert))
            row.update(status='UNSAT' if checked['unsat'] else 'MISS',
                recovered_parities=matched,recovered_fraction=matched/len(equations),
                resolution_DAG_nodes=len(cnf)+res_steps,resolution_DAG_edges=2*res_steps,
                checked_resolution_steps=res_steps,GF2_DAG_nodes=len(cert['parities'])+len(cert['gf2']['steps']),
                GF2_steps=len(cert['gf2']['steps']),certificate_bytes=len(payload),
                certificate_sha256=hashlib.sha256(payload).hexdigest(),certificate_path=str(path),
                certificate_per_input=len(payload)/len(data),
                discovery_per_clause=stats['discovery_time']/len(cnf),
                checked_steps_per_recovered=res_steps/matched if matched else None,
                attempts_per_accepted=stats['candidate_attempts']/matched if matched else None,
                total_time=stats['discovery_time']+stats['GF2_time']+
                    sum(checked[k] for k in ('resolution_check_time','parity_registration_time','GF2_check_time')))
            # All deliberately false SAT parity proposals conflict with a checked model.
            bad_attempts = bad_rejects = 0
            if kind == 'SAT':
                nodes = [clause(c) for c in cnf]+[clause(s['clause']) for s in cert['resolution']]
                for q in cert['parities']:
                    bad = dict(q,rhs=q['rhs']^1)
                    assert sum(model[x] for x in bad['vars'])%2 != bad['rhs']
                    bad_attempts += 1
                    bad_rejects += not register(nodes,bad)
                assert bad_attempts == bad_rejects
            row.update(false_parity_attempts=bad_attempts,false_parity_checker_rejects=bad_rejects,
                       checker_certificate_rejects=0,sat_assignment_checked=kind=='SAT')
        else:
            start = perf_counter()
            parities = [dict(vars=list(s),rhs=r) for s,r in equations]
            gf2 = eliminate(parities)
            generation = perf_counter()-start
            cert = dict(equations=equations,steps=gf2['steps'],conclusion=gf2['conclusion'])
            start = perf_counter()
            accepted = check_oracle(original,cert)
            verify = perf_counter()-start
            assert accepted == (kind=='UNSAT')
            row.update(status='UNSAT' if accepted else 'NO_CONTRADICTION',
                total_time=generation+verify,GF2_time=generation,oracle_check_time=verify,
                GF2_steps=len(gf2['steps']),recovered_parities=len(equations),
                oracle_privileged=True)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sizes',nargs='+',type=int,default=[80,160,320,640])
    ap.add_argument('--seeds',nargs='+',type=int,default=list(range(10,20)))
    ap.add_argument('--depths',nargs='+',type=int,default=[0,1,2,3])
    ap.add_argument('--seconds',type=float,default=2.)
    ap.add_argument('--step-budget',type=int,default=200000)
    ap.add_argument('--attempt-budget',type=int,default=2000000)
    ap.add_argument('--output',default='results/round3')
    args = ap.parse_args()
    prefix = Path(args.output)
    directory = Path(str(prefix)+'_certificates')
    directory.mkdir(parents=True,exist_ok=True)
    sources = ['derived_parity.py','round3_inputs.py','round3_solver.py','round3_experiment.py',
               'global_xor.py','global_xor_experiment.py']
    metadata = dict(arguments=vars(args),python=platform.python_version(),
        networkx=networkx.__version__,pysat=pysat.__version__,pycryptosat=pycryptosat.__version__,
        sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources})
    Path(str(prefix)+'_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with open(str(prefix)+'_raw.jsonl','w') as f:
        for n in args.sizes:
            for depth in args.depths:
                for seed in args.seeds:
                    for kind in ('UNSAT','SAT'):
                        rows = run_case(n,seed,depth,kind,args,directory)
                        for row in rows:
                            f.write(json.dumps(row)+'\n')
                        f.flush()
                        states = ' '.join(r['mode']+':'+r['status'] for r in sorted(rows,key=lambda x:x['mode']))
                        d = next(r for r in rows if r['mode']=='D')
                        print(f'n={n} d={depth} seed={seed} {kind} {states} '
                              f'recovered={d["recovered_parities"]}/{n} Dtime={d["total_time"]:.3f}s',flush=True)
    rows = [json.loads(line) for line in Path(str(prefix)+'_raw.jsonl').read_text().splitlines()]
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with open(str(prefix)+'_raw.csv','w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
