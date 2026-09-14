"""Evaluation-only expensive mapping search with a completing native backend."""
from dataclasses import asdict
import gzip
import hashlib
from itertools import permutations
import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter

from satcache import Certificate, Step, check, normalize
from proofmodule import ProofContext, ProofModule
from round4_core import decode, slice_proof
from resolution_import import convert

DIRECTORY = Path('results/evaluation_oracle_native')
NATIVE = Path('/private/tmp/satfinding-native-cdcl')
METRICS = ('analysis_resolution_steps', 'minimization_reason_visits',
           'binary_minimization_candidates', 'conflicts', 'decisions', 'propagations')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dimacs(path, cnf):
    path.write_text(f'p cnf {max(abs(x) for c in cnf for x in c)} {len(cnf)}\n'+
                    ''.join(' '.join(map(str, c))+' 0\n' for c in cnf))


def native(cnf, tag, mode='counted'):
    input_path, proof_path = DIRECTORY/f'{tag}.cnf', DIRECTORY/f'{tag}.drup'
    dimacs(input_path, cnf)
    started = perf_counter()
    try:
        process = subprocess.run([str(NATIVE/mode), str(input_path), str(proof_path), '1000000'],
                                 text=True, capture_output=True, check=True, timeout=30)
        row = json.loads(next(line for line in reversed(process.stdout.splitlines()) if line.startswith('{')))
        row.update(input_path=str(input_path), input_sha256=sha(input_path),
                   proof_path=str(proof_path), proof_sha256=sha(proof_path))
    except subprocess.TimeoutExpired:
        row = dict(status='TIMEOUT')
    row['process_seconds'] = perf_counter()-started
    return row


def replay(cnf, history, permutation, colors):
    """Strict old-edge replay, matching the optimizer's exact scoring predicate."""
    def lit(x):
        v, c = divmod(abs(x)-1, 3)
        return (3*permutation[v]+colors[c]+1)*(1 if x > 0 else -1)
    nodes, steps = list(cnf), []
    lookup = {c: i for i, c in enumerate(nodes)}
    bindings = []
    for c in history.premises:
        mapped = tuple(sorted(lit(x) for x in c))
        bindings.append(lookup.get(mapped))
    direct, present = 0, sum(i is not None for i in bindings)
    for s in history.steps:
        a, b = bindings[s.left], bindings[s.right]
        if a is None or b is None:
            bindings.append(None)
            continue
        pivot = lit(s.pivot)
        c = tuple(sorted(lit(x) for x in s.clause))
        assert pivot in nodes[a] and -pivot in nodes[b]
        assert c == tuple(sorted((set(nodes[a])-{pivot}) | (set(nodes[b])-{-pivot})))
        if c not in lookup:
            lookup[c] = len(nodes)
            nodes.append(c)
            steps.append(Step(a, b, pivot, c))
        bindings.append(lookup[c])
        direct += 1
    proof = Certificate('UNSAT', premises=cnf, steps=tuple(steps))
    conclusion = nodes[-1]
    assert ProofContext(cnf).check(ProofModule((), (), cnf, conclusion, proof.steps)) is not None
    return proof, list(nodes[len(cnf):]), dict(direct_inferences=direct, present_leaves=present,
        unique_replay_inferences=len(steps), historical_inferences=len(history.steps), historical_leaves=len(history.premises))


