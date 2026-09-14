# Replay budget curve：小集合有价值，但 HISTORY 尚未赢得总时间

已跑完用户指定的 8 档：0、32、128、512、2,048、8,192、32,768、ALL。
固定 identity vertex/color mapping；HISTORY top-K、TEMPLATE top-K、3 个固定种子的
RANDOM historical K；3 个冻结目标，每配置重复 3 次，共 333 次运行。

[完整曲线 PNG](results/replay_budget/curve.png) ·
[可导出 PDF](results/replay_budget/curve.pdf) ·
[全部表格](results/replay_budget/report.md) ·
[汇总 CSV](results/replay_budget/summary.csv) ·
[逐次 JSONL](results/replay_budget/raw.jsonl) ·
[协议](docs/replay-budget-protocol.md)

## 主实例：n=200，1% edge drift

以下 wall-clock 是 3 次运行的中位数。Replay/check 包含当前目标上的 eligibility/selection、
所选祖先的 materialization 和检查；total 还包含 CNF 序列化、native 子进程、输入解析、
搜索、proof 输出及 artifact 哈希。源 proof 的加载、验证、建索引属于单独记录的离线成本。

| 路线 / cap | 实际 lemma | Replay/check ms | Completion search ops | Conflicts | Total wall ms |
|---|---:|---:|---:|---:|---:|
| BLIND | 0 | 0.00 | 289,664 | 7,872 | 125.02 |
| HISTORY 32 | 32 | 65.06 | 256,664 | 6,950 | 185.71 |
| HISTORY 128 | 128 | 68.42 | 226,023 | 6,128 | 164.91 |
| HISTORY 512 | 512 | 78.40 | 216,296 | 6,135 | 176.39 |
| HISTORY 2,048 | 2,048 | 85.00 | 161,840 | 5,157 | 171.08 |
| HISTORY 8,192 | 8,192 | 112.30 | 189,115 | 7,469 | 287.25 |
| HISTORY 32,768 | 32,768 | 210.14 | 150,102 | 6,223 | 555.33 |
| HISTORY ALL | 145,888 | 756.27 | 108,959 | 4,485 | 2,018.94 |
| TEMPLATE ALL | 67 | 11.82 | 203,623 | 5,325 | 89.18 |
| 旧版 FULL replay | 145,888 | 1,366.40 | 108,959 | 4,485 | 2,613.98 |

HISTORY 2,048 条拿到 FULL 搜索收益的 **70.7%**：
`(289664 - 161840) / (289664 - 108959)`。只用了 FULL 输出的 1.4%，
总时间减少 91.5%，但仍比 BLIND 慢 36.8%。不能据此说已经实现在线加速。
8,192 条还比 2,048 条搜索更多，曲线不是单调递减，也没有干净的平台。

TEMPLATE 的 67 条在本实例上同时改善 search 和 wall（分别下降 29.7%、28.7%）。
这是同族非 lineage proof 的控制，不能把收益全部归因于 lineage 历史。

## Ranking 与随机对照

主实例 K=512，HISTORY 为 216,296 ops；三次随机子集分别为
171,498、235,661、389,965 ops。一个随机种子更好，不能声称 512 档稳定胜过随机。

K=2,048 时，HISTORY 为 161,840 ops / 171 ms，三个 RANDOM 为
231,233–247,664 ops / 452–476 ms；这一档有更清楚的 ranking 信号。
HISTORY 的 support 只有 5,350 步，随机需要约 5.8–5.9 万步。
当前分数对 support 成本的改善，比它对每个 K 的搜索收益更稳定。
但只跑了 3 个随机种子，仍是探索性证据。

另外两个冻结目标：

- **5% drift**：HISTORY 2,048 为 225,125 ops / 189 ms，FULL 为
  254,554 ops / 1,407 ms；小集合甚至搜索也更少。但 TEMPLATE 32 为
  221,195 ops / 103 ms，仍是更好的时间点；BLIND 为 378,627 ops / 167 ms。
- **独立目标**：BLIND 为 201,878 ops / 71 ms，HISTORY ALL 只有 157 条，
  却增至 263,454 ops / 144 ms。没有普遍加速。随机 K=32 有一个种子搜索少于
  BLIND，但所有实测 replay 路线的总时间都高于 BLIND。

## 工程含义

分数在运行前固定为
`(1 + historical direct uses) / ((1 + clause width) * (1 + left width + right width))`，
同分按源 node ID。没有用目标求解结果训练或挑分数。

K 限制的是送入 completion 的唯一非输入 clause，包括 Resolution 中间 clause，
并非原始 DRUP learned-clause 数。证明所选输出需要的 ancestor 另行统计和计费，
不偷偷一起送入 solver。原有 checker 检查这一祖先并集。

这版已经实现已有 Resolution DAG 上的按需 ancestor materialization，但每次 query
仍遍历全 DAG 判定 eligibility。主实例 HISTORY 2,048 的这部分耗时约 **64 ms**。
源 HISTORY 共 251,420 个 inference node，加载、源 proof 检查、建索引另需约
0.89、0.95、1.98 秒。全部写在 metadata，不能当作免费冷启动。

**尚未解决 raw DRUP → lazy support reconstruction。** 这轮复用了已转换文件，
没有再对 n=300 启动 600 秒的全量转换。下一步应处理源端 support hints/index，
让原始 proof 保持紧凑，并减少目标侧全 DAG eligibility 扫描；有了 support 信息再按需
重建并检查所选片段。仅有无 hint 的 DRUP，不能凭空知道某条 lemma 的全部祖先。

29 项相关测试通过；105 组唯一选择、333 次运行的 artifact 审计通过，验证了
源/输入/proof 哈希、预算、嵌套子集、精确输出注入，以及 ALL 与旧版的 clause 顺序和
native search/conflict counters 完全一致。Replay support 经独立 checker 检查；
completion 的 UNSAT 仍是 solver-reported，未把最终 DRUP 全量展开成 Resolution。

重跑：`.venv/bin/python replay_budget_run.py`；审计：
`.venv/bin/python audit_replay_budget.py`；安装 matplotlib 后运行
`.venv/bin/python replay_budget_report.py` 生成图表。
