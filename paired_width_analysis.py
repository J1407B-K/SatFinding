"""Paired width effects, percentile bootstrap CIs, and exact sign tests (stdlib)."""
import argparse
import csv
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path


def quantile(xs, p):
    xs = sorted(xs)
    x = (len(xs) - 1) * p
    i = int(x)
    return xs[i] + (xs[min(i + 1, len(xs) - 1)] - xs[i]) * (x - i)


def analyze(source, prefix, draws=20000):
    pairs = defaultdict(dict)
    with open(source) as f:
        for r in csv.DictReader(f, skipinitialspace=True):
            key = (int(r['n']), r['method'], int(r['seed']))
            ext = r['extended'].strip()
            if ext not in ('True', 'False') or ext in pairs[key]:
                raise ValueError(f'Invalid/duplicate row: {key}, {ext}')
            pairs[key][ext] = r
    details, groups = [], defaultdict(list)
    for (n, method, seed), pair in sorted(pairs.items()):
        if set(pair) != {'False', 'True'}:
            raise ValueError(f'Incomplete pair: {n}, {method}, {seed}')
        b, e = pair['False'], pair['True']
        orig = int(b['original_vars'])
        if orig != int(e['original_vars']) or orig <= 0:
            raise ValueError('Inconsistent original variable counts')
        bw, ew = int(b['width']), int(e['width'])
        if bw <= 0:
            raise ValueError('Relative effect requires positive baseline width')
        row = dict(n=n, method=method, seed=seed, original_vars=orig,
                   base_width=bw, ext_width=ew, delta_width=ew-bw,
                   delta_per_original=(ew-bw)/orig,
                   improvement_pct=100*(bw-ew)/bw)
        details.append(row)
        groups[n, method].append(row)
    summaries = []
    rng = random.Random(20260909)
    for (n, method), rows in sorted(groups.items()):
        ds = [r['delta_per_original'] for r in rows]
        gains = [r['improvement_pct'] for r in rows]
        wins = sum(x < 0 for x in ds)
        losses = sum(x > 0 for x in ds)
        nonzero = wins + losses
        p = min(1., 2*sum(math.comb(nonzero, k) for k in range(min(wins, losses)+1))/2**nonzero)
        boots = [st.mean(rng.choices(ds, k=len(ds))) for _ in range(draws)]
        summaries.append(dict(n=n, method=method, pairs=len(ds), wins=wins,
            ties=len(ds)-nonzero, losses=losses,
            mean_delta_width=st.mean(r['delta_width'] for r in rows),
            median_delta_width=st.median(r['delta_width'] for r in rows),
            mean_delta_per_original=st.mean(ds), median_delta_per_original=st.median(ds),
            ci_low=quantile(boots,.025), ci_high=quantile(boots,.975),
            mean_improvement_pct=st.mean(gains), median_improvement_pct=st.median(gains),
            sign_p=p))
    adjusted = 0.
    for rank, row in enumerate(sorted(summaries, key=lambda r:r['sign_p'])):
        adjusted = max(adjusted, min(1., (len(summaries)-rank)*row['sign_p']))
        row['sign_p_holm'] = adjusted
    for suffix, rows in (('_pairs.csv', details), ('_summary.csv', summaries)):
        with open(str(prefix)+suffix, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    lines = ['# Paired width analysis', '', f'Source: `{source}`. Pairs matched by (n, method, seed).', '',
        'Delta = extension − baseline; negative favors extension. Improvement = 100 × (baseline − extension) / baseline, calculated per pair.', '',
        f'CIs: pointwise 95% percentile bootstrap for mean normalized paired delta, {draws} resamples, RNG seed 20260909. Sign tests: exact, two-sided, ties excluded; Holm adjustment across all rows below. Intervals are not multiplicity-adjusted. Seeds are treated as independent within each size; sizes are not pooled.', '',
        '| n | pairs | win/tie/loss | mean Δwidth | mean Δ/orig [95% CI] | mean improvement | sign p (Holm) |',
        '|---:|---:|:---:|---:|:---|---:|---:|']
    for r in summaries:
        lines.append(f"| {r['n']} | {r['pairs']} | {r['wins']}/{r['ties']}/{r['losses']} | {r['mean_delta_width']:.2f} | {r['mean_delta_per_original']:.4f} [{r['ci_low']:.4f}, {r['ci_high']:.4f}] | {r['mean_improvement_pct']:.2f}% | {r['sign_p_holm']:.4g} |")
    lines += ['', 'These are heuristic elimination-width upper bounds, not exact treewidth or resolution width. A high upper bound does not establish a lower bound. Finite-size effects do not establish an asymptotic rate. Runtime is excluded because the first native call includes compilation.']
    Path(str(prefix)+'.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--prefix', required=True)
    args = ap.parse_args()
    analyze(args.source, args.prefix)
