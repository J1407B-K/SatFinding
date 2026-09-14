# GOOD / BAD TRAJECTORY ANALYSIS

**结论：有早期轨迹差异，但没有发现稳定、可用的“方向”信号。前50/100 conflicts的45个标量指标可以完全相同，最终search length却相差一倍。500附近有局部信号，跨配置、跨观察窗口不稳；当前不支持立即上learned/neural predictor。**

固定原n200_T_r01_s7201、原Glucose3.0及参数。12个已有配置，先运行独立prefix进程，精确止于conflict1000；全部早期数据冻结后才join已有final labels。完整shadow运行仅核对原生counters及prefix逐项一致，未把未来指标加入特征。研究者已知这些集合的旧结局，因此这是预先固定分析的回顾性诊断，不是盲测。没有搜索新集合。

“good”固定定义为最终ops低于TEMPLATE的90%：只有Gold64和L1+L2两个；Bad64是RANDOM64_43的别名，不重复计样本。7个K64配置仅有一个good。不能把60个checkpoint或12,000个conflicts当作独立样本。

| 配置 | K | 平均width | 平均推导depth | support inferences | validation ms¹ | 最终ops（已有） |
|---|---:|---:|---:|---:|---:|---:|
| TEMPLATE | 0 | 0.00 | 0.00 | 0 | 0.21 | 203,623 |
| GOLD64 | 64 | 3.17 | 3.45 | 265 | 5.15 | 130,718 |
| RANKED64 | 64 | 3.17 | 6.47 | 385 | 4.67 | 209,416 |
| SHORTEST64 | 64 | 2.89 | 5.58 | 312 | 4.48 | 266,446 |
| USED64 | 64 | 3.36 | 7.28 | 426 | 4.69 | 255,758 |
| RANDOM64_17 | 64 | 12.12 | 27.17 | 2797 | 14.48 | 259,270 |
| RANDOM64_29 | 64 | 13.20 | 32.02 | 3313 | 15.77 | 222,492 |
| RANDOM64_43 / Bad64 | 64 | 13.55 | 31.48 | 3991 | 18.56 | 339,321 |
| L1 | 1 | 3.00 | 1.00 | 1 | 3.58 | 345,592 |
| L2 | 1 | 3.00 | 1.00 | 1 | 3.41 | 240,436 |
| L1_L2 | 2 | 3.00 | 1.00 | 2 | 3.40 | 169,858 |
| L1_L2_L3 | 3 | 3.00 | 3.00 | 13 | 3.41 | 224,926 |

¹ 当前一次warm selected-support验证，不含共同TEMPLATE/source-index加载，不作为预测特征或精确性能比较。K64匹配；width/depth/cost没有完全匹配，尤其随机集合更宽、推导更深。为保留固定成员没有重配集合。完整分布见[static.json](results/good_bad_trajectory/static.json)。

## 1. Gold与Bad/Random/Ranked最早在哪些early metrics上分叉？

**最早检查点N=50已不同。** Gold相对这三个对照的ops、dequeues和平均LBD较低，但decisions/DL并非一致更低。这个观察不能推出整个配置集合中的好坏方向。

| N=50 | ops | 实际BCP dequeues | decisions | 平均conflict DL | 平均LBD | injected reason次数 |
|---|---:|---:|---:|---:|---:|---:|
| GOLD64 | 1614 | 6082 | 75 | 17.40 | 7.00 | 207 |
| RANKED64 | 1710 | 6556 | 71 | 16.74 | 7.74 | 247 |
| RANDOM64_17 | 1899 | 6325 | 73 | 16.76 | 7.76 | 17 |
| RANDOM64_43 | 1966 | 6460 | 73 | 16.74 | 7.62 | 4 |

方向很快出现反例：N200时Ranked平均LBD6.62，优于Gold6.88，但最终Ranked209,416 ops而Gold130,718；N1000时Ranked的injected reason使用5,116次，远多于Gold2,966次，仍更慢。“更低LBD”或“更多直接使用”均不是跨配置可靠规则。

activity top10/spread、heap操作/移动、decision变量重叠、reason来源均已采集，详见[全部45个标量](results/good_bad_trajectory/early_features.csv)及[包含top10/来源/逐lemma使用的checkpoints](results/good_bad_trajectory/checkpoints.json)。activity按var_inc归一化；heap_moves是percolation中元素移动次数，不是概念性的“换了一个basin”。

