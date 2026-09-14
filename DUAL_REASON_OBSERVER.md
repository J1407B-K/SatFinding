# Dual-reason observer

The initial T5 audit accidentally used the original CNF and therefore reproduced CONTROL. This was corrected by constructing the frozen T5 treatment CNF (original clauses plus 64 certified lemmas) and running identical observer OFF/ON executions.

Both corrected runs reproduce the historical treatment count exactly: 247,852 analysis operations. They also match each other exactly: 6,568 conflicts, 7,667 decisions, and 525,778 propagations, with UNSAT status. The treatment CNF contains 64 lemmas; its hash and audit data are in `results/dual_reason_observer/T5_corrected/observer_non_interference.json`.

The current trace does not expose explicit observer invocation counters, so those remain an instrumentation follow-up. No T6–T14 run or mechanism experiment was performed.
