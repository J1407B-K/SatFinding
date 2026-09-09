# Proof-carrying semantic cache for SAT

研究原型：用结构特征检索历史 residual，尝试迁移证书，通过确定性检查后复用。
核心运行要求：Python 3.10+，无第三方依赖。真实基准额外使用 PySAT / pynauty；
第二轮结构匹配使用 igraph 和 Linux fork 子进程。

```sh
python3 demo.py
python3 demo_module.py
python3 -m unittest test_satcache test_adversarial -v
```

## 当前实现

- CNF：非零有符号整数表示文字，子句和公式规范化去重。
- 检索：子句宽度与变量出现次数直方图的稀疏向量，余弦相似度排序。
  这是结构 embedding 基线，不是神经模型；可替换 `embedding` 和排序模块。
- 迁移：预算内枚举单射变量映射和极性翻转。目前匹配算法只适合小实例。
- SAT：迁移完整赋值，逐个检查当前 residual 的全部子句。
- UNSAT：迁移历史前提及二元 resolution 反驳，检查前提属于当前 residual，
  验证每个推导步骤并确认空子句出现。当前以完整历史公式作前提，尚不提取最小 core。
- JSON 历史库：`Cache.save(path)` / `Cache.load(path)`；加载时重新验证证书。
- 基础求解器：预算内穷举赋值，若全部失败则尝试生成 resolution 反驳。
  超预算返回 UNKNOWN，不是面向生产的大规模 SAT solver。

## 证书与接受规则

SAT 证书为变量到布尔值的映射。UNSAT 证书包含有序 premises 和 steps。
每个 step 为 `(left, right, pivot, clause)`；索引指向 premises 与之前推导结果
组成的序列，两个父子句必须分别包含 pivot 和它的否定，输出必须恰好是对应 resolvent。
没有空子句的 fragment 不能返回 UNSAT。泛化 proof motif 与独立 fragment 复用尚未实现。

`check(current_residual, certificate)` 是接受边界：检索分数和历史状态不构成证据。
假设当前 CNF 表示正确、检查器实现正确，检查接受 SAT 意味着存在满足赋值；接受 UNSAT
意味着当前公式包含前提，且有效 resolution 推导出矛盾。此处是设计论证，非机器验证证明。

`run(F, cache, assumptions)` 的返回状态作用于 `F|assumptions`，输出始终携带 assumptions。
分支 UNSAT 不代表 F 全局 UNSAT；当前没有跨分支 learned clause 导出功能。
SAT 会重建并检查原公式上的赋值。调用者必须保留 UNSAT 的假设上下文。

## 限制与下一步

检索候选数量和每个候选的映射数量有界，但尚无针对恶意大文件/证明的内存与时间隔离。
完整性依赖基础求解流程与资源预算；缓存不保证命中、加速或多项式复杂度。

已增加 Glucose3 和官方 SATLIB RTI/BMS 的真实基准，以及 exact / 图 canonical / 两种
semantic 检索对照。这里使用官方关联实例，不声称独立来源泛化；没有训练神经模型。
UNSAT 大实例证明格式、真实求解器 residual 轨迹和学习式匹配仍是后续工作。

## 证明与实验

- [ProofModule 接口与 soundness](docs/proof-modules.md)：扩展定义、fresh variable 分配、带作用域的结论和模块组合。
- [第二轮研究结论](ROUND2_RESULTS.md)：独立重命名、结构匹配、非父子 motif 和四种检索基线。
- [第一轮研究结论](RESEARCH_RESULTS.md)：四项目标的证据、数值和适用范围。
- [Soundness 证明](docs/soundness.md)：明确可信边界、归结归纳证明和分支作用域。
- [复用能力与复杂度定理](docs/complexity.md)：严格超出同构的合法复用；限定 DPLL 的指数到多项式改进。
- [首次全量实验](results/satlib.md)：保留包含建库成本后没有净加速的初版结果。
- [优化后全量实验](results/satlib-optimized.md)：完整 500 对、5 轮、所有计时与来源可审计。
- `results/theory.json`：特定 DPLL 递推的有限验证。

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-round2.txt
.venv/bin/python -m unittest -v
curl -fL https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/BMS/RTI_k3_n100_m429.tar.gz -o /tmp/satcache-rti.tar.gz
curl -fL https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/BMS/BMS_k3_n100_m429.tar.gz -o /tmp/satcache-bms.tar.gz
.venv/bin/python benchmark.py --rti /tmp/satcache-rti.tar.gz --bms /tmp/satcache-bms.tar.gz --repeats 5 --output results/satlib-optimized.json
.venv/bin/python audit_benchmark.py --results results/satlib-optimized.json --rti /tmp/satcache-rti.tar.gz --bms /tmp/satcache-bms.tar.gz
.venv/bin/python native_reference.py --rti /tmp/satcache-rti.tar.gz --bms /tmp/satcache-bms.tar.gz
.venv/bin/python theory_experiment.py
```

`benchmark.py --no-prefilter ...` 可复跑未加快速筛除的算法版本。
输入存档只读取、不解压；结果 JSON 保存来源 URL、SHA-256、每实例耗时、软件版本和代码哈希。
官方数据背景：[SATLIB RTI/BMS](https://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/BMS/descr_BMS.html)。
底层接口来源：[PySAT](https://pysathq.github.io/docs/api/solvers.html)、
[pynauty](https://github.com/pdobsan/pynauty)。

## 第二轮复现

使用同一组已下载的 RTI/BMS 存档。下面的匹配实验会启动短时原生搜索子进程，耗时数分钟。

```sh
.venv/bin/python round2_permutation.py
.venv/bin/python round2_match_eval.py --queries 100
.venv/bin/python round2_feature_baselines.py
.venv/bin/python round2_motif.py
.venv/bin/python audit_round2.py
.venv/bin/python round2_report.py
```

[协议](docs/round2-protocol.md)说明了隐藏映射隔离、top-k/时间预算、抽样方式、负例和结果边界。
现阶段结构匹配未取得净加速，困难混合 motif 也未明显胜过随机；这些负结果保留在报告中。