![prefixes](results/good_bad_trajectory/good_bad_prefixes.png)

## 2. 哪些只是轨迹不同，哪些与短轨迹稳定相关？

**没有一个被检查的标量能在N50和100都把两个good与所有nongood严格分开。** activity/heap距离、reason来源变化只证明trajectory不同；当前未证明它们的变化方向等于future utility。

预先固定的四项指标与最终ops的Spearman相关如下（12配置；正值表示指标越大，最终越长）：

| N | early ops/conflict | BCP dequeues/conflict | 平均LBD | 平均DL |
|---:|---:|---:|---:|---:|
| 50 | +0.092 | -0.049 | +0.078 | -0.102 |
| 100 | +0.325 | +0.120 | +0.146 | +0.093 |
| 200 | +0.428 | +0.315 | +0.355 | -0.035 |
| 500 | +0.560 | +0.301 | +0.231 | +0.211 |
| 1000 | +0.273 | +0.112 | +0.287 | +0.308 |

N500的early ops相关约+0.56是一个局部信号，应保留；它在N1000降到+0.27，不能解释为随观察加深而稳定增强。对remaining ops（最终减去已观察ops）的相关也全部导出，避免把“总量包含前缀”误当预测力。45指标×5窗口的完整结果公开，没有挑出最大相关当结论，也不提供未做多重比较校正的显著性声明。

## 3. L1/L2/L1+L2非加性：早期状态有何不同？

**L1与L1+L2在N50、N100：45/45标量相同，activity top10及decision变量直方图也完全相同。** 最终L1为345,592 ops，pair为169,858。相同的是这些观测，不是完整solver状态：额外lemma的存在、watches等仍不同。

| 配置 | ops@50 | ops@100 | ops@200 | ops@500 | ops@1000 | 最终ops |
|---|---:|---:|---:|---:|---:|---:|
| L1 | 1,426 | 3,296 | 6,838 | 18,574 | 38,323 | 345,592 |
| L2 | 1,966 | 3,810 | 7,856 | 18,757 | 37,995 | 240,436 |
| L1_L2 | 1,426 | 3,296 | 6,837 | 18,569 | 38,590 | 169,858 |
| L1_L2_L3 | 1,426 | 3,296 | 6,837 | 18,569 | 37,797 | 224,926 |

N200 pair比L1仅少1个analysis op，dequeues与decisions完全相同；N500只少5 ops，平均LBD/DL仍相同。N1000时pair早期ops反而比L1高267，但最终约少一半。加L3的前1000 ops更低（37,797 vs pair38,590），最终却更差（224,926 vs169,858）。

已有reason路径实验解释了L2可在L1造成的上下文中替代reason；本轮说明**该上下文的长期好坏，未被这些早期聚合量编码充分**。不能声称已经解释了为什么pair最终恰好更短，也不能把传播次数或早期LBD当作隐藏的“好basin坐标”。

![nonadditive](results/good_bad_trajectory/nonadditive_prefixes.png)

## 4. 前50/100/200/500 conflicts能粗略预测最终search length吗？

**目前不能稳定预测。** 固定4特征的ridge线性sanity baseline：log(1+ops/N)、log(1+实际dequeues/N)、meanLBD、meanDL；penalty1，train-only标准化，预测log final ops。未调特征、惩罚或good阈值。

| N | LOCO log-MAE↓ | held-out预测ρ | balanced accuracy | good识别 | 分组holdout log-MAE↓ | 分组预测ρ |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 0.320 | -0.594 | 0.45 | 0/2 | 0.322 | -0.437 |
| 100 | 0.263 | -0.294 | 0.50 | 0/2 | 0.243 | -0.225 |
| 200 | 0.226 | +0.021 | 0.50 | 0/2 | 0.214 | +0.294 |
| 500 | 0.184 | -0.049 | 0.75 | 1/2 | 0.159 | +0.357 |
| 1000 | 0.278 | -0.531 | 0.50 | 0/2 | 0.296 | -0.203 |

