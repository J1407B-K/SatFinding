"""BLIND / TEMPLATE-ONLY / FULL-HISTORY on frozen independent and homologous graphs."""
from dataclasses import asdict
from itertools import permutations
import gzip
import json
from pathlib import Path
import subprocess
from time import perf_counter

from satcache import Certificate, check, normalize
from round4_core import decode
from resolution_import import convert
from evaluation_oracle_run import METRICS, dimacs, replay, sha
from homologous_graphs import evolve, overlap, regular

DIRECTORY = Path('results/homologous_template')
NATIVE = Path('/private/tmp/satfinding-native-cdcl')
EXISTING = Path('results/oracle_transfer_6regular')
FROZEN = ((120, 6200, 6201, 6300), (200, 6202, 6203, 6302))
G_SEEDS = {120: 6200, 200: 6202, 300: 6400, 400: 6402, 600: 6404}
U_SEEDS = {120: 6300, 200: 6302, 300: 6410, 400: 6412, 600: 6414}
RATES = (0.01, 0.05, 0.10, 0.20)


def encoding_leaf(clause):
    vertices = {(abs(x)-1)//3 for x in clause}
    if len(vertices) != 1:
        return False
    return (len(clause) == 3 and all(x > 0 for x in clause)) or (len(clause) == 2 and all(x < 0 for x in clause))


def encoding_only_inferences(history):
    ready = [encoding_leaf(c) for c in history.premises]
    count = 0
    for step in history.steps:
        ok = ready[step.left] and ready[step.right]
        ready.append(ok)
        count += ok
    return count


def limits(n):
    if n <= 200:
        return (1000000, 30, 180)
    if n <= 300:
        return (1000000, 180, 600)
    return (10000000, 300, 600)


def native(cnf, tag, mode='counted', budget=1000000, timeout=30):
    input_path, proof_path = DIRECTORY/f'{tag}.cnf', DIRECTORY/f'{tag}.drup'
    dimacs(input_path, cnf)
    started = perf_counter()
    try:
        process = subprocess.run([str(NATIVE/mode), str(input_path), str(proof_path), str(budget)],
                                 text=True, capture_output=True, check=True, timeout=timeout)
        row = json.loads(next(line for line in reversed(process.stdout.splitlines()) if line.startswith('{')))
        row.update(input_path=str(input_path), input_sha256=sha(input_path),
                   proof_path=str(proof_path), proof_sha256=sha(proof_path))
    except subprocess.TimeoutExpired:
        row = dict(status='TIMEOUT')
    row['process_seconds'] = perf_counter()-started
    return row


def cadical(cnf):
    from pysat.solvers import Cadical195
    started = perf_counter()
    with Cadical195(bootstrap_with=cnf) as solver:
        solved = solver.solve()
        stats = solver.accum_stats()
    return dict(status='SAT' if solved else 'UNSAT', seconds=perf_counter()-started,
                stats=stats, checker='SOLVER_REPORTED_ONLY')


def save_instance(tag, instance):
    path = DIRECTORY/f'{tag}.json'
    path.write_text(json.dumps(instance))
    instance = dict(instance)
    instance.update(path=str(path), sha256=sha(path))
    return instance


def load_history(path):
    with gzip.open(path, 'rt') as f:
        payload = json.load(f)
    proof = decode(payload['proof'])
    return proof, payload


def produce_history(tag, instance):
    n = instance['vertices']
    budget, timeout, conversion_seconds = limits(n)
    cnf = normalize(instance['cnf'])
    row = native(cnf, f'{tag}_src', budget=budget, timeout=timeout)
    if row.get('status') != 'UNSAT':
        return dict(status=row.get('status'), native=row, encoding_only_inferences=None)
    try:
        with Path(row['proof_path']).open() as proof_file:
            proof, stats = convert(cnf, proof_file, seconds=conversion_seconds)
        assert check(cnf, proof)
    except (TimeoutError, ValueError, AssertionError, MemoryError) as exc:
        return dict(status='CONVERSION_FAIL', native=row, error=repr(exc), encoding_only_inferences=None)
    out = DIRECTORY/f'{tag}.resolution.json.gz'
    with gzip.open(out, 'wt') as f:
        json.dump(dict(proof=asdict(proof), stats=stats, native=row,
                       cnf_sha256=sha(DIRECTORY/f'{tag}_src.cnf'),
                       encoding_only_inferences=encoding_only_inferences(proof)), f)
    return dict(status='UNSAT', path=str(out), sha256=sha(out), native=row, stats=stats, proof=proof,
                encoding_only_inferences=encoding_only_inferences(proof))


def complete(tag, cnf, history, n, budget, timeout):
    permutation = list(range(n))
    rows, best, best_proof = [], None, None
    for index, colors in enumerate(permutations(range(3))):
        started = perf_counter()
        proof, lemmas, stats = replay(cnf, history, permutation, colors)
        replay_seconds = perf_counter()-started
        row = native(list(cnf)+lemmas, f'{tag}_c{index}', budget=budget, timeout=timeout)
        row.update(colors=list(colors), permutation=permutation, replay=stats,
                   replay_and_check_seconds=replay_seconds, unique_lemmas=len(lemmas),
                   total_history_seconds=(replay_seconds+row['seconds']) if 'seconds' in row else None)
        rows.append(row)
        better = row.get('status')=='UNSAT' and (best is None or best.get('status')!='UNSAT'
            or row['analysis_resolution_steps']<best['analysis_resolution_steps'])
        if better or best is None:
            best, best_proof = row, proof
    return dict(best=best, colors=rows, proof=best_proof)


def summarize(blind, template, history, cadical_row):
    def pack(row, kind):
        if not row:
            return dict(status='MISSING')
        out = {k: row.get(k) for k in ('status', 'seconds', 'process_seconds', *METRICS)}
        if kind != 'BLIND':
            out.update(replay=row.get('replay'), replay_and_check_seconds=row.get('replay_and_check_seconds'),
                       unique_lemmas=row.get('unique_lemmas'), total_history_seconds=row.get('total_history_seconds'),
                       colors=row.get('colors'))
        return out
    return dict(BLIND=pack(blind, 'BLIND'), TEMPLATE_ONLY=pack(template, 'TEMPLATE'),
                FULL_HISTORY=pack(history, 'HISTORY'), cadical=cadical_row)


def lineage_history(n):
    if n in (120, 200):
        seed = G_SEEDS[n]
        path = EXISTING/f'n{n}_H_s{seed}.resolution.json.gz'
        instance = json.loads((EXISTING/f'n{n}_H_s{seed}.json').read_text())
        proof, payload = load_history(path)
        assert check(normalize(instance['cnf']), proof)
        return instance, dict(status='UNSAT', path=str(path), sha256=sha(path), proof=proof,
                              encoding_only_inferences=encoding_only_inferences(proof),
                              existing=True, stats=payload.get('stats'))
    instance = save_instance(f'n{n}_G_s{G_SEEDS[n]}', regular(n, G_SEEDS[n]))
    history = produce_history(f'n{n}_G_s{G_SEEDS[n]}', instance)
    return instance, history


def family_history(n):
    path = DIRECTORY/f'n{n}_U_s{U_SEEDS[n]}.resolution.json.gz'
    inst_path = DIRECTORY/f'n{n}_U_s{U_SEEDS[n]}.json'
    if path.exists() and inst_path.exists():
        instance = json.loads(inst_path.read_text())
        proof, payload = load_history(path)
        return instance, dict(status='UNSAT', path=str(path), sha256=sha(path), proof=proof,
                              encoding_only_inferences=encoding_only_inferences(proof), existing=True,
                              stats=payload.get('stats'))
    instance = save_instance(f'n{n}_U_s{U_SEEDS[n]}', regular(n, U_SEEDS[n]))
    return instance, produce_history(f'n{n}_U_s{U_SEEDS[n]}', instance)


def measure_target(key, n, target, g_hist, u_hist, g_edges, u_edges, certify_winner=False):
    budget, timeout, _ = limits(n)
    cnf = normalize(target['cnf'])
    print(f'{key}: BLIND', flush=True)
    blind = native(cnf, f'{key}_blind', budget=budget, timeout=timeout)
    control = None
    if key.endswith('_independent') or 'frozen' in key:
        control = native(cnf, f'{key}_control', mode='control', budget=budget, timeout=timeout)
    cadical_row = cadical(cnf)
    template = complete(f'{key}_template', cnf, u_hist['proof'], n, budget, timeout) if u_hist.get('proof') else dict(best=None, colors=[], proof=None)
    history = complete(f'{key}_history', cnf, g_hist['proof'], n, budget, timeout) if g_hist.get('proof') else dict(best=None, colors=[], proof=None)
    row = dict(key=key, n=n, target=dict(path=target.get('path'), sha256=target.get('sha256'), origin=target.get('origin'),
                                         drift=target.get('drift'), overlap_G=overlap(g_edges, target['edges']),
                                         overlap_U=overlap(u_edges, target['edges'])),
               instrumentation_control=control, cadical=cadical_row, blind=blind,
               template=dict(best=template['best'], colors=[{k: r.get(k) for k in ('status', *METRICS, 'seconds', 'replay',
                   'replay_and_check_seconds', 'unique_lemmas', 'colors', 'total_history_seconds')} for r in template['colors']]),
               history=dict(best=history['best'], colors=[{k: r.get(k) for k in ('status', *METRICS, 'seconds', 'replay',
                   'replay_and_check_seconds', 'unique_lemmas', 'colors', 'total_history_seconds')} for r in history['colors']]),
               routes=summarize(blind, template['best'], history['best'], cadical_row))
    if certify_winner and blind.get('status') == 'UNSAT':
        from evaluation_oracle_run import certify
        try:
            row['blind_certificate'] = certify(cnf, blind, Certificate('UNSAT', premises=cnf), DIRECTORY/f'{key}_blind.resolution.json.gz')
            if history['best'] and history['best'].get('status') == 'UNSAT' and history['proof'] is not None:
                row['history_certificate'] = certify(cnf, history['best'], history['proof'], DIRECTORY/f'{key}_history.resolution.json.gz')
            if template['best'] and template['best'].get('status') == 'UNSAT' and template['proof'] is not None:
                row['template_certificate'] = certify(cnf, template['best'], template['proof'], DIRECTORY/f'{key}_template.resolution.json.gz')
        except (TimeoutError, ValueError, AssertionError) as exc:
            row['certificate_error'] = repr(exc)
    return row



def scale(payload, sizes):
    payload.setdefault('scale', [])
    done={r['n'] for r in payload['scale']}
    for n in sizes:
        if n<=200 or n in done:
            continue
        tag=f'n{n}_G_s{G_SEEDS[n]}'
        inst_path=DIRECTORY/f'{tag}.json'
        instance=json.loads(inst_path.read_text()) if inst_path.exists() else save_instance(tag, regular(n, G_SEEDS[n]))
        budget, timeout, _ = limits(n)
        cnf=normalize(instance['cnf'])
        print(f'scale {tag} BLIND timeout={timeout}', flush=True)
        blind=native(cnf, f'{tag}_scale_blind', budget=budget, timeout=timeout)
        control=native(cnf, f'{tag}_scale_control', mode='control', budget=budget, timeout=timeout) if n<=300 and blind.get('status')=='UNSAT' else dict(status='SKIPPED')
        cad=cadical(cnf)
        payload['scale'].append(dict(n=n, path=instance.get('path') or str(inst_path), seed=G_SEEDS[n],
            blind=blind, instrumentation_control=control, cadical=cad,
            history_routes='NOT_RUN',
            reason='DRUP-to-Resolution conversion is a producer cap, not a transfer outcome'))
        dump(payload)
        if blind.get('status')=='TIMEOUT':
            break

def dump(payload):
    (DIRECTORY/'results.json').write_text(json.dumps(payload, indent=2))


def frozen(payload):
    done={r['n'] for r in payload['frozen']}
    for n, hs, ts, us in FROZEN:
        if n in done:
            continue
        g = json.loads((EXISTING/f'n{n}_H_s{hs}.json').read_text())
        t = json.loads((EXISTING/f'n{n}_T_s{ts}.json').read_text())
        g_hist = dict(status='UNSAT', path=str(EXISTING/f'n{n}_H_s{hs}.resolution.json.gz'),
                      sha256=sha(EXISTING/f'n{n}_H_s{hs}.resolution.json.gz'))
        g_hist['proof'] = load_history(g_hist['path'])[0]
        g_hist['encoding_only_inferences'] = encoding_only_inferences(g_hist['proof'])
        u, u_hist = family_history(n)
        assert set(map(tuple, u['edges'])) not in (set(map(tuple, g['edges'])), set(map(tuple, t['edges'])))
        t = dict(t, path=str(EXISTING/f'n{n}_T_s{ts}.json'), sha256=sha(EXISTING/f'n{n}_T_s{ts}.json'), origin='frozen_independent')
        print(f'frozen n{n}: U status {u_hist["status"]} encoding-only G/U '
              f'{g_hist["encoding_only_inferences"]}/{u_hist.get("encoding_only_inferences")}', flush=True)
        row = measure_target(f'frozen_n{n}', n, t, g_hist, u_hist, g['edges'], u['edges'], certify_winner=(n == 200))
        row.update(G=dict(path=str(EXISTING/f'n{n}_H_s{hs}.json'), history=g_hist['path'],
                          encoding_only_inferences=g_hist['encoding_only_inferences']),
                   U=dict(path=u.get('path'), history=u_hist.get('path'), status=u_hist['status'],
                          encoding_only_inferences=u_hist.get('encoding_only_inferences')))
        payload['frozen'].append(row)
        dump(payload)


def homologous(payload, sizes):
    for n in sizes:
        g, g_hist = lineage_history(n)
        u, u_hist = family_history(n)
        payload['sources_used'].append(dict(n=n, G_status=g_hist['status'], U_status=u_hist['status'],
                                            G_encoding_only=g_hist.get('encoding_only_inferences'),
                                            U_encoding_only=u_hist.get('encoding_only_inferences')))
        dump(payload)
        if g_hist.get('status') != 'UNSAT' or u_hist.get('status') != 'UNSAT':
            print(f'n{n}: skip homologous, G={g_hist.get("status")} U={u_hist.get("status")}', flush=True)
            continue
        targets = []
        for rate in RATES:
            inst = save_instance(f'n{n}_T_r{int(rate*100):02d}_s{7000+n+int(rate*100)}',
                                 evolve(n, g['edges'], rate, 7000+n+int(rate*100)))
            targets.append((f'n{n}_r{int(rate*100):02d}', inst))
        ind = save_instance(f'n{n}_T_independent_s{8000+n}', regular(n, 8000+n))
        targets.append((f'n{n}_independent', ind))
        timed_out = 0
        done={r['key'] for r in payload['homologous']}
        for key, inst in targets:
            if key in done:
                continue
            print(f'homologous {key}', flush=True)
            row = measure_target(key, n, inst, g_hist, u_hist, g['edges'], u['edges'],
                                 certify_winner=False)
            payload['homologous'].append(row)
            dump(payload)
            if row['blind'].get('status') == 'TIMEOUT':
                timed_out += 1
        if timed_out == len(targets):
            print(f'n{n}: all BLIND TIMEOUT, stop larger sizes', flush=True)
            break


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['frozen', 'homologous', 'scale', 'all'], default='all')
    ap.add_argument('--sizes', default='200,300,400,600')
    args = ap.parse_args()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    sizes = [int(x) for x in args.sizes.split(',') if x]
    payload = json.loads((DIRECTORY/'results.json').read_text()) if (DIRECTORY/'results.json').exists() else dict(
        frozen=[], homologous=[], sources_used=[],
        protocol='docs/homologous-template-protocol.md',
        native_build=json.loads((NATIVE/'build.json').read_text()),
        mapping='identity vertex correspondence; six color permutations, evaluation-selected',
        automatic_mapping=False,
        sources={p: sha(p) for p in ('homologous_template_run.py', 'homologous_graphs.py',
            'evaluation_oracle_run.py', 'resolution_import.py', 'satcache.py',
            'docs/homologous-template-protocol.md')})
    if args.phase in ('frozen', 'all'):
        frozen(payload)
    if args.phase in ('homologous', 'all'):
        homologous(payload, sizes)
    if args.phase in ('scale', 'all'):
        scale(payload, sizes)
    dump(payload)
    print(json.dumps(dict(frozen=len(payload['frozen']), homologous=len(payload['homologous']))))


if __name__ == '__main__':
    main()
