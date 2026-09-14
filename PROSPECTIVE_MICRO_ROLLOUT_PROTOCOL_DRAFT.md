**状态：设计草案，未执行、未冻结为正式实验。** Prior-art gate 为 [EXTEND](PROSPECTIVE_MICRO_ROLLOUT_PRIOR_ART_GATE.md)。先实现独立的、可截断的 micro-rollout measurement，再检验 Level-2，最后才做锁定规则的 prospective controller evaluation。以下明确下一步实现边界，不能被引用为实验结果。

| 阶段 | 可读信息 | 输出 | 不得宣称 |
|---|---|---|---|
| 正确性 smoke | 既有 T10/T8 surface、旧 counters/proofs | no-op fork 一致、合法 enqueue、shadow/real consequence 一致、独立证书检查 | 新 state 验证或泛化 |
| Level-1 prospective measurement | 预先冻结的 state 采样、全部合法 actions；选择不读取 final cost | 各 action 的 conflict/learned 变化、预算与 UNKNOWN；另行完整运行取得标签 | conflict change 必然有长期效果 |
| Level-2 development | 明示的 development CNF/state groups | 少量预先声明规则的全部正负结果；无有效规则则 NO_DIRECTION_SIGNAL | 开发集最佳规则已经泛化 |
| Locked evaluation | 未见 state groups；冻结规则及预算 | controller 对照、净工作量与墙钟、所有完成/超时/失败、独立验证 | 仅凭真实分支 analysis ops 下降宣称加速 |

S 必须包含原生调用栈位置与正在处理的 watcher loop 状态；不能只复制 trail、heap 或 JSON fields。复用单线程 native solver 的 OS fork 路径，父进程在 children 工作期间不推进。验证前后 parent fingerprint、raw object 与 heap inverse hash，child 在干预前重复检查；hash 是审计辅助，状态隔离依赖 fork。observer、文件句柄、proof streams 和计时状态另行分支管理，避免共享文件 offset 或重复输出。

动作定义为 `(stable clause identity, implied signed literal)`。只读扫描 active original/learned clauses，要求无 true literal、恰好一个未赋值 literal、native reason layout 合法；不调整 clause layout 或 watch 来扩大候选集。同一个 literal 的不同 reason 不默默合并。完整列表先保存，若预算截断按 stable ID 前缀且记录未探测项；未探测项不是 ZERO。

baseline 是同一 S 的 no-op rollout；每个 action child 只执行一次已审计的 native uncheckedEnqueue，随后恢复正常 CDCL。shadow 不允许递归触发 controller。真实 S 最终最多执行一次选中 action；不把 shadow 的 learned clauses、activity、watch mutations 或 proof additions 合并回父进程。

micro horizon 定义为首个 conflict 的原生 analysis/minimization 返回，停在后续 backtrack/学习提交前；root conflict 无 analysis 时单独记录 terminal status。如果 BCP 达到 fixpoint 后还未 conflict，需要明确记录后续原生 decisions 与工作量，不能默认首冲突必然很近。正式协议必须同时冻结确定性的工作上限和外部时间保护；超过任一界限记 UNKNOWN，真实路由 abstain。不能为获得 consequence 临时放宽上限。SAT terminal 的 model 与 UNSAT terminal 的完整 proof 必须独立验证后才可接受；普通局部 conflict 不是 UNSAT certificate。

首冲突版本只用 `conflict_changed OR learned_changed` 作为 Level-1 候选；分别保留两个 flags、canonical literals/hash、首 UIP、backtrack level、learned size/LBD、到 horizon 的工作量。next actual decision 不纳入此版本 selector；完整验证路线可记录它作事后诊断。LBD 在 backtrack 前按当前 levels 计算并核对 native nblevels 的口径，不能由旧 snapshot hash 反解。

Level-1 measurement 必须完整运行预先抽定 state 的全部纳入 actions，包括 filter-negative actions，才能检查漏掉的长期影响。只跑 conflict-changing actions 会重演旧 cohort 的条件采样，无法评估必要性。报告 HIGH≥10%、exact0 与其它效应原值；LOWER/HIGHER 成本都保留，不能只统计“命中”。

Level-2 首选检验一个有文献依据的固定比较：在 Level-1 通过且 horizon 完整的候选中，按 `(learned LBD, learned size)` 字典序与 baseline 比较，仅严格改善才干预；action 间并列用 stable ID，baseline 平局则 no-op。这是**待验证假设**，不是当前证据给出的方向规律，也不是新评分函数。不得在看完 test 标签后改为 size-first、加权或挑新的阈值。若 development 不支持该方向，应记录 NO_DIRECTION_SIGNAL；后续另一个规则属于另一个有版本的实验。

仓库已有 `good_bad_conflict_compare/GOOD_BAD_CONFLICT_COMPARE.md` 的阴性结论：两例首场 LBD/size 方向吻合，后续10-conflict均值方向反转。它们必须列入已见 development evidence，不能重包装为 holdout，也不应继续在这些 case 上调参寻求正例。上述单步规则只有经过新、预先固定样本的测试才能获得新证据。

第一版只评估每个 state 一次 intervention，避免把单步方向证据直接外推成 repeated controller。后续 repeated controller 要在其自身访问的 states 上执行同样的在线选择，不能用 baseline 未来 trajectory 作为在线 oracle。

正式运行之前还须在一个不可覆盖的 `protocol.json` 中具体冻结：CNF input hashes、development/evaluation 分组、state 采样位置与顺序、每组数量、action 上限、工作预算、时间保护、seed/config、build/checker hashes、成本终点、所有控制组与分析公式。当前不从旧 high/zero 标签选择这些数字。已知 T8/T10/T13 及 fixed GOOD 不可充当完全未见 CNF；新 exact states 若来自相同 CNF/轨迹须标记为 within-CNF，而非独立跨 CNF 泛化。

最小对照包括原生 baseline、同 instrumentation 的 no-op/shadow-only、固定稳定顺序的合法 action、Level-1 后固定选首个 action、Level-1+Level-2 controller。单独报告离线最佳 action 上界但不得在线读取它。正式算法比较还应有 PriPro / delayed-BCP / bounded multi-conflict 近邻基线；若当前 Glucose 尚未移植，不得将缺少对照的 pilot 写成算法领先结果。

计费至少分开 enumeration、clone、shadow propagation、shadow analysis、IPC、真实 search；除了原有 analysis_resolution_steps，还报告 propagation/analysis counters、总 CPU、包含所有开销的端到端墙钟。旧计时包含 parent 等待，不能直接复用其 seconds 作为 controller speedup。净分析工作可定义为真实 suffix 加所有 shadow suffix 的 analysis steps，但明确它仍不计 BCP/clone 开销。统计以 CNF/trajectory group 为单位，保留逐 state/action 表，避免把同一 proof basin 的多次命中当独立复制。

每条完成的真实 full route：UNSAT 对原始 CNF 独立 drat-trim（或另一个事先冻结的 checker）验完整 proof；SAT 由独立 checker 将 model 逐 clause 验证，必要时恢复被预处理变量。任何 checker failure 均不得进入成功性能结果；保留原文件、命令、stderr、return code 与 hashes。修复 implementation bug 必须另存 attempt，原 negative 不覆盖。预算耗尽不是 UNSAT，也不是 ZERO。
