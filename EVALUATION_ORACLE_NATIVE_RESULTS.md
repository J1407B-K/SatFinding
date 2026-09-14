# 昂贵 evaluation oracle + 可完成的 CDCL：有条件性收益，未证明最优映射

**这次 BLIND 完成了，搜索映射也真正做了。找到的映射在两个固定输入上减少了原生
CDCL 的实际工作，双方最终反驳均通过纯 Resolution checker。**

但它不是全局最优映射证书，不是最优局部 repair 实验，也没有显示在线 SAT 净加速。
不据此启动 automatic retrieval/mapping；也不能把此前 identity pilot 的 MISS 当作
历史 proof 没有价值的证据。

## 实验边界

继续使用已经保存的独立 6-regular 图，不修改 CNF、不植入 proof、不重采样。
两对为 H6200→T6201（120 顶点）和 H6202→T6203（200 顶点）。前者只是毫秒级工程
控制，后者也只有有限难度；这不是工业 hard-family 的确认性实验。

BLIND 与 history completion 都使用同一份原生 Glucose 3.0：原始默认启发式、学习、
重启与 minimization 保持不变，统一 1,000,000 conflicts 和 30 秒进程上限。
这个 backend 保留成熟 CDCL 搜索，不再用此前的 Python 全归结枚举器充当主 baseline。
Glucose 3.0 不是最新 state-of-the-art，因此额外保留 CaDiCaL 和 preprocessing 对照。

插桩计数与旧的“候选父对子句/pivot attempts”不同，不做数值串接或改名冒充：

- `analysis_resolution_steps`：first-UIP conflict analysis 中初始 conflict 之后的 reason antecedent 访问，即该阶段的归结操作。
- `minimization_reason_visits`：学习子句最小化中的 reason 访问，包括未带来删除的尝试。
- `binary_minimization_candidates`：binary minimization 检查的候选。
- conflicts、decisions、propagations 与实际时间各自记录。

这些没有覆盖所有隐式 root-level unit resolution，也不是算法无关的 proof-search
复杂度。它们直接来自 solver 搜索，**没有用 DRUP 转换步数或最终 proof 长度替代**。
开启/关闭计数的两套 binary 产生完全相同的 DRUP 哈希与 conflicts/decisions/
propagations；选中候选的独立重跑也重现全部计数与 DRUP 哈希。

## Oracle 到底做了什么

每对分配 90 秒，固定随机种子 730001，通过多起点 annealing 搜索顶点置换。
第一目标为“历史原有父边全部成立的 directly replayable inference 数”，匹配 leaves
仅用于打破平分。不根据同编号假定跨图语义。

| 顶点数 | score evaluation 次数（可重复） | 保留映射 | 后续 completion |
|---:|---:|---:|---:|
| 120 | 5,031,219 | 12 个不同置换 | 12 × 6 个全局颜色置换 |
| 200 | 293,667 | 12 个不同置换 | 12 × 6 个全局颜色置换 |

每对另测 identity 的六个颜色置换，明确标成 arbitrary control。共 156 个 candidate
completion runs。Oracle 可以查看 T 并花费真实 completion 工作来挑选最有利候选；
这些都是 evaluation-only 开销，不作为自动算法成果，也不是 held-out 预测。

第二阶段从保留集合中选择完成后 `analysis_resolution_steps` 最低的候选。最大 replay
不保证最低 completion cost：120 顶点时最大 replay 为 1,345，成本赢家 replay 为 1,335。
没有对所有评分过的映射都跑 completion，更没有枚举全部 n! 映射。

**全局最优性：未证明。**只报告 best-found。已观察到的收益是最大可能收益的一个下界，
不能拿它当成“至多只能省这么多”的上界，更不能据此排除尚未搜索到的更好映射。

History route 先重放有效旧步骤，检查 resulting Resolution module，然后将这些已证
clauses 追加在完全相同的原始 T clause prefix 之后，让同一 CDCL 完成整个反驳。
失效前提不作为公理；**本轮没有实现最优局部 gap repair**。剩余工作称 whole-target
completion。不能将该策略失败解释为所有 repair 策略失败。

## 完成同一目标后的真实搜索工作

| 目标 | BLIND analysis steps | best-found history | 减少 | BLIND / history conflicts | 根 CNF checker |
|---|---:|---:|---:|---:|---|
| n120 | 15,777 | 10,952 | 30.6% | 480 / 370 | 双方 PASS |
| n200 | 232,724 | 133,584 | 42.6% | 6,239 / 4,176 | 双方 PASS |

200 顶点上其他计数也减少：minimization reason visits 为 257,121→137,129；binary
minimization candidates 为 22,043→11,292；decisions 为 7,382→4,908；propagations
为 483,748→318,800。

| 目标 | 历史 inference nodes | arbitrary identity replay | best-found replay | unique replay outputs |
|---|---:|---:|---:|---:|
| n120 | 19,560 | 34 | 1,335 | 1,134 |
| n200 | 251,420 | 104 | 4,556 | 2,757 |

