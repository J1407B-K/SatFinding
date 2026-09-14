"""Reproducible budget curve, with raw repetitions and no best-color oracle."""
import argparse
import csv
import gc
import hashlib
import json
from pathlib import Path
import random
from statistics import median
from time import perf_counter

import homologous_template_run as backend
from evaluation_oracle_run import replay as legacy_replay, sha
from replay_budget import BUDGETS, HistoryIndex
from satcache import check, normalize


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def aggregate(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row['target'], row['route'], str(row['budget'])), []).append(row)
    result = []
    for (target, route, budget), group in groups.items():
        out = dict(target=target, route=route, budget=budget, repetitions=len(group),
                   statuses=','.join(sorted({r['status'] for r in group})))
        for key in ('selected_lemmas', 'eligible_lemmas', 'support_inferences', 'support_leaves',
                    'support_literal_work', 'selection_seconds', 'materialize_seconds', 'checker_seconds',
                    'replay_and_check_seconds', 'seconds', 'process_seconds', 'total_wall_seconds',
                    'analysis_resolution_steps', 'conflicts', 'decisions', 'propagations'):
            values = [r[key] for r in group if key in r]
            if values:
                out[key] = median(values)
        out['wall_min_seconds'] = min(r['total_wall_seconds'] for r in group)
        out['wall_max_seconds'] = max(r['total_wall_seconds'] for r in group)
        out['deterministic_search'] = len({(r.get('analysis_resolution_steps'), r.get('conflicts'))
                                         for r in group}) == 1
        result.append(out)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--targets', default='n200_r01,n200_r05,n200_independent')
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--random-seeds', default='17,29,43')
    ap.add_argument('--output', type=Path, default=Path('results/replay_budget'))
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error('--repeats must be positive')
    seeds = [int(s) for s in args.random_seeds.split(',')]
    args.output.mkdir(parents=True, exist_ok=True)
    backend.DIRECTORY = args.output / 'artifacts'
    backend.DIRECTORY.mkdir(exist_ok=True)
    old = json.loads(Path('results/homologous_template/results.json').read_text())
    targets = {r['key']: r['target']['path'] for r in old['homologous']}
    sources = {'HISTORY': 'results/oracle_transfer_6regular/n200_H_s6202.resolution.json.gz',
               'TEMPLATE': 'results/homologous_template/n200_U_s6302.resolution.json.gz'}
    metadata = dict(protocol='docs/replay-budget-protocol.md', mapping='identity vertices and colors; fixed before run',
                    budgets=BUDGETS, random_seeds=seeds, repeats=args.repeats,
                    source_only_score='(1 + direct historical uses) / ((1 + clause width) * (1 + left width + right width))',
                    completion_checker='SOLVER_REPORTED_ONLY; selected support checked by ProofContext',
                    cold_start_note='Source load, source check and ranking are offline and reported separately. '
                    'Each timed query includes fresh target eligibility, selection, ancestor materialization, '
                    'support check, CNF serialization, solver subprocess and artifact hashing.',
                    raw_drup_lazy_materialization=False,
                    build=json.loads((backend.NATIVE/'build.json').read_text()),
                    source_files={p: sha(p) for p in ('replay_budget.py', 'replay_budget_run.py',
                        'docs/replay-budget-protocol.md', 'homologous_template_run.py',
                        'evaluation_oracle_run.py', 'proofmodule.py', 'satcache.py')}, offline={})
    indexes = {}
    for name, path in sources.items():
        started = perf_counter()
        history, payload = backend.load_history(path)
        loaded = perf_counter()
        if not check(history.premises, history):
            raise ValueError('Invalid source proof')
        checked = perf_counter()
        indexes[name] = HistoryIndex(history, seeds)
        metadata['offline'][name] = dict(path=path, sha256=sha(path),
            load_seconds=loaded-started, source_check_seconds=checked-loaded,
            index_seconds=perf_counter()-checked, inference_nodes=len(history.steps),
            original_conversion_seconds=payload.get('stats', {}).get('conversion_seconds'))
        print(f'indexed {name}: {len(history.steps)} inferences', flush=True)
    metadata['targets'] = {key: dict(path=targets[key], sha256=sha(targets[key]))
                           for key in args.targets.split(',')}
    (args.output/'metadata.json').write_text(json.dumps(metadata, indent=2))
    raw_path = args.output/'raw.jsonl'
    rows = []
    with raw_path.open('w') as raw:
        for key, target in metadata['targets'].items():
            cnf = normalize(json.loads(Path(target['path']).read_text())['cnf'])
            # Untimed process warm-up; no completion outcomes feed the ranking.
            backend.native(cnf, f'{key}_warmup')
            specs = [('BLIND', 0, None, None)]
            for budget in BUDGETS[1:]:
                specs.extend([('HISTORY', budget, 'HISTORY', 'ranked'),
                              ('TEMPLATE', budget, 'TEMPLATE', 'ranked')])
                specs.extend((f'RANDOM_{seed}', budget, 'HISTORY', f'random_{seed}') for seed in seeds)
            specs.append(('LEGACY_FULL', 'ALL', 'HISTORY', 'legacy'))
            for repetition in range(args.repeats):
                schedule = specs.copy()
                random.Random(90100+repetition).shuffle(schedule)
                for route, budget, source, order in schedule:
                    gc.collect()
                    tag = f'{key}_{route}_{budget}_rep{repetition}'
                    started = perf_counter()
                    if route == 'BLIND':
                        lemmas = []
                        stats = dict(selected_lemmas=0, eligible_lemmas=0, support_inferences=0,
                                     support_leaves=0, support_literal_work=0, selection_seconds=0,
                                     materialize_seconds=0, checker_seconds=0, replay_and_check_seconds=0)
                    elif order == 'legacy':
                        proof, lemmas, legacy = legacy_replay(cnf, indexes[source].history,
                                                            list(range(200)), [0, 1, 2])
                        stats = dict(selected_lemmas=len(lemmas), eligible_lemmas=len(lemmas),
                                     support_inferences=len(proof.steps),
                                     replay_and_check_seconds=perf_counter()-started, legacy=legacy)
                        del proof
                    else:
                        proof, lemmas, stats = indexes[source].replay(cnf, budget, order)
                        del proof
                    # Hashing/selection artifact export occurs after timed work.
                    row = backend.native(list(cnf)+lemmas, tag)
                    row['total_wall_seconds'] = perf_counter()-started
                    selected = stats.pop('selected_ids', None)
                    row.update(target=key, route=route, budget=budget, repetition=repetition,
                               **stats, lemma_sha256=digest(lemmas))
                    if selected is not None:
                        selection_path = args.output/f'{key}_{route}_{budget}.selection.json'
                        if repetition == 0:
                            selection_path.write_text(json.dumps(selected))
                        row.update(selection_path=str(selection_path), selection_sha256=digest(selected))
                    raw.write(json.dumps(row)+'\n')
                    raw.flush()
                    rows.append(row)
                    print(f'{key} {route} K={budget} rep={repetition}: '
                          f'{row.get("analysis_resolution_steps")} ops '
                          f'{row["total_wall_seconds"]*1000:.1f} ms '
                          f'support={stats.get("support_inferences")}', flush=True)
    summaries = aggregate(rows)
    # ALL must have identical injected clause order and exact search counters.
    for key in metadata['targets']:
        full = [r for r in rows if r['target'] == key and r['budget'] == 'ALL'
                and r['route'] != 'TEMPLATE']
        assert len({r['lemma_sha256'] for r in full}) == 1
        assert len({(r['status'], r.get('analysis_resolution_steps'), r.get('conflicts')) for r in full}) == 1
    assert all(r['deterministic_search'] for r in summaries)
    (args.output/'summary.json').write_text(json.dumps(summaries, indent=2))
    fields = sorted({k for r in summaries for k in r})
    with (args.output/'summary.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    (args.output/'audit.json').write_text(json.dumps(dict(status='PASS', rows=len(rows),
        all_equals_legacy=True, deterministic_search=True, selected_support_checker='PASS',
        completion_checker='SOLVER_REPORTED_ONLY'), indent=2))


if __name__ == '__main__':
    main()
