"""Recheck recorded round-two transfers independently of retrieval and LAD."""
import json
from pathlib import Path

from benchmark import archive
from research import glucose_sat
from round2_permutation import prepare
from satcache import Certificate, Step, check, normalize, transfer


def certificate(raw):
    return Certificate(raw['kind'], None if raw['assignment'] is None else
                       {int(k): v for k, v in raw['assignment'].items()},
                       tuple(tuple(c) for c in raw['premises']),
                       tuple(Step(s['left'], s['right'], s['pivot'], tuple(s['clause'])) for s in raw['steps']))


def main():
    h, q, _ = prepare(archive('/tmp/satcache-rti.tar.gz'), archive('/tmp/satcache-bms.tar.gz'), 7101, 500)
    matching = json.loads(Path('results/round2-matching.json').read_text())
    counts = {}
    for method, rows in matching['methods'].items():
        count = 0
        for row in rows:
            if row['accepted'] is None:
                continue
            accepted = row['accepted']
            query, history = q[row['query_index']], h[accepted['history_index']]
            mapping = {int(k): v for k, v in accepted['mapping'].items()}
            transported = normalize([[mapping[abs(x)]*(1 if x > 0 else -1) for x in c] for c in query])
            assert len(set(mapping.values())) == len(mapping)
            assert set(transported) <= set(history)
            model = Certificate('SAT', assignment={int(k): v for k, v in accepted['assignment'].items()})
            assert check(query, model)
            count += 1
        counts[method] = count
    motifs = json.loads(Path('results/round2-motif.json').read_text())
    motif_counts = {}
    for variant, data in motifs['variants'].items():
        histories = [normalize(f) for f in data['histories']]
        queries = [normalize(f) for f in data['queries']]
        certs = [certificate(c) for c in data['history_certificates']]
        assert all(check(f, c) for f, c in zip(histories, certs))
        negative_ids = [r['query_index'] for r in data['methods']['random']['rows'] if not r['positive']]
        assert all(glucose_sat(queries[i]) is not None for i in negative_ids)
        motif_counts[variant] = {}
        for method, measured in data['methods'].items():
            count = 0
            for row in measured['rows']:
                a = row['accepted']
                if a is None:
                    continue
                got = certificate(a['certificate'])
                mapping = {int(k): v for k, v in a['mapping'].items()}
                expected = transfer(certs[a['history_index']], mapping)
                assert expected == got
                assert check(queries[row['query_index']], got)
                assert row['query_index'] not in negative_ids
                count += 1
            motif_counts[variant][method] = count
    report = dict(permutation_rechecked=counts, motif_rechecked=motif_counts,
                  note='Oracle-candidate hits are audited but are NOT counted as real retrieval successes.')
    Path('results/round2-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
