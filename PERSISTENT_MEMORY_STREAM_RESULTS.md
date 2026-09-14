# Persistent memory stream results

**判定：STOP。** 
50个query最终累计节省 -0.0811s，load/build均未回本。

## 1–3. 50个 unseen targets 中 History 赢多少？ops 与 warm total 是否改善？

| 指标 | 结果 |
| --- | --- |
| Ops 胜 / 平 / 负 | 27 / 0 / 23 |
| Ops 胜率 | 54.0% |
| Median ops improvement | +3.80% |
| Mean ops improvement | -2.94% |
| Warm total 胜 / 平 / 负 | [27, 0, 23] |
| Median warm total improvement | +2.30% |
| Mean warm total improvement | -4.00% |
| 50-query TARGET / HISTORY warm total | 6.137s / 6.219s |
| Cumulative saving(50) | -0.0811s |

改善定义为 `1 - HISTORY/TARGET`，正数表示 History 更好。mean 是50个逐target改善率的
算术平均，不是比值的比值；warm累计则是绝对秒数之和。每个 target/route 取5次中位数。
750次测量尝试全部保留，749次完成、1次在solver启动前触发原selection wall cap。
失败为T44/HISTORY/repeat3（第4次复测），实际失败前耗时61.31ms；没有重试或替换。
主统计把未完成尝试的completion ops/conflicts/time评分设为正无穷，再取5次中位数。
这是一项失败惩罚，**不是声称测得无穷耗时**；T44/HISTORY另4次有完整结果，因此5次
保守中位数仍有限。成功尝试单独计算时，累计节省为
-0.0806s，供敏感性核对，不替代主结果。
三路线为 TEMPLATE、TARGET、HISTORY，无 Oracle。不能声称所有预算guard都通过；
预算失败率为1/750（HISTORY为1/250），原cap及失败记录均未修改。

Median ops bootstrap95%区间：[-10.22%, +8.02%]；
median warm total：[ -12.54%, +7.30% ]。
固定seed重采样10000次，按target成对抽样；它不把同源图变成独立benchmark家族，也不
把5次相同deterministic counters当成250个独立样本。
两个median区间均跨0，不能把点估计略正说成稳定正收益。

协议与完整性：T5–T54固定seeds9205–9254，沿用H6202、n200、6-regular、3-coloring、1% drift。
50个输入与T1–T4及旧同家族输入不重复。所有候选和在线输出在任何completion前冻结；
原selector源码、prior内容及native binary哈希均匹配上一轮。K64、512候选、原生成和
选择预算保持，五次复测全局固定随机打乱、单进程顺序运行。

**TEMPLATE适用性说明：** Baseline：**frozen TEMPLATE-67 source set with per-target soundness filtering**。用户确认后，对全部50个target统一过滤原67条中失效的TEMPLATE；三路线共享同一有效子集。原候选生成仍排除原67条，prior、候选池、两条选择结果与冻结版完全一致。
严格原TEMPLATE预检查有10个target缺前提，记录保留于template_preflight.json。
这不是按性能筛除query；全部50个seeds照跑，未补齐TEMPLATE、未重新选K。
40个target保留67条，另10个保留60–66条。本文结论限定在这一获准的soundness处理规则下。
Amendment在 2026-09-11T03:06:31.488219+00:00 UTC 记录；执行阶段在 2026-09-11T03:06:34.225709+00:00 UTC 启动。
二者通过[amendment哈希记录](results/persistent_memory_stream/protocol_amendment.json)及
[执行记录](results/persistent_memory_stream/execution_start.json)关联。原协议和driver版本另行保留，
未覆盖准备阶段的provenance。每个target的三个必需字段见
[template_validity.json](results/persistent_memory_stream/template_validity.json)和每次raw测量。

## 4. Cumulative saving 曲线是什么形状？

![History ratio and cumulative saving](results/persistent_memory_stream/stream.png)

