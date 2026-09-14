"""Independent saved-artifact audit; never imports transfer or search producers."""
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path

from satcache import Certificate, Step, check, normalize
from proofmodule import ProofContext, ProofModule
from audit_round4 import cert, check_hashes, reachable


def initial_closure(cnf, history):
    nodes = list(history.premises)+[s.clause for s in history.steps]
    available = set(cnf)
    uses = defaultdict(list)
    for i, s in enumerate(history.steps):
        uses[nodes[s.left]].append(i)
        uses[nodes[s.right]].append(i)
    pending = deque(range(len(history.steps)))
    while pending:
        i = pending.popleft()
        s = history.steps[i]
        if s.clause not in available and nodes[s.left] in available and nodes[s.right] in available:
            available.add(s.clause)
            pending.extend(uses[s.clause])
    return available


def audit_sessions(row, cnf, history=None):
    full = cert(row['full_certificate'])
    assert full.premises == cnf
    global_nodes = list(full.premises)+[s.clause for s in full.steps]
    assert ProofContext(cnf).check(ProofModule((), (), full.premises, global_nodes[-1], full.steps)) is not None
    total_attempts, literal_visits = 0, 0
    outcomes = dict(new=0, duplicate=0, tautology=0)
    merged, touched = set(), set()
    for session in row['sessions']:
        before = session.get('global_nodes_before', len(cnf))
        initial = session['initial_global_ids']
        assert all(type(i) is int and 0 <= i < before for i in initial)
        assert before <= len(global_nodes)
        assert session['start_attempts'] == total_attempts
        local_nodes = [global_nodes[i] for i in initial]
        local_index = {c: i for i, c in enumerate(local_nodes)}
        local_to_global = list(initial)
        global_index = {c: i for i, c in enumerate(global_nodes[:before])}
        next_global = before
        steps = []
        for left, right, pivot, outcome, result in session['trace']:
            assert 0 <= left < len(local_nodes) and 0 <= right < len(local_nodes)
            a, b = local_nodes[left], local_nodes[right]
            assert pivot in a and -pivot in b
            literal_visits += len(a)+len(b)
            total_attempts += 1
            touched.update((local_to_global[left], local_to_global[right]))
            c = tuple(sorted((set(a)-{pivot}) | (set(b)-{-pivot})))
            if any(-x in c for x in c):
                assert outcome == 'tautology' and result is None
            elif c in local_index:
                assert outcome == 'duplicate' and result == local_index[c]
            else:
                assert outcome == 'new' and result == len(local_nodes)
                local_index[c] = result
                local_nodes.append(c)
                steps.append(Step(left, right, pivot, c))
                if c not in global_index:
                    assert next_global < len(global_nodes) and global_nodes[next_global] == c
                    expected = Step(local_to_global[left], local_to_global[right], pivot, c)
                    assert full.steps[next_global-len(cnf)] == expected
                    global_index[c] = next_global
                    merged.add(next_global)
                    next_global += 1
                local_to_global.append(global_index[c])
            outcomes[outcome] += 1
        recorded = [Step(s['left'], s['right'], s['pivot'], tuple(s['clause'])) for s in session['new_steps']]
        assert steps == recorded
        assert session['end_attempts'] == total_attempts
        if row['route'] == 'ORACLE_HISTORY':
            assert len(session['trace']) <= 2000
    assert row['budget']['attempts'] == total_attempts <= row['budget']['limit'] == 400000
    assert row['budget']['literal_visits'] == literal_visits
    assert row['budget']['outcomes'] == outcomes
    assert row['new_generated_nodes_all'] == outcomes['new']
    replayed = set()
    if history is not None:
        hnodes = list(history.premises)+[s.clause for s in history.steps]
        allowed = {(hnodes[s.left], hnodes[s.right], s.pivot, s.clause) for s in history.steps}
        h = row['history']
        replayed = set(h['replay_global_ids'])
        assert len(replayed) == len(h['replay_global_ids'])
        for i in replayed:
            s = full.steps[i-len(cnf)]
            assert (global_nodes[s.left], global_nodes[s.right], s.pivot, s.clause) in allowed
        first_before = row['sessions'][0]['global_nodes_before'] if row['sessions'] else len(global_nodes)
        assert first_before-len(cnf) == h['initial_direct_inferences']
        available = initial_closure(cnf, history)
        assert h['initial_present_leaves'] == sum(c in set(cnf) for c in history.premises)
        assert h['initial_missing_leaves'] == len(history.premises)-h['initial_present_leaves']
        assert h['initial_broken_inferences'] == sum(s.clause not in available for s in history.steps)
        assert h['replay_after_repair'] == len(replayed)-h['initial_direct_inferences']
        assert h['repair_attempts'] == len(row['sessions'])
        assert h['repair_successes'] == sum(tuple(s['target']) in {
            global_nodes[i] for i in s['initial_global_ids']} | {tuple(step['clause']) for step in s['new_steps']}
            for s in row['sessions'])
    assert not (merged & replayed)
    assert merged | replayed == set(range(len(cnf), len(global_nodes)))
    # Traverse all search operands once; account for their input ancestors.
    seen, pending = set(), list(touched)
    while pending:
        i = pending.pop()
        if i in seen:
            continue
        seen.add(i)
        if i >= len(cnf):
            s = full.steps[i-len(cnf)]
            pending.extend((s.left, s.right))
    if row['status'] == 'UNSAT':
        assert check(cnf, cert(row['certificate'])) and row['checker'] == 'PASS'
    else:
        assert row['certificate'] is None and () not in global_nodes
    assert row['attempts_saved'] is None and row['comparison_censored']
    return dict(attempts=total_attempts, new_generated_nodes_all=outcomes['new'],
                unique_new_nodes=len(merged), checked_nodes=len(global_nodes),
                search_touched_input_clauses=sum(i < len(cnf) for i in seen),
                current_cnf_clauses=len(cnf))


