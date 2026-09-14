**Decision: EXTEND.** 检索日期：2026-09-12（Asia/Shanghai）。本轮先读取指定的11份报告及对应 JSON/CSV，再核对 solver instrumentation、验证代码和既有 proof artifacts；没有使用旧聊天作为证据，没有运行新 solver experiment。

本 gate 针对的是下列完整组合：在当前 CDCL 搜索中暂停于传播尚未完成的状态 S；枚举当前真实 unit、implied literal 尚未赋值的合法 clause/literal actions；从同一个 S 为 baseline 和每个 action 建立隔离 shadow；只提前一次合法 enqueue，然后运行到首个 conflict 并完成 analysis；比较 consequence，决定真实 S 是否执行哪个 action。完整求解成本不进入这个选择过程。

已核查来源中**未找到这一完整闭环的直接实现**。这不等于不存在，也不足以给出 NEW/首创结论。相邻工作的机制重叠很强，尤其是 priority/delayed BCP 与 multi-conflict analysis。若后续发现逐 action 的同状态探测与真实调度选择已经实现，应重开 gate；仅改名或替换 cloning 技术不能避免 STOP_DUPLICATE。

| 路线 / 一手来源 | 已有方法与本题的关系 | 判断 |
|---|---|---|
| [Heule / van Maaren, march_dl，§2](https://www.cs.cmu.edu/~mheule/publications/JSAT2_3_Heule.pdf) | 对试探 literal 赋真后做传播，用结果选择 branch；failed literal 的反面被强制。这里待选动作已经有当前 unit reason，选择的是执行时机，不是试探新分支真假。 | REUSE lookahead 的试探/撤销思想；非直接重复 |
| [Biere / Järvisalo / Kiesl, Preprocessing in SAT Solving，probing / hyper binary resolution](https://cca.informatik.uni-freiburg.de/papers/BiereJarvisaloKiesl-SAT-Handbook-2021-Preprocessing-Chapter-Manuscript.pdf) | probing 推导 forced literals / binary consequences；也存在 binary-first 传播。不能将当前已强制 literal 的调度选择称为新 failed-literal probing。 | REUSE 合法性与探测边界；动作语义不同 |
| [Concurrent Cube-and-Conquer](https://arxiv.org/pdf/1402.4465) | lookahead 与 CDCL 协作，划分并求解 cube，判断何时停止划分。本题不添加 cube assumptions，也不选 branch polarity。 | 邻近，非直接重复 |
| [Biere, Lingeling and Friends，2012，Treengeling](https://cca.informatik.uni-freiburg.de/papers/Biere-SAT-Challenge-2012.pdf) | 明确区分仅复制 clauses/assumptions 的 lglfork 与复制 phase、variable queue 等状态的 lglclone；后者用于 lookahead splitting，两个分支分别加入 decision 及其反面。状态 cloning 早已存在。 | REUSE；cloning 本身无新意 |
| [Speculative SAT Modulo SAT，§III/V](https://arxiv.org/pdf/2306.17765) | secondary module 在 main module 尚未完成时做 decisions；模块交换 unit literals，并进行跨模块 analysis。控制对象是模块的 speculative decisions，不是同一 CDCL state 的候选 unit 调度。 | 邻近；已读机制非本题闭环 |
| [Chen, Core First Unit Propagation，2019](https://arxiv.org/abs/1907.01192) | 优先处理 core clauses，以改变传播和学习结果。 | EXTEND；不能声称传播调度本身新颖 |
| [PriPro: Prioritised Unit Propagation by Partitioning the Watch Lists，§3–4](https://ceur-ws.org/Vol-3545/paper2.pdf) | 两套 watch-list scheme，动态升降 clause priority；依据近期 resolution 使用及 LBD/size 等调整。确实有意改变搜索路径，但选择来自启发式，没有所述同状态逐 action shadow 比较。 | EXTEND；主要调度近邻 |
| [Chung, Prioritized Unit Propagation and Extended Resolution Techniques for SAT Solvers，2023，Chapter 3](https://uwspace.uwaterloo.ca/items/b9fd3615-1cc7-4120-bb9d-883c85fd3c7a) | Immediate/Delayed BCP 区分 assignment order 与 processing order；priority queue 控制尚未赋值的 implied variables。还讨论根据 solver state 选择 BCP 的理想策略，实际以 restart 间的历史反馈切换。这里不能声称首次提出 state-dependent BCP control。 | EXTEND；最接近动作语义的工作之一；不采用其 ML 路线 |
| [Si et al., PUPPER，2019，§2](https://arxiv.org/pdf/1912.05906) | 从 full assignments 出发，按变化率安排变量，交替构造赋值并传播，加 periodic resetting。标题相近，但不是当前 CDCL 内待调度 unit actions 的对照探测。 | 非直接重复 |
| [Cao, Concurrent Multi-conflict Analysis，2022，§3.3–3.8](https://www.researchgate.net/publication/365361605_Concurrent_Multi-conflict_Analysis_in_SAT_Solvers) | 作者公开预印本：继续传播收集多个 conflict，在扩展 implication graph 上分析，按 size/glue 等选择 lemma；还有 bounded overhead。不是为各调度动作复制 S，但已覆盖“先比较后果再选较好学习结果”。 | EXTEND；关键概念近邻，不能只与 branching lookahead 比较 |
| [Oliveras / Rodríguez-Carbonell / Zhao, Analyzing Multiple Conflicts in SAT: An Experimental Evaluation，§3–5](https://easychair.org/publications/paper/8DDd/download) | CaDiCaL 收集多个 conflicts，分析/minimize 后选择最低 LBD、再最短、再最早的 lemma。优化版在首个 conflict 后扫描 pending watch lists，不改 assignment/watches，并限制额外工作。与逐 action 改变未来 propagation 的分支有区别。 | EXTEND；Level-2 的直接基线来源，LBD/size 评分无新意 |
| [Audemard / Simon, Predicting Learnt Clauses Quality，IJCAI 2009](https://www.ijcai.org/Proceedings/09/Papers/074.pdf) | LBD 是已有 learned-clause 质量指标；不能将它解释为已证明的单次 scheduling intervention 长期收益信号。 | REUSE 指标；方向预测仍待验证 |

表内“非直接重复”是对已读算法的比较判断，不是对整条研究线全部文献的不存在证明。Cao 来源为作者上传全文而非 ResearchGate 自动摘要；预印本身份不作同行评审结论。Chung 的算法细节同时核对[机构存档全文 Chapter 3](https://dspacemainprd01.lib.uwaterloo.ca/server/api/core/bitstreams/8dc83ea9-9592-488b-8860-7b6c0d7d450e/content)。

检索覆盖 SAT lookahead、failed-literal probing、speculative propagation、cube-and-conquer、conflict/learned quality prediction、state cloning，并沿 priority BCP 与 multi-conflict 的相关工作继续核查。代表检索串保存在 `results/prospective_micro_rollout_gate/search_log.json`。精确组合词检索有大量无关结果；不把零相关命中计为无先例的证据。未完成所有相关 solver 源码的逐行审计，因此不宣称源码层面的穷尽排重。

仓库证据对应的实现决定如下：

- `conflict_frontier_discovery.inc` / `state_sensitivity_cohort.inc` 已有同父进程 OS fork、单次合法 early enqueue 和首个 conflict analysis stop，应该复用。`fixed_state_action_surface.inc` / `multi_state_action_surface.inc` 已有整个合法 action 列表冻结与 parent-state 审计。JSON snapshot 是 manifest，不是可加载 checkpoint。
- [Original early propagation](results/original_clause_early_prop/ORIGINAL_CLAUSE_EARLY_PROP.md) 的 345,571 → 174,433 是 **analysis_resolution_steps** 的变化，不是完整计算工作减少约一半。此前 C600–C655 的 L2 历史仍保留。未来“净收益”必须包含 enumeration、cloning、shadow propagation/analysis、IPC 和真实求解。
- [84次局部审计](results/high_leverage_discovery_local_audit/HIGH_LEVERAGE_DISCOVERY_LOCAL_AUDIT.md) 的70/14分组是所观测 consequence 相同/仅 dequeue 改变，不是证明完整内部状态相同。
- [Cohort](results/state_sensitivity_cohort/STATE_SENSITIVITY_COHORT.md) 有15个 event、14个指纹 context、5个粗 decision contexts。10个 HIGH 为5 speedup / 5 slowdown；全15个则5 speedup / 9 slowdown / 1 zero。不能将 event 当独立样本。
- [Consequence abstraction](results/consequence_abstraction_v1/CONSEQUENCE_ABSTRACTION_V1.md) 的11个 action 只有4 HIGH和7 ZERO；四条候选 flags 完全同向，不是四份独立证据。T13_P329 已反驳 conflict change 对 high leverage 的充分性。
- [Action abstraction](results/action_abstraction_v1/ACTION_ABSTRACTION_V1.md) 仅7个 numeric 字段完整覆盖，另7个不完整。它支持停止当前静态特征路线，不能表述为所有静态字段已被证伪。
- [Same action / different context](results/same_action_context_compare/SAME_ACTION_CONTEXT_COMPARE.md) 也已核对：C130 early566 在首个 conflict 前未被 dequeue；C656 会被 dequeue。不能把“enqueue 提前”直接等同于影响穿透。
- 补读的 [Good vs bad conflict comparison](results/good_bad_conflict_compare/GOOD_BAD_CONFLICT_COMPARE.md) 已给出 **NO_SIMPLE_CONFLICT_QUALITY_EXPLANATION**：首场 LBD/length 方向吻合，但固定后续10场的均值方向反转。该 negative 保留；不能把 Level-2 的 LBD 假设写成仓库已经证明的方向信号。

Level-1 采用 conflict canonical clause / learned canonical clause 的变化作为待验证筛选。到首个 conflict 并完成 analysis 后，**next actual decision 可能仍未知**；不能偷跑至下一 decision 后仍称同一个首冲突预算。相同 canonical consequence 也不保证 reason graph、clause layout、activity 和后续轨迹全部相同。

Level-2 可以检验已有指标在此动作空间中的方向价值，但不能用现有 T8/T10 标签反复挑公式。最低 LBD / 最短 learned clause 的启发式已有直接先例；其 prospective 收益与开销偿还能力才是这里要回答的问题。所有 negative、timeout、UNKNOWN 和 validation failures 必须保留。

最终定位是 **EXTEND existing prioritized propagation and consequence selection with paired, bounded state-local action trials**。仓库已有机制实验的 REUSE 不等于外部学术新意。没有直接重复的充分证据触发 STOP_DUPLICATE，也没有足够排重证据选择 NEW。后续设计见 [prospective protocol](PROSPECTIVE_MICRO_ROLLOUT_PROTOCOL_DRAFT.md)；本 gate 不宣称 controller 已验证或有效。

本轮 artifact 审计输出为 [repository_audit.json](results/prospective_micro_rollout_gate/repository_audit.json)：核对指定实验内171份既有验证日志均包含 `s VERIFIED`，对应 gzip proof 可解压，其解压 SHA256 可在本实验 JSON 记录中找到；并核对 abstraction 的 input hashes、关键计数与表格标签。它是存档一致性审计，**没有重新执行 checker**，不能替代独立证书验证。171包含重复基线与复跑，不代表171个独立case。本轮仅新增 gate、审计 artifact 和协议草案；没有改 solver 或旧实验 protocol。
