# Soundness of proof-carrying reuse

## Contract and trusted boundary

A CNF F is a finite sequence of clauses. Each clause is a strictly sorted tuple
of distinct nonzero integer literals. Interpret a positive integer v as a Boolean
variable and -v as its negation. Empty conjunction is true; empty disjunction is false.
Input normalization removes repeated literals/clauses and reorders them, all of which
preserve this interpretation. It does not remove tautologies.

Candidates consist only of finite data: Certificate, Step, integer literals, Boolean
assignments, and tuples. The threat model permits any values in those fields, corrupt
history, arbitrary ranking, incorrect mappings, and incorrect producer statuses.
It does not give the candidate Python code execution, control over the checker, or
concurrent mutation of data while checking. JSON loading does not execute code.

The trusted computing base is the input interpretation/normalization, residual
construction, `check`, the final result/assumption handling, and their Python/runtime
execution. Glucose, graph canonicalization, embeddings, mapping search, histories,
and claims from those components need not be trusted for logical acceptance.

This document is a mathematical proof of the stated finite-data algorithm. It is
not a Lean/Coq proof or a machine-checked refinement of the Python implementation.
Exhaustive tests supplement the argument; they do not prove the unbounded theorem.

## Lemma 1: accepted SAT certificates

`check(R, c)` accepts a SAT certificate only if its assignment a contains a Boolean
value for every variable occurring in R and each clause contains a literal true under a.
Therefore a satisfies every conjunct, so a satisfies R. Extra assigned variables have
no effect. A partial model or a historical model that fails any current clause is rejected.

## Lemma 2: resolution is consequence-preserving

Let parent clauses A and B contain p and -p respectively. Their resolvent is

    C = (A \ {p}) union (B \ {-p}).

Suppose an assignment satisfies A and B but falsifies C. Every literal of
A other than p is false, so p must be true. Every literal of B other than -p
is false, so -p must be true, a contradiction. Hence A and B entail C.
The proof also covers signed pivots and tautological clauses.

## Lemma 3: accepted UNSAT certificates

Every initial certificate premise must literally occur in R, so R entails it.
Induct on the ordered step list. The checker requires both parent indices to refer
to premises or earlier steps, requires the complementary pivot literals, and requires
the recorded output to equal the resolvent exactly. By Lemma 2 and the induction
hypothesis, R entails every new clause. Acceptance requires the empty clause among
the premises or derived clauses. Thus R entails false and is unsatisfiable.

Forward references, negative indices, made-up premises, omitted resolvent literals,
and unfinished proof fragments cannot pass these conditions. An empty clause already
present in R is a valid zero-step refutation.

## Theorem 1: cache-independent local soundness

For every valid finite R, every finite history H, and any terminating candidate
proposal procedure P, if an answer derived from P(H,R) is accepted by `check`,
then SAT implies R is satisfiable and UNSAT implies R is unsatisfiable.

Proof: case analysis on the accepted kind, using Lemmas 1 and 3. The proof makes
no assumption about similarity, history provenance, or correctness of variable maps.
Even an invalid map can only affect which candidate is checked, not the theorem.
All cache implementations check before returning a certificate. `run` and the benchmark
driver check again at the final acceptance boundary. UNKNOWN and exceptions are not
SAT/UNSAT conclusions. Rejection may cost time but cannot justify a conclusion.

## Theorem 2: residual scope

For a partial Boolean assignment alpha, R = F|alpha removes clauses already true under
alpha and removes false assigned literals from the other clauses. For every total
extension a of alpha, a satisfies F iff its restriction to the remaining variables
satisfies R. This follows clause by clause from the definition of residual.

Consequently an accepted SAT certificate for R extends with alpha (and arbitrary
values on unused variables) to a model of F. `run` reconstructs and checks this model.
An accepted UNSAT certificate for R proves only that F has no model extending alpha.
Equivalently F entails the clause consisting of the negations of all literals in alpha.
This is global UNSAT only when alpha is empty, or all branches have been separately
discharged. The current API always returns the assumptions and never implements
unchecked global clause insertion. Consumers must interpret status together with scope.

## Corollary: repeated/adaptive use

Consider any finite adaptive sequence of solver calls. On each call, independently of
earlier retrieval errors, every accepted certificate has the meaning above. Induction
on call count therefore preserves correct scoped conclusions even when the history
was built from previous results. A later mutation of a stored candidate is rechecked
before acceptance. This proves safety, not termination, resource bounds, or speedup.

## Proof transfer and fragments

An injective signed variable renaming preserves satisfaction and resolution, provided
literal polarity is transported consistently. The implementation nevertheless rechecks
the transported proof against the current premises. For a generic fragment D |- C,
the same induction would certify consequence C only after D is justified in the current
context. The present implementation accepts full refutations, not generic fragments
as final UNSAT answers. Neural proposal generation can be added without extending the
logical trusted boundary, provided this interface is retained.
