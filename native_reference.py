"""Stronger timing reference: bare Glucose, excluding certificate verification."""
import argparse
import json
from pathlib import Path
import random
import statistics
from time import perf_counter

from pysat.solvers import Glucose3

from benchmark import archive
from satcache import Certificate, check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rti", required=True)
    parser.add_argument("--bms", required=True)
    parser.add_argument("--results", default="results/satlib-optimized.json")
    args = parser.parse_args()
    reference = json.loads(Path(args.results).read_text())
    rti, bms = archive(args.rti), archive(args.bms)
    ids = sorted(rti)[:reference["pairs"]]
    shuffled = ids.copy()
    random.Random(20260909).shuffle(shuffled)
    formulas = [rti[i][1] for i in ids] + [bms[i][1] for i in shuffled]
    with Glucose3(bootstrap_with=[[1]]) as warmup:
        warmup.solve()
    totals = []
    for repeat in range(reference["repeats"]):
        total = 0.0
        for f in formulas:
            start = perf_counter()
            with Glucose3(bootstrap_with=f) as solver:
                status = solver.solve()
                model = solver.get_model()
            total += perf_counter()-start
            # Validation outside the native timing window; never trust status alone.
            cert = Certificate("SAT", assignment={abs(x): x > 0 for x in (model or [])})
            if not status or not check(f, cert):
                raise ValueError("Invalid SAT result")
        totals.append(total)
        print(f"native repeat={repeat} seconds={total:.6f}", flush=True)
    result = dict(note="Separate sequential measurement; Glucose initialization, solve, model "
                  "extraction and destruction only. Verification and cache overhead excluded "
                  "from native reference, but INCLUDED in semantic total.",
                  benchmark_sha256=__import__("hashlib").sha256(Path(args.results).read_bytes()).hexdigest(),
                  seconds=totals, median_seconds=statistics.median(totals),
                  semantic_total_seconds=reference["summary"]["semantic"]["total"],
                  speedup=statistics.median(totals)/reference["summary"]["semantic"]["total"])
    Path("results/native-reference.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
