"""Audit frozen/homologous 3-route artifacts without claiming mapping optimality."""
import gzip
import json
from pathlib import Path

from satcache import check, normalize
from audit_round4 import cert, check_hashes
from evaluation_oracle_run import METRICS
from homologous_template_run import encoding_only_inferences, DIRECTORY
from audit_evaluation_oracle import replayed_clauses
from round4_core import decode


def main():
    data = json.loads((DIRECTORY/'results.json').read_text())
    check_hashes(data['sources'])
    assert data['automatic_mapping'] is False
    native = data['native_build']
    for binary in native['binaries'].values():
        check_hashes({binary['path']: binary['sha256']})
    report = dict(status='PASS', frozen=[], homologous=[], encoding_only=[], automatic_mapping=False)
    for row in data['frozen']+data['homologous']:
        cnf = normalize(json.loads(Path(row['target']['path']).read_text())['cnf']
                        if row['target'].get('path') and Path(row['target']['path']).exists()
                        else json.loads(Path(row['target']['path']).read_text())['cnf'])
        blind = row['blind']
        if row.get('instrumentation_control') and blind.get('status')=='UNSAT' and row['instrumentation_control'].get('status')=='UNSAT':
            control = row['instrumentation_control']
            assert all(blind[k]==control[k] for k in ('conflicts', 'decisions', 'propagations'))
            assert blind['proof_sha256']==control['proof_sha256']
            assert all(control[k]==0 for k in ('analysis_resolution_steps', 'minimization_reason_visits',
                                               'binary_minimization_candidates'))
        for name in ('template', 'history'):
            best = row[name]['best']
            if not best or best.get('status') != 'UNSAT':
                continue
            assert best['analysis_resolution_steps']==min(r['analysis_resolution_steps'] for r in row[name]['colors']
                if r.get('status')=='UNSAT')
        for cert_name in ('blind_certificate', 'history_certificate', 'template_certificate'):
            if cert_name not in row:
                continue
            info = row[cert_name]
            check_hashes({info['path']: info['sha256']})
            with gzip.open(info['path'], 'rt') as f:
                proof = cert(json.load(f)['certificate'])
            target = normalize(json.loads(Path(row['target']['path']).read_text())['cnf'])
            assert check(target, proof)
        bucket = 'frozen' if row['key'].startswith('frozen') else 'homologous'
        report[bucket].append(dict(key=row['key'], n=row['n'],
            blind=row['routes']['BLIND']['status'],
            template=row['routes']['TEMPLATE_ONLY']['status'],
            history=row['routes']['FULL_HISTORY']['status'],
            replace_rate=row['target']['overlap_G']['replace_rate'],
            template_lemmas=row['routes']['TEMPLATE_ONLY'].get('unique_lemmas'),
            history_lemmas=row['routes']['FULL_HISTORY'].get('unique_lemmas')))
    (DIRECTORY/'audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(status='PASS', frozen=len(report['frozen']), homologous=len(report['homologous']))))


if __name__ == '__main__':
    main()
