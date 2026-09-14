# Gold-64 proof anatomy

结论：本例支持“多数具有独立廉价推导的 clause，组合后改变搜索”，
**不支持“64 条背后只是少量共享 proof modules”**。
语义独立性没有得到证明，也没有建立 semantic abstraction memory。

本轮先完成 [PRIOR_ART_GATE.md](PRIOR_ART_GATE.md)，读取本地 IPR 论文和实现，
再新增一个实验驱动；所有 traversal、checker、SAT solving 和图连通分量复用现成实现。
源重要性、稀疏 lemma、局部着色规则、模块分组都不作为新贡献。

## Frozen experiment

沿用 n200_T_r01_s7201、历史 G6202、67 个 TEMPLATE 和原 Oracle exact-64。
历史输出排除 TEMPLATE exact duplicates、subsumed clauses 和 encoding-only 推导，
保持原 CNF / TEMPLATE / 源 ID 注入顺序。153 个不同配置，各 3 次，共 459 次；
按固定随机种子打乱执行顺序，单进程依次启动原 native Glucose backend。
所有 search counters 重复一致，Gold 与上一轮完全一致。

下表是**本轮**中位数，包含选中 support 的 replay/check、输入输出和 native process，
不含离线 oracle、加载/索引和全 completion proof 转换。历史支持先独立从当前 CNF
重证，再注入输出；不把未验证历史 clause 当公理。时间随机器负载浮动，完整范围见 CSV。

| Route | Search ops | Conflicts | Replay/check ms | Total ms |
|---|---:|---:|---:|---:|
| BLIND | 289,664 | 7,872 | 0.00 | 123.21 |
| TEMPLATE | 203,623 | 5,325 | 4.15 | 81.10 |
| GOLD64 | 130,718 | 3,584 | 9.09 | 56.34 |
| RANKED64 | 209,416 | 5,672 | 9.16 | 93.90 |
| SHORTEST64 | 266,446 | 7,340 | 8.90 | 130.21 |
| USED64 | 255,758 | 6,931 | 9.36 | 120.61 |
| RANDOM64_17 | 259,270 | 6,981 | 19.36 | 135.20 |
| RANDOM64_29 | 222,492 | 5,906 | 21.44 | 110.09 |
| RANDOM64_43 | 339,321 | 9,354 | 24.68 | 177.78 |

## DAG 与 source-importance baseline

64 个根的独立 inference 数总和 291，联合 265，共享节省 26 步（8.93%）。
265 个节点中 243 仅服务一个根，18 服务两个，4 服务三个；没有 Gold 根是另一个
Gold 根的 ancestor。共享推导图有 61 个 component：3、2，以及 59 个单根。
这不是少量大模块。相比之下，RANKED64 有 40 个 component，USED64 有 32 个，
它们更共享，但本例目标搜索更差。SHORTEST64 使用现有 width / use-count 排序；
USED64 使用重建 DAG 的直接使用次数，均非真实 LBD 或 activity。

共同 premise 图有 32 组（最大 25），仅 encoding premise 有 33 组（最大 22），
仅 edge premise 有 47 组（最大 11）。输出变量图有 24 组，support 变量图有 12 组。
这些宽松连通关系不能自动叫 proof module：同一个顶点编码可以把不同局部推论串起来。
阈值 0.1 / 0.25 / 0.5 下的完整敏感性分析已导出；inference 图分别为 61 / 62 / 63 组。

