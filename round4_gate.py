"""Evaluation driver; no history or evaluation metadata passed to workers."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

import pysat
from satcache import normalize

METHODS = ('UP', 'BVE', 'CADICAL_PREPROCESS', 'CADICAL_SOLVE')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', default='results/round4_dev')
    args = ap.parse_args()
    directory = Path(args.directory)
    manifest = json.loads((directory/'private_manifest.json').read_text())
    rows = []
    for i, case in enumerate(manifest['cases']):
        public = json.loads(Path(case['path']).read_text())
        # Exact request is persisted. It contains ONLY CNF, including for controls.
        request = json.dumps(dict(cnf=normalize(public['cnf'])), separators=(',', ':'))
        input_hash = hashlib.sha256(request.encode()).hexdigest()
        for method in METHODS[i % 4:] + METHODS[:i % 4]:
            started = perf_counter()
            try:
                worker = subprocess.run([sys.executable, 'round4_shortcuts.py', method,
                                         '--budget', '100000'], input=request, text=True,
                                        capture_output=True, timeout=10, check=True)
                row = json.loads(worker.stdout)
            except subprocess.TimeoutExpired:
                row = dict(method=method, status='TIMEOUT', checker='NOT_RUN')
            except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                row = dict(method=method, status='ERROR', checker='NOT_RUN', error=str(exc))
            row.update(case_id=case['case_id'], input_sha256=input_hash,
                       process_seconds=perf_counter()-started)
            rows.append(row)
        print(f'Checked shortcuts: {i+1}/{len(manifest["cases"])} inputs', flush=True)
    metadata = dict(version=1, phase='development_shortcut_gate', methods=METHODS,
                    python=sys.version, executable=sys.executable, platform=platform.platform(),
                    pysat=pysat.__version__, worker_budget=100000, process_watchdog_seconds=10,
                    manifest_sha256=hashlib.sha256((directory/'private_manifest.json').read_bytes()).hexdigest(),
                    formal_routes_executed=False, sources={})
    for file in ('round4_gate.py', 'round4_shortcuts.py', 'round4_core.py',
                 'satcache.py', 'proofmodule.py', 'round4_schema.json', 'docs/round4-protocol.md'):
        metadata['sources'][file] = hashlib.sha256(Path(file).read_bytes()).hexdigest()
    (directory/'gate_raw.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    metadata['raw_sha256'] = hashlib.sha256((directory/'gate_raw.jsonl').read_bytes()).hexdigest()
    (directory/'gate_metadata.json').write_text(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
