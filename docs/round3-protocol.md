# Round 3：可携带证明的 parity 恢复

## 固定范围

无历史、无 learned retriever。简单连通 6-regular Tseitin 图，n=80/160/320/640，每组 seeds=10..19（预检 seed=100 不进入正式统计），planted_depth=0/1/2/3。每个配置包含 UNSAT 和有已知满足赋值的 SAT 对照，共 320 个输入、1600 路实验。

6 元 parity 的 canonical CNF 含 32 个子句。每层将每条 C 替换为 C∨z 和 C∨¬z，每个内部树结点使用独立 fresh z。构造器另行检查 split witness：父句存在、z 此前未出现、两个孩子恰好为指定子句、最终叶子多重集等于输出。随后对全部变量（包括辅助变量）做随机双射与极性变换，并打乱子句；blind discovery 与 A/B/C 均不接收原变量边界、split witness、XOR scopes 或 planted assignment。

变量数为 3n+32n(2^d−1)，子句数为 32n·2^d。输入大小按实际 DIMACS 字节计。planted_depth 只描述构造路径，不是 minimum proof depth，也不称 abstraction distance。

## 两层证书和检查器

`derived_parity.py` 的证书包含共享 Resolution DAG、DerivedParity 列表和 GF(2) DAG。输入子句占据初始索引，每个 resolution 结点只能引用之前的两个结点，显式给出正 pivot 与精确 resolvent。检查器验证父句包含相反 pivot、其余文字的并集等于输出，拒绝错误索引、错误 pivot 和错误 resolvent。

每个 DerivedParity 包含排序且互异的正变量列表、rhs∈{0,1} 和 canonical 子句的索引。宽度限制为 1≤k≤8。检查器枚举与 rhs 相反的 2^(k−1) 个赋值，形成完整 canonical block，并逐条验证引用结点**恰好等于**该 canonical 子句。

这里没有一般的 CNF ⊨ XOR 判断，没有 SAT 调用，也不尝试隐式 subsumption 或补推导。只在全部 canonical 子句已明确证明后登记方程。之后独立使用变量集合对称差重放 GF(2) 步骤，仅以 0=1 接受 UNSAT。空的 GF(2) conclusion 可表示有效的部分证书，不表示 SAT。

可靠性论证：input CNF 的每个模型满足所有被检查的 resolution 后果；完整 canonical block 恰好排除错误 parity 赋值，因此每个登记方程对这些模型成立；GF(2) 相加保持蕴含；0=1 不存在模型。此论证以输入解释与检查器实现正确为前提，测试不等于形式化实现证明。

## Blind discovery 与预算

建立当前子句的变量 occurrence index。候选变量必须恰有两个 active occurrences；两个父句必须除 pivot 极性外完全相同。成功后记录一个 resolution 结点，在 active 集中用 resolvent 替换父句，再更新 occurrence index。队列按确定性变量/子句顺序处理，不读取 fresh-variable 标签。

搜索预算固定为最多 200,000 个成功 resolution 步骤及 2,000,000 次 resolution 候选尝试。随后对所有输入和已证明子句按 scope 分组，为 k≤8 的每个 scope 尝试两个 RHS。没有达到 canonical block 必要子句数的 scope 可直接拒绝，无需指数枚举。GF(2) 消元保留全部引用步骤。

这是一种受限的互补子句对消元，也属于预处理范畴；没有声称通用 bounded resolution search、证明长度最优或自动发现新运算。

## 五路对照与计时

| 路线 | 输入和实现 |
|---|---|
| A | 同一份 CNF → Glucose3 |
| B | 同一份 CNF → CryptoMiniSat 5.14.7，threads=1，默认 CNF/XOR 识别和 Gaussian 配置 |
| C | 同一份 CNF → CaDiCaL（PySAT Processor，默认技术、3 rounds、不冻结变量）→ 同一 CryptoMiniSat |
| D | 同一份 CNF → blind discovery → Resolution / canonical parity / GF(2) checker |
| E | 原始 XOR equations → GF(2)，使用原始未拆分 CNF 检查，属于特权 oracle |

