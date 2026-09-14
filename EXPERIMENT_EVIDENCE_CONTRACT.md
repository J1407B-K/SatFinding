# Experiment evidence contract

A PASS claim requires source revision, build command/exit code, binary hash, invocation, stdout/stderr, route metadata, proof artifact, checker invocation/exit code, derived result, and a tying manifest. `REPORT_ONLY` artifacts cannot qualify. `QUALIFIED=true` must be emitted by an automated verifier.

## Input provenance

Every experiment manifest must bind each input path, SHA-256, size, and `source_type` (`ARCHIVED_FILE` or `GENERATED`). Generated inputs additionally require generator source/hash, exact command, seed, parameters, and generated hash/size.

The `native-execution-v2` schema is checked fail-closed by
`verify_experiment_evidence.py`: all artifact paths, byte sizes and SHA-256
hashes are mandatory, as are input-source bindings, recorded build source
hashes, successful invocations, matching raw-output summaries, six checker
executions, and computed trace audits. A manifest with only field names or
handwritten PASS flags is rejected. File verification establishes archive
integrity; the independently executable auditors establish semantic checks.

Observer schema v2 records full trail/pending at every processing boundary.
Canonical reasons are event-sourced: each enqueue binds a reason's sorted
literal copy and its SHA-256; checkpoint snapshots bind reasons for assignments
already present. Backtracks remove the corresponding assignment/reason entries.
No native clause is sorted or mutated by serialization. Final root conflicts
are recorded without invented UIP/learned/backtrack events.
