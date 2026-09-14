# Frozen unseen selector protocol

Frozen before any new target is solved, 2026-09-11. This is a discrimination
experiment, not a new selector or benchmark proposal.

## Prior-art gate: REUSE / BASELINE

- [CrystalBall, SAT 2019](https://www.cs.utoronto.ca/~meel/publications/b2hd-SKM19.html): existing framework for clause-use data and prediction. BASELINE conceptual boundary; do not rebuild its learning pipeline or claim future-utility prediction as novel.
- [Freezing/reactivating clauses, SAT 2011](https://www.cril.univ-artois.fr/~lagniez/papers/AudemardLMS11.pdf): past information predicts remaining-search relevance. BASELINE; not a changed-target measurement.
- [ATPG 2007](https://uww.revlib.org/doc/konf/07vlsiDesign.pdf): related-instance learned information reuse. BASELINE.
- [CausalSAT, SAT 2023](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SAT.2023.28): clause utility and branching relationship. BASELINE.
- Repository `HistoryIndex.scores`: REUSE existing direct-use/width/local-proof-cost importance. It uses reconstructed resolution DAG use counts, not measured native activity, LBD, or learned-clause future-use labels.
- Existing one-step `ProofDB.resolve`, `HistoryIndex.materialize`, `Evaluator`, and native Glucose: REUSE. No SAT engine rewrite or generic preprocessor.

Search covered historical clauses as priors, cross-instance clause utility,
future-search utility, transferred search guidance and target consequence
selection. No claim of novelty from not finding an identical experiment.

## Targets and frozen choices

- Reuse the existing n=200, degree=6, 3-coloring homologous family and existing
  `evolve`, H seed6202, drift 0.01; fresh target seeds 9202,9203,9204 = T2,T3,T4.
  No new synthetic benchmark family, encoding, generator or hardness filtering.
  Audit these seeds are absent from prior stored target JSON; compare CNF hashes.
- Same fixed 67 TEMPLATE outputs from prior experiment. Check against each T,
  stop on inapplicability; no remapping or permutation selection.
- K=64, 512 unique candidate outputs examined by each online selector, max4096
  resolver attempts to reach them, <=1 inference/root, exactly64 validation
  inferences plus fixed TEMPLATE. No fallback larger pool or parameter retuning.
- Generation depends only on T: original-premise occurrence lists, shuffled
  original premise traversal using fixed seed17, complementary resolutions via
  existing ProofDB; discard tautology, original, encoding-only and TEMPLATE-
  subsumed outputs. TEMPLATE clause-content exclusion is common fixed input.
  Both online routes regenerate independently using identical schedule/budgets.
- Target feature tuple: width ascending, support-edge common-neighbor count
  descending, sum of opposite-literal Jeroslow-Wang occurrence weights descending,
  SHA256 clause tie-break. Common-neighbor count uses the existing known coloring
  graph (all candidates are edge+ALO one-step consequences). No solve/probe T.
- History rank: existing H source-importance score descending, then exact same
  target tuple. Build a clause->max(source score) lookup once from H before target
  generation. No target proof, conflicts, prior oracle sets or Gold IDs are read.
  Missing H clause has score0. Both inspect same512 candidates; H adds512 lookups.
- Selection caps:512 feature evaluations, one stable sort of512 records,
  <=512 optional prior lookups; common50ms online selection wall guard. Generation
  guard100ms excluding target JSON loading; breaches invalidate run, not retune.
  Match compute caps, report actual times; do not pad faster route with sleep.
- Fixed canonical clause injection by candidate ID, fresh original Glucose3.0,
  default heuristics, conflict budget1e6, timeout30s, /dev/null completion proofs.
- Freeze every T's online selections before ANY target completion. Five shuffled,
  sequential full-pipeline timing repetitions; no parallel timing. Source prior
  build/check/index cost and prior load separately measured. Warm, amortized over
  these3 targets, and cold-history totals reported. H proof production treated as
  pre-existing sunk history, not free newly generated training.

## Oracle and decision

One diagnostic oracle per T over the SAME512 candidates: fixed seed17,96 random
exact64 sets plus frozen TARGET/HISTORY sets; then4 rounds of16 one-swap proposals
around incumbent. Reuse Evaluator, objective ops then conflicts then IDs. No
singletons, backwards search, per-target tuning, extra restarts, or optimizing
this oracle after results. Finite best-found reference, NOT certified global
upper bound. Include online seeds so the reference cannot be worse than them.
Oracle is offline only; charge full discovery separately and never as online cost.

Report TEMPLATE anchor and all three routes. ALIVE only if H has >=10% fewer ops
and >=5% lower warm total on each of3 targets, plus positive3-target aggregate
savings after amortizing source-prior preprocessing. WEAK if warm benefits meet
these per-target gates but observed3-target amortization fails, or mixed-target
improvements lack stability. STOP if H median ops ratio>=0.95 and fewer than2/3
have >=10% ops improvement, or H is worse on at least2/3 with no aggregate warm
saving. Otherwise WEAK, never retune. These operational thresholds are not
statistical significance tests;3 related targets share H and are not3 families.
