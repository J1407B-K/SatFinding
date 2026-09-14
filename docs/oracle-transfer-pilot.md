# Supplied-domain-alignment pilot, exploratory only

No response to the optional oracle-scope question has arrived; proceed using
the stated default: free (vertex,color) identity correspondence. This is not a
proved optimal alignment between independent random graphs. Do not call a
negative result an upper bound over all mappings, all repairs, or all proofs.

The second screen produced six UNSAT inputs; all six survived CaDiCaL
preprocessing. The 120-vertex endpoints solve in about 4-5 ms and are only an
engineering control, despite preprocessing alone not deciding them. The
200-vertex endpoints solve in about 44-68 ms and are modest difficulty. The
320-vertex endpoints require about 2.2 and 4.1 seconds with CaDiCaL, but the
current historical DRUP reconstruction exceeded its fixed 60-second cap.
Retain that exclusion; it is a tool limitation, not a transfer negative.

Run only available checked historical proofs (120 and 200), with target proof
files withheld. Routes: BLIND and ORACLE_HISTORY. No SUPPORT-ONLY, retrieval,
mapping search, cascade or five-route infrastructure.

Before measurement freeze: 400,000 global complementary-pair attempts,
2,000 attempts per local repair call, 20 seconds inside the worker, 40 seconds
outer process watchdog, 250,000 pending candidates and 50,000 generated+input
nodes. Memory policy is checked for both routes. Caps are infrastructure
limits; hitting them means censored/MISS, not falsity or impossibility.

Reuse round4_core.ResolutionSearch unchanged. Both routes count duplicate
and tautological attempts. ORACLE imports replayed clauses only with explicit
valid Resolution parents. Search targets are initially unavailable historical
nodes ordered by clause width then historical ID. In particular, the empty
target is first and gets a 2,000-attempt full-input search, then subsequent
targets get one incidence neighborhood of current root CNF plus available
proved clauses contained in that neighborhood. Local searches share one
global Budget; no reset on failure. Persist failed search derivations and
attempt traces. This local strategy is not an oracle for optimal repair.

Proof results remain about the same empty clause on T. Every full emitted DAG
(including partial failed work) must pass the pure Resolution module checker;
an UNSAT success additionally passes satcache.check. Certificate slicing
does not discard attempt accounting. Record initial directly replayed steps,
missing leaves, unavailable inferences, repairs, new nodes and censored costs.
No percentage saving if either route fails to finish.

If the existing enumerative kernel cannot finish these natural inputs under
its resource policy, the result is EXPERIMENT_INCONCLUSIVE / KERNEL_LIMITATION,
not a negative about the historical-proof hypothesis. Do not compensate with
planted proof-leaf replacements or weaken the modern solver baseline.
