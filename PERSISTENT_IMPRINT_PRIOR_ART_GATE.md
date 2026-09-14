# Persistent heuristic imprint prior-art gate

This gate is limited to the exact proposed mechanism:

`redundant clause changes propagation reason → conflict-analysis/activity/heap
state persists after clause deletion → transplanting that heuristic state into a
control run transfers the search benefit`.

| Area | Existing work found | Decision |
|---|---|---|
| Incremental SAT / learned information reuse | Assumptions and retained learned clauses; ATPG-style reuse across related circuit instances | REUSE |
| VSIDS/activity and variable-order heaps | Standard CDCL branching heuristics and clause deletion/decay studies | REUSE |
| Proof-derived literals / historical lemma guidance | Backbone mining, ProofWatch, mined theorem lemmas, proof skeletons | REUSE |
| Incremental solver-state reuse | Persistent clauses, assumptions, frames, and solver continuation are established | REUSE |
| Solver-state migration | State serialization/checkpointing and parallel/incremental solver engineering are adjacent, but do not isolate activity+heap as a transferable causal memory | EXTEND |
| Proof-guided branching | Proof statistics, conflict analysis, branching heuristics and proof-guided verification are established separately | EXTEND |
| Reason-path divergence changing VSIDS/heap order | Mechanistically expected from CDCL, but no directly matching clause-deletion persistence experiment was found in the local literature boundary | EXTEND |
| Clause deleted while its heuristic imprint remains useful | No direct matching result found | NEW |
| Reverse activity+heap transplant transferring future benefit | No direct matching result found | NEW |
| Full multi-target replication of this causal chain | No direct matching result found | NEW |
| Broad proof-memory / cross-instance reuse claim | Already occupied by proof mining, incremental SAT, constraint reuse and verification-state reuse | STOP_DUPLICATE |

The existing repository gate documents the closest boundaries: `PRIOR_ART_GATE.md`
lists incremental SAT, proof-derived backbone information, Proof Skeletons,
constraint memory, IPR/FuseIC3 state reuse, clause deletion and proof-guided
analysis. Those works justify reusing their solvers, proof checkers, clause
validation and heuristic terminology. They do not test the conjunction above.

The multi-target experiment is therefore cleared only as a bounded **EXTEND/NEW**
mechanism replication. It must not be presented as a new general solver-state
migration algorithm, history selector, semantic abstraction, or cross-target
heuristic-state transfer method.

No target was selected or run before this gate was written. The next protocol
must freeze ten previously unused targets before inspecting CONTROL/TREATMENT
outcomes and retain every gap, failure, and illegal-intervention case.
