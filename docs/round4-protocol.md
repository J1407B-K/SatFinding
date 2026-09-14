# Round 4: development gate before transfer implementation

Scope: Resolution only; L0, L1, L2 5%, L2 15%; no cascade, L3,
XOR/GF(2), ML, abstraction language or historical-library retrieval.

## Frozen development family v1

Four seeds 4100..4103. Each historical CNF is a uniformly sampled set of 34
distinct signed ternary clauses over seven variables, rejection sampled for
UNSAT and a bounded actual Resolution search success (200,000 attempts).
No planted proof chain. Preserve the full successful search trace, all generation
trial counts, and the root ancestor slice. The family is explicitly small and
synthetic, not an industrial or independent-source claim.

L0 is signed permutation and clause shuffle. L1 retains the historical proof
leaves and independently samples 12 satisfiable ternary context clauses from
12 variables; enforce neither formula is a clause subset of the other before
renaming. L2 removes ceil(rate * sliced leaf count) leaves, with nested broken
sets, replacing each by an independently sampled satisfiable 14-clause ternary
region over five variables (the leaf variables plus two from the common pool
1..9). Require a checked exact derivation of the missing leaf with at most 32
ancestor inference nodes and a 20,000-attempt generation search cap. Removed
leaves cannot occur in any replacement or context. Regions may overlap.
This conditioning is disclosed; all generation trials and search totals are
recorded. It is not evidence that finding the repair online is difficult.
L2 levels use independent replacement/context samples, not strictly monotonic
difficulty; only the removed leaf sets are nested. Actual rounded fractions
are reported. One checked SAT control per seed is additional to the four levels.

No acceptance or rejection uses a shortcut outcome. There is no retuning after
seeing shortcut results. A failed generator seed is an explicit failure, not
silently substituted. Normalization erases clause order for every algorithm.

## Shortcut gate (before formal experiment)

Run CNF-only UP, no-clause-growth BVE (maximum 64 parent pairs per pivot),
CaDiCaL preprocessing (three rounds), and CaDiCaL solving. Each subprocess
receives only CNF on stdin and public limits, never a manifest, history, seed,
mapping, replacement witness or support. Fixed 100,000-attempt cap for UP/BVE;
10-second common process watchdog. Log worker time and startup-inclusive time.
UP/BVE emit pure Resolution witnesses; solver-only UNSAT is labeled as such.
Failed BVE probes count attempts, including duplicate and tautological results.

Stop this family if cheap CNF-only preprocessing refutes every positive input:
in particular, checked BVE <= 1,000 attempts/case or CaDiCaL preprocessing
<= 0.1 worker seconds/case on all positives. These are development rejection
criteria, not claims of comparative speedup. Report partial shortcut coverage
too. Do not wait to implement history routes after a stop condition is met.
If a gate result is a timeout/error, keep it distinct from a logical MISS.
If the gate survives, implement mapping and the five routes below, then stop
if SUPPORT-ONLY explains any apparent benefit. No formal experiment is claimed
until those routes and their audit actually exist.

## Formal routes reserved, not executed by the gate

BASELINE: modern solver, plus higher-budget same-kernel reference separately.
BLIND: CNF-only indexed Resolution saturation.
SUPPORT-ONLY: same algorithm-derived mapping and support as history, with all
historical derived clauses, parent edges, pivots and gap targets removed.
REPLAY: same candidate mappings as REPLAY+REPAIR; no search, gaps are MISS.
REPLAY+REPAIR: replay available parents; exact clause repair under one global
Budget shared across gaps, candidates and failed searches. Local limits cannot
reset the global counter. Budget grid 1,000 / 10,000 / 100,000 attempts; same
rules, search implementation, checker and wall-clock policy for search routes.
History generation witnesses and source mappings remain evaluation-only.

The search kernel indexes complementary occurrences and orders candidates by
sum of parent widths then current input-derived node IDs. Each candidate
parent pair/pivot is scheduled once. Charge every dequeued complementary pair,
including duplicates and tautologies; record parent-literal visits separately.
No truth-assignment prepass, hidden target-dependent width limits, or free
speculative Resolution in the matcher. Ancestor slicing does not erase search
attempts or discarded generated clauses from accounting.

Main endpoint: a checked empty clause on the same T. Primary measure is new
Resolution search attempts saved, not reused nodes. Exact saving fractions
require both routes to finish; budget exhaustion is right-censoring, not a
completion cost. No history advantage has been measured by the shortcut gate.

## Schema and independent audit

`round4_schema.json` reserves formal row fields and defines gate trace fields.
Unexecuted route metrics are null/not measured, never zero. Private manifest
contains case identity, rounded breakage, mappings and generation witnesses.
Public case contains only historical CNF/proof and new CNF. Shortcut workers
receive the CNF field alone. Evaluation joins identities only after workers exit.

Audit must verify source/input hashes, matrix completeness, historical slice
reachability, historical search accounting, replacement witnesses, exact missing
leaves, L0 equivalence/L1-L2 non-subsets, SAT controls, and every gate certificate.
Audit reconstructs each attempt sequentially without importing the producer
kernel. It reuses the existing simple checker; it is not a separately implemented
logical checker. Timings are recorded observations, not proof-certified claims.