LOCO训练均值基线log-MAE=0.214；全预测nongood已有83.3% accuracy、balanced accuracy0.5，不能把83.3%当成功。N500模型识别Gold但漏掉pair，overall rank仍接近0。组留出把4个L1/L2配置整体留出、3个random配置整体留出，其余逐个留出；N500有所改善，N1000又变差。LOCO均值基线的rankρ=−1来自“移除更大的标签就降低训练均值”的代数效应，不是反向预测证据；因此均值基线主要比较MAE。

补充结果也不能省略：

- 单一early-ops回归在N500的LOCO log-MAE=0.148、rankρ=+0.315，优于均值，但N50/100/200/1000均未稳定优于均值。
- **只看7个K64配置，N200出现较好结果：4特征LOCO rankρ=+0.643、7/7分类正确。** 但只有一个positive（Gold），N50/100不成立，N500/1000又漏Gold。这是值得保留的局部观察，不是跨集合稳定预测证据。
- 固定静态width/depth/support三特征LOCO log-MAE=0.242，差于均值0.214；未找到可用的简单静态基线。
- 两个good、一个target、来自已知结局的固定sets，样本量不足以估计泛化误差。没有conflict-row随机split，也没有把重复采集当新样本。

![early-final](results/good_bad_trajectory/early_vs_final.png)

## 5. 当前最可信解释是什么？

**多因素反馈，其中branching-state shaping已有局部干预证据；“反馈朝好还是朝坏”仍未充分解释。** 注入clauses改变reason/propagation与conflict analysis，进而改写activity/heap、learned数据库和restart状态；这些变化相互影响后续搜索。低维前缀统计丢失了哪些具体clauses、变量与future conflicts发生交互的信息。

restart提供一个时间线而非充分解释：Gold在215发生restart；L1和pair都在756 restart，但只有坏L1在807再次restart，三元组合前1000没有restart。不能据此推断“越早/越多restart越好”：两个good的时点不同，坏run也restart。没有做restart干预，不能给它分配最终收益比例。

因此数据支持context-dependent的非加性search effect，不支持已经发现真实动力学basin、简单单调进度量，或“某类静态lemma天生把solver推好”的机制。

## 6. 是否值得下一步做learned/neural predictor？

**目前不值得直接启动神经模型训练。** 此样本没有稳定的50/100-conflict方向信号，pair反例明确，较晚窗口的局部成功又不稳定。更复杂模型容易记住configuration或唯一Gold，无法弥补positive数量和独立评估不足。

这不等于证明任何早期表示都不可能预测：本轮只否定“当前聚合runtime指标已经足够支持预测器”的判断。若以后继续，应先验证更完整的早期状态表示在严格隔离的固定配置上是否带来可重复增量信息，再决定是否训练；本轮没有启动该扩展。

## 7. 如果未来值得建模，真正应预测什么target？

应预测**给定target、具体注入集合、已观察搜索状态和固定solver后的剩余search work及其不确定性**，而非“轨迹离CONTROL多远”、activity改变量、直接使用量或不可观测的basin标签。已有完整同target对照时，可评估相对固定CONTROL的净future-work改善；要用于online决策，还必须扣除验证和早期探测成本。

本轮没有证明这个更丰富的条件目标可预测；不把它当作已获支持的下一路线。

证据：[冻结协议](docs/good-bad-trajectory-protocol.md) · [early freeze](results/good_bad_trajectory/early_frozen.json) · [逐配置/预算汇总](results/good_bad_trajectory/checkpoint_summary.csv) · [全部相关](results/good_bad_trajectory/all_correlations.csv) · [LOCO与分组预测](results/good_bad_trajectory/predictor_scores.csv) · [每个held-out预测](results/good_bad_trajectory/predictions.csv) · [pair相同/不同指标](results/good_bad_trajectory/pair_early_differences.json) · [audit](results/good_bad_trajectory/audit.json)。
原生propagations计数有binary-conflict早退漏记口径，另报actual dequeues；source数组顺序为original/TEMPLATE/injected/learned，逐lemma数组为reason/BCP/analysis/minimization/conflict。早期进程返回UNKNOWN是预算停止，完整shadow为solver-reported UNSAT并匹配原结果。
只读复核：`.venv/bin/python good_bad_trajectory_analyze.py`，`.venv/bin/python good_bad_trajectory_report.py`。
