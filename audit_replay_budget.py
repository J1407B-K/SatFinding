"""Read-only artifact audit, independently deriving all top-K selections."""
import json
from pathlib import Path

from evaluation_oracle_run import sha
from homologous_template_run import load_history
from replay_budget import BUDGETS, HistoryIndex
from replay_budget_run import aggregate, digest
from satcache import check, normalize


def main():
    directory = Path('results/replay_budget')
    metadata = json.loads((directory/'metadata.json').read_text())
    raw = [json.loads(line) for line in (directory/'raw.jsonl').read_text().splitlines()]
    for path, expected in metadata['source_files'].items():
        assert sha(path) == expected, path
    for item in metadata['build']['binaries'].values():
        assert sha(item['path']) == item['sha256']
    indexes = {}
    for name, item in metadata['offline'].items():
        assert sha(item['path']) == item['sha256']
        history, _ = load_history(item['path'])
        assert check(history.premises, history)
        indexes[name] = HistoryIndex(history, metadata['random_seeds'])
    expected_configurations = {('BLIND', '0'), ('LEGACY_FULL', 'ALL')}
    for cap in BUDGETS[1:]:
        expected_configurations.update((route, str(cap)) for route in
            ['HISTORY', 'TEMPLATE']+[f'RANDOM_{s}' for s in metadata['random_seeds']])
    checked_selections = 0
    for target, item in metadata['targets'].items():
        assert sha(item['path']) == item['sha256']
        cnf = normalize(json.loads(Path(item['path']).read_text())['cnf'])
        rows = [r for r in raw if r['target'] == target]
        for rep in range(metadata['repeats']):
            rr = [r for r in rows if r['repetition'] == rep]
            assert len(rr) == len(expected_configurations)
            assert {(r['route'], str(r['budget'])) for r in rr} == expected_configurations
        selections = {}
        for row in rows:
            assert sha(row['input_path']) == row['input_sha256']
            if 'proof_sha256' in row:
                assert sha(row['proof_path']) == row['proof_sha256']
            assert row['total_wall_seconds'] >= row['replay_and_check_seconds'] + row['process_seconds']
            if row['route'] in ('BLIND', 'LEGACY_FULL'):
                continue
            source = 'TEMPLATE' if row['route'] == 'TEMPLATE' else 'HISTORY'
            order = row['route'].lower() if row['route'].startswith('RANDOM_') else 'ranked'
            key = (row['route'], str(row['budget']))
            ids = json.loads(Path(row['selection_path']).read_text())
            assert digest(ids) == row['selection_sha256']
            if key not in selections:
                expected, stats = indexes[source].select(cnf, row['budget'], order)
                assert ids == expected
                if isinstance(row['budget'], int):
                    assert len(ids) <= row['budget']
                selections[key] = ids
                checked_selections += 1
                # Independent injection-file check: target clauses followed only
                # by selected outputs, with no proof support accidentally added.
                lines = Path(row['input_path']).read_text().splitlines()
                clauses = [tuple(map(int, line.split()[:-1])) for line in lines[1:]]
                lemmas = [indexes[source].clauses[i] for i in ids]
                assert clauses == list(cnf) + lemmas
                assert digest(lemmas) == row['lemma_sha256']
            assert len(ids) == row['selected_lemmas']
            assert row['checker'] == 'PASS'
        for route in ['HISTORY', 'TEMPLATE']+[f'RANDOM_{s}' for s in metadata['random_seeds']]:
            previous = set()
            for cap in BUDGETS[1:]:
                current = set(selections[(route, str(cap))])
                assert previous <= current
                previous = current
        full = [r for r in rows if r['budget'] == 'ALL' and r['route'] != 'TEMPLATE']
        assert len({(r['lemma_sha256'], r['analysis_resolution_steps'], r['conflicts']) for r in full}) == 1
    assert aggregate(raw) == json.loads((directory/'summary.json').read_text())
    assert all(r['deterministic_search'] for r in aggregate(raw))
    report = dict(status='PASS', rows=len(raw), independently_checked_selections=checked_selections,
                  nested_unique_budgets=True, all_matches_legacy=True, provenance_hashes=True,
                  input_and_proof_hashes=True, exact_output_injection=True,
                  completion_checker='SOLVER_REPORTED_ONLY')
    (directory/'artifact_audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
