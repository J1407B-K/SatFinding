"""Supplied-alignment pilot, not an optimum-mapping certificate.

Only BLIND and ORACLE_HISTORY; same Resolution kernel and global attempt cap.
History repair is a deliberately bounded local policy, not optimal repair.
"""
import argparse
from collections import defaultdict, deque
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from satcache import Certificate, Step, check, normalize, transfer
from round4_core import Budget, ProofDB, ResolutionSearch, decode, slice_proof

LIMITS = dict(attempts=400000, local_attempts=2000, seconds=20,
              max_pending=250000, max_nodes=50000)


def search_until(engine, target, local_limit, deadline):
    stop = min(engine.budget.limit, engine.budget.attempts+local_limit)
    while target not in engine.index and () not in engine.index and engine.heap:
        if engine.budget.attempts >= stop:
            return 'GLOBAL_BUDGET' if stop == engine.budget.limit else 'LOCAL_BUDGET'
        if perf_counter() >= deadline:
            return 'WALL_CLOCK'
        if len(engine.heap) > LIMITS['max_pending'] or len(engine.nodes) > LIMITS['max_nodes']:
            return 'MEMORY_POLICY'
        engine.search(target, local_limit=1)
    return 'TARGET' if target in engine.index else ('CONTRADICTION' if () in engine.index else 'SATURATED')


