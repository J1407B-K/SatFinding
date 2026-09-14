# Persistent memory stream: frozen protocol

2026-09-11, before generation or solving: T5..T54 use seeds9205..9254 in
ascending order. Exactly50 new queries, no outcome filtering or replacement.
Use unchanged `homologous_graphs.evolve(200,H.edges,0.01,seed)` and encoding.
Check hashes against T1..T4 and prior saved same-family inputs, and each other.

Reuse `unseen_selector.candidates`, `select`, `template_data`, existing prior
contents, `HistoryIndex.materialize` and native `Evaluator.solve` unmodified.
Verify all prior experiment source hashes. Same H, 512 candidates, K64, 4096
resolution-attempt/100ms generation guard, 512 feature evaluations/50ms selection
guard, fixed67 TEMPLATE, one-step64-clause validation, original native settings.
No Oracle. No online adaptation, prior updates, feature changes or selector tuning.

Load the gzip archive losslessly once, verify original uncompressed prior hash;
retain all246003 scores. Record current loading separately. Main amortization
lines use the requested frozen costs0.82s and3.87s (also report exact previous
0.822510125s and3.870796375s sensitivity). No per-query prior startup charges.

Freeze all50 target inputs and both online selections before any completion.
If frozen TEMPLATE or another frozen pipeline component is inapplicable, record
that failure against the original query; never replace its seed, silently filter
it out, inject unchecked clauses or change the algorithm. Report protocol failure
rather than pretend the complete50-query experiment passed.

Same previous repetition method: five fresh solver runs per target/route,
TEMPLATE/TARGET/HISTORY,750 jobs globally shuffled by seed20260911 and executed
sequentially. Logical query stream order is seed order, independent of measurement
job order. Full warm timing includes generation, ranking/retrieval, checked
validation, temporary CNF writing, process execution and result parsing. Inputs
and prior already in memory; no raw DRUP files. Append measured runs immediately.

Per target use median of its5 repetitions. Improvement=1-H/T; report arithmetic
mean and median of per-target percentages, plus aggregate ratios separately.
Ops ties are exact; time wins use median totals with no post-hoc tolerance.
Cumulative saving sums per-target median TARGET_total-HISTORY_total. Report first
crossing of each line, subsequent recrossing, final net margin and sustained
crossing (all later prefixes remain above). Show all ratios and cumulative curve.

Stability: report positive/negative saving sums, top1/top5/top10 gain contributions,
net saving after removing top5 winners (diagnostic only),5 blocks of10 queries,
mean/median differences and fixed-seed10000 paired target bootstrap intervals.
Bootstrap does not create independent families. Also recompute50-query cumulative
curve for each repetition index to show timing repeatability without extra solves.

Decision uses user's gates: ALIVE requires >25/50 ops wins, positive median ops
and warm total improvements, final cumulative saving>=0.82s; AMORTIZED_BUILD_PASS
requires final saving>=3.87s. Report bootstrap stability as qualification, not a
substitute for gates. WEAK if positive aggregate signal exists but wins/medians/
amortization fail. STOP if ops/time essentially flat or worse (median ops<=0
and median time<=0), or cumulative trend fails (final saving<=0 and at least3/5
10-query blocks have nonpositive net saving). No lowering gates after results.


## Authorized soundness-preserving protocol amendment

Recorded UTC: 2026-09-11T03:06:31.488219+00:00. User explicitly authorized this amendment after preflight,
before ANY solve on T5..T54. It supersedes only the fixed67 applicability/failure
rule above; all other algorithm and measurement rules remain frozen.

Baseline description: **frozen TEMPLATE-67 source set with per-target soundness filtering**.

For ALL50 frozen targets, including the40 with all67 valid, filter the original67
outputs using the existing proof-premise availability criterion. Cache each
original root's premise support using existing `ancestors`; test support against
current CNF, then replay/check the retained roots through the unchanged
`HistoryIndex.materialize`. Do not replace premises, repair proofs, fill back to67
or infer validity from the target's eventual UNSAT result. All3 routes share the
same retained outputs in the same original source-ID order.

Record `template_valid_count`, `invalid_template_ids` (original source root IDs),
and `valid_template_hash` per target before solve and on every measured run.
Hash is SHA256 of the existing `digest` serialization of the ordered retained
clauses. Filtering and checked validation are included in warm pipeline time;
source-support preprocessing is shared with all3 routes.

Keep all50 targets and seeds, prior, original512-candidate pool, original64 chosen
outputs, K, generation/selection budgets and native solver/settings unchanged.
Candidate generation STILL uses the original67-clause exclusion list. Repeated
ranking only re-evaluates identical frozen inputs for timing and asserts identical
selected IDs; no reselection based on the changed TEMPLATE is permitted.
No target deletion, outcome screening, replenishment, feature changes or Oracle.

Original driver/protocol are archived with their preparation hashes. The amendment
manifest records this protocol and measurement-driver hashes, original frozen
selection/seed/input hashes, and the UTC timestamp. A separate execution-start
record links that manifest and the complete per-target validity table before any
native completion call. The original metadata is retained without rewriting its
pre-amendment provenance.
