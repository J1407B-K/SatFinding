"""Larger, fixed-prefix matching evaluation, without hidden maps in the matcher."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

from benchmark import archive
from research import glucose_sat
from round2_permutation import prepare
from satcache import check
from structural import Retriever, reuse_sat


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=int, default=100)
    p.add_argument("--seconds", type=float, default=0.25)
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--output", default="results/round2-matching.json")
    args = p.parse_args()
    h, q, private = prepare(archive('/tmp/satcache-rti.tar.gz'), archive('/tmp/satcache-bms.tar.gz'), 7101, 500)
    certs = [glucose_sat(f) for f in h]
    result = dict(settings=vars(args), seed=7101, history_count=len(h), methods={},
                  note="Fixed first 100 shuffled queries, including original pilot's first 20. "
                       "Oracle mode supplies candidate index only, never a variable mapping.",
                  code_sha256={f: sha256(Path(f).read_bytes()).hexdigest()
                               for f in ("structural.py", "round2_match_eval.py")})
    for method in ("random", "jaccard", "minhash", "tfidf", "bm25", "wl", "oracle_candidate"):
        retriever = Retriever(h, method) if method != "oracle_candidate" else None
        rows = []
        for qi, query in enumerate(q[:args.queries]):
            start = perf_counter()
            ranking = retriever.rank(query)[0][:args.top_k] if retriever else [private[qi]["history_index"]]
            rank_seconds = perf_counter()-start
            start = perf_counter()
            attempts, accepted = [], None
            for hi in ranking:
                cert, mapping, status, elapsed = reuse_sat(h[hi], certs[hi], query, args.seconds)
                attempts.append(dict(history_index=hi, status=status, seconds=elapsed))
                if cert is not None:
                    assert check(query, cert)
                    accepted = dict(history_index=hi, mapping=mapping, assignment=cert.assignment)
                    break
            rows.append(dict(query_index=qi, attempts=attempts, accepted=accepted,
                             retrieval_seconds=rank_seconds, lookup_seconds=perf_counter()-start,
                             parent_retrieved=private[qi]["history_index"] in ranking))
            if (qi+1) % 20 == 0:
                print(f"{method}: {qi+1}/{args.queries}, verified={sum(r['accepted'] is not None for r in rows)}", flush=True)
        result["methods"][method] = rows
        # Checkpoint each completed arm for long native-matcher runs.
        Path(args.output).write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
