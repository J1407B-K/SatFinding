# Oracle Transfer: proof value before automatic mapping

This stage does not implement retrieval, WL, mapping search, a library,
cascade, abstractions, XOR/GF(2) or ML. Preserve the rejected Round 4 family.

## Readiness screen, fixed before results

Candidate: 3-colorability of independently sampled simple 5-regular graphs.
Pairs (vertices, H seed, T seed): (80,6100,6101), (120,6102,6103),
(160,6104,6105). NetworkX random_regular_graph with recorded library version.
Every graph is generated independently; no input is made by changing proof
leaves or keeping a historical core. Keep SAT, UNKNOWN and failed cases in
the screen; do not resample until UNSAT or until a history route wins.
One-hot encoding: one 3-clause plus pairwise at-most-one constraints per
vertex; one binary color exclusion per edge/color. No symmetry-breaking
units, planted subgraphs, hidden inverse transformations or graph rejection
filters. Same generator and encoding do not imply a useful instance alignment.

Run CaDiCaL preprocessing (three rounds, installed PySAT defaults), CaDiCaL
solving, and Glucose3 proof production in separate CNF-only workers. Imports
precede worker timing; construction is included. Fifteen-second process
watchdog per method. Export DRUP from Glucose only on UNSAT. Retain all six
screened inputs and results; only pairs with both endpoints UNSAT and neither
refuted by cheap preprocessing are eligible for a transfer measurement.
Direct solving time remains reported even if preprocessing does not decide.
Screening is not an oracle transfer outcome.

Sources: [NetworkX generator](https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.random_regular_graph.html),
[PySAT proof interface](https://pysathq.github.io/docs/html/api/solvers.html),
[graph coloring SAT literature](https://www.cs.cmu.edu/~mheule/publications/CP22-CliColCom.pdf).
These sources establish tools/domain background, not hardness of these seeds.

## Oracle and conclusion boundary

Proposed oracle is free supplied domain correspondence (vertex/color meaning),
not a learned or searched mapping. With independent random graphs, vertex
labels alone need not yield the best structural alignment. Unless optimality
is established, a negative result is conditional on the supplied alignment,
historical proof and bounded search implementation. It is not an impossibility
result over all mappings/proofs or all natural families. A successful checked
transfer can establish opportunity for a future mapping algorithm; failure
of BLIND to finish leaves completion costs censored.

Oracle may supply a mapping and historical proof, never T's proof, missing
leaf repair witnesses or an unproved clause as an axiom. Any oracle selection
using T's metadata must be explicitly recorded and free only in this upper
bound experiment, not passed off as an algorithmic result.

## Proof boundary and measurement

Final acceptance remains exact input membership plus binary Resolution replay
and empty-clause presence using satcache.check. A DRUP log is not yet a pure
Resolution certificate. Reconstruction belongs to the producer, outside the
checker; unsupported proof steps are explicit failures. Preserve generation,
reconstruction and checker costs separately, and slice only after validation.

BLIND and oracle repair must use one Resolution search kernel, rule set and
global attempts accounting. Replay carries parent/pivot hints and incurs no
new search attempts but full checker work. Missing historical leaves cannot
be assumed; blocked descendants are distinct from local repair roots. Record
direct replay, new attempts, generated nodes including failures, checked
nodes, full certificate size, support and times. Primary comparison is
attempts to the SAME empty clause, with a common cap and wall-clock policy.
No numerical saving ratio unless both routes finish. No project-wide NO from
a failed candidate mapping or a single censored family.
