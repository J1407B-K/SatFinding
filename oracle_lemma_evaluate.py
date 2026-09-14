"""Sequential final timings and separate completion certification of oracle sets."""
import argparse
import csv
from dataclasses import asdict
import gc
import gzip
import json
from pathlib import Path
import random
from statistics import median
from time import perf_counter

from evaluation_oracle_run import sha
import homologous_template_run as backend
from oracle_lemma import CAPS, DIRECTORY, SEED, TARGET, prepare
from replay_budget_run import digest
from resolution_import import convert
from round4_core import slice_proof
from satcache import Certificate, Step, check


def specifications(data, discovery):
    specs = [dict(route='BLIND', cap=0, template=False, ids=[]),
             dict(route='TEMPLATE', cap=0, template=True, ids=[])]
    for cap in CAPS:
        specs.append(dict(route='RANKED', cap=cap, template=True, ids=sorted(data['ranked'][:cap])))
        for seed in (17, 29, 43):
            order = data['population'].copy()
            random.Random(seed).shuffle(order)
            specs.append(dict(route=f'RANDOM_{seed}', cap=cap, template=True, ids=sorted(order[:cap])))
        specs.extend(dict(route=f'ORACLE_{mode.upper()}', cap=cap, template=True,
                          ids=discovery[mode][str(cap)]['selected_ids']) for mode in ('exact', 'at_most'))
    specs.extend([dict(route='RANKED', cap=2048, template=True, ids=sorted(data['ranked'][:2048])),
                  dict(route='FULL_STRIPPED', cap='ALL', template=True, ids=data['population']),
                  dict(route='BEST_SINGLETON', cap=1, template=True,
                       ids=discovery['best_singleton']['selected_ids'])])
    all_ids, _ = data['h'].select(data['cnf'], 'ALL', 'ranked')
    specs.append(dict(route='UNCONDITIONAL_FULL', cap='ALL', template=False, ids=all_ids))
    return specs


def materialize(data, spec):
    started = perf_counter()
    template_lemmas, history_lemmas, proofs = [], [], []
    template_stats, history_stats = {}, {}
    if spec['template']:
        proof, template_lemmas, template_stats = data['t'].materialize(data['cnf'], data['template_ids'])
        proofs.append(proof)
    if spec['ids']:
        # Derive historical outputs from original target premises, not from
        # treating TEMPLATE or selected historical outputs as unproved axioms.
        proof, history_lemmas, history_stats = data['h'].materialize(data['cnf'], spec['ids'])
        proofs.append(proof)
    result = dict(replay_and_check_seconds=perf_counter()-started,
                  template_replay=template_stats, history_replay=history_stats,
                  template_lemmas=len(template_lemmas), historical_lemmas=len(history_lemmas),
                  support_inferences=sum(s.get('support_inferences', 0) for s in (template_stats, history_stats)),
                  checker='PASS')
    if spec['template'] and set(template_lemmas) & set(history_lemmas):
        raise ValueError('Historical outputs overlap TEMPLATE')
    return list(data['cnf'])+template_lemmas+history_lemmas, proofs, result


def summarize(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r['route'], str(r['cap'])), []).append(r)
    summaries = []
    for (route, cap), rr in groups.items():
        row = dict(route=route, cap=cap, repetitions=len(rr),
                   statuses=','.join(sorted({r['status'] for r in rr})),
                   historical_lemmas=rr[0]['historical_lemmas'], template_lemmas=rr[0]['template_lemmas'],
                   selection_sha256=rr[0]['selection_sha256'])
        for field in ('analysis_resolution_steps', 'conflicts', 'decisions', 'propagations',
                      'minimization_reason_visits', 'binary_minimization_candidates',
                      'seconds', 'process_seconds', 'replay_and_check_seconds', 'total_wall_seconds',
                      'support_inferences'):
            values = [r[field] for r in rr if field in r]
            if values:
                row[field] = median(values)
        row.update(wall_min_seconds=min(r['total_wall_seconds'] for r in rr),
                   wall_max_seconds=max(r['total_wall_seconds'] for r in rr))
        assert len({(r['status'], r.get('analysis_resolution_steps'), r.get('conflicts'), r['input_sha256'])
                    for r in rr}) == 1
        summaries.append(row)
    return summaries


