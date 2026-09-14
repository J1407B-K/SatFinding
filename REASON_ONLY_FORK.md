# Reason-only fork

No T6–T14 fork was executed. The existing treatment ledgers identify reason hashes and treatment reason/analysis uses, but they do not retain a complete assignment/trail snapshot at each enqueue. The protocol explicitly forbids inferring a dual-reason event from static clause scans. Therefore every target is conservatively recorded as `NO_DUAL_REASON_EVENT` with the reason `instrumentation insufficiency`, not as evidence that no event exists.

Per-target records and cohort summary are in [results/reason_only_fork/T6_T14](results/reason_only_fork/T6_T14). T5 remains excluded and T6–T14 treatment inputs/results were not modified. No heuristic transplant, checkpoint search, or additional intervention was run.

The next required step is a fresh treatment-only observer that snapshots the complete state immediately before every treatment-lemma enqueue, while independently checking whether a non-treatment clause is unit at that exact trail. Only that observer can authorize one earliest dual-reason fork per target.
