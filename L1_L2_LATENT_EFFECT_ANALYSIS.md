# L1 / L1+L2：晚激活，然后延迟分叉

**前 100 conflicts 的 aggregate metrics 一样，首先因为 L2 到 conflict 198 后才首次成为 reason。** 随后的潜伏是真实可见的：conflict 199 的分析路径、activity、heap 已不同，但传播 literal 到 290 后才不同，learned content 到 656 才不同，第 828 次 decision 才不同。当前证据支持“晚激活后存在微状态差异与分层延迟分叉”，不能证明第一次扰动单独造成最终近半搜索下降。

仅比较固定 target `n200_T_r01_s7201`：A = TEMPLATE + L1（24458，`[-261,88,89]`），B = TEMPLATE + L1 + L2（30149，`[-507,565,566]`）。CNF、Glucose、seed、preprocessing、参数与原 injection order 均冻结，没有其他 subset / target。输入与构建 SHA256 见 [protocol.json](results/l1_l2_latent/protocol.json)。

| 完整自然 run | search ops¹ | conflicts | decisions | propagations |
|---|---:|---:|---:|---:|
| A | 345,592 | 8,944 | 10,415 | 737,302 |
| B | 169,858 | 4,544 | 5,286 | 359,859 |

¹ 沿用已有 `analysis_resolution_steps` 定义，不等于所有 CPU 操作。减少 175,734 ops（50.85%）。完整 native counters 与冻结结果逐项相同；两份 UNSAT proof 经 drat-trim VERIFIED。instrumented wall time 不用于比较性能。

## 1. L2 第一次真正参与 runtime 是什么时候？

要区分三个时刻：

- 初始化时，B 已多一个 clause / 两个 watches，`clauses_literals` 多 3；这是输入存储差异。
- 第一次被 watcher 检查：B `g=792, c=2, d=20, e=536, W:1`，触发 literal `-565`。检查不等于产生新赋值或更换 reason。`W_AFTER` 仅表示走过完整 watch 处理路径，不证明首次 watch 移动。
- **第一次 successful unit / reason 使用：B `g=58093, c=198, d=271, e=28916, E:191`，推出 `565=true`。** A 同时也推出 565，但 reason 是原始 `[565,566,567]`；B 的 reason 是 L2。此时 `566=false,567=false`，L2 的其他 antecedent `507=true`。

因此不能把 watcher 早期访问称为已经存在有效的 activity 扰动。首次 reason 使用确实晚于前 50 / 100 conflicts 的观察窗口。首次 UIP 使用是 conflict 199；首次直接 minimization visit 是 B `g=248169,c=815,d=1025,e=121783,M:35`；首次 L2 本身作为 conflict clause 是 B `g=223065,c=731,d=922,e=109313,C:1`。

完整 B run：L2 successful reason **175** 次、first-UIP antecedent **68** 次、minimization reason visit **105** 次、直接 conflict **1** 次。另有 watcher inspection 1,491 次。所有直接使用位置列于 [l2_direct_use_positions.csv](results/l1_l2_latent/l2_direct_use_positions.csv)，没有仅抽样展示首次事件。未成功 enqueue 的“逻辑上已 unit”不计作 successful unit；minimization visit 不代表最终删除了 literal。

## 2. A/B 第一个微状态差异是什么？

严格说，输入 clause/watch 状态从初始化就不同，不能声称整个 solver state 前 198 conflicts 一样。首次已定位的**reason 差异**是上述 enqueue 28,916。该次 enqueue 前后 activity、heap、assignment literals、phase 和 learned 内容仍相同；reason565 是新出现的动态差异。

下面给出精确事件位置。`c` 在 propagation/decision 时是已完成 conflict 数，在 C/A/U/L 时是当前 1-based conflict；`d` 是累计 decision 序号，`e` 是累计 enqueue 序号。`g` 为各 run 独立事件号，B 有额外 W 事件，不能直接相减。`type:k` 是该类型在当前 conflict 内的序号。行内均为 A / B。

