# TEMPLATE-ONLY ablation and homologous drift

Do not start automatic retrieval or mapping in this round. The previous
best-found n200 mapping remains an evaluation-only reference, not a mapper.

## Question, frozen before outcomes

The n200 independent pair reduced native first-UIP analysis steps from
232,724 (BLIND) to 133,584 (oracle FULL-HISTORY). This round asks how much of
that, and of any later saving, is:

1. shared 3-coloring encoding, represented by a same-family non-lineage proof;
2. lineage-specific historical inferences.

A third fact is recorded, not used as a solver route: inferences whose ancestor
leaves are only within-vertex one-hot clauses. Those lemmas would be valid on
every n-vertex instance of this encoding. If that count is zero, encoding
closure alone cannot explain a BLIND-to-HISTORY gap.

## Routes

BLIND: native Glucose 3.0 on T, original defaults, no lemmas.

TEMPLATE-ONLY: checked Resolution proof of a held-out same-n 6-regular instance
U, identity vertex numbering, six global color permutations. U is generated
independently of G and of T. This is the family-encoding control, not a
searched correspondence and not T's own proof.

FULL-HISTORY: checked Resolution proof of the lineage ancestor G, same identity
vertex numbering and six color permutations. For homologous targets, identity
is the supplied domain correspondence (vertices were not renamed). For the
frozen independent pair, the same identity rule is the fair history route;
the previous 90-second mapping oracle is cited as a privileged extra number,
never as TEMPLATE-ONLY.

If replay yields no new lemmas, the worker CNF equals T and the run is not a
history benefit. Missing edge premises never become axioms. Remainder is
whole-target CDCL completion, not optimal local repair.

Color permutation is chosen after seeing completion analysis_resolution_steps.
That selection is evaluation-only and constant-size (6). No vertex permutation
search is run.

## Frozen independent pair

Do not regenerate H6200/T6201 or H6202/T6203. Remeasure BLIND, identity
FULL-HISTORY from H, and TEMPLATE-ONLY from a new U on those exact T CNFs.
n120 remains a milliseconds control.

U seeds: n120 → 6300, n200 → 6302. Reject and record failure if U equals G or T
or is disconnected.

## Homologous family

G is the existing 6-regular graph for n120/n200 (seeds 6200/6202) and a new
`random_regular_graph` for n in {300,400,600} with seeds 6400/6402/6404.
Degree 6, one-hot 3-coloring, no symmetry breaking, no planted proof.

From G, degree-preserving connected double-edge swaps produce T at target
replaced-edge rates 1%, 5%, 10%, 20%. An additional T is an independent
6-regular graph (seeds 8000+n). Record exact `|E_G \ E_T|/|E_G|`, shared edges
and Jaccard; do not resample to force those numbers or to force UNSAT.
Keep SAT, TIMEOUT and conversion failures as explicit outcomes.

U seeds for homologous sizes: 6300/6302/6410/6412/6414. One U per n, reused
across that n's targets.

## Backend and metrics

Same counted native Glucose 3.0 binary as the evaluation-oracle round.
n<=200: 1,000,000 conflicts and 30-second process limit. Larger n: same
conflict cap, 180-second process limit. Counter-disabled control once per n
on BLIND of the independent or first available T.

Primary search counters remain analysis_resolution_steps, conflicts,
minimization_reason_visits, binary_minimization_candidates, decisions and
propagations. Also record replayed proof steps, unique replay lemmas,
completion counters, replay/check time, completion solve time, their sum,
BLIND solve time and CaDiCaL solve time (solver-reported UNSAT/SAT only).
Do not replace native counters by DRUP length or Python conversion work.
Certificate conversion is optional and separate; n200 selected winners should
be checked when conversion finishes within 120s.

History proofs for new G/U: native DRUP, then the existing RUP-to-Resolution
adapter (180s at n<=200, 600s above). Adapter timeout is a producer failure,
not a transfer MISS and not evidence against other proof formats.

## Scale and stopping

Measure n=200 fully first. Then n=300,400,600 in that order. If BLIND and both
history routes TIMEOUT on a size, stop climbing. Wall-clock crossover is a
same-machine comparison of BLIND solve time versus replay/check plus
completion, and separately versus CaDiCaL. One size with HISTORY total below
BLIND is not a project-wide YES; absence of crossover at these sizes is not
an impossibility result.

No automatic mapper is implemented from this protocol.