**表示限制：**这里是 DRUP 重建出的 Resolution DAG，而非真实 CDCL derivation DAG。
该区别已有 [CP 2020](https://jakobnordstrom.se/docs/publications/UsingProofs_CP.pdf) 明确讨论。
结论只针对当前证书表示；不能由支持不相交推出语义互不相关。

## Module-level ablation

| Group | IDs | TEMPLATE + group ops | Gold minus group ops |
|---|---|---:|---:|
| 0 | [54322, 66621, 150191] | 195,398 | 269,475 |
| 1 | [50651, 245106] | 281,177 | 258,035 |

两个共享组单独使用都不能重现 Gold 的收益，第二组甚至比 TEMPLATE 更差。
但删除任一组都会严重破坏 Gold 的搜索表现。61 组中，删除 60 组增加 ops，
1 组不变；删除 penalty 中位数 61,201，
最大 179,990。
单组加入 TEMPLATE，只有 11 / 61 组减少 ops。
这是同一启发式轨迹下的条件边际效应，不能把 penalty 相加分配成各组的“贡献比例”。

三组固定种子的同尺寸随机 partition 作为控制；单根集合重复时复用完全相同配置，
保留 aliases。随机 3-clause 组的删除 penalty 也可超过真实共享组，故大 penalty
不是共享结构特有的信号。完整 ONLY / DROP 和控制组数据见 selections、summary、partitions。
这些不是新的 oracle 搜索，也没有因为看到 ablation 结果而调整分组阈值。

## Semantic analysis

局部 premise **64/64 都 SAT**；加上结论取反后 **64/64 UNSAT**，
均用已有 PySAT solver 验证。55/64 可直接由局部 premise 单位传播完成 RUP 检查；
其余仍有已检查的 Resolution 支持。没有用全局 UNSAT 的 target 做空洞 implication 验证。

31 条是一条边加一个顶点 ALO 的一步推论：

`(v0 ∨ v1 ∨ v2) ∧ (¬u1 ∨ ¬v1) ⇒ (¬u1 ∨ v0 ∨ v2)`。

另外 13 条是两条边加一个 ALO 的两步推论：

`(v0 ∨ v1 ∨ v2) ∧ (¬u0 ∨ ¬v0) ∧ (¬w1 ∨ ¬v1) ⇒ (¬u0 ∨ ¬w1 ∨ v2)`。

这 44 条是标准着色传播关系在具体顶点上的实例化。已逐条检查前提形状、颜色一致、
消去变量和最终 clause，而非只凭长度猜测；标注表保留每条 ID。剩余 20 条只描述为
更长的局部着色推论，不强行命名为新 abstraction。局部 support 覆盖 2–10 个顶点。
这类编码/传播研究已有 [Arc Consistency in SAT](https://frontiersinai.com/ecai/ecai2002/p0121.html)。

**TEMPLATE 防火墙仍不充分：**排除那 67 条具体 clause 不等于排除全部通用知识。
这 44 条包含图的特定边，因此不是 encoding-only，却仍是通用关系的 grounded instance。
Oracle 可能在挑适合当前搜索轨迹的实例化位置；本轮没有证明这些信息必须从历史学习。
两个规则描述能概括 44 条，不意味着把 44 个 grounded outputs 替换为两条“抽象”后
还保留收益。没有运行这种替换，也没有证明跨图/跨 encoding transfer。

## What this answers

暂时选择 A 的谨慎版本：大多数 clause 的证书支持独立且便宜，目标收益非加性。
没有证据进入“少量共享模块”的 B 结论；C 只有既有通用语义的描述，没有 abstraction
压缩或迁移实证。单 target 的同目标 oracle 选择偏差仍在，不能推广到其他实例。

若后续继续，研究设计首先需要控制这些廉价通用规则的具体实例化位置，并测试
未参与选择的 target；该实验要再次过 literature challenge。当前不新增 detector、
模块 selector 或 abstraction 算法，也不继续全量 DRUP→Resolution 工程。

## Artifacts and validation

- [Driver](gold64_anatomy.py), [plot](results/gold64_anatomy/anatomy.png), [PDF](results/gold64_anatomy/anatomy.pdf)
- [Audit](results/gold64_anatomy/audit.json), [Metadata / hashes](results/gold64_anatomy/metadata.json), [raw runs](results/gold64_anatomy/raw.jsonl), [summary](results/gold64_anatomy/summary.csv)
- [Per-root proof IDs and local premises](results/gold64_anatomy/roots.json), [overlaps](results/gold64_anatomy/pairwise_overlap.csv), [threshold sensitivity](results/gold64_anatomy/sensitivity.json)
- [Module ablation](results/gold64_anatomy/module_ablation.csv), [semantic annotations](results/gold64_anatomy/semantic_annotations.csv)

所有 replay 均通过已有 checker；completion 为 native solver 报告 UNSAT。
本轮未重新把 459 份 completion 展成纯 Resolution；原 Gold-64 的完整证书审计
沿用上一轮，原始 DRUP 保留供复查。相关现有 14 个单元测试通过。

Reproduce: `MPLCONFIGDIR=/private/tmp/satfinding-mplconfig PYTHONPATH=/private/tmp/satfinding-plotdeps .venv/bin/python gold64_anatomy.py`。
同一环境下加 `--report-only` 只重建报告和图。测量程序版本哈希记录于 metadata，
最终含报告代码版本另记于 report_manifest，不覆盖测量时的 provenance。