replay 数量是历史 DAG 节点数，可能含不同旧节点得出相同 clause；unique outputs 单列。
这与此前 pilot 将 alias 单独分类的直接重放计数不同。主要搜索计数没有因此重复计费。

不能隐藏 arbitrary control：其六个颜色置换中最好的 completion analysis steps 为
11,926 / 146,993。因此昂贵 oracle 相对“最佳已测 identity”只额外减少 **8.2% / 9.1%**。
42.6% 是相对零历史 BLIND，不全是优化 mapping 本身的贡献。

## 强 baseline 与时间：尚无在线净加速

| 路线 / 时间组成 | n120 | n200 |
|---|---:|---:|
| 原生 BLIND solve | 3.20 ms | 85.77 ms |
| best-found completion solve | 3.13 ms | 61.18 ms |
| best-found replay + module check | 10.31 ms | 62.23 ms |
| CaDiCaL 从零 solve | 5.57 ms | 42.64 ms |
| CaDiCaL preprocessing + 同一原生 backend | 7.71 ms | 73.02 ms |

即使 oracle mapping 免费，n200 的 replay/check + completion 约 **123.4 ms**，仍高于
BLIND 的 85.8 ms，也高于 CaDiCaL。从零 preprocessing 后，同一 backend 的 analysis
steps 为 161,269；history 的 133,584 仍较少，但 preprocessing 后 propagations 为
296,462，反而少于 history 的 318,800。没有任何路线在全部成本维度上统治其他路线。
在 n120 控制上，preprocessing 后 analysis steps 为 9,217，已低于 history 的 10,952。

上述是单次运行的分阶段时间，不给毫秒级统计加速结论。证明转换另计：n200 BLIND
和 history 的 Python DRUP→Resolution 转换分别约 14.36 / 8.60 秒；不能把这种
adapter 主导的耗时当成现代 solver 的 proof-search 时间。完整证书生产、编码、检查
的所有阶段也没有被合并成一个已充分验证的端到端性能主张。

CaDiCaL/preprocessed reference 的 UNSAT 是原生 solver 输出；preprocessed proof 的
根公式不是原 T，未冒称经过本项目 root checker。两条主路线的四份最终反驳则通过
拼接 replay 与 completion 的显式 Resolution，全部追溯到原始 T 并完成独立重放。

## 320 顶点的工具检查与剩余限制

原生 drat-trim 对保存的 n320 历史 DRUP 在约 7.1 秒内完成验证并导出 LRAT，报告
0 RAT lemmas。这说明有可用的原生证明工具链，但**该任务不等同于展开并保存全部
Python Step 对象**，不能将 7.1 秒直接宣称为原 adapter 的等价替代耗时。
记录中的原生 Glucose 计数开关对照也能在约 3.16 秒完成该历史 CNF，并产生相同 DRUP。
更难 n320 配对仍未加入本次 checked transfer 主表。

当前最强结论是：在两个既定输入、指定 native CDCL 与已测试映射集合内，存在通过
checker 的历史 transfer，能减少真实搜索操作。它没有展示 50× 的空间，没有得到最佳
mapping/repair 的上界，也没有排除廉价 preprocessing 或启发式顺序效应对收益的解释。
**保留这个有限正结果；不启动自动 mapping 工程，不作项目级 YES/NO。**

## 可审计材料

- [固定协议](docs/evaluation-oracle-native.md)
- [完整结果与 156 次候选记录](results/evaluation_oracle_native/results.json)
- [独立审计：四个 root refutations PASS](results/evaluation_oracle_native/audit.json)
- [强基线参考](results/evaluation_oracle_native/modern_references.json)
- [选中候选的计数/DRUP 重现](results/evaluation_oracle_native/selected_reexecution.json)
- [native 插桩 builder](build_native_cdcl.py)、[oracle optimizer](evaluation_oracle.cpp)

逻辑 checker 仍复用已有实现。Native work counters 的审计依靠源代码、binary 哈希、
计数关闭对照及重执行；不声称单凭 proof replay 可以独立认证 CDCL 内部计数。

构建需要 `python-sat 1.9.dev15` 官方 sdist 中的 `solvers/glucose30.tar.gz`。来源：
[PyPI 固定版本](https://pypi.org/project/python-sat/1.9.dev15/)、
[drat-trim 官方仓库](https://github.com/marijnheule/drat-trim)。原始 Glucose 许可证保留在 archive 内。

```sh
.venv/bin/python build_native_cdcl.py --archive /path/to/glucose30.tar.gz
c++ -O3 -std=c++11 evaluation_oracle.cpp -o /private/tmp/satfinding-evaluation-oracle
.venv/bin/python -m unittest test_evaluation_oracle -q
.venv/bin/python evaluation_oracle_run.py
.venv/bin/python evaluation_oracle_references.py
.venv/bin/python audit_evaluation_oracle.py
```

Oracle 使用 wall-clock cap，因此评价次数及 best-found mapping 可能随机器负载改变；
保存的输入、映射、计数与证书可以逐项审计，不声称 oracle 搜索输出跨机器完全确定。
