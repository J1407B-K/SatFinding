# Current Scientific State

SatFinding 当前研究主线是 **CDCL search-control / propagation scheduling**。正式 prospective temporal
state cohort v3 已封存，结论为 **B — NO_SIMPLE_TEMPORAL_STATE_ABSTRACTION**。后续 exploratory
opportunity discovery v1 也已完成，结论为 **B — NO_OBVIOUS_INTERVENTION_OPPORTUNITY_DESCRIPTOR_V1**。
二者均不支持 state gate；`READY_FOR_MICRO_ROLLOUT_ACTION_SELECTION = false`。

# Valid Claims

- 合法 redundant lemma 或合法 early propagation 的时机可以显著改变 CDCL 长期 trajectory。
- 固定机制案例中曾观察到约 345k → 174k analysis operations 的变化。
- 效果不要求 Gold lemma 长期存在、Gold-specific reason provenance 或持续使用 Gold；原始 CNF
  clause 可以合法推出关键 literal。
- 同一个 exact solver state 下，不同合法 actions 可以产生 high leverage、zero effect，以及历史
  action-surface 中的 speedup/slowdown。T8/T10 有 exact-state、full-continuation、proof-verified evidence。
- 当前可靠的描述是 `effect = f(state, action)`；它是经验模型，不是已验证 predictor。
- Harness v3 已验证 multi-state collection、K=6、rank-6 replay、dynamic routes、final counters、generic
  finalization，以及 canonical logical/heuristic exact replay。

# Negative Results

- Prospective temporal v3：18 states、85 actions、103/103 exact routes；SENSITIVE=1，HIGH=1/85，唯一
  HIGH 为 -21.81% remaining-ops speedup。Frozen temporal descriptors 没有优于 frozen static snapshot。
  正式结论是 **NO_SIMPLE_TEMPORAL_STATE_ABSTRACTION**。
- Opportunity discovery v1：pending antecedent、qhead frontier、queue state、action multiplicity 等 bounded
  predicates 未产生值得 prospective promotion 的 descriptor。正式探索结论是
  **NO_OBVIOUS_INTERVENTION_OPPORTUNITY_DESCRIPTOR_V1**。
- Opportunity discovery 没有运行 prospective gate、ML、controller 或新的 native intervention。

# Invalidated Experiments

- `results/prospective_temporal_state_cohort/`：
  `COHORT_V1_INVALID_FOR_SENSITIVITY_LABELING`，first-K action contract 不完整。
- `results/prospective_temporal_state_cohort_v2/`：
  `INVALID_FOR_SCIENTIFIC_PROMOTION`，feature-schema binding 和 route/package identity 不一致。
- 旧 qualification packages：`OLD_QUALIFICATION_PACKAGES_INVALID_IDENTITY`，legacy `hc_state_hash()`
  不是跨进程 canonical identity。
- 上述数据可以解释失败原因与 harness 演进，但不能参与 v3 labels、A/B/C 判定或机会规则晋级。

# Qualified Harness

- Lock：[HARNESS_LOCK_V3.json](results/harness_qualification_v3/HARNESS_LOCK_V3.json) 与
  [SHA256](results/harness_qualification_v3/HARNESS_LOCK_V3.sha256)。
- 状态：`HARNESS_V3_CAPABILITY_QUALIFIED = true`。
- Qualification evidence：T8/T10 各 2 states，K=6，4 packages、24 actions、28 routes；logical replay
  28/28、heuristic replay 28/28、action verification 24/24、proof VERIFIED 28/28。
- HARNESS_LOCK_V3 绑定的 collector、canonical identities、runner、package contract、schema、auditor、
  finalizer 与 native binaries 不得修改。若任何 component hash 改变，必须重新 qualification。

# Preserved Evidence

- 正式 v3 报告：[PROSPECTIVE_TEMPORAL_STATE_COHORT_V3.md](results/prospective_temporal_state_cohort_v3/PROSPECTIVE_TEMPORAL_STATE_COHORT_V3.md)
- 正式 science manifest：[SCIENCE_RESULT_MANIFEST.json](results/prospective_temporal_state_cohort_v3/SCIENCE_RESULT_MANIFEST.json)
- Opportunity discovery 报告：[INTERVENTION_OPPORTUNITY_DISCOVERY_V1.md](results/intervention_opportunity_discovery_v1/INTERVENTION_OPPORTUNITY_DISCOVERY_V1.md)
- 唯一 v3 sensitive state 的 action pair：[V3_SENSITIVE_STATE_ACTION_PAIR.md](results/intervention_opportunity_discovery_v1/V3_SENSITIVE_STATE_ACTION_PAIR.md)
- Historical-positive audit：[historical_positive_audit.json](results/intervention_opportunity_discovery_v1/historical_positive_audit.json)
- T10 fixed-state evidence：`results/fixed_state_action_surface/`
- T8 S5 evidence：`results/multi_state_action_surface/S5/`
- Original-clause early-propagation mechanism evidence：`results/original_clause_early_prop/`
- 完整索引：[SCIENTIFIC_ARTIFACT_INDEX.md](SCIENTIFIC_ARTIFACT_INDEX.md)

`results/` 是本地 scientific archive，默认由 `.gitignore` 排除。不要移动 sealed evidence；需要提交经
审阅的小型 artifact 时使用 `git add -f results/path/to/file`。

# Current Open Mechanism Question

为什么极少数合法 early propagations 能改变长期 CDCL trajectory，而绝大多数合法 interventions
几乎没有效果？当前最具体的未验证线索是 **branch displacement / interaction with high-priority
branching state**：v3 同-state pair 中，HIGH action implied variable 的 activity/heap rank 为 5/3，
zero action为 96/79；pending/qhead frontier relation 则相同且没有解释力。历史 positives 缺少可对齐的
activity/semantic-heap ranks，因此不能声称该关系已经复制或可以预测 sensitivity。

# Next Recommended Experiment

## Mechanistic branch-displacement test

只对已有 auditable HIGH actions 做 bounded exact replay：

1. 在 exact checkpoint 记录 implied variable 的 canonical activity 和 semantic heap rank。
2. 检查 baseline continuation 中该变量是否很快成为 branch decision，以及 action enqueue 是否替代或
   延迟了哪个高优先级 branch。
3. 定位 intervention 与 baseline 的第一处真实 propagation/conflict/learned/branch trajectory divergence。
4. 冻结并执行最小 branch-restoration / branch-suppression counterfactual，区分“提前赋值本身”与
   “移走一次高优先级 branch”的作用。
5. 保持 exact state/action identity、完整 continuation 和独立 proof verification。

该实验是 mechanism test，不是 predictor、gate 或 controller。不要做 ML、threshold search、action
selection、direction prediction 或 micro-rollout deployment。

# Do Not Redo

- generic history ranking、proof-module abstraction、static semantic abstraction
- static action-local predictor、generic exact-alignment hunting
- first-conflict consequence 作为通用 Level-1 predictor
- static state snapshot abstraction、frozen temporal aggregate feature family
- temporal v1/v2 修补晋级、旧 non-canonical qualification package 恢复
- prior-art gate；现有定位是 **EXTEND**，不能宣称 NEW
- 正式 temporal v3 或 opportunity discovery v1 的重算、重解释或 post-hoc promotion
- ML、controller、state gate、direction predictor 或部署型 micro-rollout
