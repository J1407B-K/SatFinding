# HISTORY GUIDED GENERATION RESULTS

**判定：STOP。** 20 个冻结的新同家族 targets × 5 档预算 × 2 路线 × 3 次顺序重复，共600次求解；无调参、无 Oracle。

1. **相同 resolver budget 下谁的 candidates 更有用？** 见下表。ops 比值为逐 target H/T 的中位数；小于1表示 History 更好。两路仅探索顺序不同，后续使用原有 target rank。K 上限64，池不足时取全部。

| attempts | 候选数 T/H（中位） | K T/H（中位） | ops H/T | H胜 /20 | ≥10%胜 /20 |
|---:|---:|---:|---:|---:|---:|
| 64 | 64/64 | 64/64 | 0.927 | 15 | 8 |
| 128 | 128/128 | 64/64 | 1.029 | 9 | 6 |
| 256 | 256/256 | 64/64 | 1.021 | 10 | 4 |
| 512 | 512/512 | 64/64 | 0.994 | 10 | 5 |
| 1024 | 512/512 | 64/64 | 0.994 | 10 | 5 |

2. **History 是否在小 budget 优势最大？** 最低中位 ops 比值出现在 64 attempts（0.927）；64/128 分别为 0.927/1.029。不据单一最优预算调参。512候选上限使1024档仍保留前512个，因此512→1024的ops平台是协议所致，不是自然收敛证据。

3. **优势是否跨 unseen targets 稳定？** 64/128 档达到≥10% ops改善的分别为 8/20、6/20；预注册要求两档均≥16/20。20个 targets 共享一个历史源，不能当作20个独立家族。

![预算与 search ops / 路线差距](results/history_guided_generation/discovery_curves.png)

4. **加上 retrieval/generation 成本后是否值得？** warm 已计入逐次 history lookup、全部调度与生成、排序、验证、solver进程及I/O。下表warm时间是20个 target各自3次中位数的均值，generation/retrieval则取跨target中位数；摊销把一次H索引构建+加载完整分摊给20个 targets，未按预算或重复次数稀释。

| attempts | generation T/H ms | H retrieval ms（已含） | warm T/H ms | warm H/T | 摊销后 H/T | ≥5% warm胜 /20 |
|---:|---:|---:|---:|---:|---:|---:|
| 64 | 5.11/7.05 | 1.97 | 119.13/117.34 | 0.985 | 2.650 | 10 |
| 128 | 5.34/7.39 | 1.99 | 116.74/124.69 | 1.068 | 2.767 | 8 |
| 256 | 6.08/7.88 | 1.93 | 114.10/123.18 | 1.080 | 2.818 | 5 |
| 512 | 7.14/8.98 | 2.01 | 117.34/122.56 | 1.045 | 2.735 | 9 |
| 1024 | 9.17/11.17 | 2.05 | 120.15/125.78 | 1.047 | 2.698 | 8 |

H索引构建 3.966s，加载 0.0015s；2175 条原始parent-pair hints。旧H证明本身为既有成本。

5. **判定：STOP。** 本轮未通过预注册的跨target稳定小预算净收益门槛；停止这版 history-guided discovery，不调整history score救结果。结论限定于已冻结的一步parent-pair baseline。

先例 gate：已有 [Prover9 hints](https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/hints.html) / [Prooftrans](https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/prooftrans.html) 从相关问题的证明引导后续推导。本轮是其受限parent-pair baseline，不是Prover9复现或新机制声明。

求解前合法性修订：固定旧TEMPLATE在新target上缺前提，因此保留全部seeds、两路统一去掉TEMPLATE；当时尚无新target求解。原冻结和修订哈希均保留。新颖性审计限于仓库可用记录。候选短证明已重验，completion仅solver-reported UNSAT。计时未做机器隔离（本轮同时准备绘图库），小幅wall差距不作强证据；STOP同时由确定性ops的跨target不稳定支持。

证据：[协议](docs/history-guided-generation-protocol.md) · [冻结身份](results/history_guided_generation/frozen.json) · [求解前修订](results/history_guided_generation/amendment.json) · [在线冻结](results/history_guided_generation/online_manifest.json) · [逐target全部指标](results/history_guided_generation/per_target.csv) · [600条原始测量](results/history_guided_generation/raw.jsonl) · [审计](results/history_guided_generation/audit.json)。
复核（不求解）：`.venv/bin/python history_guided_generation_report.py`。
