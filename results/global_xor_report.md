# Global XOR pilot

| n | CDCL UNSAT / 10 | oracle+check median s | discovery+check median s | CDCL observed median s | discovered XOR steps median |
|---:|---:|---:|---:|---:|---:|
| 80 | 0 | 0.0029 | 0.0101 | 2.0075 | 79 |
| 160 | 0 | 0.0061 | 0.0207 | 2.0073 | 159 |
| 320 | 0 | 0.0128 | 0.0419 | 2.0088 | 319 |
| 640 | 0 | 0.0343 | 0.0892 | 2.0132 | 639 |

All 40 discovered refutations and 40 oracle refutations passed the independent CNF/GF(2) checker. All 40 planted SAT controls were checked by their assignments and produced no accepted refutation.

CDCL UNKNOWN is censored, not a completed runtime; no exact speedup or proof-size ratio is inferred. Budget: 2 seconds for the solver call, no conflict cap; actual counters and total time (including loading) are recorded. Discovery timing includes parity extraction and Gaussian elimination; total includes certificate checking. Formula generation, imports, diagnostic trace statistics and file serialization are excluded for all modes. Oracle has privileged equation/group information; discovery receives CNF only.

This pilot recognizes explicit parity blocks of width at most 8 and uses a separate GF(2) proof checker. It does not discover the XOR operation, learn from CDCL history, or produce extended-resolution proofs. Recorded DAGs are algebraic elimination histories. It establishes neither low primal treewidth nor a general SAT algorithm. No learned parameters or train/test claim; seeds 0–9 overlap earlier width experiments.

Baseline API: [PySAT solver documentation](https://pysathq.github.io/docs/api/solvers.html).
