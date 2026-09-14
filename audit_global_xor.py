"""Reconstruct inputs and independently replay persisted global XOR certificates."""
import csv
import hashlib
import json
from pathlib import Path

from global_xor import check, discover
from global_xor_experiment import instance


def main():
    metadata = json.loads(Path('results/global_xor_metadata.json').read_text())
    for name, digest in metadata['sources'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    with open('results/global_xor_raw.csv') as f:
        rows = list(csv.DictReader(f))
    expected = {(n, seed) for n in metadata['sizes'] for seed in metadata['seeds']}
    assert len(rows) == len(expected)
    assert {(int(r['n']), int(r['seed'])) for r in rows} == expected
    for row in rows:
        n, seed = int(row['n']), int(row['seed'])
        cnf, _, sat_cnf, assignment = instance(n, seed)
        assert hashlib.sha256(json.dumps(cnf).encode()).hexdigest() == row['cnf_sha256']
        assert all(any(assignment[abs(v)] == (v > 0) for v in c) for c in sat_cnf)
        assert not check(sat_cnf, discover(sat_cnf))
        assert row['baseline_status'] in ('UNSAT', 'UNKNOWN')
        for mode in ('oracle', 'discovered'):
            path = Path(f'results/global_xor_certificates/n{n}_s{seed}_{mode}.json')
            cert = json.loads(path.read_text())
            assert check(cnf, cert), path
            assert not check(sat_cnf, cert), path
    print(f'PASS: {len(rows)} input hashes, {2*len(rows)} saved proofs, '
          f'{len(rows)} SAT assignments and negative controls; code hashes match.')


if __name__ == '__main__':
    main()
