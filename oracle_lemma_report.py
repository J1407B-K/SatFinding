"""Report value, support cost, conditional controls and oracle discovery cost."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from statistics import median

from oracle_lemma import CAPS, DIRECTORY, HISTORY
from homologous_template_run import load_history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, default=DIRECTORY)
    args = ap.parse_args()
    directory = args.directory
    rows = json.loads((directory/'summary.json').read_text())
    discovery = json.loads((directory/'discovery.json').read_text())
    metadata = json.loads((directory/'metadata.json').read_text())
    audit = json.loads((directory/'audit.json').read_text())
    # Export the actual clauses and conditional labels for later predictor work;
    # do not fit a predictor or change the frozen oracle in this round.
    history, _ = load_history(HISTORY)
    leaves = len(history.premises)
    clauses = list(history.premises)+[s.clause for s in history.steps]
    uses = Counter(p for s in history.steps for p in (s.left, s.right))
    gold = dict(history_path=str(HISTORY), history_sha256=metadata['source_files'][str(HISTORY)],
                template_clauses=metadata['template_lemmas'], sets={})
    for mode in ('exact', 'at_most'):
        for cap in CAPS:
            winner = discovery[mode][str(cap)]
            gold['sets'][f'{mode}_{cap}'] = dict(
                selected_ids=winner['selected_ids'], clauses=[clauses[i] for i in winner['selected_ids']],
                search_ops=winner['analysis_resolution_steps'], conflicts=winner['conflicts'])
    (directory/'gold_lemmas.json').write_text(json.dumps(gold, indent=2))
    labels = []
    with (directory/'search.jsonl').open() as trace:
        for line in trace:
            row = json.loads(line)
            if row['stage'] != 'singletons':
                continue
            i = row['selected_ids'][0]
            step = history.steps[i-leaves]
            labels.append(dict(node_id=i, width=len(clauses[i]), historical_direct_uses=uses[i],
                local_parent_cost=1+len(clauses[step.left])+len(clauses[step.right]),
                search_ops=row['analysis_resolution_steps'], conflicts=row['conflicts'],
                saved_ops_vs_template=discovery['baseline']['analysis_resolution_steps']-row['analysis_resolution_steps'],
                saved_conflicts_vs_template=discovery['baseline']['conflicts']-row['conflicts']))
    with (directory/'singleton_marginals.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(labels[0]))
        writer.writeheader()
        writer.writerows(labels)
    lookup = {(r['route'], r['cap']): r for r in rows}
    blind, template = lookup['BLIND', '0'], lookup['TEMPLATE', '0']
    full = lookup['UNCONDITIONAL_FULL', 'ALL']
    single = lookup['BEST_SINGLETON', '1']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.3))
    measures = [('analysis_resolution_steps', 'Completion search ops', 1),
                ('total_wall_seconds', 'Warm preselected query total (ms)', 1000),
                ('support_inferences', 'Checked TEMPLATE + history support steps', 1)]
    colors = {'RANKED': '#b27b23', 'ORACLE_EXACT': '#145daa', 'ORACLE_AT_MOST': '#0c8b65'}
    for ax, (metric, title, factor) in zip(axes, measures):
        for route, color in colors.items():
            rr = [template]+[lookup[route, str(k)] for k in CAPS]
            ax.plot([0]+list(CAPS), [r[metric]*factor for r in rr],
                    'o-' if route != 'ORACLE_AT_MOST' else 's--', color=color, label=route, ms=4)
        random_points = [[lookup[f'RANDOM_{s}', str(k)][metric]*factor for s in (17, 29, 43)] for k in CAPS]
        xx = [0]+list(CAPS)
        ax.plot(xx, [template[metric]*factor]+[median(p) for p in random_points],
                'o--', color='#999999', label='RANDOM median', ms=3)
        ax.fill_between(xx, [template[metric]*factor]+[min(p) for p in random_points],
                        [template[metric]*factor]+[max(p) for p in random_points], color='#999999', alpha=.15)
        ax.scatter([0], [template[metric]*factor], color='black', s=45, label='TEMPLATE-67', zorder=5)
        ax.scatter([1], [single[metric]*factor], color='#962684', marker='*', s=100,
                   label='Best screened singleton', zorder=5)
        if metric != 'support_inferences':
            ax.axhline(blind[metric]*factor, color='#555555', ls=':', label='BLIND')
        ax.set_xscale('symlog', linthresh=16, base=2)
        ax.set_xlim(0, 290)
        ax.set_xticks([0, 32, 64, 128, 256], ['0', '32', '64', '128', '256'])
        ax.set_xlabel('Historical lemma cap K (67 TEMPLATE outputs are fixed)')
        ax.set_title(title)
        ax.grid(alpha=.16)
    axes[0].legend(fontsize=8)
    fig.suptitle('Same-target offline oracle: fixed identity mapping; 5 sequential timing repetitions', fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(directory/'curve.png', dpi=180)
    fig.savefig(directory/'curve.pdf')

    lines = ['# Offline Oracle Lemma Selection', '',
        'Same n=200, 1% drift target. Every conditional route starts from exactly the same 67 checked '
        'TEMPLATE outputs; historical output order is fixed to source-node order. '
        'Five sequential repetitions per frozen set, median wall time. Oracle optimization uses '
        'search ops, then conflicts; never measured latency.', '',
        '![Conditional oracle curves](curve.png)', '',
        '[Raw final runs](final_raw.jsonl) · [Summary CSV](summary.csv) · '
        '[Search trace](search.jsonl) · [Frozen selections](selections.json) · '
        '[Actual golden clauses](gold_lemmas.json) · [Singleton marginal labels](singleton_marginals.csv) · '
        '[Discovery and ablations](discovery.json) · [Audit](audit.json)', '',
        '## Baselines and anchors', '',
        '| Route | Historical outputs | Replay/check ms | Search ops | Conflicts | Total ms |',
        '|---|---:|---:|---:|---:|---:|']

    def table_row(name, row):
        return (f'| {name} | {row["historical_lemmas"]:,} | '
                f'{row["replay_and_check_seconds"]*1000:.2f} | {row["analysis_resolution_steps"]:,} | '
                f'{row["conflicts"]:,} | {row["total_wall_seconds"]*1000:.2f} |')

    for name, row in [('BLIND', blind), ('TEMPLATE-67', template),
                      ('TEMPLATE + best singleton', single),
                      ('TEMPLATE + RANKED-2048', lookup['RANKED', '2048']),
                      ('TEMPLATE + FULL stripped history', lookup['FULL_STRIPPED', 'ALL']),
                      ('Previous unconditioned FULL outputs', full)]:
        lines.append(table_row(name, row))
    lines.extend(['', '## Exact-K oracle sets', '',
        '| K | Replay/check ms | Search ops | Conflicts | Total ms | Support steps | Extra ops reduction vs TEMPLATE | Fraction of old BLIND→FULL saving |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|'])
    for cap in CAPS:
        row = lookup['ORACLE_EXACT', str(cap)]
        extra = 1-row['analysis_resolution_steps']/template['analysis_resolution_steps']
        fraction = ((blind['analysis_resolution_steps']-row['analysis_resolution_steps']) /
                    (blind['analysis_resolution_steps']-full['analysis_resolution_steps']))
        lines.append(f'| {cap} | {row["replay_and_check_seconds"]*1000:.2f} | '
                     f'{row["analysis_resolution_steps"]:,} | {row["conflicts"]:,} | '
                     f'{row["total_wall_seconds"]*1000:.2f} | {row["support_inferences"]:,} | '
                     f'{extra:.1%} | {fraction:.1%} |')
    lines.extend(['', '## At-most-K oracle envelope', '',
                  'These sets can be smaller than their cap and need not be nested. '
                  'They include singleton and ablation candidates, so a budget is never filled with unhelpful padding.', '',
                  '| Cap | Actual history outputs | Replay/check ms | Search ops | Conflicts | Total ms |',
                  '|---:|---:|---:|---:|---:|---:|'])
    for cap in CAPS:
        lines.append(table_row(str(cap), lookup['ORACLE_AT_MOST', str(cap)]))
    lines.extend(['', '## Conditional RANKED and RANDOM controls', '',
                  '| K | RANKED ops / ms | RANDOM median ops [seed range] / median ms | ORACLE exact ops / ms |',
                  '|---:|---:|---:|---:|'])
    for cap in CAPS:
        ranked = lookup['RANKED', str(cap)]
        oracle = lookup['ORACLE_EXACT', str(cap)]
        randoms = [lookup[f'RANDOM_{seed}', str(cap)] for seed in (17, 29, 43)]
        ops = [r['analysis_resolution_steps'] for r in randoms]
        lines.append(f'| {cap} | {ranked["analysis_resolution_steps"]:,} / {ranked["total_wall_seconds"]*1000:.2f} | '
                     f'{median(ops):,} [{min(ops):,}–{max(ops):,}] / '
                     f'{median(r["total_wall_seconds"] for r in randoms)*1000:.2f} | '
                     f'{oracle["analysis_resolution_steps"]:,} / {oracle["total_wall_seconds"]*1000:.2f} |')
    lines.extend(['', '## Leave-one-out ablation of frozen exact-K winners', '',
                  'Positive delta means removal hurt search. Negative means removal improved it; '
                  'this exposes local non-optimality and does not imply additive lemma utilities.', '',
                  '| K | Removal hurts | Removal helps | No ops change | Min / median / max delta ops |',
                  '|---:|---:|---:|---:|---:|'])
    for cap in CAPS:
        values = [r['delta_ops'] for r in discovery['ablations'][str(cap)]]
        lines.append(f'| {cap} | {sum(v > 0 for v in values)} | {sum(v < 0 for v in values)} | '
                     f'{sum(v == 0 for v in values)} | {min(values):,} / {median(values):,} / {max(values):,} |')
    ex = metadata['exclusions']
    lines.extend(['', '## Discovery cost, coverage and accounting', '',
        f'- Historical population: {ex["eligible_before"]:,} eligible before exclusions, '
        f'{ex["eligible_after"]:,} afterward. Removed {ex.get("exact_template_duplicates", 0)} exact TEMPLATE '
        f'duplicates, {ex.get("template_subsumed", 0)} TEMPLATE-subsumed outputs, '
        f'{ex.get("encoding_only", 0)} encoding-only outputs.',
        f'- Screened {discovery["singletons_screened"]:,} singleton candidates '
        f'({discovery["singletons_screened"]/discovery["population"]:.1%} of eligible population). '
        'Subset search also samples from the full population.',
        f'- {discovery["unique_evaluations"]:,} unique fresh-solver discovery evaluations; '
        f'{discovery["current_invocation_wall_seconds"]:.1f} s current invocation wall, '
        f'{discovery["sum_screen_process_seconds"]:.1f} s summed concurrent process durations. '
        f'Initial cached evaluations: {discovery["initial_cached_evaluations"]}.',
        f'- Discovery statuses: {discovery["statuses"]}.',
        '- Oracle sets are best **observed**, not globally optimal. Oracle uses the evaluation target itself; '
        'this establishes existence for this target/backend, not cheap predictability or generalization.',
        '- All routes receive preselected IDs. Timed query wall includes fresh TEMPLATE/history support '
        'materialization and checks, serialization, native process startup/parse/search/proof output and '
        'artifact hashing. Offline source loading/checking/indexing, eligibility and oracle discovery are '
        'excluded and reported separately. This is not the previous curve\'s selector-inclusive timing.',
        '- The 67 TEMPLATE clauses are a checked same-family control, not proven universal graph-coloring '
        'axioms. Removing duplicates/subsumption does not prove semantic novelty of every remaining clause.',
        f'- Audit passed for {audit["final_runs"]} final runs and {audit["completion_certificates"]} distinct '
        'oracle completion certificates, checked against the original target. Certificate reconstruction '
        'is an additional offline audit cost, not part of query time or a scalable producer implementation.', '',
        'Reproduce: `.venv/bin/python oracle_lemma.py`, then '
        '`.venv/bin/python oracle_lemma_evaluate.py`, `.venv/bin/python audit_oracle_lemma.py`, '
        'and `.venv/bin/python oracle_lemma_report.py` (matplotlib required).'])
    (directory/'report.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
