"""Audit conditional selections, marginal measurements, timings and certificates."""
import gzip
import json
from pathlib import Path

from evaluation_oracle_run import sha
from oracle_lemma import CAPS, DIRECTORY, objective, prepare
from oracle_lemma_evaluate import specifications, summarize
from replay_budget_run import digest
from round4_core import decode
from satcache import check


def main():
    directory = DIRECTORY
    metadata = json.loads((directory/'metadata.json').read_text())
    evaluation = json.loads((directory/'evaluation.json').read_text())
    for provenance in (metadata, evaluation):
        for path, expected in provenance['source_files'].items():
            assert sha(path) == expected, path
    assert sha(directory/'discovery.json') == evaluation['discovery_sha256']
    assert sha(directory/'selections.json') == evaluation['selections_sha256']
    discovery = json.loads((directory/'discovery.json').read_text())
    data = prepare()
    assert data['population'] == metadata['population']
    assert data['exclusions'] == metadata['exclusions']
    assert data['template_ids'] == metadata['template_ids']
    allowed = set(data['population'])
    trace = [json.loads(line) for line in (directory/'search.jsonl').read_text().splitlines()]
    assert len(trace) == discovery['unique_evaluations']
    assert len({tuple(r['selected_ids']) for r in trace}) == len(trace)
    by_id = {r['evaluation_id']: r for r in trace}
    for row in trace:
        ids = row['selected_ids']
        assert ids == sorted(set(ids))
        assert set(ids) <= allowed
    for mode in ('exact', 'at_most'):
        for cap in CAPS:
            winner = discovery[mode][str(cap)]
            candidates = [r for r in trace if len(r['selected_ids']) == cap
                          or (mode == 'at_most' and len(r['selected_ids']) <= cap)]
            assert objective(winner) == min(map(objective, candidates))
            assert winner == by_id[winner['evaluation_id']]
    for cap, ablations in discovery['ablations'].items():
        winner = discovery['exact'][cap]
        assert len(ablations) == int(cap)
        for ablation in ablations:
            row = by_id[ablation['remaining_evaluation_id']]
            assert set(row['selected_ids']) == set(winner['selected_ids'])-{ablation['removed']}
            assert ablation['delta_ops'] == row['analysis_resolution_steps']-winner['analysis_resolution_steps']
            assert ablation['delta_conflicts'] == row['conflicts']-winner['conflicts']
    specs = specifications(data, discovery)
    assert specs == json.loads((directory/'selections.json').read_text())
    spec_map = {(s['route'], str(s['cap'])): s for s in specs}
    raw = [json.loads(line) for line in (directory/'final_raw.jsonl').read_text().splitlines()]
    assert len(raw) == len(specs)*evaluation['repetitions']
    for rep in range(evaluation['repetitions']):
        rr = [r for r in raw if r['repetition'] == rep]
        assert {(r['route'], str(r['cap'])) for r in rr} == set(spec_map)
        assert len(rr) == len(specs)
    for row in raw:
        spec = spec_map[(row['route'], str(row['cap']))]
        assert row['selection_sha256'] == digest(spec['ids'])
        assert sha(row['input_path']) == row['input_sha256']
        assert sha(row['proof_path']) == row['proof_sha256']
        clauses = [tuple(map(int, line.split()[:-1]))
                   for line in Path(row['input_path']).read_text().splitlines()[1:]]
        expected = list(data['cnf'])+(data['templates'] if spec['template'] else [])
        expected += [data['h'].clauses[i] for i in spec['ids']]
        assert clauses == expected
        assert row['historical_lemmas'] == len(spec['ids'])
        assert row['template_lemmas'] == (67 if spec['template'] else 0)
        assert row['checker'] == 'PASS'
        assert row['total_wall_seconds'] >= row['replay_and_check_seconds']+row['process_seconds']
    assert summarize(raw) == json.loads((directory/'summary.json').read_text())
    certificates = json.loads((directory/'certificates.json').read_text())
    checked = 0
    for name, info in certificates.items():
        assert info['status'] == 'PASS', name
        if 'same_as' in info:
            assert certificates[info['same_as']]['status'] == 'PASS'
            continue
        assert sha(info['path']) == info['sha256']
        with gzip.open(info['path'], 'rt') as f:
            payload = json.load(f)
        assert check(data['cnf'], decode(payload['certificate']))
        checked += 1
    report = dict(status='PASS', discovery_evaluations=len(trace), final_runs=len(raw),
                  final_configurations=len(specs), completion_certificates=checked,
                  stripped_population=len(allowed), exact_injection=True,
                  best_observed_not_global_optimum=True, ablation_marginals=True,
                  deterministic_final_counters=True, sources_and_artifacts=True)
    (directory/'audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
