"""Controlled non-parent formulas with shared certified UNSAT motifs."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import random
from time import perf_counter

from pysat.solvers import Glucose3

from research import canonical, glucose_sat
from round2_permutation import rename
from satcache import check, normalize, solve, transfer, variables
from structural import Retriever, reuse_unsat


def satisfiable(formula):
    # Generator only, never an acceptance path in the cache.
    with Glucose3(bootstrap_with=formula) as solver:
        return solver.solve()


def clauses(rng, vs, count, width):
    return [tuple(v*rng.choice((-1, 1)) for v in rng.sample(vs, width)) for _ in range(count)]


def motif_bank(count, seed):
    rng = random.Random(seed)
    bank, seen = [], set()
    for attempt in range(20000):
        f = normalize(clauses(rng, list(range(1, 9)), 22, 2))
        if satisfiable(f):
            continue
        core = list(f)
        rng.shuffle(core)
        for c in list(core):
            candidate = [d for d in core if d != c]
            if not satisfiable(candidate):
                core = candidate
        core = normalize(core)
        if len(variables(core)) < 6:
            continue
        key = canonical(core)[0]
        if key in seen:
            continue
        cert = solve(core)
        if cert is None or cert.kind != "UNSAT" or not check(core, cert):
            continue
        seen.add(key)
        bank.append((core, cert))
        if len(bank) == count:
            return bank
    raise RuntimeError(f"Generated only {len(bank)} distinct motifs")


def context(rng, core, binary_noise, ternary_count):
    vs = sorted(set(variables(core)) | set(range(1, 41)))
    while True:
        noise = normalize(clauses(rng, vs, ternary_count, 3)+clauses(rng, vs, binary_noise, 2))
        if satisfiable(noise):
            return normalize(list(core)+list(noise))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=24)
    p.add_argument("--seed", type=int, default=7201)
    p.add_argument("--seconds", type=float, default=0.25)
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--output", default="results/round2-motif.json")
    args = p.parse_args()
    start = perf_counter()
    bank = motif_bank(args.count, args.seed)
    bank_seconds = perf_counter()-start
    result = dict(settings=vars(args), bank_seconds=bank_seconds,
                  code_sha256={f: sha256(Path(f).read_bytes()).hexdigest()
                               for f in ("round2_motif.py", "structural.py", "satcache.py")}, variants={})
    private_variants = {}
    for variant, noise in (("ternary_context_control", 0), ("mixed_binary_context", 12)):
        rng = random.Random(args.seed+noise)
        histories, certificates, queries, truth = [], [], [], []
        for idx, (core, cert) in enumerate(bank):
            h_original = context(rng, core, noise, 80)
            q_original = context(rng, core, noise, 110)
            assert not set(h_original) <= set(q_original) and not set(q_original) <= set(h_original)
            h, hm = rename(h_original, rng)
            q, qm = rename(q_original, rng)
            hc = transfer(cert, hm)
            qc = transfer(cert, qm)
            assert check(h, hc) and check(q, qc)
            assert len(h) != len(q)
            histories.append(h)
            certificates.append(hc)
            queries.append(q)
            truth.append(dict(parent=idx, oracle_certificate=asdict(qc)))
        # True-negative queries contain only unrelated noise and have checked SAT models.
        for _ in range(max(4, args.count//2)):
            while True:
                q = context(rng, (), noise, 110)
                model = glucose_sat(q)
                if model is not None:
                    break
            q, _ = rename(q, rng)
            queries.append(q)
            truth.append(dict(parent=None))
        order = list(range(len(histories)))
        rng.shuffle(order)
        inverse = {old: new for new, old in enumerate(order)}
        histories = [histories[i] for i in order]
        certificates = [certificates[i] for i in order]
        for t in truth:
            if t["parent"] is not None:
                t["parent"] = inverse[t["parent"]]
        order = list(range(len(queries)))
        rng.shuffle(order)
        queries, truth = [queries[i] for i in order], [truth[i] for i in order]
        private_variants[variant] = truth
        data = dict(histories=histories, history_certificates=[asdict(c) for c in certificates],
                    queries=queries, positive_queries=args.count, negative_queries=len(queries)-args.count,
                    methods={})
        # Certificate-aware view is generic binary projection, NOT oracle motif extraction.
        # The mixed variant deliberately adds same-width distractors and attachments.
        configs = [(m, m, False) for m in ("random", "exact", "canonical", "jaccard", "minhash", "tfidf", "bm25", "wl")]
        configs += [("proof_wl", "wl", True), ("proof_canonical", "canonical", True)]
        for label, method, proof_view in configs:
            docs = [c.premises for c in certificates] if proof_view else histories
            views = [normalize(c for c in q if len(c) <= 2) for q in queries] if proof_view else queries
            start = perf_counter()
            retriever = Retriever(docs, method)
            build_seconds = perf_counter()-start
            rows = []
            for qi, (q, view, t) in enumerate(zip(queries, views, truth)):
                start = perf_counter()
                ranking, _ = retriever.rank(view)
                retrieval_seconds = perf_counter()-start
                attempts, accepted = [], None
                for hi in ranking[:args.top_k]:
                    cert, mapping, status, elapsed = reuse_unsat(certificates[hi], q, args.seconds)
                    attempts.append(dict(history_index=hi, status=status, seconds=elapsed))
                    if cert is not None:
                        assert check(q, cert)
                        if t["parent"] is None:
                            raise AssertionError("UNSAT accepted on a SAT control")
                        accepted = dict(history_index=hi, mapping=mapping, certificate=asdict(cert))
                        break
                rows.append(dict(query_index=qi, parent_rank=(ranking.index(t["parent"])+1
                                 if t["parent"] in ranking else None), retrieval_seconds=retrieval_seconds,
                                 attempts=attempts, accepted=accepted, positive=t["parent"] is not None))
            data["methods"][label] = dict(build_seconds=build_seconds, rows=rows)
            print(f"{variant} {label}: verified={sum(r['accepted'] is not None for r in rows)}/{args.count}", flush=True)
        result["variants"][variant] = data
    out = Path(args.output)
    out.write_text(json.dumps(result, indent=2)+"\n")
    out.with_name(out.stem+"-private.json").write_text(json.dumps(private_variants, indent=2)+"\n")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
