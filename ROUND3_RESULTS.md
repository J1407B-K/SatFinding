# Round 3：能附证恢复隐藏 parity，但没有超越普通预处理

在本轮 inverse-resolution splitting 实验中，SatFinding 能从不含完整 canonical parity 模板的 CNF 中，通过显式 resolution 推导恢复全部 parity，再生成并检查 GF(2) 反驳。**CaDiCaL 预处理也在全部输入上恢复了全部原始 parity，因此本轮没有给出超越普通预处理的结构发现证据。**

配置为简单连通 6-regular 图，n=80/160/320/640，seeds=10..19，planted_depth=0/1/2/3。共 160 个 UNSAT 实例和 160 个 SAT 对照，每个输入运行五路，共 1600 行原始结果。无 history、无 learned retriever。

## 五路结果

| 路线 | UNSAT 完成数 | 原始 parity 恢复 |
|---|---:|---|
| A：Glucose3 | 0/160 | 未开放该指标 |
| B：CNF-only CryptoMiniSat 5.14.7 | 90/160 | 内部计数不可访问 |
| C：CaDiCaL 预处理 + 同一 CryptoMiniSat | 120/160 | 160/160 个 UNSAT 输入全部恢复，SAT 对照也全部恢复 |
| D：blind discovery + 两层 checker | 160/160 | 全部恢复并附证 |
| E：原始 XOR equations oracle | 160/160 | 特权输入直接给出 |

A/B/C 使用 2 秒 solver call 预算，外层 watchdog 为 12 秒；加载和预处理额外计时。D 使用固定步骤预算，最大输入耗时约 3 秒，因此**不能把完成数直接解释为同预算的速度胜负**。C 的 40 个 UNKNOWN 均已恢复全部原始 parity，不能解读为结构恢复失败。E 直接获得方程，不能充当同输入边界下的自动发现器。

## 实际证明成本

下表为 n=640、10 seeds 的 D 中位数。总时间包含发现、GF(2) 推导及两层检查，不含输入构造、证书编码/压缩写盘和诊断。

| planted_depth | 输入子句 | checked_resolution_steps | discovery + GF(2) + check | certificate/input 字节比 |
|---:|---:|---:|---:|---:|
| 0 | 20,480 | 0 | 0.137 秒 | 0.24 |
| 1 | 40,960 | 20,480 | 0.502 秒 | 1.11 |
| 2 | 81,920 | 61,440 | 1.387 秒 | 1.42 |
| 3 | 163,840 | 143,360 | 2.988 秒 | 1.49 |

本构造实际恢复步数为 32n(2^d−1)，但这不是最短证明步数或深度结论。所有提交证书的 proof sharing ratio 都为 1×：这些独立 splitting 树没有产生跨 parity 的证明共享。GF(2) 反驳仍为 n−1 次合并，它来自当前图族的特定代数结构。

## Checker 与控制

桥接阶段只接受 k≤8 的完整 canonical parity CNF block。每条 canonical clause 必须引用已检查的输入/resolution 结点；不调用 SAT solver，不判断一般 CNF 蕴含 XOR。GF(2) 阶段使用集合对称差独立重放，只以 0=1 接受 UNSAT。

160 个 SAT 输入均有逐子句检查过的完整满足赋值，D 未产生被接受的反驳；D 在 SAT 输入上返回 MISS，不表示求解 SAT。将每条恢复关系的 RHS 翻转，并用满足赋值确认候选确实错误后，48,000 个候选全部被相同注册检查器拒绝。44 项单元/回归测试通过，另有 20 个随机重命名、极性变换与打乱子句的隐藏实例检查通过。

独立重放结果在 [审计 JSON](results/round3_audit.json)：重建输入、核对源代码与输入/证书 SHA256、检查隐藏输入中模板确实缺失、重放全部 D 证书、复核 SAT 赋值和错误 RHS 候选。原生 solver 的 UNSAT 为其自身输出，不冒称通过 D 的证明审计。

## 研究判断

这轮完成了可用的正对照：**CNF → checked resolution → canonical parity → checked GF(2) → contradiction**。但当前 blind discovery 本身就是受限的互补子句对消元，预处理基线也成功恢复了所有关系。没有证据支持 history 的作用、超越普通预处理、发现一般隐藏代数结构，或任何 P/NP 结论。

下一道有区分力的实验需要破坏这种独立、低 occurrence 的拆分树结构，同时保留投影语义保证；然后再比较固定预算的 blind、普通预处理与历史候选。当前结果不应被包装为这一步已经成功。

## 数据与复现

- [完整分组报告](results/round3_report.md)
- [Raw CSV](results/round3_raw.csv)、[Raw JSONL](results/round3_raw.jsonl)、[Summary CSV](results/round3_summary.csv)
- [协议与字段口径](docs/round3-protocol.md)、[源代码/依赖版本](results/round3_metadata.json)
- [检查器与发现器](derived_parity.py)、[实验脚本](round3_experiment.py)、[独立审计](audit_round3.py)

每份压缩证书的路径与未压缩内容哈希在 raw 数据中。复现命令见协议。
