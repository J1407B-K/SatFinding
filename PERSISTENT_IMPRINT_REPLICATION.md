# Persistent imprint replication: protocol status

The prior-art gate is complete in [PERSISTENT_IMPRINT_PRIOR_ART_GATE.md](PERSISTENT_IMPRINT_PRIOR_ART_GATE.md): existing work is reused for incremental SAT, VSIDS/activity, proof mining, clause management, and solver continuation; the exact clause deletion plus heuristic-state persistence and reverse-transplant conjunction is classified **EXTEND/NEW**, with broad memory-reuse claims marked **STOP_DUPLICATE**.

Ten targets (`T5`–`T14`) were frozen before any mechanism result was read. Their input hashes, seeds, clause counts, and source provenance are in [results/persistent_imprint_replication/frozen.json](results/persistent_imprint_replication/frozen.json). They were previously used in the memory-stream benchmark, but no reason/activity/heap imprint intervention was run on them.

No CONTROL/TREATMENT solver runs have been started yet. This is deliberate: the existing repository has no generic driver that can inject independently certified per-target lemmas, record reason/heap snapshots at a legal checkpoint, and execute the three auditable transplant/ablation configurations without introducing a new selector or silently changing the target template. The frozen manifest therefore records a **pre-experiment protocol state**, not mechanism evidence.

The next implementation must build one fixed native observer/injection driver, use one predeclared treatment lemma source for all ten targets, and retain rows for no-gap, no-reason-use, illegal-checkpoint, proof-failure, and completed cases. It must write CONTROL, TREATMENT, TREATMENT_REMOVE_LEMMA, TREATMENT_REMOVE_CONTROL_HEURISTIC, and CONTROL_TREATMENT_HEURISTIC outputs only after the manifest is immutable. No target may be dropped based on outcome.

Current claim boundary: the single L2 case has strong local intervention evidence; these ten targets provide a frozen replication cohort only. No multi-target replication claim is made until all rows and independent proof checks exist.

## T5 smoke test

The reusable wrapper is [persistent_imprint_native_driver.py](persistent_imprint_native_driver.py). It delegates to the existing audited native binary and refuses treatment/removal/transplant modes without an explicit checked lemma set and certificate; it never infers lemma validity from global UNSAT. The T5 DIMACS conversion and smoke outputs are in [results/persistent_imprint_replication/T5_smoke](results/persistent_imprint_replication/T5_smoke).

T5 CONTROL completed as UNSAT with 258,595 analysis operations, 6,937 conflicts, 8,067 decisions, and 549,263 propagations. `drat-trim` verified its proof. The four non-control smoke routes were recorded as structured `ABORT` results before any solver mutation because no checked per-target lemma certificate was supplied. This deliberately exercises the negative/unsupported path. No positive gap, reason-use checkpoint, reset, or transplant claim is made. T6–T14 were not run.

The existing L1/L2 regression remains bit-exact in its frozen artifacts; the wrapper's CONTROL backend reproduces the native protocol and proof checker, while treatment integration is explicitly gated on certificate input rather than silently synthesizing a treatment.

## T5 certified-lemma smoke

T5 remains pilot-only and is excluded from confirmatory statistics. The deterministic builder is [certified_lemma_builder.py](certified_lemma_builder.py): it uses only original target clauses, one-step resolution, canonical lexical ordering, fixed `K=64`, non-tautological/non-duplicate filtering, and independent certificate replay. Artifacts are in [results/persistent_imprint_replication/T5_lemmas](results/persistent_imprint_replication/T5_lemmas).

T5 CONTROL completed at 258,595 analysis operations. The treatment with 64 certified one-step lemmas completed at 247,852 operations (4.16% lower) and its final proof was independently `drat-trim VERIFIED`. This is a small smoke gap, and the generalized wrapper did not yet tag treatment clause IDs through reason events, so there is no auditable treatment-lemma first-reason-use/checkpoint. It is therefore recorded as **NO_MECHANISM_WINDOW** and no removal or heuristic transplant was run.

[T5 summary](results/persistent_imprint_replication/T5_summary.json) records the result. The old L1/L2 case remains regression evidence for the prior specialized instrumentation; its historical treatment certificates are not represented by this new target-only builder format, so no bit-exact generalized-driver regression claim is made. T6–T14 were untouched.

The builder checker was tightened to replay parent/pivot resolution independently of the producer helper. T5 certificates now contain parent IDs, pivot, intermediate list, canonical lemma, and fixed depth/length filters. `checker_report.json` records the independent replay and treatment hash.

## T5 reason/checkpoint instrumentation

Stable clause IDs (1–64) are now part of every treatment certificate. The offline ledger [results/persistent_imprint_replication/T5_instrumentation/ledger.json](results/persistent_imprint_replication/T5_instrumentation/ledger.json) maps treatment clause hashes to enqueue/analysis reason events and records conflict, decision, level, and propagated literal. T5 treatment produced 1,084 treatment-lemma reason/analysis uses.

At the fixed native conflict-end checkpoints, no boundary satisfied the frozen alignment rule (same assignment, trail, and decision level) while providing a legal comparable state. The result is therefore `NO_ALIGNED_CHECKPOINT`; no removal or heuristic transplant was attempted. This instrumentation pass does not reinterpret T5's 4.16% gap as mechanism evidence and does not change lemma selection or K.

The frozen eligibility rule is: absolute relative ops gap at least 10%, at least one real treatment-lemma reason-use, and a native conflict-end/pre-decision checkpoint with assignment/trail/level equality plus valid heap/inverse-index audit. T6–T14 remain untouched.

## T6–T14 confirmatory Stage A

The frozen deterministic builder was run for T6–T14 only. Each target received 64 canonical depth-1 lemmas with independently replayed certificates and independent final proof checking. No target was reselected and T5 remains pilot-only.

| target | ops gap | lemma reason uses | classification |
|---|---:|---:|---|
| T6 | +29.16% | 1,088 | NO_ALIGNED_CHECKPOINT |
| T7 | −16.32% | 1,137 | NO_ALIGNED_CHECKPOINT |
| T8 | +45.57% | 1,301 | NO_ALIGNED_CHECKPOINT |
| T9 | −24.10% | 1,183 | NO_ALIGNED_CHECKPOINT |
| T10 | −29.82% | 1,107 | NO_ALIGNED_CHECKPOINT |
| T11 | −28.64% | 1,169 | NO_ALIGNED_CHECKPOINT |
| T12 | +4.63% | 1,084 | NO_GAP |
| T13 | +23.56% | 1,146 | NO_ALIGNED_CHECKPOINT |
| T14 | −18.42% | 1,261 | NO_ALIGNED_CHECKPOINT |

All nine targets had independently verified CONTROL/TREATMENT proofs. Treatment reason/analysis uses were identified for every target, including both speedups and slowdowns. T12 failed the frozen 10% effect-size threshold. The other eight had gaps but no checkpoint with exact assignment/trail/decision-level alignment under the current boundary set. Consequently Stage B interventions were executed for **zero** targets.

The complete per-target certificates, proofs, ledgers, hashes, and structured classifications are in [results/persistent_imprint_replication/T6_T14](results/persistent_imprint_replication/T6_T14), with [cohort_summary.json](results/persistent_imprint_replication/T6_T14/cohort_summary.json). Under the exact frozen protocol, this cohort produced no executable persistent-imprint replication case. This does not show that persistent imprint is absent; it shows that the current exact-alignment checkpoint protocol did not expose a legal intervention window.
