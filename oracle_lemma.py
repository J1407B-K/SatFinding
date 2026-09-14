"""Expensive same-target, TEMPLATE-conditional lemma subset oracle."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile
import threading
from time import perf_counter

from evaluation_oracle_run import sha
from homologous_template_run import encoding_leaf, load_history, NATIVE
from replay_budget import HistoryIndex
from satcache import check, normalize

DIRECTORY = Path('results/oracle_lemma')
TARGET = Path('results/homologous_template/n200_T_r01_s7201.json')
HISTORY = Path('results/oracle_transfer_6regular/n200_H_s6202.resolution.json.gz')
TEMPLATE = Path('results/homologous_template/n200_U_s6302.resolution.json.gz')
CAPS = (32, 64, 128, 256)
SEED = 20260910


def ids_key(ids):
    return tuple(sorted(set(ids)))


def objective(row):
    if row['status'] != 'UNSAT':
        return (float('inf'), float('inf'), tuple(row['selected_ids']))
    return (row['analysis_resolution_steps'], row['conflicts'], tuple(row['selected_ids']))


def strip_template(index, cnf, templates):
    """Operational exclusion, not semantic novelty relative to an UNSAT target."""
    eligible, _ = index.select(cnf, 'ALL', 'ranked')
    encoding = [encoding_leaf(c) for c in index.history.premises]
    for s in index.history.steps:
        encoding.append(encoding[s.left] and encoding[s.right])
    template_set = set(templates)
    template_sets = sorted((frozenset(c) for c in templates), key=len)
    counts = Counter()
    population = []
    for i in eligible:
        clause = index.clauses[i]
        if clause in template_set:
            counts['exact_template_duplicates'] += 1
        elif encoding[i]:
            counts['encoding_only'] += 1
        elif any(t <= set(clause) for t in template_sets if len(t) <= len(clause)):
            counts['template_subsumed'] += 1
        else:
            population.append(i)
    return population, dict(eligible_before=len(eligible), eligible_after=len(population), **counts)


def prepare():
    started = perf_counter()
    cnf = normalize(json.loads(TARGET.read_text())['cnf'])
    indexes = {}
    offline = {}
    for name, path in [('history', HISTORY), ('template', TEMPLATE)]:
        begin = perf_counter()
        proof, _ = load_history(path)
        if not check(proof.premises, proof):
            raise ValueError(f'Invalid {name} source proof')
        indexes[name] = HistoryIndex(proof)
        offline[name] = dict(path=str(path), sha256=sha(path),
                             load_check_index_seconds=perf_counter()-begin)
    h, t = indexes['history'], indexes['template']
    template_ids, _ = t.select(cnf, 'ALL', 'ranked')
    _, templates, stats = t.materialize(cnf, template_ids)
    if len(templates) != 67:
        raise ValueError('Frozen TEMPLATE baseline changed')
    population, exclusions = strip_template(h, cnf, templates)
    eligible_set = set(population)
    ranked = [i for i in h.orders['ranked'] if i in eligible_set]
    uses = Counter(p for s in h.history.steps for p in (s.left, s.right))
    shortest = sorted(population, key=lambda i: (len(h.clauses[i]), -uses[i], i))
    used = sorted(population, key=lambda i: (-uses[i], len(h.clauses[i]), i))
    return dict(cnf=cnf, h=h, t=t, template_ids=template_ids, templates=templates,
                population=population, ranked=ranked, shortest=shortest, used=used,
                offline=offline, exclusions=exclusions,
                prepare_seconds=perf_counter()-started)


class Evaluator:
    """Fresh native processes; counter-only cached screening, append-only trace."""
    def __init__(self, data, directory, workers=4):
        self.data, self.directory = data, directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        # Resume may have cached evaluations from later stages. They must not
        # influence a deterministic replay of earlier adaptive decisions.
        self.observed = set()
        self.trace = directory/'search.jsonl'
        if self.trace.exists():
            for line in self.trace.read_text().splitlines():
                row = json.loads(line)
                self.cache[ids_key(row['selected_ids'])] = row
        self.stream = self.trace.open('a')
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.local = threading.local()
        self.temp = tempfile.TemporaryDirectory(prefix='satfinding-oracle-')
        base = list(data['cnf'])+data['templates']
        self.prefix = ''.join(' '.join(map(str, c))+' 0\n' for c in base)
        self.base_count = len(base)
        self.variables = max(abs(x) for c in base for x in c)
        self.clause_lines = {i: ' '.join(map(str, data['h'].clauses[i]))+' 0\n'
                             for i in data['population']}
        self.allowed = set(data['population'])
        self.started = perf_counter()
        self.initial_evaluations = len(self.cache)

    def close(self):
        self.executor.shutdown()
        self.stream.close()
        self.temp.cleanup()

    def solve(self, ids):
        path = Path(self.temp.name)/f'{threading.get_ident()}.cnf'
        content = f'p cnf {self.variables} {self.base_count+len(ids)}\n'+self.prefix
        content += ''.join(self.clause_lines[i] for i in ids)
        started = perf_counter()
        path.write_text(content)
        try:
            p = subprocess.run([str(NATIVE/'counted'), str(path), '/dev/null', '1000000'],
                               capture_output=True, text=True, check=True, timeout=30)
            row = json.loads(next(line for line in reversed(p.stdout.splitlines()) if line.startswith('{')))
        except subprocess.TimeoutExpired:
            row = dict(status='TIMEOUT')
        row.update(selected_ids=list(ids), selected_lemmas=len(ids),
                   screen_process_seconds=perf_counter()-started,
                   input_sha256=hashlib.sha256(content.encode()).hexdigest())
        return row

    def batch(self, candidates, stage):
        keys = [ids_key(ids) for ids in candidates]
        unique = list(dict.fromkeys(keys))
        if any(not set(ids) <= self.allowed for ids in unique):
            raise ValueError('Candidate outside stripped historical population')
        missing = [ids for ids in unique if ids not in self.cache]
        for ids, row in zip(missing, self.executor.map(self.solve, missing)):
            row.update(stage=stage, evaluation_id=len(self.cache),
                       discovery_elapsed_seconds=perf_counter()-self.started)
            self.cache[ids] = row
            self.stream.write(json.dumps(row)+'\n')
            if len(self.cache) % 128 == 0:
                self.stream.flush()
                print(f'{stage}: {len(self.cache)} unique evaluations; '
                      f'latest {row.get("analysis_resolution_steps")} ops', flush=True)
        self.stream.flush()
        self.observed.update(keys)
        return [self.cache[ids] for ids in keys]

    def best(self, cap, exact=False):
        rows = [self.cache[ids] for ids in self.observed
                if len(ids) == cap or (not exact and len(ids) <= cap)]
        return min(rows, key=objective)


def singleton_candidates(data, count):
    ids = list(dict.fromkeys(data['ranked'][:2048]+data['shortest'][:2048]+data['used'][:2048]))
    if len(ids) < count:
        remaining = sorted(set(data['population'])-set(ids))
        ids.extend(random.Random(SEED).sample(remaining, min(count-len(ids), len(remaining))))
    return ids[:count]


def discovery(data, directory, workers=4, singletons=8192, subsets=384, starts=2, removals=16, swaps=8):
    directory.mkdir(parents=True, exist_ok=True)
    config = dict(workers=workers, singletons=singletons, subsets_per_cap=subsets,
                  backward_starts=starts, removal_proposals=removals, swap_rounds=swaps)
    sources = {str(p): sha(p) for p in (TARGET, HISTORY, TEMPLATE, Path('oracle_lemma.py'),
               Path('replay_budget.py'), Path('satcache.py'), Path('proofmodule.py'),
               Path('docs/oracle-lemma-protocol.md'), NATIVE/'counted')}
    metadata = dict(config=config, source_files=sources, target=str(TARGET), seed=SEED,
                    exclusions=data['exclusions'], offline=data['offline'],
                    prepare_seconds=data['prepare_seconds'], template_ids=data['template_ids'],
                    template_lemmas=data['templates'], population=data['population'],
                    objective='analysis_resolution_steps, then conflicts, then source IDs',
                    globally_optimal=False, same_target_oracle=True,
                    binary_build=json.loads((NATIVE/'build.json').read_text()))
    metadata_path = directory/'metadata.json'
    if metadata_path.exists():
        old = json.loads(metadata_path.read_text())
        if old['config'] != config or old['source_files'] != sources:
            raise ValueError('Resume configuration/provenance mismatch; use a new output directory')
    else:
        metadata_path.write_text(json.dumps(metadata, indent=2))
    engine = Evaluator(data, directory, workers)
    started = perf_counter()
    try:
        base = engine.batch([[]], 'template_baseline')[0]
        print(f'TEMPLATE baseline: {base.get("analysis_resolution_steps")} ops', flush=True)
        screened = singleton_candidates(data, singletons)
        singleton_rows = engine.batch([[i] for i in screened], 'singletons')
        singles = [r['selected_ids'][0] for r in sorted(singleton_rows, key=objective)]
        elite = singles[:512]
        singleton_order = {i: rank for rank, i in enumerate(singles)}
        mixture = list(dict.fromkeys(elite+data['ranked'][:2048]))
        rng = random.Random(SEED+1)
        for cap in CAPS:
            candidates = [data['ranked'][:cap], singles[:cap]]
            for i in range(subsets):
                pool = (data['population'], elite, mixture)[i//(subsets//3) % 3]
                candidates.append(rng.sample(pool, cap))
            engine.batch(candidates, f'subsets_{cap}')
            best = engine.best(cap, exact=True)
            print(f'seed best exact {cap}: {best["analysis_resolution_steps"]} ops', flush=True)
        seeds = sorted([engine.cache[ids] for ids in engine.observed if len(ids) == 256], key=objective)[:starts]
        for restart, seed in enumerate(seeds):
            current = seed['selected_ids']
            rng = random.Random(SEED+20+restart)
            while len(current) > 32:
                proposals = rng.sample(current, min(removals, len(current)))
                worst = max(current, key=lambda i: (singleton_order.get(i, len(singles)), i))
                if worst not in proposals:
                    proposals[-1] = worst
                children = [[j for j in current if j != remove] for remove in proposals]
                rows = engine.batch(children, f'backward_{restart}_{len(current)}')
                best = min(rows, key=objective)
                current = best['selected_ids']
                if len(current) % 16 == 0:
                    print(f'backward {restart}: size {len(current)}, {best["analysis_resolution_steps"]} ops', flush=True)
        for cap in CAPS:
            rng = random.Random(SEED+100+cap)
            for iteration in range(swaps):
                best = engine.best(cap, exact=True)
                current = best['selected_ids']
                candidates = []
                for i in range(32):
                    remove = rng.choice(current)
                    pool = elite if i % 2 == 0 else data['population']
                    add = rng.choice(pool)
                    while add in current:
                        add = rng.choice(pool)
                    candidates.append([j for j in current if j != remove]+[add])
                engine.batch(candidates, f'swaps_{cap}_{iteration}')
        # Freeze the exact-K winners before computing independent ablations.
        exact = {str(k): dict(engine.best(k, exact=True)) for k in CAPS}
        ablations = {}
        for cap, winner in exact.items():
            ids = winner['selected_ids']
            rr = engine.batch([[j for j in ids if j != remove] for remove in ids], f'ablation_{cap}')
            ablations[cap] = [dict(removed=i, remaining_evaluation_id=r['evaluation_id'],
                delta_ops=r.get('analysis_resolution_steps', 0)-winner['analysis_resolution_steps'],
                delta_conflicts=r.get('conflicts', 0)-winner['conflicts'], status=r['status']) for i, r in zip(ids, rr)]
        result = dict(exact=exact, at_most={str(k): engine.best(k) for k in CAPS},
                      baseline=base, singletons_screened=len(screened), population=len(data['population']),
                      best_singleton=min(singleton_rows, key=objective), ablations=ablations,
                      unique_evaluations=len(engine.cache), statuses=dict(Counter(r['status'] for r in engine.cache.values())),
                      current_invocation_wall_seconds=perf_counter()-started,
                      initial_cached_evaluations=engine.initial_evaluations,
                      sum_screen_process_seconds=sum(r['screen_process_seconds'] for r in engine.cache.values()),
                      globally_optimal=False)
        (directory/'discovery.json').write_text(json.dumps(result, indent=2))
        print(json.dumps({k: result[k] for k in ('unique_evaluations', 'current_invocation_wall_seconds', 'statuses')}), flush=True)
    finally:
        engine.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=DIRECTORY)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    data = prepare()
    print(json.dumps(data['exclusions']), flush=True)
    discovery(data, args.output, args.workers)


if __name__ == '__main__':
    main()
