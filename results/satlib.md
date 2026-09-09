# SATLIB RTI/BMS measured results

All times include cache lookup, solving, certificate checks, and insertion. Seed cost is included in total. Common archive loading/normalization and result serialization are excluded. Values are medians of complete runs, in seconds.

| Mode | Seed s | Query s | Total s | Query hits | Net speedup |
|---|---:|---:|---:|---:|---:|
| none | 0.931732 | 1.953837 | 2.897606 | 0 | 1.000x |
| exact | 1.159596 | 2.125836 | 3.288071 | 0 | 0.881x |
| canonical | 2.184724 | 2.790413 | 4.974068 | 0 | 0.583x |
| semantic | 2.668533 | 0.469197 | 3.144732 | 500 | 0.921x |
| structural | 3.532129 | 5.491126 | 9.047234 | 0 | 0.320x |

## Scope

Official, unmodified instances: 500 RTI and 500 BMS. All RTI are processed first; BMS query order is independently shuffled with a fixed seed. No pair ID or filename is passed to retrieval. This is a deliberately related workload, not an independent-source generalization test. No model is trained.

`semantic` uses aligned-variable clause-incidence vectors; `structural` is the name-invariant width/degree histogram ablation. Canonical uses exact colored-graph canonicalization allowing variable permutation and polarity flips. All modes use Glucose3.

Raw per-instance timing, archive/instance hashes, order, versions, and accepted source IDs are in the adjacent JSON. SAT witnesses are rechecked during every run. These timings do not establish performance on UNSAT, production traces, or neural embeddings.