def oracle_input(path, n, history, target):
    lines = [f'{n} {len(history.premises)} {len(history.steps)} {len(target["edges"])}']
    for clause in history.premises:
        if len(clause)==2 and all(x<0 for x in clause):
            a,b=[divmod(abs(x)-1,3) for x in clause]
            if a[0] != b[0]:
                assert a[1] == b[1]
                lines.append(f'{a[0]} {b[0]}')
                continue
        # Validate the always-matching one-hot clause type, rather than guessing.
        vertices = {(abs(x)-1)//3 for x in clause}
        assert len(vertices)==1
        assert (len(clause)==3 and all(x>0 for x in clause)) or (len(clause)==2 and all(x<0 for x in clause))
        lines.append('-1 -1')
    lines.extend(f'{s.left} {s.right}' for s in history.steps)
    lines.extend(f'{a} {b}' for a,b in target['edges'])
    path.write_text('\n'.join(lines)+'\n')


def certify(cnf, completion, replay_proof, output):
    with Path(completion['proof_path']).open() as f:
        augmented = list(cnf)+[s.clause for s in replay_proof.steps]
        solver_proof, stats = convert(augmented, f, seconds=120)
    nodes = list(cnf)+[s.clause for s in replay_proof.steps]
    steps = list(replay_proof.steps)
    lookup = {c: i for i,c in enumerate(nodes)}
    mapping = [lookup[c] for c in solver_proof.premises]
    for s in solver_proof.steps:
        steps.append(Step(mapping[s.left], mapping[s.right], s.pivot, s.clause))
        mapping.append(len(nodes))
        nodes.append(s.clause)
    full = Certificate('UNSAT', premises=cnf, steps=tuple(steps))
    assert check(cnf, full)
    sliced, _ = slice_proof(full)
    assert check(cnf, sliced)
    with gzip.open(output, 'wt') as f:
        json.dump(dict(certificate=asdict(sliced), conversion=stats), f)
    return dict(path=str(output), sha256=sha(output), checker='PASS', input_leaves=len(sliced.premises),
                inference_nodes=len(sliced.steps), conversion_seconds=stats['conversion_seconds'])


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    build = json.loads((NATIVE/'build.json').read_text())
    result = dict(oracle_seconds_per_pair=90, oracle_optimality_claim=False,
                  metric_scope='native CDCL counters; old enumerative attempts are not comparable',
                  completion_policy='strict replay then whole-target CDCL completion; no local repair optimality claim',
                  native_build=build, pairs=[], sources={p: sha(p) for p in (
                      'evaluation_oracle.cpp','evaluation_oracle_run.py','native_cdcl.cc','build_native_cdcl.py',
                      'resolution_import.py','round4_core.py','satcache.py','proofmodule.py','docs/evaluation-oracle-native.md')})
    for n, hs, ts in ((120,6200,6201),(200,6202,6203)):
        base = Path('results/oracle_transfer_6regular')
        hp = base/f'n{n}_H_s{hs}.resolution.json.gz'
        tp = base/f'n{n}_T_s{ts}.json'
        with gzip.open(hp,'rt') as f:
            history = decode(json.load(f)['proof'])
        hcnf = normalize(json.loads((base/f'n{n}_H_s{hs}.json').read_text())['cnf'])
        assert check(hcnf, history)
        target = json.loads(tp.read_text())
        cnf = normalize(target['cnf'])
        pair = dict(n=n, history_path=str(hp), history_sha256=sha(hp), target_path=str(tp),
                    target_sha256=sha(tp), candidates=[])
        pair['blind'] = native(cnf, f'n{n}_blind')
        pair['instrumentation_control'] = native(cnf, f'n{n}_control', 'control')
        blind, control = pair['blind'], pair['instrumentation_control']
        assert blind['status'] == control['status'] == 'UNSAT'
        assert all(blind[k]==control[k] for k in ('conflicts','decisions','propagations'))
        assert blind['proof_sha256']==control['proof_sha256']
        print(f'n{n}: BLIND completed, instrumentation preserves exact DRUP; starting 90s oracle', flush=True)
        oi, oo = DIRECTORY/f'n{n}_oracle.input', DIRECTORY/f'n{n}_oracle.json'
        oracle_input(oi,n,history,target)
        subprocess.run(['/private/tmp/satfinding-evaluation-oracle',str(oi),'90',str(oo)], check=True, timeout=100)
        oracle = json.loads(oo.read_text())
        pair['oracle'] = dict(path=str(oo), sha256=sha(oo), evaluations=oracle['evaluations'],
                              seconds=oracle['seconds'], global_optimality_proven=oracle['global_optimality_proven'],
                              score_upper_bound=oracle['score_upper_bound'])
        candidates = [dict(permutation=list(range(n)), arbitrary_identity_control=True)] + oracle['candidates']
        best = None
        best_replay = None
        for mi, candidate in enumerate(candidates):
            for ci, colors in enumerate(permutations(range(3))):
                started = perf_counter()
                rp, lemmas, statistics = replay(cnf,history,candidate['permutation'],colors)
                replay_seconds = perf_counter()-started
                if mi:
                    assert statistics['direct_inferences'] == candidate['direct_inferences']
                    assert statistics['present_leaves'] == candidate['present_leaves']
                row = native(list(cnf)+lemmas, f'n{n}_m{mi}_c{ci}')
                row.update(mapping_index=mi, colors=colors, permutation=candidate['permutation'],
                           replay=statistics, replay_and_check_seconds=replay_seconds,
                           arbitrary_identity_control=mi==0)
                pair['candidates'].append(row)
                if mi and row['status']=='UNSAT' and (best is None or row['analysis_resolution_steps']<best['analysis_resolution_steps']):
                    best, best_replay = row, rp
        assert best is not None
        pair['best_found'] = best
        pair['blind_certificate'] = certify(cnf,blind,Certificate('UNSAT',premises=cnf),DIRECTORY/f'n{n}_blind.resolution.json.gz')
        pair['best_certificate'] = certify(cnf,best,best_replay,DIRECTORY/f'n{n}_best.resolution.json.gz')
        with gzip.open(DIRECTORY/f'n{n}_best.replay.json.gz','wt') as f:
            json.dump(asdict(best_replay),f)
        pair['savings'] = {k: dict(blind=blind[k], best_found=best[k], saved=blind[k]-best[k],
                                    fraction=1-best[k]/blind[k] if blind[k] else None) for k in METRICS}
        result['pairs'].append(pair)
        (DIRECTORY/'results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(n=n, oracle_evaluations=oracle['evaluations'],
                             replay=best['replay'], savings=pair['savings'])),flush=True)
    (DIRECTORY/'results.json').write_text(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
