"""Development family only; private witnesses never enter algorithm workers."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import random
from time import perf_counter

from pysat.solvers import Glucose3
from proofmodule import ProofContext
from satcache import Certificate, check, normalize, transfer, variables
from round4_core import Budget, ResolutionSearch, as_module, slice_proof

LEVELS = ('L0', 'L1', 'L2_05', 'L2_15')
CONFIG = dict(core_variables=7, core_clauses=34, context_variables=12,
              context_clauses=12, replacement_variables=5, replacement_clauses=14,
              historical_budget=200000, replacement_budget=20000,
              replacement_max_steps=32, max_generation_trials=2000)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def random_cnf(rng, pool, count):
    clauses = set()
    while len(clauses) < count:
        clauses.add(tuple(sorted(v*rng.choice((-1, 1)) for v in rng.sample(pool, 3))))
    return normalize(clauses)


def model(cnf):
    with Glucose3(bootstrap_with=cnf) as solver:
        if not solver.solve():
            return None
        assignment = {abs(x): x > 0 for x in solver.get_model()}
    assert check(cnf, Certificate('SAT', assignment=assignment))
    return assignment


def signed_map(rng, pool):
    targets = list(pool)
    rng.shuffle(targets)
    return {v: w*rng.choice((-1, 1)) for v, w in zip(pool, targets)}


def mapped(cnf, mapping):
    return normalize([[mapping[abs(x)]*(1 if x > 0 else -1) for x in c] for c in cnf])


def replacement(rng, target, forbidden):
    """Independent random 3-CNF regions, selected for checked short derivability.

    This selection is intentional and disclosed. No shortcut outcome is used.
    """
    attempts = 0
    for trial in range(CONFIG['max_generation_trials']):
        scope = set(abs(x) for x in target)
        scope.update(rng.sample([v for v in range(1, 10) if v not in scope], 5-len(scope)))
        region = random_cnf(rng, sorted(scope), CONFIG['replacement_clauses'])
        if set(region) & forbidden:
            continue
        assignment = model(region)
        if assignment is None:
            continue
        search = ResolutionSearch(region, Budget(CONFIG['replacement_budget']))
        root = search.search(target)
        attempts += search.budget.attempts
        if root is None:
            continue
        cert, _ = slice_proof(search.certificate(), root)
        if len(cert.steps) > CONFIG['replacement_max_steps']:
            continue
        assert ProofContext(region).check(as_module(cert, target)) is not None
        return region, cert, assignment, dict(trials=trial+1, search_attempts=attempts)
    raise RuntimeError('Replacement generation cap reached; do not silently replace this seed')


def generate(seed):
    rng = random.Random(seed)
    historical_attempts = 0
    for trial in range(CONFIG['max_generation_trials']):
        h = random_cnf(rng, list(range(1, 8)), CONFIG['core_clauses'])
        if model(h) is not None:
            continue
        search = ResolutionSearch(h, Budget(CONFIG['historical_budget']))
        root = search.search()
        historical_attempts += search.budget.attempts
        if root is None:
            continue
        proof, keep = slice_proof(search.certificate(), root)
        assert check(h, proof)
        break
    else:
        raise RuntimeError('Historical generation cap reached')
    history_map = signed_map(rng, list(range(1, 8)))
    public_h, public_p = mapped(h, history_map), transfer(proof, history_map)
    histories = dict(seed=seed, raw_cnf=h, raw_proof=asdict(proof), slice_old_ids=keep,
                     search=search.record(), generation_trials=trial+1,
                     generation_search_attempts=historical_attempts)
    cases = []
    # One random leaf order; 5% broken set is nested in the 15% set.
    leaf_order = list(proof.premises)
    rng.shuffle(leaf_order)
    for level in LEVELS:
        rate = {'L0': 0, 'L1': 0, 'L2_05': .05, 'L2_15': .15}[level]
        count = math.ceil(rate*len(proof.premises))
        broken = leaf_order[:count]
        witnesses, regions, generation = [], [], []
        for c in broken:
            region, witness, assignment, stats = replacement(rng, c, set(broken))
            regions.extend(region)
            witnesses.append(dict(target=c, region=region, proof=asdict(witness), model=assignment))
            generation.append(stats)
        if level == 'L0':
            target_cnf = h
        else:
            for noise_trial in range(CONFIG['max_generation_trials']):
                noise = random_cnf(rng, list(range(1, 13)), CONFIG['context_clauses'])
                if set(noise) & set(broken) or model(noise) is None:
                    continue
                target_cnf = normalize([c for c in proof.premises if c not in broken]+regions+list(noise))
                if not set(h) <= set(target_cnf) and not set(target_cnf) <= set(h):
                    break
            else:
                raise RuntimeError('Context generation cap reached')
        pool = list(range(1, max(variables(target_cnf))+1))
        target_map = signed_map(rng, pool)
        target = list(mapped(target_cnf, target_map))
        rng.shuffle(target)
        truth = {abs(history_map[v]): target_map[v]*(1 if history_map[v] > 0 else -1)
                 for v in range(1, 8)}
        public = dict(version=1, historical_cnf=public_h, historical_proof=asdict(public_p), cnf=target)
        case_id = digest(public)[:20]
        private = dict(case_id=case_id, seed=seed, level=level, requested_broken_fraction=rate,
                       broken_leaves=count, historical_leaves=len(proof.premises),
                       actual_broken_fraction=count/len(proof.premises),
                       mapping=truth, target_map=target_map, raw_target=target_cnf,
                       broken=broken, replacement_witnesses=witnesses,
                       replacement_generation=generation)
        cases.append((public, private))
    # A SAT control is a separate case, never mislabeled as a repairable positive.
    control = random_cnf(rng, list(range(1, 13)), 12)
    assignment = model(control)
    if assignment is None:
        raise RuntimeError('SAT control generation failed')
    public = dict(version=1, historical_cnf=public_h, historical_proof=asdict(public_p), cnf=control)
    cases.append((public, dict(case_id=digest(public)[:20], seed=seed, level='SAT_CONTROL', model=assignment)))
    return histories, cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='results/round4_dev')
    ap.add_argument('--seeds', nargs='+', type=int, default=[4100, 4101, 4102, 4103])
    args = ap.parse_args()
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = dict(version=1, phase='development_shortcut_gate', config=CONFIG,
                    seeds=args.seeds, cases=[], histories=[], sources={})
    started = perf_counter()
    for seed in args.seeds:
        history, cases = generate(seed)
        history_path = directory / f'private_history_{seed}.json'
        history_path.write_text(json.dumps(history))
        manifest['histories'].append(dict(path=str(history_path), sha256=hashlib.sha256(history_path.read_bytes()).hexdigest()))
        for public, private in cases:
            path = directory / (private['case_id']+'.json')
            path.write_text(json.dumps(public))
            private.update(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            manifest['cases'].append(private)
        print(f'Generated development seed {seed}: {len(cases)} cases', flush=True)
    manifest['generation_seconds'] = perf_counter()-started
    for file in ('round4_generate.py', 'round4_core.py', 'satcache.py', 'proofmodule.py'):
        manifest['sources'][file] = hashlib.sha256(Path(file).read_bytes()).hexdigest()
    (directory/'private_manifest.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