流顺序严格为预先固定seed顺序；测量作业的随机顺序不用于重排累计曲线。
累计为 `Σ(median TARGET_total - median HISTORY_total)`，不重复扣一次性prior费用。
终值 **-0.0811s**，前缀范围 [-0.0859, +0.1161]s。
曲线反复上升和回吐，后段转负，未形成持续增长；内嵌放大图显示小幅变化，外图保留两条成本线。
每10query区段净节省依次为：+0.0834s, -0.0566s, +0.0258s, -0.0025s, -0.1312s。
细淡线为4个全部完成的复测编号各自的累计，不是额外求解；repeat3因含未完成query
无法形成有限的完整累计线，明确不绘制该线，失败仍在主统计中按上述规则惩罚。其余终值为
-0.0013s, -0.0465s, -0.2093s, -0.0853s。

## 5–6. Prior load / build 第几个query回本？

- 0.82s load：**未跨过**；从此一直保持回本的起点：未跨过。
  第50题净余量 -0.9011s；首次越线后是否跌回：False。
- 3.87s build：**未跨过**；持续回本起点：未跨过。
  第50题净余量 -3.9511s；首次越线后是否跌回：False。

用上一轮未四舍五入成本0.822510125s / 3.870796375s，首次越线分别为
未跨过 / 未跨过。
本次无损gzip prior加载+校验+解析计 0.698s，另记，
不替换用户冻结的成本线，也不把一次加载费用重复摊到每个query。
固定TEMPLATE/目标输入已在内存；warm总时间包含候选生成、选择/检索、验证、solver进程
及临时输入I/O。历史proof生产仍是已有历史的sunk cost，未重新生成prior。

## 7. 收益是否由少数outlier主导？

所有正节省合计 0.4919s，所有负节省合计 -0.5730s，净值 -0.0811s。

| 最大的正节省 | 占全部正节省 | 删除这些 winner 后净节省（诊断） |
| --- | --- | --- |
| 1 | 7.95% | -0.1202s |
| 5 | 36.44% | -0.2604s |
| 10 | 66.65% | -0.4089s |

最大正节省来自 T10：+0.0391s。
正收益分布在27题，最大单题只占正节省的7.95%，
最大5题占36.44%。这里并不存在“少量巨大winner撑起
正均值”：均值和净值本身就是负的。赢题平均省18.22ms，
输题平均多花24.91ms，较大的损失抵消了略多的胜局。
最大5个loss占全部负耗时的37.77%；完整数据保留这些不利样本。
这只是敏感性分析，正式指标没有删除任何样本。每条ratio、绝对节省和累计值均在per_query.csv。

## 8–10. 最终判定与后续

**STOP**。ALIVE的四个门槛（ops多数胜、median ops正、median warm正、最终覆盖load）
分别为：True / True / True / False。
Build摊销为额外标记，不用mean收益替代median，也不用某次短暂越线替代最终回本。
判定规则在任何completion前写入协议，未根据结果降低。
STOP触发的是“累计无法形成持续增长”：终值≤0，且5个十题区段中3个净节省非正；
同时mean ops和mean warm改善率为负。不是仅因50题尚未覆盖load而将正aggregate误判STOP。

明确停止当前冻结 selector/prior 路线；不换特征、挑 seeds、加 Oracle 或重组模块挽救结论。

不恢复semantic abstraction、unique history-specific knowledge或少量proof modules主张。
本轮只检验这一份冻结prior和selector在这一条同家族流中的可摊销价值。

证据：[逐query全部数据](results/persistent_memory_stream/per_query.csv)、
[三路线汇总](results/persistent_memory_stream/summary.csv)、[750次raw](results/persistent_memory_stream/raw.jsonl)、
[指标](results/persistent_memory_stream/metrics.json)、[固定seeds](results/persistent_memory_stream/seeds.json)、
[冻结选择](results/persistent_memory_stream/online_frozen.json)、[失败处理](results/persistent_memory_stream/analysis_failure_policy.json)、[协议](docs/persistent-memory-stream-protocol.md)、
[审计](results/persistent_memory_stream/audit.json)、
[PDF图](results/persistent_memory_stream/stream.pdf)。
驱动：[persistent_memory_stream.py](persistent_memory_stream.py)；
报告：[persistent_memory_stream_report.py](persistent_memory_stream_report.py)。
CNF仅放临时目录，completion DRUP写/dev/null；不再积累大型原始proof。
Completion状态是native solver报告，并非逐题完整completion证书认证。
独立审计逐一重新验证3350个TEMPLATE根，复核全部原candidate pool/已选IDs，重建749个
已完成运行的输入哈希，确认三路线逐题模板一致；那1次预算失败保留并单独标明。
