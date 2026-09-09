"""Separate structural representation from retrieval scoring on identical WL tokens."""
import json
from pathlib import Path
from time import perf_counter

from benchmark import archive
from round2_permutation import prepare
from structural import Retriever, wl


def tokens(formula):
    return tuple(term for term, count in sorted(wl(formula).items()) for _ in range(count))


def main():
    h, q, truth = prepare(archive('/tmp/satcache-rti.tar.gz'), archive('/tmp/satcache-bms.tar.gz'), 7101, 500)
    start = perf_counter()
    docs = [tokens(f) for f in h]
    query_tokens = [tokens(f) for f in q]
    result = dict(seed=7101, pairs=500, representation="Same 0..2 WL literal-incidence tokens for all scorers",
                  shared_encoding_seconds=perf_counter()-start, methods={})
    for method in ("jaccard", "minhash", "tfidf", "bm25"):
        start = perf_counter()
        retriever = Retriever(docs, method)
        build_seconds = perf_counter()-start
        start = perf_counter()
        ranks = []
        for query, t in zip(query_tokens, truth):
            ranking, _ = retriever.rank(query)
            ranks.append(ranking.index(t["history_index"])+1)
        result["methods"][method] = dict(build_seconds=build_seconds,
                    retrieval_seconds=perf_counter()-start, parent_ranks=ranks,
                    recall={str(k): sum(r <= k for r in ranks)/len(ranks) for k in (1, 3, 8, 32)})
        print(method, result["methods"][method]["recall"], flush=True)
    Path('results/round2-feature-baselines.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
