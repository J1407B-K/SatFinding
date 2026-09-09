# SATLIB RTI/BMS measured results

All times include cache lookup, solving, certificate checks, and insertion. Seed cost is included in total. Common archive loading/normalization and result serialization are excluded. Values are medians of complete runs, in seconds.

| Mode | Seed s | Query s | Total s | Query hits | Net speedup |
|---|---:|---:|---:|---:|---:|
| none | 0.036165 | 0.075409 | 0.111574 | 0 | 1.000x |
| exact | 0.045457 | 0.081865 | 0.127321 | 0 | 0.876x |
| canonical | 0.085330 | 0.107322 | 0.192652 | 0 | 0.579x |
| semantic | 0.057143 | 0.016747 | 0.073889 | 20 | 1.510x |
| structural | 0.098849 | 0.126008 | 0.224857 | 1 | 0.496x |

## Scope

Official, unmodified instances: 20 RTI and 20 BMS. All RTI are processed first; BMS query order is independently shuffled with a fixed seed. No pair ID or filename is passed to retrieval. This is a deliberately related workload, not an independent-source generalization test. No model is trained.

`semantic` uses aligned-variable clause-incidence vectors; `structural` is the name-invariant width/degree histogram ablation. Canonical uses exact colored-graph canonicalization allowing variable permutation and polarity flips. All modes use Glucose3.

Raw per-instance timing, archive/instance hashes, order, versions, and accepted source IDs are in the adjacent JSON. SAT witnesses are rechecked during every run. These timings do not establish performance on UNSAT, production traces, or neural embeddings.
