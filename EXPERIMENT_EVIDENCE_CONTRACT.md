# Experiment evidence contract

A PASS claim requires source revision, build command/exit code, binary hash, invocation, stdout/stderr, route metadata, proof artifact, checker invocation/exit code, derived result, and a tying manifest. `REPORT_ONLY` artifacts cannot qualify. `QUALIFIED=true` must be emitted by an automated verifier.

## Input provenance

Every experiment manifest must bind each input path, SHA-256, size, and `source_type` (`ARCHIVED_FILE` or `GENERATED`). Generated inputs additionally require generator source/hash, exact command, seed, parameters, and generated hash/size.
