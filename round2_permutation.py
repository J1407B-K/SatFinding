"""Independent renaming intervention; private correspondence is evaluation-only."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
from time import perf_counter

from benchmark import archive
from research import glucose_sat
from satcache import Certificate, check, normalize, variables
from structural import Retriever, reuse_sat

METHODS = ("random", "exact", "canonical", "jaccard", "minhash", "tfidf", "bm25", "wl")


def rename(formula, rng):
    vs = variables(formula)
    names = list(range(1, len(vs)+1))
    rng.shuffle(names)
    mapping = dict(zip(vs, names))
    renamed = normalize([[mapping[abs(x)]*(1 if x > 0 else -1) for x in c] for c in formula])
    return renamed, mapping


def prepare(rti, bms, seed, limit):
    rng = random.Random(seed)
    ids = sorted(set(rti) & set(bms))[:limit]
    histories, queries, private = [], [], []
    for i in ids:
        h, hm = rename(rti[i][1], rng)
        q, qm = rename(bms[i][1], rng)
        histories.append(h)
        queries.append(q)
        private.append(dict(original_id=i, query_to_history={qm[v]: hm[v] for v in qm}))
    # Neither rank ties nor positional order can reveal the parent.
    order = list(range(len(ids)))
    rng.shuffle(order)
    inverse = {old: new for new, old in enumerate(order)}
    histories = [histories[i] for i in order]
    for i, truth in enumerate(private):
        truth["history_index"] = inverse[i]
    qorder = list(range(len(ids)))
    rng.shuffle(qorder)
    return histories, [queries[i] for i in qorder], [private[i] for i in qorder]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rti", default="/tmp/satcache-rti.tar.gz")
    p.add_argument("--bms", default="/tmp/satcache-bms.tar.gz")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--seeds", type=int, nargs="+", default=[7101, 7102, 7103])
    p.add_argument("--match-queries", type=int, default=20)
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--seconds", type=float, default=0.25)
    p.add_argument("--output", default="results/round2-permutation.json")
    args = p.parse_args()
    rti, bms = archive(args.rti), archive(args.bms)
    result = dict(settings=vars(args), description="Official SATLIB formulas independently renamed; "
                  "all retrieval queries, matching on first shuffled sample for first seed only.",
                  code_sha256={f: sha256(Path(f).read_bytes()).hexdigest()
                               for f in ("structural.py", "round2_permutation.py", "satcache.py")},
                  archive_sha256={"rti": sha256(Path(args.rti).read_bytes()).hexdigest(),
                                  "bms": sha256(Path(args.bms).read_bytes()).hexdigest()}, runs=[])
    private_runs = []
    for seed in args.seeds:
        histories, queries, truth = prepare(rti, bms, seed, args.limit)
        private_runs.append(dict(seed=seed, ground_truth=truth))
        certificates = [glucose_sat(h) for h in histories]
        # Feasibility control only. These maps never enter Retriever or reuse_sat.
        for query, t in zip(queries, truth):
            model = certificates[t["history_index"]].assignment
            oracle = Certificate("SAT", assignment={v: model[w] for v, w in t["query_to_history"].items()})
            assert check(query, oracle)
        run = dict(seed=seed, oracle_verified=len(queries), methods={})
        sample = min(args.match_queries, len(queries)) if seed == args.seeds[0] else 0
        for method in METHODS:
            start = perf_counter()
            retriever = Retriever(histories, method)
            build_seconds = perf_counter()-start
            ranks, rankings, retrieval_seconds = [], [], 0.0
            for query, t in zip(queries, truth):
                start = perf_counter()
                ranking, scores = retriever.rank(query)
                retrieval_seconds += perf_counter()-start
                target = t["history_index"]
                ranks.append(ranking.index(target)+1 if target in ranking else None)
                rankings.append(ranking[:args.top_k])
            data = dict(build_seconds=build_seconds, retrieval_seconds=retrieval_seconds,
                        recall={str(k): sum(r is not None and r <= k for r in ranks)/len(ranks)
                                for k in (1, 3, 8, 32)},
                        mrr=sum(1/r if r else 0 for r in ranks)/len(ranks), parent_ranks=ranks,
                        matches=[])
            for qi in range(sample):
                attempts, accepted = [], None
                start = perf_counter()
                for hi in rankings[qi]:
                    cert, mapping, status, elapsed = reuse_sat(histories[hi], certificates[hi], queries[qi], args.seconds)
                    attempts.append(dict(history_index=hi, status=status, seconds=elapsed))
                    if cert is not None:
                        assert check(queries[qi], cert)
                        accepted = dict(history_index=hi, mapping=mapping, assignment=cert.assignment)
                        break
                lookup_seconds = perf_counter()-start
                fallback_start = perf_counter()
                if accepted is None:
                    assert glucose_sat(queries[qi]) is not None
                data["matches"].append(dict(query_index=qi, attempts=attempts, accepted=accepted,
                                            lookup_seconds=lookup_seconds,
                                            fallback_seconds=perf_counter()-fallback_start))
                if (qi+1) % 10 == 0:
                    print(f"seed={seed} method={method} matching={qi+1}/{sample}", flush=True)
            run["methods"][method] = data
            print(f"seed={seed} method={method} recall@3={data['recall']['3']:.3f} "
                  f"verified={sum(x['accepted'] is not None for x in data['matches'])}/{sample}", flush=True)
        # Oracle candidate-selection ablation: matcher still receives no mapping.
        run["oracle_candidate_matches"] = []
        for qi in range(sample):
            hi = truth[qi]["history_index"]
            cert, mapping, status, elapsed = reuse_sat(histories[hi], certificates[hi], queries[qi], args.seconds)
            run["oracle_candidate_matches"].append(dict(query_index=qi, status=status, seconds=elapsed,
                                                        mapping=mapping, verified=cert is not None))
        result["runs"].append(run)
    out = Path(args.output)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+"\n")
    out.with_name(out.stem+"-private.json").write_text(json.dumps(private_runs, indent=2)+"\n")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
