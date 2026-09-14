# Persistent state imprint

The frozen baseline is:

| run | analysis ops |
|---|---:|
| A | 345,592 |
| B | 169,858 |
| B_REMOVE_L2 | 174,427 |

`B_REMOVE_L2` therefore retains 97.4% of B's improvement after the L2 clause
has been deleted. The intervention below was placed at the first native pick
after conflict 660, with the propagation queue empty. The pre-reset snapshot
of `B_REMOVE_L2` was byte-identical to its natural run. A's activity vector,
heap array, and heap inverse indices were copied; all other state stayed in the
B_REMOVE_L2 process. Heap validity and eligible-variable coverage were checked
before mutation.

| run | analysis ops | conflicts | decisions | proof |
|---|---:|---:|---:|---|
| B_REMOVE_L2 | 174,427 | 4,698 | 5,421 | VERIFIED |
| B_REMOVE_L2 + A activity/heap reset | **292,662** | 7,911 | 9,242 | VERIFIED |

The reset adds 118,235 operations (+67.8%) and moves the run close to A's
345,592 operations. This is direct intervention evidence that the persistent
benefit is carried substantially by heuristic state, specifically the joint
activity/heap state. It is not a complete explanation: the reset does not fully
recover A, so learned clauses, reason graph, watches, phases, restart history,
and other distributed state still matter.

The requested activity-only and heap-only split was not executed. Both candidate
states failed the pre-mutation legality check (`heap_valid=0`) and were aborted
without changing solver state. The joint pair is a coherent heap under its
matching activity comparator; copying either field alone would create an
unreachable solver state. This is a legality result, not evidence that either
field is irrelevant.

The updated mechanism chain is:

`L2 reason use → C657–C660 analysis differences → learned/reason/watch and heuristic-state imprint → activity/heap ordering → later branch trajectory`.

Intervention-supported links are the C657 reason transplant, the L2 deletion
ablation, and this joint reset. The reset proves a strong local mediator role,
not that activity or heap alone is sufficient, nor that it explains every later
conflict avoided by B.

The next minimal experiment is to inventory the remaining non-target state at
the same pre-reset checkpoint and identify one legal, jointly consistent carrier
candidate (learned DB/reasons, phase, restart queues, or watches). Do not run
another intervention until that candidate has a precise invariant and a
pre-mutation legality test.

Artifacts: [persistent_state_imprint.py](persistent_state_imprint.py),
[results/persistent_state_imprint](results/persistent_state_imprint), and the
full proof/hash audit in `runs.json` and `protocol.json`.
