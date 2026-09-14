"""Audit saved Round 4 gate data without importing search/generator code.

    Proof validity uses the existing simple checker. Search-attempt accounting
    is reconstructed independently, event by event, including discarded work.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import statistics

from satcache import Certificate, Step, check, normalize, transfer
from proofmodule import ProofContext, ProofModule


def cert(raw):
    return Certificate(raw['kind'], premises=tuple(map(tuple, raw['premises'])),
                       steps=tuple(Step(s['left'], s['right'], s['pivot'], tuple(s['clause']))
                                   for s in raw['steps']))


def module(proof, target):
    return ProofModule((), (), proof.premises, target, proof.steps)


def reachable(proof, root):
    pending, seen = [root], set()
    while pending:
        i = pending.pop()
        if i in seen:
            continue
        seen.add(i)
        if i >= len(proof.premises):
            s = proof.steps[i-len(proof.premises)]
            assert 0 <= s.left < i and 0 <= s.right < i
            pending.extend((s.left, s.right))
    return seen


def audit_trace(record):
    proof = cert(record['full_certificate'])
    nodes = list(proof.premises)
    index = {c: i for i, c in enumerate(nodes)}
    outcomes = dict(new=0, duplicate=0, tautology=0)
    steps, visits, touched = [], 0, set()
    for left, right, pivot, outcome, result in record['trace']:
        assert type(left) is int and type(right) is int and type(pivot) is int and pivot
        assert 0 <= left < len(nodes) and 0 <= right < len(nodes)
        a, b = nodes[left], nodes[right]
        assert pivot in a and -pivot in b
        visits += len(a)+len(b)
        touched.update((left, right))
        derived = tuple(sorted((set(a)-{pivot}) | (set(b)-{-pivot})))
        if any(-x in derived for x in derived):
            assert outcome == 'tautology' and result is None
        elif derived in index:
            assert outcome == 'duplicate' and result == index[derived]
        else:
            assert outcome == 'new' and result == len(nodes)
            index[derived] = result
            nodes.append(derived)
            steps.append(Step(left, right, pivot, derived))
        outcomes[outcome] += 1
    budget = record['budget']
    assert 0 <= budget['attempts'] == len(record['trace']) <= budget['limit']
    assert outcomes == budget['outcomes'] and visits == budget['literal_visits']
    assert tuple(steps) == proof.steps
    assert ProofContext(proof.premises).check(module(proof, nodes[-1])) is not None
    # Count all root clauses contributing to search operands, not just final proof.
    support = set()
    for i in touched:
        support.update(j for j in reachable(proof, i) if j < len(proof.premises))
    return dict(attempts=budget['attempts'], generated_nodes=len(steps),
                search_touched_input_clauses=len(support))


def check_hashes(sources):
    for path, digest in sources.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path


def append_proof(proof, nodes, steps):
    """Evaluation-only witness composition; never a measured search route."""
    index = {c: i for i, c in enumerate(nodes)}
    mapped = [index[c] for c in proof.premises]
    for s in proof.steps:
        new = Step(mapped[s.left], mapped[s.right], s.pivot, s.clause)
        mapped.append(len(nodes))
        nodes.append(s.clause)
        steps.append(new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', default='results/round4_dev')
    args = ap.parse_args()
    directory = Path(args.directory)
    manifest = json.loads((directory/'private_manifest.json').read_text())
    metadata = json.loads((directory/'gate_metadata.json').read_text())
    assert hashlib.sha256((directory/'private_manifest.json').read_bytes()).hexdigest() == metadata['manifest_sha256']
    assert hashlib.sha256((directory/'gate_raw.jsonl').read_bytes()).hexdigest() == metadata['raw_sha256']
    check_hashes(manifest['sources'])
    check_hashes(metadata['sources'])
    schema = json.loads(Path('round4_schema.json').read_text())
    cases = {c['case_id']: c for c in manifest['cases']}
    assert len(cases) == len(manifest['cases'])
    assert len(manifest['seeds']) == len(set(manifest['seeds']))
    expected_levels = set(schema['levels']) | {'SAT_CONTROL'}
    assert Counter((c['seed'], c['level']) for c in cases.values()) == Counter(
        (s, l) for s in manifest['seeds'] for l in expected_levels)
    histories = {}
    for info in manifest['histories']:
        check_hashes({info['path']: info['sha256']})
        h = json.loads(Path(info['path']).read_text())
        audit_trace(h['search'])
        assert h['generation_search_attempts'] >= h['search']['budget']['attempts']
        full, sliced = cert(h['search']['full_certificate']), cert(h['raw_proof'])
        assert check(normalize(h['raw_cnf']), full) and check(normalize(h['raw_cnf']), sliced)
        nodes = list(full.premises)+[s.clause for s in full.steps]
        keep = sorted(reachable(full, nodes.index(())))
        assert keep == h['slice_old_ids']
        remap = {old: new for new, old in enumerate(keep)}
        expected_premises = tuple(nodes[i] for i in keep if i < len(full.premises))
        expected_steps = []
        for i in keep:
            if i >= len(full.premises):
                s = full.steps[i-len(full.premises)]
                expected_steps.append(Step(remap[s.left], remap[s.right], s.pivot, s.clause))
        assert sliced.premises == expected_premises and sliced.steps == tuple(expected_steps)
        histories[h['seed']] = h
    positives, controls, witnessed_repairs = set(), set(), 0
    cnfs, historical_sizes, breakages = {}, {}, []
    evaluation_certificates = {}
    for key, c in cases.items():
        check_hashes({c['path']: c['sha256']})
        public = json.loads(Path(c['path']).read_text())
        assert set(public) == {'version', 'historical_cnf', 'historical_proof', 'cnf'}
        cnf = normalize(public['cnf'])
        cnfs[key] = cnf
        p = cert(public['historical_proof'])
        assert check(normalize(public['historical_cnf']), p)
        historical_sizes[c['seed']] = dict(leaves=len(p.premises), inferences=len(p.steps))
        if c['level'] == 'SAT_CONTROL':
            controls.add(key)
            assignment = {int(k): v for k, v in c['model'].items()}
            assert check(cnf, Certificate('SAT', assignment=assignment))
            continue
        positives.add(key)
        truth = {int(k): v for k, v in c['mapping'].items()}
        target_map = {int(k): v for k, v in c['target_map'].items()}
        assert len({abs(v) for v in truth.values()}) == len(truth)
        raw_target = normalize(c['raw_target'])
        assert normalize(transfer(Certificate('UNSAT', premises=raw_target), target_map).premises) == cnf
        target_p = transfer(p, truth)
        raw_p = cert(histories[c['seed']]['raw_proof'])
        assert target_p == transfer(raw_p, target_map)
        raw_h = normalize(histories[c['seed']]['raw_cnf'])
        if c['level'] == 'L0':
            assert raw_target == raw_h
            assert set(target_p.premises) <= set(cnf)
        else:
            assert not set(raw_h) <= set(raw_target) and not set(raw_target) <= set(raw_h)
        rate = {'L0': 0, 'L1': 0, 'L2_05': .05, 'L2_15': .15}[c['level']]
        assert c['requested_broken_fraction'] == rate
        expected_broken = math.ceil(rate*len(p.premises))
        missing = set(target_p.premises) - set(cnf)
        assert len(missing) == c['broken_leaves'] == expected_broken
        assert c['actual_broken_fraction'] == expected_broken/len(p.premises)
        assert len(c['replacement_witnesses']) == expected_broken
        assert set(map(tuple, c['broken'])) == {tuple(w['target']) for w in c['replacement_witnesses']}
        breakages.append(dict(seed=c['seed'], level=c['level'], broken=expected_broken,
                              leaves=len(p.premises), actual_fraction=c['actual_broken_fraction']))
        nodes, steps = list(cnf), []
        for w in c['replacement_witnesses']:
            region, wp = normalize(w['region']), cert(w['proof'])
            target = tuple(w['target'])
            assert target not in region and len(wp.steps) <= manifest['config']['replacement_max_steps']
            assert ProofContext(region).check(module(wp, target)) is not None
            assert check(region, Certificate('SAT', assignment={int(k): v for k, v in w['model'].items()}))
            mapped_wp = transfer(wp, target_map)
            assert set(mapped_wp.premises) <= set(cnf)
            append_proof(mapped_wp, nodes, steps)
            witnessed_repairs += 1
        append_proof(target_p, nodes, steps)
        complete = Certificate('UNSAT', premises=cnf, steps=tuple(steps))
        assert check(cnf, complete)
        evaluation_certificates[key] = asdict(complete)
    for seed in manifest['seeds']:
        by_level = {c['level']: c for c in cases.values() if c['seed'] == seed}
        assert set(map(tuple, by_level['L2_05']['broken'])) <= set(map(tuple, by_level['L2_15']['broken']))
    rows = [json.loads(line) for line in (directory/'gate_raw.jsonl').read_text().splitlines()]
    keys = [(r['case_id'], r['method']) for r in rows]
    assert len(keys) == len(set(keys))
    assert set(keys) == {(key, method) for key in cases for method in schema['gate_methods']}
    checked, metrics = 0, []
    for row in rows:
        assert set(schema['gate_required_fields']) <= set(row)
        cnf = cnfs[row['case_id']]
        request = json.dumps(dict(cnf=cnf), separators=(',', ':'))
        assert hashlib.sha256(request.encode()).hexdigest() == row['input_sha256']
        if row['method'] in ('UP', 'BVE') and row['status'] not in ('TIMEOUT', 'ERROR'):
            assert set(schema['gate_resolution_fields']) <= set(row)
            assert row['budget']['limit'] == metadata['worker_budget']
            metric = audit_trace(row)
            assert cert(row['full_certificate']).premises == cnf
            if row['status'] == 'UNSAT':
                assert row['case_id'] in positives and row['checker'] == 'PASS'
                sliced = cert(row['certificate'])
                assert check(cnf, sliced)
                assert len(reachable(sliced, len(sliced.premises)+len(sliced.steps)-1)) == len(sliced.premises)+len(sliced.steps)
                checked += 1
                metric.update(certificate_input_clauses=len(sliced.premises),
                              certificate_inferences=len(sliced.steps),
                              certificate_bytes=len(json.dumps(row['certificate']).encode()))
            else:
                assert row['status'] == 'MISS' and row['certificate'] is None
                assert () not in cert(row['full_certificate']).premises
                assert all(s.clause != () for s in cert(row['full_certificate']).steps)
            metric.update(case_id=row['case_id'], method=row['method'], total_clauses=len(cnf),
                          search_touched_ratio=metric['search_touched_input_clauses']/len(cnf))
            metrics.append(metric)
        if row['case_id'] in controls:
            assert row['status'] != 'UNSAT'
        if row.get('assignment') is not None:
            assert check(cnf, Certificate('SAT', assignment={int(k): v for k, v in row['assignment'].items()}))
    bve = [r for r in rows if r['case_id'] in positives and r['method'] == 'BVE']
    cadical = [r for r in rows if r['case_id'] in positives and r['method'] == 'CADICAL_PREPROCESS']
    cheap_bve = all(r['status'] == 'UNSAT' and r['budget']['attempts'] <= 1000 for r in bve)
    cheap_cadical = all(r['status'] == 'UNSAT' and r['end_to_end_seconds'] <= .1 for r in cadical)
    stopped = cheap_bve or cheap_cadical
    result = dict(status='PASS', decision='STOP_FAMILY_NEGATIVE' if stopped else 'GATE_SURVIVED',
                  positive_cases=len(positives), sat_controls=len(controls), rows=len(rows),
                  historical_proofs=len(histories), checked_shortcut_refutations=checked,
                  evaluation_only_composed_refutations=len(evaluation_certificates),
                  checked_replacement_witnesses=witnessed_repairs, historical_sizes=historical_sizes,
                  breakages=breakages, search_accounting=metrics,
                  formal_routes_executed=False, new_search_attempts_saved=None,
                  reason='CNF-only ordinary preprocessing meets frozen rejection threshold' if stopped else None,
                  audit_sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                 for p in ('audit_round4.py', 'satcache.py', 'proofmodule.py')})
    (directory/'audit.json').write_text(json.dumps(result, indent=2))
    (directory/'evaluation_only_refutations.json').write_text(json.dumps(evaluation_certificates))
    lines = ['# Round 4 development gate: '+result['decision'], '',
             'This is a benchmark-family rejection, not a measured history-versus-BLIND comparison.', '',
             '| Method | Positive UNSAT | Median worker ms | Max worker ms | Median process ms |',
             '|---|---:|---:|---:|---:|']
    for method in schema['gate_methods']:
        subset = [r for r in rows if r['case_id'] in positives and r['method'] == method]
        times = [r['end_to_end_seconds']*1000 for r in subset if 'end_to_end_seconds' in r]
        lines.append(f'| {method} | {sum(r["status"]=="UNSAT" for r in subset)}/{len(subset)} | '
                     f'{statistics.median(times):.3f} | {max(times):.3f} | '
                     f'{statistics.median(r["process_seconds"]*1000 for r in subset):.3f} |')
    lines += ['', 'CaDiCaL UNSAT is solver-reported, not a Resolution checker PASS. '
              'Every positive input has a separate evaluation-only composed Resolution refutation. '
              'UP/BVE certificates and every recorded Resolution attempt were independently re-audited.', '',
              '## Per-input search attempts (shortcut work, not history savings)', '',
              '| Seed | Level | Clauses | Broken/leaves | UP attempts | BVE attempts | BVE result |',
              '|---|---|---:|---:|---:|---:|---|']
    for c in manifest['cases']:
        if c['case_id'] not in positives:
            continue
        rs = {r['method']: r for r in rows if r['case_id'] == c['case_id']}
        lines.append(f'| {c["seed"]} | {c["level"]} | {len(cnfs[c["case_id"]])} | '
                     f'{c["broken_leaves"]}/{c["historical_leaves"]} | {rs["UP"]["budget"]["attempts"]} | '
                     f'{rs["BVE"]["budget"]["attempts"]} | {rs["BVE"]["status"]} |')
    lines += ['', '## Interpretation and stop boundary', '',
              'Four independent development supports, four levels each, plus four SAT controls. '
              'All seeds and cases retained. L2 rates are rounded upward because supports are small; '
              'they are requested 5%/15%, not exact achieved fractions. Same-support levels are paired '
              'measurements, not independent samples. No formal seeds were run.', '',
              'The family remains a small-variable random core with independently sampled context and '
              'small replacement regions. Removing a fixed splitting template did not establish a '
              'useful proof-search barrier: ordinary CNF preprocessing already resolves the target. '
              'No larger instances, changed baseline limits, or selective removals were used after this outcome.', '',
              'Ancestor slicing, resumable indexed Resolution, a shareable global Budget, generator, '
              'field registry, CNF-only shortcut workers and independent gate audit are implemented. '
              'Partial mapping/replay, SUPPORT-ONLY, and the formal five-route runner are NOT implemented '
              'or measured because the family reached its preregistered stop condition. '
              'New Resolution search attempts saved is NOT MEASURED (null). '
              'Do not interpret the gate as demonstrating that history and BLIND are equal.', '',
              'Audit independence means independent from producer/search control flow; the logical '
              'checker implementation is reused. Generator-wide rejected-region search totals are '
              'recorded counters; detailed replay auditing covers the successful historical search, '
              'replacement certificates, and all UP/BVE traces, not discarded generator trials.', '',
              'Reproduce: `.venv/bin/python round4_generate.py`, '
              '`.venv/bin/python round4_gate.py`, `.venv/bin/python audit_round4.py`. '
              'The generator is deterministic; timing measurements are not. '
              'Protocol: `docs/round4-protocol.md`; fields: `round4_schema.json`.']
    (directory/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'decision', 'positive_cases', 'sat_controls',
          'rows', 'checked_shortcut_refutations', 'checked_replacement_witnesses', 'new_search_attempts_saved')}))


if __name__ == '__main__':
    main()
