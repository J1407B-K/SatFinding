# Target local vs history: frozen protocol

Prior-art gate (2026-09-11), before experiments: REUSE repository ProofDB.resolve,
HistoryIndex.materialize, ProofContext, Evaluator, native Glucose and objective.
No new generic preprocessor, clustering, or semantic abstraction.

- [Een/Biere SAT 2005](https://fmv.jku.at/papers/EenBiere-SAT05.pdf): resolution preprocessing, including short derivations. REUSE bounded resolution as a baseline.
- [ATPG 2007](https://uww.revlib.org/doc/konf/07vlsiDesign.pdf): learned information reuse across related instances. BASELINE, not a novelty claim.
- [Incremental Glucose](https://www.cril.univ-artois.fr/articles/xmain.pdf): retained clauses and solver state in successive calls. BASELINE; our cold processes isolate clause injection from saved activities.
- [CausalSAT, SAT 2023](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SAT.2023.28): clause utility and branching relationships. BASELINE; ablations here are not a causal model identifying mediation.
- [Biere SAT lecture](https://cca.informatik.uni-freiburg.de/sat/ss23/08/): butterfly effects from seeds and clause order. BASELINE order sensitivity control.
- [Vivification](https://arxiv.org/abs/1807.11061): target-side propagation already exploited by existing solvers. BASELINE; do not call cheap consequences historical inventions.

Searches covered cross-instance learned-clause set synergy, non-additive clause
utility, historical clauses shaping future CDCL trajectory, and target-only cheap
implications vs transferred history. No directly matching published controlled
Gold64 experiment was located; this is not evidence of novelty. Existing local
IPR discussion of nonlinear search benefit remains applicable.

1. Freeze original target, TEMPLATE, Gold64, source-ID injection. LOCAL means
exact clause derivable in <=2 binary resolution inferences from target CNF.
Enumerate all premise/premise resolvents then first-round/premise resolvents,
using existing ProofDB; reject tautologies, deduplicate. This exhausts <=2-step
resolution proofs, not arbitrary logical inference calculi or weakening.
Candidate generation reads T alone before loading H or TEMPLATE; subsequent
filtering excludes original clauses, encoding-only and TEMPLATE-subsumed outputs.
Preserve intermediate clauses in checked proof, inject only selected outputs.
2. Four ablations, five shuffled sequential repetitions; objective unchanged:
first-UIP antecedent visits (search ops), then conflicts. Report checked support
cost, total warm selected-set time, and offline costs separately.
3. Matched finite offline oracles: three search seeds 17,29,43, each with 512
random singleton screens, 96 random sets per K=16,32,64 (half entire pool, half
best 128 singletons), singleton-best prefix, backward 64->16 with 8 removal
proposals, then 4 rounds of 16 swaps per K. Same proposal counts and objective.
Fresh independent search directories, no old oracle or Gold seeds. Report each
seed and best-of-three; these are heuristic oracles, not global optima. Frozen
Gold64 is a separately labeled older, more expensive oracle reference.
4. Gold singleton, leave-one-out, 128 fixed-seed random pairs, all prefix sizes
0..64 for singleton-best, leave-one-out-best, source-importance and five random
orders. Membership follows the chosen order; injection stays in source-ID order.
Separately randomize injection for full Gold and four ablations using five seeds.
Five repeats establish measurement repeatability, not independent target evidence.
5. Lightweight aggregate trajectory counters only if observational instrumentation
is straightforward; check equality of existing counters against original binary.
No cross-target synergy claim without independent target replication.
6. Stop strong history-specific claims if target matches/exceeds history. If
results depend on order, do not promote stable threshold synergy. Next matrix
must test unseen targets with matched candidate/selection budgets.