def certify(data, spec, row, output):
    """Join selected supports and an offline reconstructed completion proof."""
    started = perf_counter()
    cnf, proofs, _ = materialize(data, spec)
    with Path(row['proof_path']).open() as f:
        completion, conversion_stats = convert(cnf, f, seconds=120)
    original = data['cnf']
    nodes, steps = list(original), []
    lookup = {c: i for i, c in enumerate(nodes)}
    for proof in proofs+[completion]:
        bindings = [lookup[c] for c in proof.premises]
        for step in proof.steps:
            steps.append(Step(bindings[step.left], bindings[step.right], step.pivot, step.clause))
            bindings.append(len(nodes))
            lookup[step.clause] = len(nodes)
            nodes.append(step.clause)
    full = Certificate('UNSAT', premises=original, steps=tuple(steps))
    if not check(original, full):
        raise ValueError('Combined oracle completion certificate rejected')
    sliced, _ = slice_proof(full)
    if not check(original, sliced):
        raise ValueError('Sliced oracle completion certificate rejected')
    with gzip.open(output, 'wt') as f:
        json.dump(dict(certificate=asdict(sliced), conversion=conversion_stats,
                       input_sha256=row['input_sha256'], selected_ids=spec['ids'],
                       original_target_sha256=sha(TARGET)), f)
    return dict(status='PASS', path=str(output), sha256=sha(output),
                inference_nodes=len(sliced.steps), offline_seconds=perf_counter()-started,
                conversion_seconds=conversion_stats['conversion_seconds'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, default=DIRECTORY)
    ap.add_argument('--repeats', type=int, default=5)
    args = ap.parse_args()
    directory = args.directory
    metadata = json.loads((directory/'metadata.json').read_text())
    for p, expected in metadata['source_files'].items():
        if sha(p) != expected:
            raise ValueError(f'Source changed: {p}')
    discovery = json.loads((directory/'discovery.json').read_text())
    data = prepare()
    specs = specifications(data, discovery)
    (directory/'selections.json').write_text(json.dumps(specs, indent=2))
    backend.DIRECTORY = directory/'artifacts'
    backend.DIRECTORY.mkdir(exist_ok=True)
    backend.native(list(data['cnf'])+data['templates'], 'warmup')
    rows = []
    with (directory/'final_raw.jsonl').open('w') as stream:
        for repetition in range(args.repeats):
            schedule = specs.copy()
            random.Random(SEED+1000+repetition).shuffle(schedule)
            for spec in schedule:
                gc.collect()
                started = perf_counter()
                cnf, proofs, replay = materialize(data, spec)
                tag = f'{spec["route"]}_{spec["cap"]}_rep{repetition}'
                row = backend.native(cnf, tag)
                row.update(total_wall_seconds=perf_counter()-started, **replay,
                           route=spec['route'], cap=spec['cap'], repetition=repetition,
                           selection_sha256=digest(spec['ids']))
                del proofs
                if spec['route'].startswith('ORACLE_') or spec['route'] == 'BEST_SINGLETON':
                    if spec['route'] == 'BEST_SINGLETON':
                        expected = discovery['best_singleton']
                    else:
                        mode = spec['route'][7:].lower()
                        expected = discovery[mode][str(spec['cap'])]
                    assert row['analysis_resolution_steps'] == expected['analysis_resolution_steps']
                    assert row['conflicts'] == expected['conflicts']
                    assert row['input_sha256'] == expected['input_sha256']
                stream.write(json.dumps(row)+'\n')
                stream.flush()
                rows.append(row)
                print(f'{tag}: {row.get("analysis_resolution_steps")} ops, '
                      f'{row["total_wall_seconds"]*1000:.1f} ms; '
                      f'{row["historical_lemmas"]} historical, {row["support_inferences"]} support', flush=True)
    summary = summarize(rows)
    (directory/'summary.json').write_text(json.dumps(summary, indent=2))
    with (directory/'summary.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=sorted({k for r in summary for k in r}))
        writer.writeheader()
        writer.writerows(summary)
    certificates, seen = {}, {}
    for spec in specs:
        if not spec['route'].startswith('ORACLE_'):
            continue
        key = f'{spec["route"]}_{spec["cap"]}'
        selection = tuple(spec['ids'])
        if selection in seen:
            certificates[key] = dict(same_as=seen[selection], status=certificates[seen[selection]]['status'])
            continue
        row = next(r for r in rows if r['route'] == spec['route'] and r['cap'] == spec['cap'])
        try:
            certificates[key] = certify(data, spec, row, directory/f'{key}.certificate.json.gz')
        except (ValueError, TimeoutError, AssertionError) as exc:
            certificates[key] = dict(status='FAIL', error=repr(exc))
        seen[selection] = key
        (directory/'certificates.json').write_text(json.dumps(certificates, indent=2))
        print(f'certificate {key}: {certificates[key]["status"]}', flush=True)
    evaluation = dict(repetitions=args.repeats, rows=len(rows), deterministic_search=True,
                      timing_scope='warm preselected IDs; includes support checks; excludes offline selectors',
                      source_files={p: sha(p) for p in ('oracle_lemma_evaluate.py', 'resolution_import.py',
                                                       'round4_core.py', 'homologous_template_run.py')},
                      discovery_sha256=sha(directory/'discovery.json'),
                      selections_sha256=sha(directory/'selections.json'))
    (directory/'evaluation.json').write_text(json.dumps(evaluation, indent=2))


if __name__ == '__main__':
    main()
