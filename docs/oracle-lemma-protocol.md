# Offline conditional oracle lemma selection

Frozen target: `n200_T_r01_s7201.json` from the preceding replay-budget run.
Identity vertices/colors; native counted Glucose binary unchanged. No engineering
optimization of replay, producer, mapping or selection latency in this round.

Baseline is the **same 67 checked TEMPLATE clauses**, in their previous source
order, appended to the original normalized target. Every conditional experiment
keeps that prefix fixed and appends historical outputs in source-node order.
No oracle changes input clause order or reuses a warmed/incremental SAT solver.

Historical population: strictly replayable, unique G6202 Resolution clauses.
Remove exact TEMPLATE duplicates, clauses subsumed by any TEMPLATE output, and
nodes with encoding-only historical support. Ancestors needed to certify an
output may still use shared knowledge. This is an operational control, not a
proof of semantic lineage specificity: U6302's replayable clauses are not known
to hold on every graph. Do not call all of them universal encoding axioms.

Objective: minimize completion `analysis_resolution_steps`, with conflicts and
then lexicographic source IDs breaking ties. No timing-based oracle selection.
This is an expensive same-target, best-found search, not a globally optimal
subset oracle and not evidence of a deployable selector or held-out generalization.

## Search, fixed before completion outcomes

1. Screen 8,192 single historical lemmas on top of TEMPLATE. Candidate coverage
   is a union of the first 2,048 source-ranked, 2,048 shortest, and 2,048 highest
   direct-use clauses, filled to 8,192 by a seeded uniform population sample.
   If that union exceeds 8,192, retain the deterministic prefix.
2. For each exact K in {32,64,128,256}, evaluate source-ranked and singleton-ranked
   prefixes plus 384 seeded subsets: 128 uniform from the full population,
   128 from the best 512 screened singleton candidates, 128 from the union of
   those 512 and the top 2,048 source-ranked candidates.
3. Take two best distinct exact-256 seeds. For each, perform stochastic greedy
   backward deletion down to 32: evaluate up to 16 single-lemma removals at
   every size and accept the best child, even when all removals worsen the score.
   Include the lowest singleton-ranked currently present lemma among the removal
   proposals. This measures conditional marginal utility and explores interactions.
4. For each exact K, perform eight rounds of 32 proposed single-lemma swaps from
   the current best exact-K set. Half the replacements come from the best 512
   singleton candidates, half from the full historical population; accept only
   objective improvements.
5. Independently leave-one-out ablate the frozen best exact-K sets. Save all
   marginal changes. Also choose the best observed set of size **at most K**,
   including singletons and TEMPLATE alone. Exact-K and <=K outputs are separate;
   do not pad a smaller winner with harmful clauses or imply the sets are nested.

Seed 20260910; three random baseline seeds 17/29/43. Search counters are cached
by exact selected-ID tuple. Screening can use four independent subprocesses;
timings under this contention are discovery costs only. Screening DRUP output
goes to `/dev/null`; final measurements retain input and proof artifacts.
Report actual unique evaluations, statuses, coverage, discovery wall time and
sum of subprocess times. Failure to find a tiny core does not prove one absent.

## Final measurement

Freeze selections, then stop search workers. Run five repetitions in seeded
shuffled order, fresh native solver each time, recording BLIND, TEMPLATE,
TEMPLATE + RANKED-K, TEMPLATE + RANDOM-K (three seeds), TEMPLATE + ORACLE-exact-K,
and TEMPLATE + ORACLE-at-most-K, for K=32/64/128/256. Add ranked-2048,
TEMPLATE + full eligible history, and the previous unconditioned FULL as anchors.

For this **value/existence experiment**, all routes receive preselected IDs.
Source loading/checking, eligibility and selection are offline for all methods.
Timed total includes template and historical ancestor materialization/checking,
serialization, native subprocess/parse/search/proof output and artifact hashing.
Keep replay/check, native time, process time, ops, conflicts and support counts
separate. This is a warm preselected-set cost, not end-to-end online retrieval.
Do not compare its total directly to the previous budget curve's selector-inclusive
total without pointing out the accounting difference.

The final exact-K and <=K winners get checked historical support. Attempt full
completion certificates on distinct oracle winners as a separate offline audit,
with a 120-second conversion cap each. Conversion time is never hidden in query
timing or represented as a scalable raw-DRUP materialization implementation.
