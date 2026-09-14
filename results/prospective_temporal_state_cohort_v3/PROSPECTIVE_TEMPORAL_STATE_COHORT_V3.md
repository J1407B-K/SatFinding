# Prospective Temporal State Cohort v3

Result: **B. NO_SIMPLE_TEMPORAL_STATE_ABSTRACTION**.

HARNESS_LOCK_V3 verified completely; all core hashes remain unchanged. This is the first temporal cohort with scientific label promotion after full pre-GT and route-integrity audits. v1/v2 invalid cohorts and all qualification labels/features are excluded. The two earlier stop files are preserved in `../prospective_temporal_state_cohort_v3_prelock_history/`.

## Prospective design

T8/T10/T13 each contributed six fresh exact states: 18 total. The v1.1 fixed-window first-eligible rule (at least two legal actions) was instantiated before collection with six identical windows per target, conflicts 3000–3599. No runtime, feature or intervention outcome adjusted the schedule. K=6; each package freezes first min(6,legal_count) actions by stable creation ID. All 128 raw samples precede the exported checkpoint boundary, including the most recently completed conflict. All SHORT/MID/LONG descriptors use the locked v1.1 extractor and were independently audited. Static comparisons use the previously frozen feature list; enumeration_literal_visits is unavailable.

18 states froze 85 actions and 103 routes before any action outcome. Canonical logical/heuristic replay passed 103/103; action verification 85/85; proofs 103/103 VERIFIED. Duplicate/missing/extra and collector/discovery/package emissions are zero. Package and peripheral science input hashes remained unchanged. Labels come from the locked finalizer: remaining ops = final analysis-resolution steps − prefix analysis-resolution steps; HIGH iff abs(100*(action_remaining/baseline_remaining−1)) >= 10%.

## Sensitivity structure

SENSITIVE: 1/18. INERT within frozen tested-action budget: 17/18. HIGH actions: 1/85 (1.18%), including 1 speedups and 0 slowdowns. Moderate (1%≤abs(delta)<10%): 0; zero/near-zero (abs(delta)<1%): 84, including 84 exact zeros. These bins are mutually exclusive. 0/1 sensitive states are SPARSE (HIGH fraction < 0.5). Per-state counts, proportions and signed extrema are retained in sensitivity_structure.json. Distribution status: SENSITIVITY_DISTRIBUTION_SHIFT. Earlier observations are compared qualitatively only; this is no statistical test against invalid cohorts.

The sole positive is T10_S3_B488045: one of two tested actions reduces remaining analysis ops by 21.8104%; the other is exactly zero. All other 83 actions are also exactly zero. HIGH leverage is rare and confined to one state in this cohort. The sensitive surface is not SPARSE under the inherited strict <50% criterion (it is exactly 50%). Thus rarity/concentration recur qualitatively, but sparse-state dominance does not replicate. SENSITIVITY_DISTRIBUTION_SHIFT here is a descriptive flag, not a statistically established shift from historical cohorts.

## Temporal versus static

Every frozen scalar descriptor is reported with raw values, availability, group medians/ranges, interval overlap and within-target midranks. No ML, regression, composite feature, optimized threshold, best-feature selection or new action predictor was used. 0 temporal descriptors and 0 static descriptors satisfy the frozen necessary test of robust strict separation in multiple targets. Pooled strict temporal separation occurs for 1 descriptors. Full per-target directions and leave-one-state-out checks are in within_target_temporal_analysis.json. Temporal superiority over static snapshot is not established.

The analysis specification was frozen before collection. Candidate promotion requires a frozen specific descriptor/relation and robust non-confounded prospective evidence; the inherited temporal protocol specifies a feature family but no directional candidate. No candidate is invented after observing labels. This result is limited to the frozen family, tested action budget, schedule and small cohort; it does not rule out all temporal mechanisms. Missing within-target label classes are recorded as uninformative, not treated as negative separation evidence.

Only T10 contains both label classes (one SENSITIVE, five INERT within budget); T8 and T13 each contain six INERT within budget. Cross-target direction consistency is therefore not estimable from multiple informative targets. Deleting the sole positive removes the sensitive class entirely. One pooled descriptor has strict separation, but this cannot establish an outlier-robust relation. B is supported by the absence of the required robust evidence, not by equating an uninformative comparison with proof of no underlying effect. C is not asserted: target confounding was not demonstrated by the frozen criterion.

## Stage decision and costs

**SKIP_STATE_GATE_BY_PROTOCOL**. No held-out state gate was run. Exploration budget saving from an implemented gate is 0; sensitive coverage is not applicable. **READY_FOR_MICRO_ROLLOUT_ACTION_SELECTION = false**.

Offline collection, full replay/continuation, proof verification and labeling are separate from online-relevant costs. Checkpoint extraction timing includes the independent reference check; isolated ring-maintenance overhead is unmeasured and not claimed to be zero. No scientific full-route cost is presented as online controller overhead. See cost_accounting.json.
