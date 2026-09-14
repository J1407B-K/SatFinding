# History-guided generation: frozen independent hypothesis

2026-09-11. Freeze before any completion. No tuning or oracle.

Prior-art gate: REUSE / BASELINE. [Prover9 hints](https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/hints.html)
use proofs of related problems to prioritize given clauses for further inference;
[Prooftrans](https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/prooftrans.html)
extracts those hints. This experiment uses a restricted propositional parent-pair
replay baseline, not a reproduction of Prover9 or a new mechanism claim. Quick
search covered cross-instance clause generation, proof-guided generation,
history-guided resolution/lemma discovery, transferred proof guidance. Existing
ProofDB, HistoryIndex scores, target candidate rank, checker and native solver
are reused. No ML, multi-history, abstraction or new benchmark family.

- 20 new seeds 19201..19220; existing n200 degree6 coloring family, H6202,
  evolve drift .01. Audit stored JSON/JSONL seed/hash/CNF identities recursively;
  freeze targets, source hashes and protocol before generation or solving.
  Existing outcomes are never used for selection or tuning. Absence audit is
  relative to available repository artifacts, not unverifiable external runs.
- TARGET-GEN uses existing cheap target-only occurrence traversal, seed17
  shuffled original premises, complementary literal order. Symmetric duplicate
  pair attempts are canonicalized for BOTH routes. No resolvents are calculated
  in scheduling. Common encoding-only pairs are excluded before scheduling.
- HISTORY-GEN moves applicable original-parent steps from H to the front of
  this same universe; order is the unchanged HistoryIndex source score, then
  source node ID. Deduplicate unordered parent/pivot keys; remaining order is
  exactly TARGET-GEN. Missing original parents are skipped. No target completion,
  target conflicts, Gold IDs or outcome files are available to scheduling.
- Resolver budgets 64,128,256,512,1024. Exactly B calls, common 100ms wall guard
  including occurrence scheduling, lookup, resolving and candidate index build.
  Guard failure invalidates the experiment, never increases the budget.
  Retain at most512 unique eligible candidates (first512); continue resolver
  calls to B if cap reached, discard excess from both retained pools. Record all
  distinct eligible outputs as well as retained counts. Original, encoding-only,
  tautological and common TEMPLATE-subsumed outputs excluded as before.
- Both use unchanged unseen_selector.select(prior=None), K cap64, choose
  min(64,pool size), no padding or extra attempts when scarce. Exact selected K
  reported, so different pool yield is an intended generation effect. Same
  short-proof validation, no TEMPLATE injection. Canonical clause-content
  injection order, independent of generation IDs. No history ranking of outputs.
- Freeze every candidate pool, short proof and selection across all targets and
  budgets BEFORE any target solve. 3 sequential full-pipeline repeats, globally
  shuffled seed20260911. Each repeats generation and validation from scratch;
  fresh native counted Glucose, 1e6 conflict budget,30s timeout,/dev/null proof.
  Solver search ops = analysis_resolution_steps; solver completion status is
  solver-reported, candidate proofs are independently checked. No cold anchor
  or third online route. Total warm time includes preparation, history retrieval,
  generation, ranking, validation, solver input/process/cleanup. Source proof
  is sunk, index build/load costs separately reported and amortized over20
  actual targets (not100 budget cells or300 repeats).
- Per-target comparisons use median timing over3 repeats. Primary small budgets
  are64,128. ALIVE requires at BOTH: >=16/20 targets with >=10% ops reduction,
  >=16/20 with >=5% warm reduction, median ops ratio<=.90, aggregate warm
  ratio<=.95, and positive savings after build+load cost /20 per target.
  If ops/warm gates pass but amortization alone fails: WEAK. Otherwise STOP
  (including mixed/unstable benefits). No post-hoc score changes or rescue.

Pre-solve amendment: initial frozen protocol tried to reuse67 TEMPLATE clauses,
but applicability validation raised Missing target premise before any new solve
or online pool freeze. Keep all20 seeds unchanged; remove TEMPLATE from BOTH
routes (including its subsumption exclusion) so only T and one historical H
are involved. The original protocol/driver and identity freeze are retained.
This is an applicability repair, no solver outcomes existed or were consulted.
The amended source/protocol hashes are frozen in amendment.json before retry.
