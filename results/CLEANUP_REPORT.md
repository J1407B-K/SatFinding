# SatFinding cleanup report

Cleanup completed at `2026-09-14T07:01:36.236739+00:00` using the frozen plan `fdb8f6633cf092ab59302cf7d0594252dade89da1b0a939a35770de65ce73808`.

- Before: **1.67 GiB** logical / **1.75 GiB** allocated
- After: **1.57 GiB** logical / **1.65 GiB** allocated
- Released: **101.06 MiB** logical / **101.91 MiB** allocated
- Deleted files: **584**

The main deletion was raw `.drup/.drup.gz` and transient captures from the invalid 105-route temporal-v2 input cohort. Compact route results, proof hashes, proof-check logs, state traces, protocols, manifests, and invalidation reports remain. Superseded diagnostic build/setup trees and unprotected zero-byte/cache residue were also removed.

Preserved in full: prospective temporal v3, harness qualification v3, current opportunity discovery, and harness qualification v2. The small v1/v2 invalidation history packs remain. Current historical-positive fixed-state, T8 S5, and original-early-propagation evidence remain, including the proofs used by discovery.

Integrity after deletion:

- HARNESS_LOCK_V3: **PASS**
- SCIENCE_RESULT_MANIFEST: **PASS**
- DISCOVERY_RESULT_MANIFEST: **PASS**
- Sealed artifacts modified: **0**

`.venv/` and `artifact_/` remain in place with ARCHIVE recommendations because repository reports invoke the environment path and the external artifact's provenance is uncertain.

Every deleted file's prior path, size, category, reason, and SHA-256 is recorded in the JSON report and cleanup plan.
