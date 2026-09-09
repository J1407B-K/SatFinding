# SATLIB RTI/BMS measured results

All times include cache lookup, solving, certificate checks, and insertion. Seed cost is included in total. Common archive loading/normalization and result serialization are excluded. Values are medians of complete runs, in seconds.

| Mode | Seed s | Query s | Total s | Query hits | Net speedup |
|---|---:|---:|---:|---:|---:|
| none | 0.932308 | 1.966684 | 2.904512 | 0 | 1.000x |
| exact | 1.160253 | 2.128277 | 3.288530 | 0 | 0.883x |
| canonical | 2.173702 | 2.798495 | 4.969262 | 0 | 0.584x |
| semantic | 1.445624 | 0.514953 | 1.955169 | 500 | 1.486x |
| structural | 2.352103 | 4.721690 | 7.073792 | 0 | 0.411x |

## Scope

Official, unmodified instances: 500 RTI and 500 BMS. All RTI are processed first; BMS query order is independently shuffled with a fixed seed. No pair ID or filename is passed to retrieval. This is a deliberately related workload, not an independent-source generalization test. No model is trained.

`semantic` uses aligned-variable clause-incidence vectors; `structural` is the name-invariant width/degree histogram ablation. Canonical uses exact colored-graph canonicalization allowing variable permutation and polarity flips. All modes use Glucose3.

Raw per-instance timing, archive/instance hashes, order, versions, and accepted source IDs are in the adjacent JSON. SAT witnesses are rechecked during every run. These timings do not establish performance on UNSAT, production traces, or neural embeddings.