| 首次差异 | c | d | e | g | local event |
|---|---:|---:|---:|---:|---|
| reason / successful unit | 198 / 198 | 271 / 271 | 28916 / 28916 | 58063 / 58093 | E:191 / E:191 |
| first-UIP antecedent | 199 / 199 | 271 / 271 | 28980 / 28980 | 58139 / 58170 | A:4 / A:4 |
| activity vector | 199 / 199 | 271 / 271 | 28980 / 28980 | 58141 / 58172 | U:7 / U:7 |
| heap array + indices | 199 / 199 | 271 / 271 | 28980 / 28980 | 58141 / 58172 | U:7 / U:7 |
| propagation literal | 290 / 290 | 383 / 383 | 42862 / 42862 | 85588 / 85634 | E:217 / E:217 |
| conflict clause | 291 / 291 | 383 / 383 | 42888 / 42870 | 85615 / 85644 | C:1 / C:1 |
| conflict trail | 291 / 291 | 383 / 383 | 42888 / 42870 | 85615 / 85644 | C:1 / C:1 |
| restart internal queue | 291 / 291 | 383 / 383 | 42888 / 42870 | 85616 / 85645 | QT:1 / QT:1 |
| minimization path | 633 / 633 | 799 / 799 | 94128 / 94082 | 191871 / 191944 | M:1 / M:1 |
| learned content | 656 / 656 | 827 / 827 | 97901 / 97858 | 199657 / 199712 | L:1 / L:1 |
| decision literal | 657 / 657 | 828 / 828 | 98056 / 98013 | 200046 / 200088 | D:1 / D:1 |

conflict 199 的第 4 个 UIP antecedent（pivot 565）首先不同。第 7 次 bump，A 更新变量 567，B 更新变量 507，activity 和 heap hash 首次分叉；该步 exact snapshot 有 2 个 activity 分量、5 个 heap array 位置和 5 个 indices 位置不同。**整个 conflict 199 分析结束后，activity 仅变量 567 不同，heap array / indices 各 3 个位置不同；learned clause 相同。** A 的 activity567 为精确 double `0x1.ac1677aad4ab3p+63`，B 为 0；这里沿用冻结 solver 的 activity 数值，不重新归一化或优化。

“完整 conflict state”包含 reasons/activity，因此在 C199 已可不同；表中 C291 是首次 conflict **clause / trail** 不同，不能把两者混同。restart queue 在 QT291 首次不同；实际第一次 restart 两边都在 c756，但分别为 d952 / d942、g230555 / g231917。按 conflict index 看，首次 restart 动作有无的分叉是 c807（A g244434,d1033,e120833；B 此处没有 restart）。

## 3. 第一次宏观搜索分叉是什么？

按外部 literal 序列定义，首次是 **c290 后，decision count383，enqueue42862**：A 推出 `-405`（reason `[-447,-405]`），B 推出 `565`（L2）。此前 enqueue literals 的前 42,861 项完全相同。接着 C291 的 A conflict 为 `[565,566,567]`，B 为 `[-565,-427]`。

如果把“search ops 计数不同”也视为宏观差异，则 conflict 199 的分析路径长度已经不同；不能说所有 aggregate 指标直到 290 / 656 都相同。C199 的 UIP antecedent visits 为 A67 / B66，累计 ops 从共同6721变为 A6787 / B6786：此处已直接少一个 resolution step，但远不足以解释最终175,734 ops差距。前 50 / 100 的 45 项完全相同与这一结果不矛盾。

learned content 首次不同在 C656：

- A：`[-157,133,137,206,226,294,300,301,505,543,565,577,586]`，width13 / LBD6。
- B：`[-157,137,153,226,300,301,367,505,565]`，width9 / LBD4。

decision literals 前 827 项相同，第 **828** 次（c657 后）A 选择 **-187**，B 选择 **-570**。这不是先 branching 分叉、再造成首个 learned 分叉；当前 pair 的顺序相反。

## 4. 两者之间潜伏了多久？

