# Replay budget curve

Frozen before this run: n200_r01 (primary, 1% edge drift), n200_r05 and
n200_independent from the existing homologous experiment. No regenerated targets,
no automatic mapping, no outcome-selected colors: identity vertices and colors.
Do not change the ranking after viewing this curve.

Budgets: 0, 32, 128, 512, 2048, 8192, 32768, ALL. K counts unique, strictly
replayable, non-input Resolution clauses supplied to completion. These include
intermediate Resolution clauses, not just original CDCL learned clauses.
An unavailable K saturates at the eligible population; plot actual lemma count.
Zero is shared BLIND. Only selected outputs enter the solver; support ancestors
are checked but not injected. Therefore K does not bound support reconstruction.

HISTORY uses G6202. TEMPLATE uses held-out U6302 with the same ranking.
RANDOM uses three uniform random permutations (seeds 17,29,43) of historical
nodes, filtered to one canonical eligible derivation per unique clause. Each
seed defines nested subsets. All selected clauses enter completion in source
topological order, including ALL, so insertion order is not another intervention.

Deterministic source-only score:
`(1 + direct historical uses) / ((1 + clause width) * (1 + left width + right width))`.
Rational comparison; source node ID breaks ties. Direct uses come from the
already contradiction-sliced historical refutation. Local parent width is only
a replay cost proxy. It is not exact ancestor cost and utility is not measured
on the current target. No claim that this score is optimal.

Load, source verification and index/ranking construction are offline, separately
reported. Every query freshly scans eligibility and filters the fixed ranking;
then traverses just the selected ancestor union and checks it with the existing
ProofContext. This still loads an already expanded Resolution DAG. It is NOT
lazy reconstruction from raw DRUP and does not solve the n300 conversion failure.
Keep that limitation visible; future producer work needs support hints/indexing
to avoid full DRUP-to-Resolution conversion before selection.

Three repetitions, randomized configuration order with fixed scheduler seeds,
one untimed BLIND warm-up per target. Record raw native counters, status,
replay/check time, eligibility/selection time, materialization time, checker time,
support steps/literal-work proxy, solver time and total query wall time. Total
includes selection, checking, DIMACS writing, process startup, native parse/search,
proof output and artifact hashing. It excludes cold source/index construction,
post-run selection artifact export and final completion proof reconstruction.
Native `seconds` includes DIMACS parsing; search work means
`analysis_resolution_steps`, with other native counters retained separately.
UNSAT completion is solver-reported; replay support is independently checked.

Record median and min/max wall time, never minimum-time winner. Each random
seed is reported individually; summarize their distribution separately from
timing repetition noise. An additional LEGACY_FULL reproduces old all-DAG
replay and checks exact equality of ALL lemma sequence and search counters.
Pareto means jointly non-dominated in measured search ops and median total
query time, including BLIND. Report unfavorable/nonmonotonic curves honestly.
