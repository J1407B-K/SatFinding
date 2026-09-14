# 跨区域抽象：首个可核验基线

本轮问题：同一组高连接性的图上，局部 extension 没能明显降低消元宽度时，直接使用跨区域关系能否得到短的、可验证的矛盾证明？

## 输入与隔离

简单连通 6-regular 图，n=80/160/320/640，每组 seeds=0..9。边变量共 3n 个。先随机生成边赋值，从赋值计算每个顶点的 parity charge，得到有已知满足赋值的 SAT 对照；翻转一个顶点的 charge 得到 UNSAT 实例。每个 6 元 parity 直接编码为 32 个子句。变量编号随机置换，子句顺序打乱。

Oracle 获得局部 parity 方程，按顶点顺序全部相加。自动算法只获得 CNF：按变量 scope 分组，检查一个 parity 的全部禁止赋值是否都有对应 blocking clause，然后用 GF(2) 消元合并方程。候选 scope 上限为 8；算法只承诺识别显式、完整的小 parity 块。变量重命名和子句打乱没有隐藏这种编码特征。

## 证书与可信边界

每份 JSON 证书包含局部方程、引用已有结点的二元 XOR 步骤，以及结论结点。独立检查器从当前 CNF 检查每条局部方程的全部必要子句，再以集合对称差重放每一步，只接受最终的 0=1。不能把缺失子句、前向引用或负数索引当作合法证明。

这是一个单独的代数证明系统。没有把空子句未经证明塞进现有 ProofContext，也没有将该证书当作已生成的 resolution 或 extended-resolution 证书。XOR 消元规则是预先编程的；本轮不是从历史学习到了一种新运算。

## 成本和对照

Baseline 为 Glucose3，每实例 solver call 时间预算 2 秒，无冲突数上限；记录加载和运行总时间、状态及 conflicts/decisions/propagations。接口依据 [PySAT 文档](https://pysathq.github.io/docs/api/solvers.html)。UNKNOWN 是截尾观察，不是求解用时，也不能拿它计算精确加速倍数。

自动路线计入 CNF 分组、parity 识别、消元和证书检查；oracle 计入合并和同样的检查。图/CNF 生成、imports、诊断统计与写盘不计入任一路线。每例只计时一次，因此不做精细运行时间显著性推断。SAT 对照有完整赋值检查，并要求自动路线不能给出被接受的反驳。

保留 `global_xor_raw.csv`、代码哈希/版本 metadata 和 80 份证明 JSON。复跑：

```sh
.venv/bin/python -m pip install -r requirements-bench.txt networkx==3.2.1
.venv/bin/python -m unittest test_global_xor -v
.venv/bin/python global_xor_experiment.py
.venv/bin/python audit_global_xor.py
```

## 这一步之后真正要测什么

这是已知 parity 结构的正对照，不是一般 SAT 的结构发现突破。下一阶段应先固定当前算法，在未使用的 seeds 上加入 XOR-chain 编码、冗余/混合子句、局部编码变化，测量识别率及总成本。只有在现成识别器失效的输入上，历史驱动方法仍能稳定恢复并验证有用抽象，才有证据表明 history-discovered 带来了新增能力。

后续历史路线需要获取实际 CDCL 轨迹，按冲突共同涉及的变量/约束提出跨区域候选；比较无历史、随机候选、历史候选和 oracle，并把收集历史的搜索成本计入。当前 DAG 是代数消元历史，不应冒称为这一阶段的结果。
