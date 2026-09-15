# 实验数据保留与清理

## Fresh executable evidence：永久保留（2026-09-15）

`results/fresh_heuristic_causal_cohort_v1/`、
`results/fresh_trajectory_divergence_audit_v1/` 及其对应的
`execution_pipeline_v1/` 源码、构建、可执行文件、输入、requests、proofs、
checker 输出、telemetry、route-level mappings 和 manifests 必须永久保留。
下文历史清理规则不适用于这些目录；不得以“可重生成”为由清理。
旧 H1–H5 executable provenance 已永久丢失，不得重新纳入 active science。

2026-09-11 清理仅涉及未跟踪的可重生成实验产物，没有删除已跟踪文件或改写 Git 历史。
逐文件路径、大小与 SHA-256 见 [删除清单](results/cleanup_20260911.json)。

删除范围：

- `results/` 下生成的 `.cnf` solver 输入及 `.drup` 原始 completion proofs，包含每次重复测量的副本。
- 早期 `round3_certificates/` 和 `round3_large_smoke_certificates/` 批量证书。

保留范围：

- 所有源码、协议、报告、图、汇总、原始数值测量和 oracle 搜索记录。
- JSON target 输入、历史与 TEMPLATE 的 `.resolution.json.gz`、Gold 选中 ID、关键 `.certificate.json.gz`。
- 最新 `target_local_history/` 的完整数据，包括 target-only 短证明、选择结果和轻量 trajectory。
- 较小的 round3 smoke 证书及其他压缩证明。
- 外部 `artifact_/` 资料在本地保留，整体加入 `.gitignore`，不作为项目实验数据提交。

`.gitignore` 同时屏蔽上述会重新生成的大型数据和 `.DS_Store`。
不要忽略整个 `results/`：复核结论所需的小型数据仍应入库。

历史报告中的原始 CNF/DRUP 路径以及已清理 round3 证书路径现在是历史 provenance，
并非仍存在的文件。旧的逐文件 proof/hash 审计需要先按对应协议重新生成产物；
本次没有修改 checker 来静默跳过缺失证据。重跑产生的时间值会变化，不能冒充原运行。
删除清单的哈希只记录被删除文件的身份，不替代原证明。

当前冻结主实验仍可运行 `audit_target_local_history.py`；复现入口见
[TARGET_LOCAL_VS_HISTORY.md](TARGET_LOCAL_VS_HISTORY.md)。
依赖旧原始产物的全量审计，应参考 `docs/` 中相应轮次协议和实验驱动重新生成。
