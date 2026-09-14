# Decision828 context analysis

**找到一个具体、可干预的 reason/learned-clause ingredient，但它不足以解释 B 的短轨迹。** A/B 在 d828 前 assignments 一样，当前 reason 仅变量259不同。同选-570后，该差异进入 C660 分析并改变 learned clause。唯一移植实验成功复现了 B 的这条 learned，却没有复现后续选支，最终变成367,830 ops。当前整体结论是 **distributed context dependence**，其中有一个已经定位的局部 learned/reason 作用链。

固定四条run：A normal345,592、B normal169,858、A force-570为331,444、B force-187为330,644 ops。全部重新观测后的native counters与旧结果完全相同，完整proof逐字节相同并再次VERIFIED。只额外执行了下述一个自然trace选出的context-ingredient干预。

## 1. conflict600到decision828，A/B context具体差在哪？

**d828在c657后。** C700/750/800是分支后的检查点，不能当作分支前原因。下面比较完整逻辑snapshot中的具体字段；数字为不同变量/条目数，heap是array / inverse-indices位置数，eligible为solver的decision标志。checkpoints在冲突分析、回跳、learned安装完成后、下次传播前；d828前则已完成传播。

| checkpoint | assignments | active reasons | activity分量 | heap位置 | phases | learned内容位置 | eligibility |
|---|---:|---:|---:|---|---:|---:|---:|
| C600 | 0 | 0 | 0 | 45 / 45 | 1 | 0 | 0 |
| C650 | 0 | 0 | 40 | 217 / 217 | 0 | 0 | 0 |
| C656 | 0 | 1 | 70 | 272 / 272 | 3 | 1 | 0 |
| C657 | 0 | 1 | 71 | 279 / 279 | 3 | 2 | 0 |
| d828前 | 0 | 1 | 71 | 279 / 279 | 3 | 2 | 0 |
| C700 | 139 | 145 | 501 | 474 / 483 | 145 | 41 | 0 |
| C750 | 79 | 70 | 571 | 528 / 544 | 199 | 91 | 0 |
| C800 | 149 | 152 | 588 | 545 / 576 | 205 | 141 | 0 |

C600的activity vector已经再次完全相同，heap仍有45个位置不同；这不是C199差异从此单调累积的故事。C650之前learned内容仍同；C656/C657产生两条不同内容的learned。d828前的具体差异是：

- **assignments、trail、levels、qhead、decision eligibility相同**，不存在B独有的已赋值literal使-570立即多剪枝。
- 仅**变量259的当前reason**不同，均解释`-259=true`，分别为各自的C657 learned。
- 71个activity分量、279个heap位置不同；phase只在变量254、413、549不同。
- ordered learned内容只在第656和657条不同，此外存在metadata差异；并非已有大量内容不同的learned。
- restart的`sumLBD`、`lbdQueue`、`trailQueue`不同，但此前实际restart动作并未分叉。watches也已不同，且B一直多L2。

C656：A width13/LBD6，B width9/LBD4。C657：A width27/LBD7，B width24/LBD6。完整clauses、活动变量ID、reason与heap差异以及restart字段见 [context_analysis.json](results/decision828_context/context_analysis.json) 和各checkpoint snapshot。四条run在分支前分别保持自己的A/B context，未从对方复制状态。

## 2. 同一个-570，第一处响应差异是什么？

比较 **A_FORCED vs B normal**：最初并没有不同的传播收益，两边都走：

`decision -570 → [-187,252,570] 推出-187 → [187,188,189] 推出189 → -324,-300,-201 → …`

这几条reason都已在A/B中存在。第一批传播、C658冲突`[1,2,3]`、C659冲突`[-316,-82]`以及两条新learned内容相同。d829两边均选-568。

最早的新**分析响应**差异在 **C658 minimization第21次reason visit**：访问变量259的不同C657 clause（A g200841/e98122，B g200883/e98079，均d829）。这次差异尚未改变最终learned内容。随后按顺序：

| 事件 | A_FORCED | B normal |
|---|---|---|
| C660 UIP第21个antecedent，pivot-259 | A C657 reason；g201439/e98391 | B C657 reason；g201481/e98348 |
| C660 learned，第3个post-branch conflict | width24/LBD6，含额外133、577 | width22/LBD5，无133、577 |
| C660后assert -45 | 相同literal、不同learned reason；e98392 | 相同literal、不同learned reason；e98349 |
| d830（c660后） | +187；g201584 | +58；g201620 |
| d830后的第一条不同BCP literal | -568；e98394/g201586 | -451；e98351/g201622 |
| 首次不同conflict clause：C664，第7个post-branch conflict | `[-505,-328]` | `[556,557,558]` |

