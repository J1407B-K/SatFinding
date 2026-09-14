"""Build an exportable curve and a report from the recorded medians."""
import argparse
import json
from pathlib import Path
from statistics import median

from replay_budget import BUDGETS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, default=Path('results/replay_budget'))
    args = ap.parse_args()
    directory = args.directory
    rows = json.loads((directory/'summary.json').read_text())
    metadata = json.loads((directory/'metadata.json').read_text())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    targets = list(metadata['targets'])
    fig, axes = plt.subplots(len(targets), 3, figsize=(16, 4*len(targets)), squeeze=False)
    measures = [('analysis_resolution_steps', 'Completion search ops', 1),
                ('total_wall_seconds', 'Total query wall time (ms)', 1000),
                ('support_inferences', 'Checked support inferences', 1)]
    colors = {'HISTORY': '#1261a0', 'TEMPLATE': '#d27c10', 'RANDOM': '#888888'}
    lines = ['# Replay budget curve', '',
             'Fixed identity mapping and color order. Three timing repetitions per configuration; '
             'three fixed RANDOM seeds. All times below are medians, not best runs. '
             'K limits injected outputs; checked support can exceed K.', '',
             '![Budget curves](curve.png)', '',
             'Full raw rows: [raw.jsonl](raw.jsonl); aggregates: [summary.csv](summary.csv); '
             'provenance and offline costs: [metadata.json](metadata.json).', '']
    pareto = {}
    for target_index, target in enumerate(targets):
        subset = [r for r in rows if r['target'] == target]
        blind = next(r for r in subset if r['route'] == 'BLIND')
        routes = {route: [next(r for r in subset if r['route'] == route and r['budget'] == str(k))
                           for k in BUDGETS[1:]] for route in ('HISTORY', 'TEMPLATE')}
        for col, (metric, title, scale) in enumerate(measures):
            ax = axes[target_index, col]
            for route, rr in routes.items():
                # Saturated K rows have the same data intervention. Collapse at
                # actual population size, using ALL's repeated timing there.
                points = {r['selected_lemmas']: r[metric]*scale for r in rr}
                points[0] = blind[metric]*scale
                xx = sorted(points)
                ax.plot(xx, [points[x] for x in xx], 'o-', color=colors[route], label=route, ms=4)
            random_rows = [[r for r in subset if r['route'].startswith('RANDOM_') and r['budget'] == str(k)]
                           for k in BUDGETS[1:]]
            points = {rr[0]['selected_lemmas']: [r[metric]*scale for r in rr] for rr in random_rows}
            points[0] = [blind[metric]*scale]
            xx = sorted(points)
            ax.plot(xx, [median(points[x]) for x in xx], 'o--', color=colors['RANDOM'], label='RANDOM median', ms=3)
            ax.fill_between(xx, [min(points[x]) for x in xx], [max(points[x]) for x in xx],
                            color=colors['RANDOM'], alpha=.18, label='RANDOM seed range')
            ax.scatter([0], [blind[metric]*scale], c='black', s=35, zorder=5, label='BLIND')
            if col < 2:
                ax.axhline(blind[metric]*scale, color='black', alpha=.3, lw=.8)
            ax.set_xscale('symlog', linthresh=32, base=2)
            maximum = max(r['selected_lemmas'] for r in subset)
            ticks = [0, 32, 128, 512, 2048, 8192, 32768]
            ticks = [v for v in ticks if v < maximum] + [maximum]
            ax.set_xticks(ticks)
            ax.set_xlim(0, maximum*1.08)
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v/1000:.0f}k' if v >= 1000 else f'{v:.0f}'))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v/1000:g}k' if v >= 10000 else f'{v:g}'))
            ax.tick_params(axis='x', labelrotation=35)
            ax.set_title(f'{target} — {title}')
            ax.set_xlabel('Actual injected replay lemmas (symlog)')
            ax.grid(alpha=.15)
            if target_index == 0 and col == 0:
                ax.legend(fontsize=8)
        lines.extend([f'## {target}', '',
            '| HISTORY cap | Injected | Support steps | Replay/check ms | Search ops | Conflicts | Total wall ms |',
            '|---:|---:|---:|---:|---:|---:|---:|'])
        for r in [blind]+routes['HISTORY']:
            lines.append(f'| {r["budget"]} | {r["selected_lemmas"]:,} | {r["support_inferences"]:,} | '
                         f'{r["replay_and_check_seconds"]*1000:.2f} | {r["analysis_resolution_steps"]:,} | '
                         f'{r["conflicts"]:,} | {r["total_wall_seconds"]*1000:.2f} |')
        lines.extend(['', '| Cap | HISTORY ops / wall ms | TEMPLATE injected; ops / wall ms | RANDOM median ops [seed range] / wall ms |',
                      '|---:|---:|---:|---:|'])
        for k, h, t in zip(BUDGETS[1:], routes['HISTORY'], routes['TEMPLATE']):
            rr = [r for r in subset if r['route'].startswith('RANDOM_') and r['budget'] == str(k)]
            ops = [r['analysis_resolution_steps'] for r in rr]
            wall = median(r['total_wall_seconds'] for r in rr)*1000
            lines.append(f'| {k} | {h["analysis_resolution_steps"]:,} / {h["total_wall_seconds"]*1000:.2f} | '
                         f'{t["selected_lemmas"]:,}; {t["analysis_resolution_steps"]:,} / {t["total_wall_seconds"]*1000:.2f} | '
                         f'{median(ops):,} [{min(ops):,}–{max(ops):,}] / {wall:.2f} |')
        candidates = [r for r in subset if r['statuses'] == 'UNSAT' and r['route'] != 'LEGACY_FULL'
                      and not (r['route'].startswith('RANDOM_') and r['budget'] == 'ALL')
                      and not (r['budget'] not in ('ALL', '0')
                               and int(r['budget']) >= r['eligible_lemmas'])]
        frontier = [r for r in candidates if not any(
            q['analysis_resolution_steps'] <= r['analysis_resolution_steps']
            and q['total_wall_seconds'] <= r['total_wall_seconds']
            and (q['analysis_resolution_steps'] < r['analysis_resolution_steps']
                 or q['total_wall_seconds'] < r['total_wall_seconds']) for q in candidates)]
        pareto[target] = frontier
        lines.extend(['', 'Measured Pareto points (search ops / median query wall, including BLIND): '+
                      '; '.join(f'{r["route"]} K={r["budget"]}' for r in sorted(frontier, key=lambda r:r['total_wall_seconds']))+'.', ''])
        legacy = next(r for r in subset if r['route'] == 'LEGACY_FULL')
        lines.extend([f'Old full-DAG replay: {legacy["replay_and_check_seconds"]*1000:.2f} ms replay/check, '
                      f'{legacy["total_wall_seconds"]*1000:.2f} ms total. ALL injection order and native counters '
                      'match this legacy route exactly.', ''])
    lines.extend(['## Accounting and limits', '',
        'Replay/check includes fresh whole-DAG eligibility scanning and selection, selected ancestor materialization, '
        'and the existing proof checker. Total wall additionally includes CNF serialization, process startup, '
        'native parsing/search, proof output and artifact hashing. Source load, source proof verification and '
        'ranking are offline and excluded from warm query time:', '',
        '| Source | Load s | Source check s | Index/rank s | Original conversion s |',
        '|---|---:|---:|---:|---:|'])
    for name, r in metadata['offline'].items():
        lines.append(f'| {name} | {r["load_seconds"]:.3f} | {r["source_check_seconds"]:.3f} | '
                     f'{r["index_seconds"]:.3f} | {r["original_conversion_seconds"]} |')
    lines.extend(['', 'The score is a source-only heuristic: `(1 + direct uses) / '
                  '((1 + clause width) * (1 + left width + right width))`. Parent width is only '
                  'a local cost proxy; exact support unions can be much larger.', '',
                  'These are Resolution intermediate clauses, not a count of raw DRUP additions. '
                  'This prototype reuses an existing expanded DAG and checks selected ancestor unions; '
                  'it does not yet provide lazy materialization directly from DRUP. Completion statuses '
                  'are solver-reported; the replay support is independently checked. Three targets and '
                  'three random seeds are exploratory evidence, not a broad ranking validation.', '',
                  'Pareto reporting uses ALL as the canonical saturated configuration and HISTORY ALL '
                  'for the identical RANDOM ALL endpoint, avoiding duplicate endpoint timing selection.', '',
                  'Reproduce: `.venv/bin/python replay_budget_run.py`, then run '
                  '`replay_budget_report.py` with matplotlib installed.'])
    fig.suptitle('Replay budget: fixed mapping, selected ancestor support, median of 3 repetitions', fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, .97))
    fig.savefig(directory/'curve.png', dpi=180)
    fig.savefig(directory/'curve.pdf')
    (directory/'report.md').write_text('\n'.join(lines)+'\n')
    (directory/'pareto.json').write_text(json.dumps(pareto, indent=2))


if __name__ == '__main__':
    main()
