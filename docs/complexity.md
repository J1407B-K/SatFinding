# Reuse separation and a structural complexity theorem

## What exact/canonical means

Exact cache reuses only an identical normalized full CNF. Canonical cache additionally
identifies bijective variable renamings, independent polarity flips, and clause/literal
permutations. It does not identify all logically equivalent formulas: that would be
a substantially different, potentially SAT-hard baseline. Our canonical implementation
encodes complementary literal pairs and clause incidence as a colored graph.

## Proposition 1: strictly additional legal reuse

SAT example: H = (x) AND (y), R = (x OR y). The model x=y=true satisfies both.
Their clause counts differ, so exact and canonical full-formula caches cannot reuse
the H entry for R; a model-carrying cache can. No containment check is needed for soundness.

UNSAT example: H = (x) AND (NOT x), R = H AND (z OR w). The two-premise resolution
refutation of H is also a refutation from premises of R. Again clause counts differ.
Thus proof/model transfer has legal hits outside the equivalence classes supported by
exact/canonical lookup. This is an expressiveness separation, not a guarantee that a
bounded heuristic retrieves every such hit. Tests exercise both examples.

## Theorem 3: stable inconsistent core with varying padding

Let C be the four clauses

    (x OR y), (x OR NOT y), (NOT x OR y), (NOT x OR NOT y).

Resolve the first two on y to derive x, the last two on y to derive NOT x, and
resolve those units to derive the empty clause. This is a constant-size certificate pi.
Let

    F_n = C AND conjunction_{i=1..n} (z_i OR w_i),

with all variables distinct. All F_n contain the same inconsistent core and differ
in variable/clause counts. A history containing only (C, pi) yields zero exact/canonical
hits on F_n for n>0, but the semantic cache's clause index retrieves C and its proof
passes on every F_n. Identity mapping suffices; this is structural proof reuse.

Define D as recursive chronological DPLL with exhaustive unit propagation, no pure-literal
elimination, no component decomposition, no clause learning, and variable order
z_1,...,z_n,w_1,...,w_n,x,y, skipping variables absent from the current formula.
Before any z decision, C has no units. On z_i=true its padding clause disappears;
on z_i=false, unit propagation sets w_i=true and its clause disappears. Neither branch
affects C or any remaining padding. Hence both branches reduce to the same situation
with one fewer padding clause. When no padding remains, deciding x produces a unit
conflict in either branch. Therefore the number of decision nodes obeys

    D(0)=1,  D(n)=1+2D(n-1),  so D(n)=2^(n+1)-1.

After caching pi, reading/indexing F_n and checking its premises takes O(n) expected
word-RAM time with the implementation's hash tables, plus O(1) proof work. A deterministic
balanced-tree membership implementation instead gives O(n log n), still polynomial.
Literal encodings introduce the usual logarithmic bit-cost factors. Thus for this
precisely specified DPLL algorithm and family, reuse changes exponential search to
linear expected checking (or deterministic quasilinear checking). Certificate generation
cost is constant here and is not hidden in an unbounded offline advice oracle.
These bounds start with a normalized CNF; including the current front end's sorting
of arbitrary raw clauses adds O(n log n) work for this constant-width family.

`theory_experiment.py` executes the specified DPLL and checks decision counts and cache
certificates. It is a finite illustration of the recurrence, not the proof itself.

## More general amortized bound

For queries Q_i = tau_i(C) AND P_i, let S be the one-time cost of finding a valid
refutation pi of C, M_i the actual cost of proposing tau_i, and V_i the cost of checking
transported premises and pi against Q_i. A successful cache gives total cost

    S + sum_i (M_i + V_i),

including construction of the historical certificate. It improves on independent solves
only when this expression is smaller than their total cost. For a bounded stored core,
aligned identities, and linear-size queries, M_i+V_i is linear expected input work.
Arbitrary hidden core matching may itself be hard; no constant-cost matching assumption
is justified for general formulas or arbitrary renamings.

For SAT, the dual easy family is a sequence of subformulas of a previously solved H:
its complete model is a certificate for each query, checkable in linear input time.
The prototype additionally sorts variable IDs during its model coverage check,
which adds O(v log v) for v query variables.
The official RTI/BMS workload has exactly this relationship, but the speedup over
Glucose is an empirical result, not an asymptotic lower bound against Glucose.

## Limits

This does not establish an exponential improvement over CDCL or the best possible SAT
algorithm: component decomposition or pure-literal elimination already neutralizes
the padding above. It does not prove P=NP, polynomial certificates for all UNSAT inputs,
or polynomial matching. The rigorous result is an algorithm-relative separation and
an explicit amortized bound for recurring certified cores/models.