def audit_screen(directory):
    manifest = json.loads((directory/'screen.json').read_text())
    assert manifest['complete']
    check_hashes(manifest['sources'])
    assert len(manifest['cases']) == 2*len(manifest['pairs'])
    cases = {}
    import networkx as nx
    for case in manifest['cases']:
        check_hashes({case['path']: case['sha256']})
        data = json.loads(Path(case['path']).read_text())
        n, degree = data['vertices'], data['degree']
        graph = nx.random_regular_graph(degree, n, seed=data['seed'])
        assert sorted(tuple(sorted(e)) for e in graph.edges()) == list(map(tuple, data['edges']))
        cnf = []
        for v in range(n):
            cs = [3*v+c+1 for c in range(3)]
            cnf.append(cs)
            cnf.extend([[-cs[a], -cs[b]] for a in range(3) for b in range(a+1, 3)])
        for u, v in data['edges']:
            cnf.extend([[-(3*u+c+1), -(3*v+c+1)] for c in range(3)])
        assert normalize(cnf) == normalize(data['cnf'])
        for result in case['methods'].values():
            if result.get('assignment') is not None:
                assert check(normalize(cnf), Certificate('SAT', assignment={int(k): v for k, v in result['assignment'].items()}))
            if 'drup_path' in result:
                check_hashes({result['drup_path']: result['drup_sha256']})
        cases[case['key']] = (case, data)
    for n, hs, ts in manifest['pairs']:
        h = set(map(tuple, cases[f'n{n}_H_s{hs}'][1]['cnf']))
        t = set(map(tuple, cases[f'n{n}_T_s{ts}'][1]['cnf']))
        assert not h <= t and not t <= h
    return cases


def main():
    first = audit_screen(Path('results/oracle_transfer'))
    directory = Path('results/oracle_transfer_6regular')
    cases = audit_screen(directory)
    transfer = json.loads((directory/'transfer.json').read_text())
    check_hashes(transfer['sources'])
    assert Counter((r['target_key'], r['route']) for r in transfer['rows']) == Counter(
        (f'n{n}_T_s{ts}', route) for n, ts in ((120,6201), (200,6203)) for route in ('BLIND','ORACLE_HISTORY'))
    assert len(transfer['excluded']) == 1 and transfer['excluded'][0]['pair'][0] == 'n320_H_s6204'
    report = dict(status='PASS', conclusion='EXPERIMENT_INCONCLUSIVE',
                  oracle_optimality_proven=False, proof_search_savings_measured=False,
                  screened_inputs=len(first)+len(cases), rows=[], historical_proofs=[],
                  scope='supplied identity alignment; bounded local repair; resource-censored enumerative kernel',
                  sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                           for p in ('audit_oracle_transfer.py','satcache.py','proofmodule.py')})
    proofs = {}
    for n, seed in ((120,6200),(200,6202)):
        key = f'n{n}_H_s{seed}'
        path = directory/f'{key}.resolution.json.gz'
        with gzip.open(path, 'rt') as f:
            payload = json.load(f)
        check_hashes(payload['sources'])
        assert payload['cnf_sha256'] == cases[key][0]['sha256']
        check_hashes({cases[key][0]['methods']['PROOF']['drup_path']: payload['drup_sha256']})
        proof = cert(payload['proof'])
        assert check(normalize(cases[key][1]['cnf']), proof)
        assert len(reachable(proof, len(proof.premises)+len(proof.steps)-1)) == len(proof.premises)+len(proof.steps)
        proofs[key] = proof
        report['historical_proofs'].append(dict(key=key, leaves=len(proof.premises),
            inferences=len(proof.steps), checker='PASS', artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for summary in transfer['rows']:
        check_hashes({summary['path']: summary['sha256']})
        with gzip.open(summary['path'], 'rt') as f:
            row = json.load(f)
        assert summary['attempts'] == row['budget']['attempts']
        assert summary['history'] == row['history']
        assert summary['status'] == row['status'] and summary['route'] == row['route']
        assert row['target_sha256'] == cases[row['target_key']][0]['sha256']
        assert row['historical_proof_sha256'] == next(p['artifact_sha256'] for p in report['historical_proofs'] if p['key']==row['historical_key'])
        metric = audit_sessions(row, normalize(cases[row['target_key']][1]['cnf']),
                                proofs[row['historical_key']] if row['route']=='ORACLE_HISTORY' else None)
        metric.update(target_key=row['target_key'], route=row['route'], status=row['status'],
                      stop_reason=row['stop_reason'], history=row['history'],
                      raw_artifact_bytes=Path(summary['path']).stat().st_size)
        report['rows'].append(metric)
    (directory/'audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(status='PASS', conclusion=report['conclusion'], rows=len(report['rows']),
                          audited_search_attempts=sum(r['attempts'] for r in report['rows']),
                          savings=None, oracle_optimality_proven=False)))


if __name__ == '__main__':
    main()