CryptoMiniSat 正对照日志已确认会调用 occ-xor 和 Gaussian matrix initialization。其默认调度可能先进行 CDCL 搜索再发现 XOR；预算内 UNKNOWN 不意味着“不支持 XOR”。B/C 从不调用 add_xor_clause，也不接收提取器输出。

A/B/C 每次 solver call 预算为 2 秒（各后端时间控制语义有差异），外层 worker watchdog 为 12 秒。加载和 C 的预处理时间另计；worker wall time 也保存。C 为评价额外扫描预处理后的显式 parity，扫描结果不传给求解器；这个诊断的成本包含在 C total_time 中。C 恢复率由 harness 将扫描结果与隐藏真值比较得到。B 的内部恢复率不可访问，记为不可用。

D 使用步骤预算而非相同 wall budget，最大输入可超过 2 秒。不能把这一设置当作同预算速度胜负。每例单次计时，各路线顺序按 seed/depth 确定性打乱，路线之间不并行。UNKNOWN/TIMEOUT 是截尾观察，不当作完整求解耗时。

D total_time = discovery_time + GF2_time + resolution_check_time + parity_registration_time + GF2_check_time。构造/导入、证书 JSON 编码与 gzip 写盘、sharing 诊断、错误候选对照不计入该总计；保存完整分项。证书字节为未压缩 compact JSON，不使用压缩后字节美化结果。E 省略从拆分 CNF 恢复关系的成本，不能冒充同样可信输入边界下的 checker 时间。

GF(2) producer 使用按输入变量编号定位的整数 bitset；全体变量重命名后，原变量编号之间可夹有辅助变量编号，因此 bitset 的存储跨度也会随输入膨胀。这是本实现的表示成本，不应解释成代数消元所需维度或渐近复杂度下界。

## 指标约定

记录 recovered_parities / total_parities；candidate_attempts/accepts/rejects 指 parity scope/RHS 的句法匹配尝试，未满 canonical block 是拒绝注册候选，不宣称该关系语义为假。resolution_candidate_attempts/misses 单列。达到搜索预算是 MISS，不是 FALSE。

Resolution DAG nodes 包含输入叶子与所有提交的派生结点，edges=2×派生步骤数。checked_resolution_steps 是实际被检查的步骤数。GF2 DAG nodes 包含登记方程与行相加步骤。证书还包含每条 parity 的 canonical clause 引用，但这部分不计为 Resolution DAG edges。

proof sharing ratio = 各 parity 的祖先结点集合大小之和 / 这些集合的并集大小，包含输入叶子。它描述提交证书，不描述最优独立证明。此构造各 clause tree 互不共享，预期为 1；实验按实际 DAG 计算。

派生指标包括 certificate_bytes/input_bytes、discovery_time/input_clauses、checked_steps/recovered_parity 和 candidate_attempts/accepted_parity。完整记录在 raw JSONL/CSV 与 summary CSV。

## SAT 与负候选

每个 SAT 输入都由完整 planted assignment 检查。D 不可给出被接受的反驳。对于每条恢复出的真实 parity，翻转 RHS 并保留 canonical clause 引用；先用满足赋值确认该候选确实错误，再调用相同注册检查器，必须拒绝。该控制检查发生在计时外，计数单列。

A/B/C 的 SAT model 逐条检查当前输入子句，C 先 restore 消元变量。原生 solver 的 UNSAT 只记录其输出，不宣称通过 D 的独立证明审计。D 的每份证书 gzip 保存并经 `audit_round3.py` 重建输入、核对 SHA256、重放两层 checker 和错误 RHS 控制。

## 复现

```sh
.venv/bin/python -m pip install -r requirements-round3.txt
.venv/bin/python -m unittest discover -v
.venv/bin/python round3_experiment.py > results/round3.log
.venv/bin/python round3_report.py
.venv/bin/python audit_round3.py
```

参考：[PySAT Processor](https://pysathq.github.io/docs/html/api/process.html)、[CryptoMiniSat](https://github.com/msoos/cryptominisat)。
