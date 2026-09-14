# 找到了小型历史搜索加速集合：TEMPLATE + 64 条，130,718 ops / 57.3 ms

在冻结的 n=200、1% drift 实例上，先固定原有 67 条 TEMPLATE，再做昂贵的历史
lemma selection。**额外 64 条历史 lemma 同时降低了搜索量和包含 replay/check 的总时间。**
本轮没有优化 replay、proof 转换、mapping 或在线 selector。

[曲线 PNG](results/oracle_lemma/curve.png) · [PDF](results/oracle_lemma/curve.pdf) ·
[完整表格](results/oracle_lemma/report.md) · [黄金 clause 实体](results/oracle_lemma/gold_lemmas.json) ·
[选择 ID](results/oracle_lemma/selections.json) · [原始逐次测量](results/oracle_lemma/final_raw.jsonl) ·
[8,192 个单 lemma 边际收益标签](results/oracle_lemma/singleton_marginals.csv)

## 主要结果

下面全部来自本轮复测。固定 identity vertex/color mapping，固定 clause 注入顺序，
每个冻结集合用全新 native Glucose 运行 5 次；时间取中位数。所有带历史的条件路线
都先加入**同一份 67 条 TEMPLATE**；表中的 K 只计算额外历史输出。

| 路线 | 额外历史 lemma | Replay/check ms | Completion search ops | Conflicts | 总时间 ms |
|---|---:|---:|---:|---:|---:|
| BLIND | 0 | 0.00 | 289,664 | 7,872 | 125.70 |
| TEMPLATE | 0 | 4.14 | 203,623 | 5,325 | 82.89 |
| TEMPLATE + 最佳已筛选单条 | 1 | 7.64 | 164,974 | 4,326 | 68.59 |
| TEMPLATE + Oracle-32 | 32 | 8.27 | 155,250 | 4,216 | 67.99 |
| TEMPLATE + Oracle-64 | 64 | 8.56 | **130,718** | **3,584** | **57.26** |
| TEMPLATE + Oracle-128 | 128 | 9.77 | 141,884 | 3,888 | 64.27 |
| TEMPLATE + Oracle-256 | 256 | 20.25 | 139,467 | 3,733 | 73.51 |
| TEMPLATE + Oracle≤128 | **86** | 9.13 | **125,420** | **3,495** | **54.74** |
| TEMPLATE + FULL stripped history | 145,855 | 714.34 | 118,603 | 4,824 | 2,096.89 |
| 原先不加 TEMPLATE 的 FULL 输出 | 145,888 | 725.52 | 108,959 | 4,485 | 2,003.19 |

64 条在 TEMPLATE 基础上额外减少 **35.8% search ops、32.7% conflicts、30.9% 总时间**。
它取得旧 BLIND→FULL 搜索收益的 **88.0%**；用更严格的条件比较，取得
TEMPLATE→TEMPLATE+FULL 搜索收益的 **85.7%**。

86 条集合取得旧 BLIND→FULL 搜索收益的 **90.9%**。恰好 K 条的集合各自优化，
没有要求嵌套；因此 128/256 条并不一定优于 64 条。≤K 表包络不强行添加无益 clause。
这些是找到的集合，不能把 64 或 86 称为数学意义上的最小核心。

## 随机与源分数对照

K=64，始终在同一个 TEMPLATE baseline 上：

| 选择方式 | Search ops | 总时间 ms |
|---|---:|---:|
| 原先的 deterministic RANKED | 209,416 | 95.97 |
| RANDOM seed 17 | 259,270 | 138.30 |
| RANDOM seed 29 | 222,492 | 111.54 |
| RANDOM seed 43 | 339,321 | 179.30 |
| ORACLE | **130,718** | **57.26** |

这次并非随机拿 64 条也有同等效果。现有 source-only 分数没有预测出这个集合。
其余 32/128/256 档对照、随机种子范围均保存在完整报告和 CSV 中。

## 输出稀疏，历史 support 也很小

Oracle-64 的 64 条历史输出只需要 **265 步历史 support**；TEMPLATE 另需 72 步，
合计 **337 步**。所以没有出现“64 个输出背后还得 replay 十万步”的问题。
本轮沿用原来的 ancestor materialization/checker，就测到了 8.56 ms 的合计 replay/check。