| 从首次 reason 变化 c198/d271/e28916 到… | 间隔 |
|---|---|
| UIP / activity / heap 变化 C199 | 下一个 conflict，同一 decision271 |
| 首次 propagation literal 变化 c290/d383/e42862 | 已完成 conflict 数 +92，decision count +112，enqueue 序号 +13,946 |
| 首次 learned content 变化 C656 | conflict 编号差458；C199…C655 的457条新 learned 内容仍相同 |
| 首次 decision 变化 d828/c657 | 已完成 conflict 数 +459；d272…d827 共556次后续 decision literal 仍相同 |

这是按不同 observable 定义的多段潜伏期，不是一个期间所有宏观指标都静止的单一区间。传播序列在 learned / branching 尚一致时已改变；reason / activity 的首次变化更早。

## 5. 哪些 state 在潜伏期已经不同？

完整逻辑 snapshot 保留 exact assignment、active reason 内容 hash、double activity/var_inc、heap array+indices、phase、trail/levels、ordered learned IDs/LBD/activity、restart queues 与 watches。精确文件与 SHA256 见 [snapshot_detail.json](results/l1_l2_latent/snapshot_detail.json)。

| checkpoint | assignments / trail | active reasons | activity / heap | phases | learned | restart |
|---|---|---|---|---|---|---|
| 首次 reason 前，e28915 | 相同 | 相同 | 相同 | 相同 | 相同 | 相同 |
| 首次 reason 后，e28916 | 相同 | 仅565不同 | 相同 | 相同 | 相同 | 相同 |
| U199:7 后 | 相同 | 不同 | 不同 | 相同 | 相同 | 相同 |
| C199 分析结束 | 相同 | 仅565不同 | activity567；heap各3位置 | 相同 | 相同 | 相同 |
| C656 analysis 前 | 不同 | 不同 | 不同 | 见原始snapshot² | 655个有序ID相同；2个条目metadata不同 | 不同 |
| decision828 前 | **重新相同** | 不同 | 不同 | 不同 | 内容已不同 | 不同 |

² phase 在 C656 analysis 前相同；decision828 前才在这组 checkpoints 中观察到不同，未宣称这是 phase 的首次差异。

watches 从初始化就因 L2 不同。e28915 去掉 L2 项后仍有一个公共 watch-list 不同，C199 分析结束时去掉 L2 后公共 watches 又相同。enqueue 内 snapshot 是 propagation watch 循环中的现场，可能含正在搬移的条目，不能把它当成传播结束后的规范 watch 布局。当前没有逐次全量 watch 内容日志，**未定位公共 watch 顺序差异的第一个写入事件**。因此“第一个微状态”应严格限定为已定位的 reason/activity/heap；不能排除更早的 watch 内部差异。

`simpDB_props` 在 e28915 为 A -8279 / B -8276，`clauses_literals` 为5632 /5635；这是额外 clause 引入的已有预算/存储差异，不把它解释为已证明的收益来源。

## 6. L2 的作用更像哪一种？

**相对于前100 conflicts：late activation。激活以后：持续存在的微状态差异、重复激活与延迟分叉。** 不支持“前50/100已有隐藏 activity 信号只是 aggregate 没抓到”这一具体解释；更不能从该 pair 推出 early aggregate predictor 可行。

第一处 reason substitution 同一 literal 换了一条更短的证明路径，跳过分析中的变量567，却暂时得到相同 learned clause。不同的分析过程可以收敛到相同 learned 内容；相同的 decision 序列也不要求 heap 全部相同。这解释了为何某些 observable 长时间保持一致。最终为什么 B 的后续整段搜索更短，仍没有可归因到单一早期事件的完整证明。

## 7. 是否存在可检查的 delayed amplification 链？

有局部执行链，以及时间上连续的分层分叉；没有成功的反事实实验证明第一处扰动对最终收益必要或充分。以下三个 case 可分别检查 [critical_analysis_paths.json](results/l1_l2_latent/critical_analysis_paths.json) 与已有 implication paths [pair_path_cases.json](results/gold_mechanism/pair_path_cases.json)。