因此不是“-570在B立即触发一条A没有的神奇传播链”。具体差异首先来自既有reason如何参与分析，然后表现为learned及后续选支不同。两边前334条非decision enqueue literals相同，第335条非decision enqueue才在d830后不同；若把decision入栈也计入，第337次enqueue不同，其实是d830本身，不能误报为BCP差异。

精确first-response记录见 [first_response_details.json](results/decision828_context/first_response_details.json)。每条UIP antecedent、conflict、learned、LBD/width、backjump、activity bump精确double与后续decision，均保存在 [branch_responses.json](results/decision828_context/branch_responses.json)。

## 3. 为什么A force-570不能复制B？

**它复制了最初的赋值响应，却没有复制分析上下文和后续branch ordering。** 最明确的一个差异是当前-259使用的C657 reason。它在C660参与first-UIP，使A学出的clause比B多133和577，LBD也不同。

本轮唯一干预在A的d828前，添加B的C657 learned clause并将它设为当前-259的reason，然后执行原定的force-570。保留A已有C657，不复制activity/heap/phase/restart，也不添加L2。结果：

| run | C660 learned | d830 / d831 | 最终ops |
|---|---|---|---:|
| A force-570 | A式：width24/LBD6 | +187 / +58 | 331,444 |
| B normal | B式：width22/LBD5 | +58 / +187 | 169,858 |
| A移植B-C657作为reason，再force-570 | **完全匹配B的内容及LBD5** | **仍为+187 / +58** | **367,830** |

移植把与B的首次learned-content差异从C660推迟到C662，但d830没有推迟；截至观测上限C800，其后176次decision literals仍与原A_FORCED一致。相同C660 learned仍可对应不同branch ordering，且最终更长。因此C657是局部有效ingredient，**不是收益的充分条件**。这也排除了“只缺这条learned/reason，补上就能复制B”的解释。

![单个ingredient的局部作用与不足](results/decision828_context/ingredient_chain.png)

合法性检查通过：干预前snapshot与原A_FORCED完全相同；head=-259已为true，其他23个literals均false，head及最高antecedent level都是9，新clause正确放置head和watches。变化限于新learned及其watches和reason259；assignment/trail、variable activity、heap、phase、restart、eligibility均不变。不是仅替换一个裸指针：新clause有正常learned DB归属与生命周期，因此这个实验检验的是**一条clause及其当前reason角色**。

证书中加入B到C657的有效推导前缀及L2的推导支持，仅用于proof；这些辅助clauses没有装入solver DB。完整干预proof在原A输入上drat-trim VERIFIED。结果与变更hash见 [intervention/result.json](results/decision828_context/intervention/result.json)、[intervention/protocol.json](results/decision828_context/intervention/protocol.json)。没有做第二个干预。

## 4. 为什么B force-187会丢掉短轨迹？

本轮发现，**-187与-570在这个现场很快会互相推到，而不是进入两个初始赋值互斥的区域**：

- 选-570：通过`[-187,252,570]`推出-187，再推出189。
- 选-187：通过`[187,188,189]`推出189，再由`[-570,-189]`推出-570。

四条run到首个冲突C658时，已赋值literal集合都是同样的215项、conflict clause也相同。在同一context内，选支改变的是187/570谁是decision、谁是有reason的propagation，以及trail顺序；不是这个时刻多排除了哪些assignment。重建记录见 [first_conflict_state.json](results/decision828_context/first_conflict_state.json)。

B normal与B_FORCED首先在C659学出不同内容，随后分析与未来轨迹改变；此前双向forced intervention已经证明其最终长度影响。但这次trace**没有完整识别哪一段重复搜索因此重现**，不能把“330k”全部归因于一条已找到的clause。

同样，B_FORCED还保留B的C656/C657、全部先前heuristic state以及后续L2，仍然长。因此这些ingredients单独存在也不能保证短轨迹，必须考虑reason-root选择与后续反馈的组合。

## 5. 是否存在少量可识别的context ingredients？

有，但目前是局部ingredient，不是完整收益清单：

1. **C657 learned及reason259：** C658 minimization、C660 UIP直接访问；移植能复现B的C660 learned，已有干预证据。
2. **后续variable ordering：** 71个activity分量和279个heap位置不同；修复上述learned以后d830仍相反，说明该局部learned不足以修复后续选支。未分离activity与heap贡献，不能宣称某个分量已被证明必要。
3. **L2后续仍然可用：** B在c660后d834/e98483再次用L2推出565，C661的UIP再访问它；移植run此处仍用原始`[565,566,567]`作为reason。持续在线的L2是剩余context的一部分，不能全部称为“828前已写好的状态”。

