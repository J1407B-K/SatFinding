"""Aggregate Round 3 without treating censored solver times as solved times."""
import argparse
import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix',default='results/round3')
    args = ap.parse_args()
    prefix = args.prefix
    config = json.loads(Path(prefix+'_metadata.json').read_text())['arguments']
    rows = [json.loads(line) for line in Path(prefix+'_raw.jsonl').read_text().splitlines()]
    groups = defaultdict(list)
    for r in rows:
        groups[r['n'],r['planted_depth'],r['kind'],r['mode']].append(r)
    summaries = []
    metrics = ['total_time','discovery_time','resolution_check_time','parity_registration_time',
        'GF2_time','GF2_check_time','recovered_fraction','recovered_parities',
        'candidate_attempts','candidate_accepts','candidate_rejects','resolution_candidate_attempts',
        'resolution_DAG_nodes','resolution_DAG_edges','checked_resolution_steps','GF2_DAG_nodes',
        'GF2_steps','certificate_bytes','input_bytes','total_input_vars','total_input_clauses',
        'certificate_per_input','discovery_per_clause','checked_steps_per_recovered',
        'attempts_per_accepted','proof_sharing_ratio','preprocess_time','processed_clauses']
    for (n,d,kind,mode),rs in sorted(groups.items()):
        out = dict(n=n,planted_depth=d,kind=kind,mode=mode,cases=len(rs),
                   solved=sum(r['status']==kind for r in rs),
                   unknown=sum(r['status'] in ('UNKNOWN','TIMEOUT') for r in rs))
        for key in metrics:
            values = [r[key] for r in rs if isinstance(r.get(key),(int,float))]
            if values:
                out['median_'+key] = st.median(values)
        summaries.append(out)
    with open(prefix+'_summary.csv','w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=sorted(set().union(*(r.keys() for r in summaries))))
        writer.writeheader()
        writer.writerows(summaries)
    lines = ['# Round 3: derived parity discovery', '',
        'A = Glucose3; B = CNF-only CryptoMiniSat 5.14.7; C = CaDiCaL preprocessing (3 rounds) + the same CryptoMiniSat; D = blind complementary-pair resolution + canonical parity registration + GF(2); E = privileged original XOR equations.', '',
        f"All solver timings are single-run observations. A/B/C have a {config['seconds']:g}-second solver budget and a {config['seconds']+10:g}-second worker watchdog; preprocessing/loading are additional. D has {config['step_budget']:,} resolution-step and {config['attempt_budget']:,} resolution-candidate budgets, not the same wall-time budget. No claim of matched-budget runtime superiority is made. UNKNOWN/TIMEOUT observations are censored.", '',
        '## UNSAT completion and recovered relations', '',
        '| n | depth | A solved | B solved | C solved | D verified | E solved | C median recovery | D median recovery |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    index = {(r['n'],r['planted_depth'],r['kind'],r['mode']):r for r in summaries}
    for n,d in sorted({(r['n'],r['planted_depth']) for r in rows}):
        modes = [index[n,d,'UNSAT',m] for m in 'ABCDE']
        counts = ' | '.join(f"{r['solved']}/{r['cases']}" for r in modes)
        c,drow = modes[2:4]
        c_recovery = c.get('median_recovered_fraction')
        ctxt = 'N/A' if c_recovery is None else f'{c_recovery:.1%}'
        lines.append(f"| {n} | {d} | {counts} | {ctxt} | {drow['median_recovered_fraction']:.1%} |")
    lines += ['', '## D: search, proof and input costs (UNSAT medians)', '',
        '| n | depth | input clauses | checked resolution steps | candidate attempts | discovery s | check s | total s | certificate/input bytes | sharing |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summaries:
        if r['kind']!='UNSAT' or r['mode']!='D':
            continue
        check_time = sum(r['median_'+k] for k in ('resolution_check_time','parity_registration_time','GF2_check_time'))
        lines.append(f"| {r['n']} | {r['planted_depth']} | {r['median_total_input_clauses']:.0f} | {r['median_checked_resolution_steps']:.0f} | {r['median_candidate_attempts']:.0f} | {r['median_discovery_time']:.4f} | {check_time:.4f} | {r['median_total_time']:.4f} | {r['median_certificate_per_input']:.2f} | {r['median_proof_sharing_ratio']:.2f} |")
    controls = [r for r in rows if r['kind']=='SAT' and r['mode']=='D']
    false_attempts = sum(r['false_parity_attempts'] for r in controls)
    false_rejects = sum(r['false_parity_checker_rejects'] for r in controls)
    lines += ['', '## Controls and interpretation', '',
        f'{len(controls)} planted SAT controls: no D UNSAT verdict. {false_attempts} deliberately false RHS proposals, {false_rejects} checker rejections. These proposals contradict the independently checked planted assignment; they are not merely proof-search misses.', '',
        'D does not solve SAT: MISS means no refutation, even when all parities are recovered. Baseline SAT models are checked on the original split CNF (C restores eliminated variables). Native UNSAT outputs are solver-reported, not replayed by the D checker. D certificates are separately replayed by audit_round3.py.', '',
        'The blind algorithm uses no split IDs or original XOR scopes. It identifies variables with exactly two active occurrences and resolves identical clause remainders with opposite pivot signs. This is a restricted variable-elimination preprocessor, not evidence of novel abstraction search. C recovery measures exact original parities syntactically present in its output, assessed only by the harness after preprocessing; B internal recovery counts are unavailable.', '',
        'For this disjoint splitting construction, the known restoration uses 32*n*(2**depth-1) resolution steps and the input has 32*n*2**depth clauses. These are construction-specific counts, not minimum-proof claims. Shared proof ratio includes input leaves and counts per-parity ancestor sets versus their union; a value of 1 means no inter-parity sharing in these certificates.', '',
        'Discovery, resolution checking, parity registration, GF(2) generation/checking are timed separately. D total excludes input generation, imports, certificate serialization/compression, proof-sharing diagnostics and false-candidate control tests. Certificate bytes are uncompressed compact JSON; input bytes are exact DIMACS. Normalized metrics are in the raw and summary CSVs.', '',
        '[Protocol](../docs/round3-protocol.md). [PySAT preprocessing](https://pysathq.github.io/docs/html/api/process.html). [CryptoMiniSat](https://github.com/msoos/cryptominisat).']
    Path(prefix+'_report.md').write_text('\n'.join(lines)+'\n')
    print(f'Wrote {prefix}_report.md and {prefix}_summary.csv ({len(rows)} rows)')


if __name__ == '__main__':
    main()
