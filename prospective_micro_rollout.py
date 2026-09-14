"""Frozen prospective CDCL propagation experiments. Never overwrite run artifacts."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

OUT = Path('results/prospective_micro_rollout').resolve()
BUILD = OUT / 'source'
PROTOCOL = OUT / 'frozen_protocol.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, data):
    with Path(p).open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def load(p):
    return json.loads(Path(p).read_text())


def protocol():
    assert sha(PROTOCOL) == (OUT / 'frozen_protocol.sha256').read_text().strip()
    p = load(PROTOCOL)
    for inp in p['inputs'].values():
        assert sha(inp['path']) == inp['sha256']
    assert sha(p['checker']['path']) == p['checker']['sha256']
    return p


def events(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines()] if Path(p).exists() else []


def writecsv(p, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open('x') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in r.items()})


def replace(s, a, b):
    assert s.count(a) == 1, (a, s.count(a))
    return s.replace(a, b)


def build():
    protocol()
    prior = Path('/private/tmp/satfinding-high-leverage-discovery')
    root = BUILD / 'glucose-3.0'
    shutil.copytree(prior / 'glucose-3.0', root)
    for name in ['prospective_micro_rollout.inc', 'prospective_micro_rollout_state.inc']:
        shutil.copy2(name, BUILD / name)
    h = root / 'core/Solver.h'
    s = h.read_text()
    s = replace(s, '    void hc_observe();', '    void hc_observe();\n    void pm_dequeue();\n    void pm_conflict_hook(CRef);\n    void pm_analysis_hook(const vec<Lit>&,int,unsigned);\n    void pm_backtrack_hook();')
    h.write_text(s)
    cc = root / 'core/Solver.cc'
    s = cc.read_text()
    s = replace(s, str(Path('high_leverage_discovery.inc').resolve()), str(BUILD / 'prospective_micro_rollout.inc'))
    for anchor, extra in [
        ("        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.", '\n        pm_dequeue();'),
        ('for(int k = 0;k<wbin.size();k++) {', '\n          pm_watch();'),
        ('for (i = j = (Watcher*)ws, end = i + ws.size();  i != end;){', '\n            pm_watch();'),
        ('\t  conflicts++; conflictC++;conflictsRestarts++;', '\n          pm_conflict_hook(confl);'),
        ('            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);', '\n            pm_analysis_hook(learnt_clause,backtrack_level,nblevels);'),
        ('            cancelUntil(backtrack_level);', '\n            pm_backtrack_hook();'),
        ('            Lit q = c[j];', '\n            pm_visit(var(q));'),
    ]:
        if anchor.startswith('for(') or anchor.startswith('for ('):
            lo, hi = s.index('CRef Solver::propagate()'), s.index('struct reduceDB_lt')
            s = s[:lo] + replace(s[lo:hi], anchor, anchor + extra) + s[hi:]
        elif anchor == '            Lit q = c[j];':
            lo, hi = s.index('void Solver::analyze('), s.index('bool Solver::litRedundant(')
            s = s[:lo] + replace(s[lo:hi], anchor, anchor + extra) + s[hi:]
        else:
            s = replace(s, anchor, anchor + extra)
    cc.write_text(s)
    driver = (prior / 'driver.cc').read_text()
    driver = driver.replace('extern void hc_finish();', 'extern void pm_finish(const char*);')
    driver = driver.replace('Glucose::lbool result;std::string failure;', 'Glucose::lbool result((uint8_t)2);std::string failure;')
    driver = driver.replace('    hc_finish();', '''    if (result == Glucose::lbool((uint8_t)0) && failure.empty()) {
        printf("{\\\"event\\\":\\\"MODEL\\\",\\\"model\\\":[");
        for(int v=0;v<solver.nVars();++v) printf("%s%d",v?",":"",(v+1)*(solver.modelValue(v)==Glucose::lbool((uint8_t)0)?1:-1));
        printf("]}\\n");
    }
    pm_finish(status);''')
    (BUILD / 'driver.cc').write_text(driver)
    cmd = ['c++', '-O3', '-DNDEBUG', '-std=c++11', '-Wno-deprecated', '-I' + str(root), str(BUILD / 'driver.cc'), str(cc), str(root / 'utils/Options.cc'), str(root / 'utils/System.cc'), '-lz', '-o', str(OUT / 'run')]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (OUT / 'build.log').write_text(r.stdout + r.stderr)
    r.check_returncode()
    source_files = [f for f in BUILD.rglob('*') if f.is_file() and f.suffix in ['.cc', '.h', '.inc']]
    dump(OUT / 'build.json', {'command': cmd, 'binary_sha256': sha(OUT / 'run'), 'source_hashes': {str(f.relative_to(OUT)): sha(f) for f in source_files}, 'protocol_sha256': sha(PROTOCOL), 'runner_sha256': sha(__file__)})
    print('BUILD OK', flush=True)


def run_parent(target, d, mode, at=0, start=100, end=700):
    p = protocol()
    b = load(OUT / 'build.json')
    assert sha(OUT / 'run') == b['binary_sha256']
    for f, h in b['source_hashes'].items():
        assert sha(OUT / f) == h
    d.mkdir(parents=True, exist_ok=False)
    inp = str(Path(p['inputs'][target]['path']).resolve())
    cmd = [str(OUT / 'run'), inp, str(d / 'prefix.drup'), '1000000', str(d), str(at)]
    env = dict(os.environ, PM_MODE=mode, PM_START=str(start), PM_END=str(end))
    before = time.monotonic()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    (d / 'parent.stdout.txt').write_text(r.stdout + r.stderr)
    dump(d / 'command.json', {'command': cmd, 'mode': mode, 'start': start, 'end': end, 'returncode': r.returncode, 'wall_seconds': time.monotonic() - before})
    es = events(d / 'states.jsonl')
    assert r.returncode == 0, ('PARENT_FAILURE', d, r.stdout[-1000:], r.stderr[-1000:])
    assert any(e['event'] == 'STOP' for e in es), ('EARLY_PARENT_TERMINATION', d)
    return es


def canonical(c):
    return hashlib.sha256((' '.join(map(str, sorted(c))) + ' 0\n').encode()).hexdigest()


def horizon(d, tag):
    es = events(d / (tag + '.trace.jsonl'))
    h = next((e for e in es if e['event'] == 'HORIZON'), None)
    if h:
        h = dict(h)
        h['conflict_hash'] = canonical(h['conflict_clause'])
        h['learned_hash'] = canonical(h['learned_clause'])
    return es, h


def validate_full(target, d, tag):
    p = protocol()
    out = d / (tag + '.stdout.txt')
    stdout = events(out)
    stats = next((e for e in stdout if 'analysis_resolution_steps' in e), None)
    if stats is None:
        return {'status': 'UNKNOWN_TIMEOUT', 'proof_validation': 'NOT_APPLICABLE'}
    status = stats['status']
    result = {'status': status, 'stats': stats, 'proof_validation': 'NOT_APPLICABLE'}
    proof = d / (tag + '.drup')
    if status == 'UNSAT':
        cmd = [p['checker']['path'], str(Path(p['inputs'][target]['path']).resolve()), str(proof)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        (d / (tag + '.proof_check.txt')).write_text(r.stdout + r.stderr)
        result.update(proof_validation='VERIFIED' if r.returncode == 0 and 's VERIFIED' in r.stdout else 'FAILED', checker_returncode=r.returncode, proof_sha256=sha(proof), checker_command=cmd)
        with gzip.open(d / (tag + '.drup.gz'), 'wb') as f:
            f.write(proof.read_bytes())
    elif status == 'SAT':
        model = next(e['model'] for e in stdout if e.get('event') == 'MODEL')
        signed = set(model)
        assert not any(-x in signed for x in signed)
        clause = []
        n = 0
        for line in Path(p['inputs'][target]['path']).read_text().splitlines():
            if not line.strip() or line[0] in 'cp':
                continue
            for x in map(int, line.split()):
                if x:
                    clause.append(x)
                else:
                    assert any(x in signed for x in clause), ('SAT_MODEL_FAILURE', tag, n)
                    n += 1
                    clause = []
        assert not clause
        result.update(proof_validation='VERIFIED', model=model, clauses_checked=n)
        dump(d / (tag + '.model_check.json'), result)
    elif status != 'UNKNOWN':
        raise RuntimeError(('FULL_SOLVER_HARD_FAILURE', d, tag, stats))
    dump(d / (tag + '.result.json'), result)
    if status in ['SAT', 'UNSAT']:
        assert result['proof_validation'] == 'VERIFIED', ('PROOF_FAILURE', d, tag)
    return result


def state_records(es):
    return [{**e, 'actions': [a for a in es if a['event'] == 'ACTION' and a['bucket'] == e['bucket']]} for e in es if e['event'] == 'STATE']


def compare_horizons(a, b):
    # Timing/resource measurements intentionally excluded from semantic comparison.
    keys = ['conflict_clause', 'learned_clause', 'learned_length', 'lbd', 'backtrack_level', 'backjump', 'analysis_visited', 'retained_assignments', 'pending_literals', 'immediate_potential', 'analysis_ops', 'watcher_visits', 'dequeues']
    assert a and b and all(a[k] == b[k] for k in keys), 'SHADOW_FULL_HORIZON_MISMATCH'


def smoke():
    a = OUT / 'smoke_shadow'
    b = OUT / 'smoke_full'
    run_parent('T10', a, 'smoke_shadow')
    run_parent('T10', b, 'smoke_full')
    smoke_report()


def smoke_report():
    a, b = OUT / 'smoke_shadow', OUT / 'smoke_full'
    sa, sb = events(a / 'states.jsonl'), events(b / 'states.jsonl')
    assert state_records(sa)[0]['state_hash'] == '422271443557180589'
    assert state_records(sa)[0]['actions'] == state_records(sb)[0]['actions']
    old = load('results/fixed_state_action_surface/response_surface_summary.json')
    baseline = old['baseline']
    surface = list(csv.DictReader(Path('results/fixed_state_action_surface/all_action_runs.csv').open()))
    reports = []
    for i in range(6):
        ae, ah = horizon(a, f'C0_SHADOW_{i}')
        be, bh = horizon(b, f'C0_FULL_{i}')
        compare_horizons(ah, bh)
        assert ae[0]['state_hash'] == be[0]['state_hash']
        assert sum(e['event'] == 'EARLY_ENQUEUE' for e in ae) == bool(i)
        result_path = b / f'C0_FULL_{i}.result.json'
        r = load(result_path) if result_path.exists() else validate_full('T10', b, f'C0_FULL_{i}')
        expected = baseline['stats']['analysis_resolution_steps'] if i == 0 else int(next(x for x in surface if x['action_id'] == f'ACTION_{i}')['ops'])
        assert r['stats']['analysis_resolution_steps'] == expected, (i, expected, r)
        reports.append({'action': i, 'ops': expected, 'proof_validation': r['proof_validation'], 'horizon_match': True})
    dump(OUT / 'smoke_validation.json', {'status': 'PASSED', 'known_state_only': True, 'rows': reports})
    print('SMOKE PASSED', flush=True)


def collect():
    assert load(OUT / 'smoke_validation.json')['status'] == 'PASSED'
    p = protocol()
    known = {(r['target'], str(r['pre_state_hash'])) for r in load('results/state_sensitivity_cohort/cohort_summary.json')['rows']}
    def hashes(obj, target):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ['pre_state_hash', 'state_hash']:
                    known.add((target, str(v)))
                else:
                    hashes(v, target)
        elif isinstance(obj, list):
            for x in obj:
                hashes(x, target)
    hashes(load('results/fixed_state_action_surface/frozen_state.json'), 'T10')
    hashes(load('results/multi_state_action_surface/selected_states.json'), 'T8')
    selected, rows = [], []
    for target in p['targets']:
        d = OUT / 'shadow' / target
        es = run_parent(target, d, 'shadow')
        states = state_records(es)
        for state in states:
            assert (target, state['state_hash']) not in known, 'PREVIOUSLY_USED_STATE'
            assert state['bucket'] in p['selection']['development_buckets']
            state.update(target=target, state_id=f'{target}_C{state["bucket"]}', directory=str(d.relative_to(OUT)))
            selected.append(state)
            for exit_record in [e for e in es if e['event'] == 'CHILD_EXIT' and e['bucket'] == state['bucket']]:
                tag = exit_record['tag']
                te, h = horizon(d, tag)
                assert te and te[0]['state_hash'] == state['state_hash'], 'CHILD_STATE_MISMATCH'
                idx = exit_record['action_index']
                assert sum(e['event'] == 'EARLY_ENQUEUE' for e in te) == bool(idx)
                rows.append({'target': target, 'state_id': state['state_id'], 'bucket': state['bucket'], 'action_index': idx, 'tag': tag, 'status': 'COMPLETE' if h else 'UNKNOWN', **(h or {}), **{k: v for k, v in exit_record.items() if k != 'event'}})
        print('SHADOW', target, 'states', len(states), 'actions', sum(s['selected_count'] for s in states), flush=True)
    dump(OUT / 'selected_states.json', {'protocol_sha256': sha(PROTOCOL), 'selection_completed_before_any_prospective_full_solve': True, 'states': selected, 'missing_windows': {t: sorted(set(p['selection']['development_buckets']) - {s['bucket'] for s in selected if s['target'] == t}) for t in p['targets']}})
    writecsv(OUT / 'all_shadow_rollouts.csv', rows)
    dump(OUT / 'shadow_rollouts.json', rows)


def ground():
    frozen = load(OUT / 'selected_states.json')
    rows = []
    for state in frozen['states']:
        target, bucket = state['target'], state['bucket']
        d = OUT / 'ground_truth' / state['state_id']
        es = run_parent(target, d, 'full', at=bucket)
        replay = state_records(es)[0]
        for k in ['state_hash', 'heap_hash', 'conflicts', 'decisions', 'level', 'trail_length', 'qhead', 'global_enqueue', 'prefix_analysis', 'actions']:
            assert replay[k] == state[k], ('STATE_REPLAY_MISMATCH', state['state_id'], k)
        sd = OUT / state['directory']
        baseline_remaining = None
        for i in range(state['selected_count'] + 1):
            tag = f'C{bucket}_FULL_{i}'
            te, h = horizon(d, tag)
            _, sh = horizon(sd, f'C{bucket}_SHADOW_{i}')
            if sh:
                compare_horizons(sh, h)
            r = validate_full(target, d, tag)
            exit_record = next(e for e in es if e['event'] == 'CHILD_EXIT' and e['action_index'] == i)
            finish = next((e for e in te if e['event'] == 'FINISH'), {})
            stats = r.get('stats', {})
            remaining = stats.get('analysis_resolution_steps', 0) - state['prefix_analysis'] if stats else None
            if i == 0:
                baseline_remaining = remaining
            delta = 100 * (remaining / baseline_remaining - 1) if remaining is not None and baseline_remaining else None
            row = {'target': target, 'state_id': state['state_id'], 'bucket': bucket, 'action_index': i, 'state_hash': state['state_hash'], 'status': r['status'], 'proof_validation': r['proof_validation'], 'proof_sha256': r.get('proof_sha256'), 'prefix_analysis_ops': state['prefix_analysis'], 'remaining_analysis_ops': remaining, 'baseline_remaining_analysis_ops': baseline_remaining, 'final_ops_delta_percent': delta, 'HIGH_LEVERAGE': abs(delta) >= 10 if delta is not None else None, 'direction': 'speedup' if delta is not None and delta < 0 else 'slowdown' if delta is not None and delta > 0 else 'zero' if delta == 0 else 'unknown', **stats, 'child_cpu_seconds': exit_record['child_cpu_seconds'], 'child_wall_seconds': exit_record['child_wall_seconds'], 'fork_cpu_seconds': exit_record['fork_cpu_seconds'], 'fork_wall_seconds': exit_record['fork_wall_seconds'], 'search_watchers': finish.get('watchers', state['prefix_watchers']) - state['prefix_watchers'], 'search_dequeues': finish.get('dequeues', state['prefix_dequeues']) - state['prefix_dequeues'], 'search_redundancy': finish.get('redundancy', state['prefix_redundancy']) - state['prefix_redundancy'], 'search_binary': finish.get('binary', state['prefix_binary']) - state['prefix_binary'], 'ground_truth_horizon_potential_scan': finish.get('potential_literal_visits', 0)}
            rows.append(row)
        print('GROUND', state['state_id'], state['selected_count'], 'actions VERIFIED', flush=True)
    writecsv(OUT / 'full_ground_truth.csv', rows)
    dump(OUT / 'ground_truth.json', {'selected_states_sha256': sha(OUT / 'selected_states.json'), 'rows': rows})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'smoke', 'smoke_report', 'collect', 'ground'])
    args = parser.parse_args()
    globals()[args.phase]()