B的C656 clause虽然是B独有内容，但在B normal的d828后到C800范围没有直接E/A/M/C使用；不能仅因为它出现得早就把它指认为第一响应的直接触发者。不同run中的直接使用不同，详细使用位置见context_analysis中的ingredients。

## 6. 当前更像哪一种机制？

**整体：distributed context dependence；局部：specific learned/reason context与heuristic-state context同时可见。** 单一assignment-context解释不成立，因为分支前assignment完全相同；“立即更多propagation pruning”也不符合最初响应。不是等很久才首次出现差异：第1个post-branch conflict的minimization已经不同，第3个产生learned差异，第2次后续decision再次分叉。

但早出现差异也不等于已找到最终收益来源。前1/5/10/20/50 conflicts的compact响应如下，每格为**native propagations / analysis ops增量**，截至对应冲突分析完成：

| post-branch conflicts | A | B | A force-570 | B force-187 |
|---:|---|---|---|---|
| 1 | 60 / 18 | 60 / 18 | 60 / 18 | 60 / 18 |
| 5 | 429 / 219 | 435 / 219 | 435 / 220 | 361 / 250 |
| 10 | 938 / 438 | 899 / 456 | 627 / 318 | 706 / 474 |
| 20 | 1784 / 797 | 1517 / 806 | 1017 / 708 | 1180 / 890 |
| 50 | 4679 / 1920 | 3665 / 2178 | 3791 / 1918 | 3921 / 2149 |

B在前50 conflicts用了2178 ops，A_FORCED只用1918，最终却是B显著短。不能把本表变成早期评分器，也不能把本地少一两条literal直接等同于全局好轨迹。图的上半部逐conflict比较learned内容，下半部只展示响应成本，不做预测。

![四条run的逐conflict branch response](results/decision828_context/branch_response_comparison.png)

## 7. 哪些链条有intervention或direct trace支持？

- **直接trace：** 相同-570→相同最初传播；不同reason259→C658 minimization差异→C660 UIP访问不同C657→不同learned。
- **本轮唯一intervention：** 移植B-C657及其reason角色→C660 learned内容/LBD复现B；但d830不复现、最终更差。这验证了局部作用，同时否定其充分性。
- **前轮合法双向intervention：** 在各自固定context里改变d828确实改变最终search length，且强烈不对称。
- **仍未分离：** 哪些activity/heap/phase/watches成分必要、持续L2的贡献、哪些具体长尾被避免、是否少量ingredients组合足够。本轮没有组合移植或继续调整干预救结果。

证据审计见 [audit.json](results/decision828_context/audit.json)。600…800的event ledger有精确c/d/e/g/k及完整内容catalog，logical snapshots保留具体数组与reason/learned身份；未保存整个求解的巨大完整日志。原四条run与旧有效proof完全一致，额外干预proof也通过。源码入口：[decision828_context.py](decision828_context.py)、[decision828_context_analyze.py](decision828_context_analyze.py)、[decision828_context_intervene.py](decision828_context_intervene.py)。

## 8. 下一步最小实验是什么？

下一轮可只冻结一个 **B在d828前移除L2、保留已形成的context，然后照常选-570** 的run，前提是当时L2不是任何active reason且删除操作合法。与现有B比较，区分“先前形成的context已足够”与“L2后续持续参与仍重要”。保持所有已学clauses、activity/heap/phase/restart不变，验证proof；非法则中止。

**本轮未执行这个实验。** 目前能回答的是：-570的即时赋值收益并非B独有；差异通过已有reason与后续选支/继续传播的反馈产生。已定位并干预验证了一条局部链，但尚未把十几万ops收益归约为少数充分状态因素。

## 9. 已完成的 L2 消融

按上述最小实验执行了一次冻结消融：从 B 的 conflict657 / decision828
边界开始，在 native pick 前严格移除唯一 L2 原始 clause
`[-507,565,566]`。此时三个 literal 都未赋值，且没有 active reason；移除
只改变该 clause 的 watches 与 `clauses_literals`，并记录 DRAT deletion。

控制重跑保持 169,858 ops、4,544 conflicts、5,286 decisions、359,859
propagations，与冻结 B 一致。移除 L2 后仍为 UNSAT，`drat-trim` VERIFIED，
结果为 174,427 ops、4,698 conflicts、5,421 decisions、367,157 propagations。
因此 d828 之前形成的 context 保留了大部分短轨迹；L2 在 d828 后继续可用有约
4,569 ops 的可测贡献，但不是 169k 轨迹的充分解释。完整协议、快照、事件和
证明见 [DECISION828_L2_ABLATION.md](DECISION828_L2_ABLATION.md)。
