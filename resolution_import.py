"""DRUP producer adapter to existing pure binary Resolution certificates.

RUP propagation is reconstruction work, NOT the final checker. Deletions are
ignored soundly; a derived subclause may replace an added clause. All output
inferences have explicit parents/pivots and no assumptions or extension axioms.
Unsupported non-RUP additions fail closed.
"""
import argparse
from collections import defaultdict, deque
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from satcache import Certificate, Step, check, normalize
from round4_core import slice_proof


class RUPImporter:
    def __init__(self, cnf):
        self.cnf = normalize(cnf)
        self.nodes = list(self.cnf)
        self.steps = []
        self.occ = defaultdict(list)
        self.active = set()
        self.units = []
        self.stats = dict(additions=0, deletions_ignored=0, propagations=0,
                          occurrence_visits=0, reconstruction_resolution_steps=0,
                          strengthened_additions=0)
        for i in range(len(self.nodes)):
            self.activate(i)

    def activate(self, i):
        if i in self.active:
            return
        self.active.add(i)
        for lit in self.nodes[i]:
            self.occ[lit].append(i)
        if len(self.nodes[i]) <= 1:
            self.units.append(i)

    def infer(self, left, right, pivot):
        a, b = self.nodes[left], self.nodes[right]
        assert pivot in a and -pivot in b
        c = tuple(sorted((set(a)-{pivot}) | (set(b)-{-pivot})))
        self.steps.append(Step(left, right, pivot, c))
        self.nodes.append(c)
        self.stats['reconstruction_resolution_steps'] += 1
        return len(self.nodes)-1

    def add(self, clause):
        values, trail, pending = {}, [], deque()
        false_counts = defaultdict(int)
        for lit in clause:
            if -lit in clause:
                raise ValueError('Tautological DRUP addition unsupported')
            values[abs(lit)] = -lit
            trail.append((-lit, None))
            pending.append(-lit)
        conflict = None
        for i in self.units:
            c = self.nodes[i]
            if not c:
                conflict = i
                break
            lit = c[0]
            if values.get(abs(lit)) == -lit:
                conflict = i
                break
            if abs(lit) not in values:
                values[abs(lit)] = lit
                trail.append((lit, i))
                pending.append(lit)
        while pending and conflict is None:
            lit = pending.popleft()
            self.stats['propagations'] += 1
            for i in self.occ[-lit]:
                self.stats['occurrence_visits'] += 1
                c = self.nodes[i]
                false_counts[i] += 1
                if false_counts[i] < len(c)-1:
                    continue
                if any(values.get(abs(x)) == x for x in c):
                    continue
                remaining = [x for x in c if abs(x) not in values]
                if not remaining:
                    conflict = i
                    break
                if len(remaining) == 1:
                    unit = remaining[0]
                    values[abs(unit)] = unit
                    trail.append((unit, i))
                    pending.append(unit)
        if conflict is None:
            raise ValueError('Non-RUP or unsupported proof addition')
        result = conflict
        for lit, reason in reversed(trail):
            if reason is not None and -lit in self.nodes[result]:
                result = self.infer(result, reason, -lit)
        if not set(self.nodes[result]) <= set(clause):
            raise ValueError('Reconstruction failed to discharge propagation reasons')
        self.stats['additions'] += 1
        self.stats['strengthened_additions'] += self.nodes[result] != clause
        self.activate(result)
        return result


def convert(cnf, lines, max_additions=400000, seconds=120):
    started = perf_counter()
    importer = RUPImporter(cnf)
    root = importer.nodes.index(()) if () in importer.nodes else None
    for line_number, line in enumerate(lines, 1):
        if root is not None:
            break
        if perf_counter()-started >= seconds:
            raise TimeoutError('DRUP reconstruction wall-clock cap')
        fields = line.split()
        if not fields or fields[0] == 'c':
            continue
        if fields[0] == 'd':
            importer.stats['deletions_ignored'] += 1
            continue
        if importer.stats['additions'] >= max_additions:
            raise TimeoutError('DRUP reconstruction addition cap')
        if fields[-1] != '0':
            raise ValueError('Unterminated DRUP clause')
        clause = tuple(sorted(set(map(int, fields[:-1]))))
        if 0 in clause:
            raise ValueError('Interior zero')
        try:
            result = importer.add(clause)
        except ValueError as exc:
            raise ValueError(f'DRUP line {line_number}: {exc}') from exc
        if not importer.nodes[result]:
            root = result
    if root is None:
        raise ValueError('No reconstructed contradiction')
    conversion_seconds = perf_counter()-started
    full = Certificate('UNSAT', premises=importer.cnf, steps=tuple(importer.steps))
    checker_started = perf_counter()
    if not check(importer.cnf, full):
        raise ValueError('Existing checker rejected full reconstruction')
    full_checker_seconds = perf_counter()-checker_started
    sliced, keep = slice_proof(full, root)
    checker_started = perf_counter()
    if not check(importer.cnf, sliced):
        raise ValueError('Existing checker rejected sliced reconstruction')
    return sliced, dict(**importer.stats, full_input_nodes=len(full.premises),
                        full_inference_nodes=len(full.steps), sliced_input_nodes=len(sliced.premises),
                        sliced_inference_nodes=len(sliced.steps), conversion_seconds=conversion_seconds,
                        full_checker_seconds=full_checker_seconds,
                        sliced_checker_seconds=perf_counter()-checker_started,
                        checker='PASS', slice_old_ids=keep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('drup')
    ap.add_argument('output')
    ap.add_argument('--seconds', type=float, default=120)
    args = ap.parse_args()
    source = json.loads(Path(args.input).read_text())
    with Path(args.drup).open() as proof_file:
        proof, stats = convert(source['cnf'], proof_file, seconds=args.seconds)
    payload = dict(proof=asdict(proof), stats=stats,
                   cnf_sha256=hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
                   drup_sha256=hashlib.sha256(Path(args.drup).read_bytes()).hexdigest(),
                   sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                            for p in ('resolution_import.py', 'round4_core.py', 'satcache.py')})
    with gzip.open(args.output, 'wt') as f:
        json.dump(payload, f)
    print(json.dumps({k: v for k, v in stats.items() if k != 'slice_old_ids'}), flush=True)


if __name__ == '__main__':
    main()