def run(cnf, route, historical=None, supplied_mapping=None):
    started = perf_counter()
    deadline = started+LIMITS['seconds']
    cnf = normalize(cnf)
    budget = Budget(LIMITS['attempts'])
    sessions = []
    if route == 'BLIND':
        engine = ResolutionSearch(cnf, budget)
        reason = search_until(engine, (), budget.limit, deadline)
        sessions.append(dict(start_attempts=0, end_attempts=budget.attempts,
                             initial_global_ids=list(range(len(cnf))), target=(),
                             stop_reason=reason, trace=engine.trace,
                             new_steps=[asdict(s) for s in engine.steps]))
        db = engine
        history_stats = None
    else:
        if historical is None or supplied_mapping is None:
            raise ValueError('Oracle proof and explicit mapping required')
        proof = transfer(historical, supplied_mapping)
        pnodes = list(proof.premises)+[s.clause for s in proof.steps]
        base = len(proof.premises)
        db = ProofDB(cnf, budget)
        bindings = {}
        children, clauses_to_old = defaultdict(list), defaultdict(list)
        for i, c in enumerate(pnodes):
            clauses_to_old[c].append(i)
        for j, s in enumerate(proof.steps, base):
            children[s.left].append(j)
            children[s.right].append(j)
        origins, replay_steps = {}, []

        def propagate(new_ids):
            queue = deque()
            for global_id in new_ids:
                for old in clauses_to_old.get(db.nodes[global_id], ()):
                    if old not in bindings:
                        bindings[old] = global_id
                        origins[old] = 'input' if global_id < len(cnf) else 'search'
                        queue.extend(children[old])
            while queue:
                old = queue.popleft()
                if old in bindings:
                    continue
                s = proof.steps[old-base]
                if s.left not in bindings or s.right not in bindings:
                    continue
                left, right = bindings[s.left], bindings[s.right]
                a, b = db.nodes[left], db.nodes[right]
                expected = tuple(sorted((set(a)-{s.pivot}) | (set(b)-{-s.pivot})))
                if s.pivot not in a or -s.pivot not in b or expected != s.clause:
                    raise ValueError('Invalid direct replay')
                if expected not in db.index:
                    db.index[expected] = len(db.nodes)
                    db.nodes.append(expected)
                    db.steps.append(Step(left, right, s.pivot, expected))
                    replay_steps.append(len(db.nodes)-1)
                bindings[old] = db.index[expected]
                origins[old] = 'replay'
                queue.extend(children[old])
                # Equal historical clauses can use this already-proved result,
                # but their old inferences were not themselves replayed.
                for alias in clauses_to_old[expected]:
                    if alias not in bindings:
                        bindings[alias] = db.index[expected]
                        origins[alias] = 'available_alias'
                        queue.extend(children[alias])

        propagate(range(len(cnf)))
        initial_direct = sum(i >= base and origin == 'replay' for i, origin in origins.items())
        initial_present = sum(i < base for i in bindings)
        initial_bound = set(bindings)
        # Fix targets before repair: short clauses first, then historical ID.
        # No target proof or success labels participate in this choice.
        targets = sorted((i for i in range(len(pnodes)) if i not in bindings),
                         key=lambda i: (len(pnodes[i]), i))
        reason = 'GAPS_REMAIN'
        repair_successes = 0
        for old in targets:
            if () in db.index:
                reason = 'CONTRADICTION'
                break
            if old in bindings:
                continue
            if budget.attempts >= budget.limit:
                reason = 'GLOBAL_BUDGET'
                break
            if perf_counter() >= deadline:
                reason = 'WALL_CLOCK'
                break
            target = pnodes[old]
            scope = {abs(x) for x in target}
            # Empty target receives the whole input, exactly like BLIND.
            # Nonempty targets receive one incidence-neighborhood of root input;
            # already proved clauses entirely inside that region are available.
            root_ids = [i for i, c in enumerate(cnf) if not scope or any(abs(x) in scope for x in c)]
            expanded = {abs(x) for i in root_ids for x in cnf[i]}
            initial_ids = root_ids + [i for i in range(len(cnf), len(db.nodes))
                                      if all(abs(x) in expanded for x in db.nodes[i])]
            # Preserve unique clauses; global database already de-duplicates them.
            initial_ids = list(dict.fromkeys(initial_ids))
            local = ResolutionSearch(tuple(db.nodes[i] for i in initial_ids), budget)
            before = budget.attempts
            global_nodes_before = len(db.nodes)
            local_reason = search_until(local, target, LIMITS['local_attempts'], deadline)
            local_to_global = list(initial_ids)
            newly_added = []
            for s in local.steps:
                if s.clause not in db.index:
                    db.index[s.clause] = len(db.nodes)
                    db.nodes.append(s.clause)
                    db.steps.append(Step(local_to_global[s.left], local_to_global[s.right], s.pivot, s.clause))
                    newly_added.append(db.index[s.clause])
                local_to_global.append(db.index[s.clause])
            sessions.append(dict(start_attempts=before, end_attempts=budget.attempts,
                                 global_nodes_before=global_nodes_before,
                                 initial_global_ids=initial_ids, target=target, historical_target=old,
                                 stop_reason=local_reason, trace=local.trace,
                                 new_steps=[asdict(s) for s in local.steps]))
            propagate(newly_added)
            repair_successes += target in db.index
            if local_reason in ('WALL_CLOCK', 'MEMORY_POLICY'):
                reason = local_reason
                break
            if len(db.nodes) > LIMITS['max_nodes']:
                reason = 'MEMORY_POLICY'
                break
        history_stats = dict(historical_leaves=base, historical_inferences=len(proof.steps),
                             mapped_nodes=len(pnodes), initial_present_leaves=initial_present,
                             initial_missing_leaves=base-initial_present,
                             initial_direct_inferences=initial_direct,
                             initial_broken_inferences=len(proof.steps)-sum(i >= base for i in initial_bound),
                             replay_after_repair=sum(i >= base and origin == 'replay' for i, origin in origins.items())-initial_direct,
                             restored_by_search=sum(i not in initial_bound and origin == 'search' for i, origin in origins.items()),
                             unresolved_nodes=len(pnodes)-len(bindings), repair_attempts=len(sessions),
                             repair_successes=repair_successes, replay_global_ids=replay_steps,
                             replay_ratio=initial_direct/len(proof.steps) if proof.steps else None)
    search_end = perf_counter()
    full = db.certificate()
    certificate = None
    checked = False
    if () in db.index:
        reason = 'CONTRADICTION'
        certificate, _ = slice_proof(full)
        checked = check(cnf, certificate)
        if not checked:
            raise ValueError('Final checker rejected oracle/BLIND proof')
    return dict(route=route, status='UNSAT' if checked else 'MISS', stop_reason=reason,
                budget=asdict(budget), history=history_stats, sessions=sessions,
                full_certificate=asdict(full), certificate=asdict(certificate) if certificate else None,
                checker='PASS' if checked else 'NO_REFUTATION',
                search_and_replay_seconds=search_end-started,
                checker_seconds=perf_counter()-search_end, end_to_end_seconds=perf_counter()-started,
                new_generated_nodes_all=sum(s['new_steps'].__len__() for s in sessions),
                attempts_saved=None, comparison_censored=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worker', choices=['BLIND', 'ORACLE_HISTORY'])
    args = ap.parse_args()
    if args.worker:
        data = json.load(sys.stdin)
        h = decode(data['proof']) if args.worker == 'ORACLE_HISTORY' else None
        mapping = {int(k): v for k, v in data['mapping'].items()} if h else None
        print(json.dumps(run(data['cnf'], args.worker, h, mapping)))
        return
    directory = Path('results/oracle_transfer_6regular')
    screen = json.loads((directory/'screen.json').read_text())
    cases = {c['key']: c for c in screen['cases']}
    result = dict(limits=LIMITS, oracle='supplied_vertex_color_identity_NOT_PROVEN_OPTIMAL',
                  selection='all screened pairs with an available checked historical Resolution proof',
                  rows=[], excluded=[], sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                    for p in ('oracle_transfer_run.py', 'round4_core.py', 'satcache.py')})
    for n, hs, ts in screen['pairs']:
        hk, tk = f'n{n}_H_s{hs}', f'n{n}_T_s{ts}'
        hp = directory/f'{hk}.resolution.json.gz'
        if not hp.exists():
            result['excluded'].append(dict(pair=[hk, tk], reason='NO_CHECKED_HISTORICAL_RESOLUTION_ARTIFACT'))
            continue
        with gzip.open(hp, 'rt') as f:
            historical = json.load(f)
        hdata = json.loads(Path(cases[hk]['path']).read_text())
        target = json.loads(Path(cases[tk]['path']).read_text())
        proof = decode(historical['proof'])
        if not check(normalize(hdata['cnf']), proof):
            raise ValueError('Historical certificate invalid')
        for route in ('BLIND', 'ORACLE_HISTORY'):
            request = dict(cnf=target['cnf'])
            if route == 'ORACLE_HISTORY':
                request.update(proof=historical['proof'], mapping={v: v for v in range(1, 3*n+1)})
            started = perf_counter()
            try:
                process = subprocess.run([sys.executable, __file__, '--worker', route],
                                         input=json.dumps(request), text=True, capture_output=True,
                                         check=True, timeout=40)
                row = json.loads(process.stdout)
            except subprocess.TimeoutExpired:
                row = dict(route=route, status='TIMEOUT', stop_reason='PROCESS_WATCHDOG')
            except subprocess.CalledProcessError as exc:
                row = dict(route=route, status='ERROR', error=exc.stderr[-2000:])
            row.update(historical_key=hk, target_key=tk, process_seconds=perf_counter()-started,
                       target_sha256=cases[tk]['sha256'],
                       historical_proof_sha256=hashlib.sha256(hp.read_bytes()).hexdigest())
            out = directory/f'{tk}.{route}.json.gz'
            with gzip.open(out, 'wt') as f:
                json.dump(row, f)
            summary = {k: row[k] for k in ('route', 'status', 'stop_reason', 'historical_key', 'target_key', 'process_seconds') if k in row}
            summary.update(path=str(out), sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                           attempts=row.get('budget', {}).get('attempts'), history=row.get('history'))
            result['rows'].append(summary)
            print(json.dumps({k: v for k, v in summary.items() if k != 'history'}), flush=True)
            (directory/'transfer.json').write_text(json.dumps(result, indent=2))
    (directory/'transfer.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
