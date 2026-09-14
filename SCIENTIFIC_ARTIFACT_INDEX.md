# Scientific Artifact Index

本页只索引当前最重要证据。`results/` 保持原路径作为本地 scientific archive；不要移动、重写或对
sealed files 做格式化。

| Artifact | Purpose |
|---|---|
| [Formal v3 report](results/prospective_temporal_state_cohort_v3/PROSPECTIVE_TEMPORAL_STATE_COHORT_V3.md) | Prospective temporal cohort v3 的设计、完整性、分布与正式 B 结论。 |
| [Science result manifest](results/prospective_temporal_state_cohort_v3/SCIENCE_RESULT_MANIFEST.json) / [SHA256](results/prospective_temporal_state_cohort_v3/SCIENCE_RESULT_MANIFEST.sha256) | 绑定正式 v3 scientific outputs；验证 sealed artifacts。 |
| [Harness lock v3](results/harness_qualification_v3/HARNESS_LOCK_V3.json) / [SHA256](results/harness_qualification_v3/HARNESS_LOCK_V3.sha256) | 绑定 qualified collector、canonical identities、runner、schema、auditor、finalizer 和 qualification evidence。 |
| [Harness v3 qualification evidence](results/harness_qualification_v3/attempt_001/CAPABILITY_QUALIFICATION.json) | 4 packages、K=6、28 dynamic routes、rank-6 replay 与 generic label dry-run 的资格结论。 |
| [Opportunity discovery report](results/intervention_opportunity_discovery_v1/INTERVENTION_OPPORTUNITY_DISCOVERY_V1.md) | B — NO_OBVIOUS_INTERVENTION_OPPORTUNITY_DESCRIPTOR_V1。 |
| [Opportunity result manifest](results/intervention_opportunity_discovery_v1/DISCOVERY_RESULT_MANIFEST.json) / [SHA256](results/intervention_opportunity_discovery_v1/DISCOVERY_RESULT_MANIFEST.sha256) | 绑定 exploratory discovery outputs。 |
| [V3 same-state action pair](results/intervention_opportunity_discovery_v1/V3_SENSITIVE_STATE_ACTION_PAIR.md) | 唯一 HIGH 与同-state zero action 的逐字段结构对照。 |
| [Historical-positive audit](results/intervention_opportunity_discovery_v1/historical_positive_audit.json) | 审计 T10 fixed-state、T8 S5 与被排除历史案例的 exactness、effect 和 proof evidence。 |
| [Discovery dataset audit](results/intervention_opportunity_discovery_v1/DISCOVERY_DATASET_AUDIT.json) | 明确 exploratory discovery 的 included/excluded 数据及原因。 |
| [Cleanup inventory](results/CLEANUP_INVENTORY.md) | 第一轮 dependency-aware cleanup inventory。 |
| [Cleanup report](results/CLEANUP_REPORT.md) | 第一轮删除、保留与 integrity 结果。 |
| [Text/JSONL audit](results/CLEANUP_TEXT_AUDIT.md) | 第二轮解释哪些 TXT/JSONL 是 evidence，哪些是 transient outputs。 |
| [Text/JSONL cleanup report](results/CLEANUP_TEXT_REPORT.md) | 第二轮清理与 sealed integrity 结果。 |

正式结论只来自正式 manifests 绑定的数据。v1/v2 invalid cohorts、old identity-invalid qualification
packages 与 qualification labels 不参与 v3 scientific claims。

## Active trusted results
- Observer v2 qualification evidence and provenance audits.
- Branch displacement scoped result.
- Propagation availability: `PROPAGATION_AVAILABILITY_NOT_PRIMARY_MECHANISM`.
- Fixed route recovery: `FIXED_CAUSAL_COHORT_NOT_RECOVERABLE`.
- Current heuristic wording: `HEURISTIC_STATE_AMPLIFICATION_HYPOTHESIS`; `CAUSAL_MEDIATION_UNRESOLVED`.
- Invalidated reports: `results/INVALIDATED_RESULTS_INDEX.md`.