最佳单条历史 lemma（source node ID **52434**）只额外需要 **2 步 support**，
单独就把 TEMPLATE 的 203,623 ops 降到 164,974。它是值得后续理解的具体样本，
但本轮没有据此开发新 ranking 或特征模型。

对 Oracle-64 逐条删除再求解：**63 次删除增加 search ops，1 次 ops 不变**。
删除导致的 ops 增量中位数为 56,113。Oracle-32 的 32 次删除均增加 ops。
这表明找到的集合对当前求解轨迹有明显作用；它不等于证明这些 lemma 语义必需，
也不支持把各条边际收益相加。Oracle-128/256 仍有删除后变好的成员，说明搜索并非全局最优。

## Oracle 做了什么、花了多少

协议在看 completion 结果前固定于 [oracle-lemma-protocol.md](docs/oracle-lemma-protocol.md)：

1. 从源 ranking、短 clause、高历史使用次数及随机来源构造 8,192 个 singleton 候选。
2. 在 TEMPLATE 上独立测单条收益，再测各 K 的 384 个随机/精英/混合集合及排名前缀。
3. 从两个 256 条起点做 stochastic greedy backward deletion，一直删到 32 条；
   每一步评估最多 16 个删除的条件边际收益。
4. 每个 exact-K 做 8 轮、每轮 32 个替换提案；最后对冻结赢家完整 leave-one-out 消融。

**18,409 次唯一 completion，4 个独立子进程，发现阶段 wall-clock 485.3 秒**。
并发子进程耗时之和为 1,855.9 秒；全部返回 UNSAT。Singleton 覆盖候选总体的 5.6%，
集合采样也访问整个候选总体。这是昂贵的 best-found oracle，**没有穷举 145,855 条
的所有组合，也没有证明全局最优**。全部查询保存在 [search.jsonl](results/oracle_lemma/search.jsonl)。

## 时间口径与归因边界

这是一个 **offline selection 后的集合价值实验**：ORACLE、RANKED、RANDOM 都拿到
预选好的 ID。总时间包含 TEMPLATE 和历史 support 的重新 materialize/check、CNF 序列化、
native 启动/解析/搜索/proof 输出和 artifact 哈希；不包含离线加载/源验证/建索引、
eligibility 扫描、oracle 搜索和最终 completion 证书的离线转换。
因此 **57.3 ms 不能直接宣称为已经实现的在线 retrieval→solve 延迟**。
这轮未实现便宜预测这 64 条的方法，也未优化上轮约 64 ms 的全 DAG eligibility 扫描。

模板剥离前 145,888 条历史候选，剥离了与 TEMPLATE 完全相同的 **33 条**，剩下
145,855 条；没有额外的 TEMPLATE-subsumed 或 encoding-only 候选。
67 条 TEMPLATE 是同族独立 proof 的控制，并非已经证明对所有图都成立的通用公理。
结论是**超出这份固定 TEMPLATE 控制的增量收益**，不能进一步等同于不可由其他通用
图着色策略产生的 lineage 独有知识。

目前只在这个冻结目标、这个 native backend/固定顺序上做 same-target oracle。
证明了此处存在一个小而便宜可检查的加速集合；还没有证明跨实例泛化或可廉价发现。

## 验证与可复现文件

15 项相关测试通过。30 个配置、150 次最终复测，search/conflict counters 与对应 oracle
发现阶段精确一致。独立 [审计](results/oracle_lemma/audit.json) 检查了源和 artifact 哈希、
候选排除、exact/≤K 最好已观测结果、消融差值、精确输入注入和最终测量。

5 个不同 oracle 集合的完整 UNSAT 证书均已通过原始目标上的独立 Resolution checker，
不是把注入 lemma 当成未经证明的公理。64 条集合的
[完整证书](results/oracle_lemma/ORACLE_EXACT_64.certificate.json.gz)
包含历史 support 与 completion 的组合；该证书的离线重建/检查/保存耗时约 12.5 秒，
单独记录于 [certificates.json](results/oracle_lemma/certificates.json)，没有计入 57.3 ms。

本轮没有对大规模 raw DRUP 路径做工程改动。下一步是否值得研究便宜 selector，
现在有了正向存在性证据，而不只是“加几千条可能有效”的观察。
