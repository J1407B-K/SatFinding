"""Reproducible SATLIB RTI -> BMS benchmark. Reads archives without extracting."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import statistics
import tarfile
from time import perf_counter

from research import CanonicalCache, ExactCache, SemanticCache, glucose_sat
from satcache import check, normalize, variables

SOURCE = "https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/BMS/"


def dimacs(text):
    clauses, current, header = [], [], None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p"):
            _, fmt, n, m = line.split()
            if fmt != "cnf" or header is not None:
                raise ValueError("Bad DIMACS header")
            header = int(n), int(m)
            continue
        for token in line.split():
            x = int(token)
            if x == 0:
                clauses.append(current)
                current = []
            else:
                current.append(x)
    if header is None or current or len(clauses) != header[1]:
        raise ValueError("Incomplete DIMACS")
    if any(abs(x) > header[0] for c in clauses for x in c):
        raise ValueError("Variable exceeds header")
    return normalize(clauses)


def archive(path):
    entries = {}
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith(".cnf"):
                raw = tar.extractfile(member).read()
                idx = int(Path(member.name).stem.rsplit("_", 1)[1])
                if idx in entries:
                    raise ValueError("Duplicate instance ID")
                entries[idx] = (Path(member.name).name, dimacs(raw.decode()), sha256(raw).hexdigest())
    return entries


def execute(seed, queries, mode, prefilter=True):
    cache = {"none": lambda: None, "exact": ExactCache, "canonical": CanonicalCache,
             "semantic": lambda: SemanticCache(prefilter=prefilter),
             "structural": lambda: SemanticCache(structural_only=True, prefilter=prefilter)}[mode]()
    rows = []
    for phase, entries in (("seed", seed), ("query", queries)):
        for name, formula, digest in entries:
            start = perf_counter()
            cert = cache.lookup(formula) if cache is not None else None
            lookup_end = perf_counter()
            hit = cert is not None
            source = cache.last_source if hit else None
            if not hit:
                cert = glucose_sat(formula)
            solve_end = perf_counter()
            # Same final acceptance boundary in every arm.
            if cert is None or not check(formula, cert):
                raise ValueError(f"No verified SAT certificate: {name}")
            verify_end = perf_counter()
            if not hit and cache is not None:
                cache.add(formula, cert, name)
            end = perf_counter()
            rows.append(dict(phase=phase, name=name, sha256=digest, clauses=len(formula),
                             hit=hit, source=source, seconds=end-start,
                             lookup_seconds=lookup_end-start, solve_seconds=solve_end-lookup_end,
                             verify_seconds=verify_end-solve_end, insert_seconds=end-verify_end))
    return rows


def report(result):
    lines = ["# SATLIB RTI/BMS measured results", "",
             "All times include cache lookup, solving, certificate checks, and insertion. "
             "Seed cost is included in total. Common archive loading/normalization and result "
             "serialization are excluded. Values are medians of complete runs, in seconds.", "",
             "| Mode | Seed s | Query s | Total s | Query hits | Net speedup |",
             "|---|---:|---:|---:|---:|---:|"]
    summary = {}
    for mode in result["modes"]:
        runs = [r for r in result["runs"] if r["mode"] == mode]
        seed = statistics.median(sum(x["seconds"] for x in r["rows"] if x["phase"] == "seed") for r in runs)
        query = statistics.median(sum(x["seconds"] for x in r["rows"] if x["phase"] == "query") for r in runs)
        total = statistics.median(sum(x["seconds"] for x in r["rows"]) for r in runs)
        hits = statistics.median(sum(x["hit"] for x in r["rows"] if x["phase"] == "query") for r in runs)
        summary[mode] = dict(seed=seed, query=query, total=total, hits=hits)
    baseline = summary["none"]["total"]
    for mode, s in summary.items():
        lines.append(f"| {mode} | {s['seed']:.6f} | {s['query']:.6f} | {s['total']:.6f} | {s['hits']:g} | {baseline/s['total']:.3f}x |")
    lines += ["", "## Scope", "",
              f"Official, unmodified instances: {result['pairs']} RTI and {result['pairs']} BMS. "
              "All RTI are processed first; BMS query order is independently shuffled with a fixed seed. "
              "No pair ID or filename is passed to retrieval. This is a deliberately related workload, "
              "not an independent-source generalization test. No model is trained.", "",
              "`semantic` uses aligned-variable clause-incidence vectors; `structural` is the "
              "name-invariant width/degree histogram ablation. Canonical uses exact colored-graph "
              "canonicalization allowing variable permutation and polarity flips. All modes use Glucose3.", "",
              "Raw per-instance timing, archive/instance hashes, order, versions, and accepted source IDs "
              "are in the adjacent JSON. SAT witnesses are rechecked during every run. "
              "These timings do not establish performance on UNSAT, production traces, or neural embeddings."]
    result["summary"] = summary
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rti", required=True)
    parser.add_argument("--bms", required=True)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default="results/satlib.json")
    parser.add_argument("--no-prefilter", action="store_true")
    args = parser.parse_args()
    import pysat
    import pynauty
    load_start = perf_counter()
    rti, bms = archive(args.rti), archive(args.bms)
    load_seconds = perf_counter()-load_start
    if set(rti) != set(bms):
        raise ValueError("Mismatched official archive IDs")
    ids = sorted(rti)[:args.limit]
    if not ids or args.repeats < 1:
        raise ValueError("Positive sample size and repeats required")
    for i in ids:
        if not set(bms[i][1]) < set(rti[i][1]):
            raise ValueError(f"Pair {i} is not a strict subformula")
    seed = [rti[i] for i in ids]
    query_ids = ids.copy()
    random.Random(20260909).shuffle(query_ids)
    queries = [bms[i] for i in query_ids]
    modes = ["none", "exact", "canonical", "semantic", "structural"]
    result = dict(pairs=len(ids), repeats=args.repeats, modes=modes,
                  prefilter=not args.no_prefilter, top_k=8, shared_load_seconds=load_seconds,
                  code_sha256={p: sha256(Path(p).read_bytes()).hexdigest()
                               for p in ("satcache.py", "research.py", "benchmark.py")},
                  python=platform.python_version(), platform=platform.platform(),
                  pysat=pysat.__version__, pynauty=pynauty.__version__,
                  dataset_description=SOURCE+"descr_BMS.html",
                  archives={kind: dict(url=SOURCE+f"{kind}_k3_n100_m429.tar.gz",
                                      sha256=sha256(Path(path).read_bytes()).hexdigest())
                            for kind, path in (("RTI", args.rti), ("BMS", args.bms))}, runs=[])
    # Untimed import/startup warmup is identical for all experimental arms.
    glucose_sat(normalize([[1]]))
    for repeat in range(args.repeats):
        order = modes[repeat % len(modes):] + modes[:repeat % len(modes)]
        for mode in order:
            rows = execute(seed, queries, mode, prefilter=not args.no_prefilter)
            result["runs"].append(dict(repeat=repeat, mode=mode, rows=rows))
            print(f"repeat={repeat} mode={mode} seconds={sum(x['seconds'] for x in rows):.3f} "
                  f"query_hits={sum(x['hit'] for x in rows if x['phase']=='query')}", flush=True)
    # Independently certify an extra-reuse witness by invariant, not a canonical miss.
    semantic_rows = next(r["rows"] for r in result["runs"] if r["mode"] == "semantic")
    all_formulas = {name: f for name, f, _ in seed+queries}
    extra = []
    for row in semantic_rows:
        if row["phase"] == "query" and row["hit"]:
            source = all_formulas[row["source"]]
            if len(source) != row["clauses"]:
                extra.append(dict(query=row["name"], source=row["source"],
                                  source_clauses=len(source), query_clauses=row["clauses"]))
    result["nonisomorphic_reuse_witnesses"] = extra
    text = report(result)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+"\n")
    output.with_suffix(".md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
