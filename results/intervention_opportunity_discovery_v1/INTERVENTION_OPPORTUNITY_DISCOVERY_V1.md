# Intervention opportunity discovery v1

**B. NO_OBVIOUS_INTERVENTION_OPPORTUNITY_DESCRIPTOR_V1**

Exploratory hypothesis generation only. The sealed temporal v3 conclusion is not modified or reinterpreted. No native solver was run, no intervention was executed and no package or label was changed. Existing canonical snapshots supplied all v3 fields; historical proof rechecks were the only new external executions.

Discovery includes 18 v3 states/85 actions (1 HIGH), plus 2 audited historical positive states/11 actions including controls (4 HIGH). Thus 5 HIGH actions occur across 3 distinct positive states on T8 and T10. Historical observations are selected discovery positives, not prospective validation or an unbiased prevalence estimate.

Historical exactness is same-parent OS fork identity with matching operational/raw-object/heap fingerprints inside one run, legal action and enqueue records, full continuation counters, and newly reverified proofs. No legacy hash is used to assert cross-run canonical equality. Complete pending queue positions are recovered from the baseline FIFO dequeue prefix; historical activity and semantic heap rank are unavailable and not imputed. Original/Gold is excluded from feature/label comparisons because an exact matched baseline pre-snapshot was not established; its existing mechanism finding is not disputed.

The opportunity protocol was frozen before new feature/label association. V3 and historical feature artifacts were hashed before joining outcomes. Eight listed natural predicates and two explicitly listed conjunctions were tested; no extra predicate, weighted score, continuous cutoff sweep, regression or classifier was tried.

## Exact within-state contrast

HIGH #5633 versus NON-HIGH #2544 is fully tabulated in V3_SENSITIVE_STATE_ACTION_PAIR.md. Pending-antecedent status alone does not distinguish them. Clause source/length, older antecedent positions and implied-variable search-control ranks differ, but this single pair cannot identify which difference caused the continuation effect.

## Bounded opportunity tests

| Predicate (state has such a frozen action) | HIGH states covered | V3 inert states excluded | Meets candidate criteria |
|---|---:|---:|---|
| exists frozen action: pending_antecedent_count > 0 | 3/3 | 0/17 | False |
| exists frozen action: all_antecedents_processed | 0/3 | 17/17 | False |
| exists frozen action: distinct_implied_literal_count > 1 | 3/3 | 0/17 | False |
| exists frozen action: same_implied_literal_multiplicity > 1 | 0/3 | 17/17 | False |
| exists frozen action: pending_queue_length > 0 | 3/3 | 0/17 | False |
| exists frozen action: newest_antecedent_relative_to_qhead == 0 | 1/3 | 0/17 | False |
| exists frozen action: newest_antecedent_relative_to_qhead > 0 | 2/3 | 16/17 | False |
| exists frozen action: watched_false_pending_count > 0 | 3/3 | 0/17 | False |
| exists frozen action: pending_antecedent_count > 0 AND distinct_implied_literal_count > 1 | 3/3 | 0/17 | False |
| exists frozen action: newest_antecedent_relative_to_qhead == 0 AND distinct_implied_literal_count > 1 | 1/3 | 0/17 | False |

These are descriptive discovery counts, not gate validation. Continuous features are reported as complete-case distributions and ranks only, separately for v3 and historical data. Correlated actions from one state are not independent positive replications.

The common frontier relationship is not sufficient to explain intervention leverage: positive and zero-effect actions can occupy the same pending frontier, including within the exact same state. The evidence supports asking how a particular enqueue interacts with subsequent propagation/learning, but this feature family does not establish that mechanism or supply a promotable opportunity rule. Equal final analysis ops do not by themselves prove bit-exact trajectory identity.

No opportunity gate is promoted, no held-out test is run under B/C, and no controller, Level-1 selector, direction predictor or micro-rollout is validated. The appropriate next step is further bounded mechanism discovery, not deployment or action selection.

## Quantitative interpretation of the frontier comparison

All 85 v3 actions have a pending antecedent, a pending false watched literal, and distinct-implied-literal competition within their state. These predicates cover the positive but exclude 0/17 inert states. The newest-antecedent-at-qhead predicate covers the v3 HIGH and 81/84 non-HIGH actions; at state level it still excludes no inert states. Newest antecedent strictly after qhead covers all four historical HIGH actions, but misses the v3 HIGH. It passes only one v3 inert state and no v3 sensitive state; historical ascertainment cannot turn that into prospective evidence. This contrast, not lack of available historical positives, motivates B.

The v3 HIGH implies variable 27 (activity rank 5, semantic heap-pop rank 3); its same-state zero control implies variable 430 (activity rank 96, heap-pop rank 79). The HIGH reason is learned and length 6; the zero reason is original and length 3. Both have newest antecedent at trail position 80=qhead, age 0, and one pending antecedent. Pending fractions are 1/5 and 1/2 respectively. Activity/heap ordering is the most conspicuous unresolved contrast in this pair, but historical activity/semantic heap ranks are unavailable; no threshold, common-positive claim or gate is inferred from it.

B means no obvious shared opportunity descriptor under this predeclared bounded v1 search and the audited discovery set. It does not establish that all legal interventions are redundant in trajectory space or explain away the positive cases. The reason a particular variable enqueue changes later conflict/learning choices remains unresolved. The sealed temporal v3 result remains exactly B — NO_SIMPLE_TEMPORAL_STATE_ABSTRACTION.