**Case 1 — C199，same consequence / different reason。** 两边共同有 L1→89(e28749)→-299(e28759)→298(e28789)→-505(e28811)→507(e28825)。A 经 `[-567,-507]` 得到 -567，再由 `[565,566,567]` 推出565；B 由 L2 直接以507及-566推出565(e28916)。共同再由 `[-565,-427]` 推出-427(e28950)。UIP pivot565使用不同 reason，A 额外沿 pivot-567 分析，B 跳过；activity567 / heap 不同，但最终 learned 相同。这条 reason→analysis→activity/heap 链有直接事件与 exact snapshot 支持。

**Case 2 — C291，different conflict / same learned。** B 的 L2→565(e42862) 与427使 `[-565,-427]` 冲突；A 首先遇到 `[565,566,567]` 冲突。B 的 UIP 第2个 antecedent 是 L2。两边 C291 最终都学出 `[-468,86,152,179,204,217,252,290,330,425,450,478,490,513,517,535]`。这说明 conflict/propagation 已不同，并不立即意味着 learned content 不同。不能仅凭时间先后断言 C199 的 heap 差异导致 C291，L2 的再次直接传播也在作用。

**Case 3 — C656→decision828，different learned before different branch。** B 的可回溯链为 L2→566(e97777)→-23(e97789)→22(e97800)→-151(e97819)→152(e97833)→冲突 `[-152,-11]`；A 冲突为 `[103,104,105]`。B 在 UIP 第13个 antecedent 再次访问 L2（pivot566），第一次学出与 A 内容不同的 clause。下一 conflict 后发生 decision828=-187/-570 的分叉。此时 assignments/trail 已重新相同，但 reason/activity/heap/phase/learned/restart 不同；**不能唯一归因于 activity/heap，也不能把 C199→C656 画成已验证的单一路径。**

**本轮唯一 intervention 尝试没有形成可解释的反事实 run。** 自然 trace 后冻结：在 B e28916 只把565的reason换为 A 的原始 `[565,566,567]`，不改其他字段。实际检查确认该 clause 存在、其他 literals 都 false，但 B 中其 slot0 不是565；不满足本 solver first-UIP 的 reason layout 约定。程序在写入前 exit14。pre-attempt snapshot 与自然 B 完全相同，无 after-reset snapshot、无完成 counters / proof / divergence-delay 结果。没有调换 clause literals / watches，也没有改试另一种 intervention。[intervention_protocol.json](results/l1_l2_latent/intervention_protocol.json)、[audit.json](results/l1_l2_latent/audit.json) 可核对。

因此目前支持的是 **late reason activation→不同分析与 activity/heap→多次传播/冲突差异→learned 与 branching 后续分叉** 的描述性链。尚未证明存在一条从首次扰动到最终175,734 ops收益的必要因果链；也没有证明“直到分叉前没有状态差异”。

## 8. 下一步最小实验是什么？

若继续，单独冻结一次 **C199 analysis结束后的 activity567 恢复**：仅把 B 的该分量设为 A 值，并做该变量所需的合法 heap 更新；其余状态保持 B。这是对当前直接观测到的持久 mediator 的一个实验，不再碰尚在 watch 循环中的 reason 布局。只检验首次传播/learned/decision 分叉是否推迟，并验证非允许字段与 native proof；无论结果如何不追加其他重置。**本轮未执行**，也不声称该实验能分离整个 heap 历史或解释最终50.85%收益。

## 可复查边界

完整事件 ledger 只保留 c≤900；L2直接使用位置保留到完整求解结束。总 gzip ledger约17MB，另有少量完整关键 snapshots，没有保存全程所有传播日志或生成 aggregate plots。事件级64-bit hash用于发现差异，关键位置由完整逻辑数组和 SHA256补充核对；reason/learned IDs按内容定义，不使用跨run allocator地址。

读取式补充 snapshot replay 的完整 native counters 与原自然 run 相同，解压事件 ledger 逐字节相同。源文件 SHA256 未变；自然 A/B 全部完整 counters 重现，proof 均 VERIFIED。实现入口：[l1_l2_latent.py](l1_l2_latent.py)、[l1_l2_latent_analyze.py](l1_l2_latent_analyze.py)、[l1_l2_latent_report.py](l1_l2_latent_report.py)。本轮没有新target、subset、selector、ML或第二次干预。
