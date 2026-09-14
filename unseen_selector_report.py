"""Render the fixed unseen-selector decision experiment without further solving."""
import json
import csv
from pathlib import Path
from statistics import median
from evaluation_oracle_run import sha
P=Path('results/unseen_selector')


def load(name):return json.loads((P/name).read_text())
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])


def main():
    rows=load('summary.json');m=load('metadata.json');audit=load('audit.json');frozen=load('online_frozen.json')
    d={(r['target'],r['route']):r for r in rows}
    with (P/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    opstable=table(['Target','TEMPLATE','TARGET','HISTORY','ORACLE','H/T ops'],[
        [t,*[f"{d[t,r]['analysis_resolution_steps']:,}" for r in ['TEMPLATE','TARGET','HISTORY','ORACLE']],
         f"{(d[t,'HISTORY']['analysis_resolution_steps']/d[t,'TARGET']['analysis_resolution_steps']-1)*100:+.2f}%"] for t in frozen])
    times=table(['Target','Route','Conflicts','生成 ms','选择/检索 ms','验证 ms','Solver ms','Total ms'],[
        [r['target'],r['route'],r['conflicts'],*[f"{1000*r[k]:.2f}" for k in ['generation_seconds','selection_seconds','validation_seconds','solver_seconds','total_seconds']]] for r in rows])
    costs=table(['Target','H 比 T 少用时间 ms（负为更慢）','H/T total','H build 摊销后 total ms','已有 prior 加载摊销后 total ms'],[
        [t,f"{1000*(d[t,'TARGET']['total_seconds']-d[t,'HISTORY']['total_seconds']):.2f}",
         f"{(d[t,'HISTORY']['total_seconds']/d[t,'TARGET']['total_seconds']-1)*100:+.2f}%",
         f"{1000*(d[t,'HISTORY']['total_seconds']+m['prior']['build_check_index_seconds']/3):.2f}",
         f"{1000*(d[t,'HISTORY']['total_seconds']+m['prior']['prior_load_seconds']/3):.2f}"] for t in frozen])
    budget=table(['Target','Resolver attempts A=B','Examined A=B','K A=B','验证 steps A=B','History prior hits / 512'],[
        [t,frozen[t]['generation']['resolver_attempts'],512,64,64,frozen[t]['history_selection']['prior_hits']] for t in frozen])
    oracle=table(['Target','固定 offline calls','Offline discovery 秒','Best online → oracle ops 改善'],[
        [t,load(f'{t}/oracle.json')['unique_calls'],f"{load(f'{t}/oracle.json')['discovery_seconds']:.2f}",
         f"{(1-d[t,'ORACLE']['analysis_resolution_steps']/min(d[t,'TARGET']['analysis_resolution_steps'],d[t,'HISTORY']['analysis_resolution_steps']))*100:.2f}%"] for t in frozen])
    saving=audit['warm_aggregate_saving_seconds'];build=m['prior']['build_check_index_seconds'];loading=m['prior']['prior_load_seconds']
    report=f'''# Unseen selector results
+
+**判定：{audit['verdict']}。** History 在 3 个 unseen targets 中赢 2 个、输 1 个。
+两个收益超过额外在线检索/选择成本，但没有逐 target 稳定优势，且本次三个查询的
+总节省不足以摊销 prior 构建或加载成本。**不能据此宣布 historical-proof-memory 主线成立。**
+
+## 1. TARGET / HISTORY / ORACLE 各是多少？
+
+{opstable}
+
+K=64；ops 是原 native Glucose 的 first-UIP antecedent visits，口径不变。
+每项 5 次顺序运行，顺序打乱，counters 全部重复一致；不是 5 个独立搜索 seed。
+全部 UNSAT。Oracle 只在同一512候选池内运行固定162个 proposals，没有继续优化：
+96随机集合 + 两个在线选择，之后4×16 swaps。它是 best-found 可达参考，
+**不是已证明全局最优的 upper bound**，其昂贵选择成本不能隐藏为在线耗时。
+
+{oracle}
+
+以下均为5次中位数；Total 直接测量整个 warm pipeline，包含未单列的进程启动、
+CNF 临时写入和 JSON 读取，不能将各阶段中位数简单相加代替 Total。
+ORACLE 行的选择时间只含读取已选 IDs，offline discovery 在上表另列。
+
+{times}
+
+**Unseen 定义与冻结。** T2/T3/T4 使用此前未出现的 seeds 9202/9203/9204。
+沿用现有 `evolve`、n200 6-regular 3-coloring、H=6202、1% drift；没有新 generator、
+新编码或新 benchmark 家族，也没有按求解结果筛除 target。种子与 CNF 哈希和
+已保存的同家族输入核对；三个 target 互异，均不是旧 Gold/Oracle target。
+固定67条 TEMPLATE，所有候选、selector、超参数和在线输出**在任何 solve(T) 前**落盘。
+三个 targets 同源且距离近，不代表三个独立 benchmark 家族。
+
+## 2. 同预算下 history 是否稳定有额外价值？
+
+**没有稳定胜出；存在两个 target 上的正信号。** T2/T3 的 ops 分别降低27.10%/18.93%，
+T4 增加6.37%。不能只报告前两个，也不能由 median 改善推广为稳定 future-utility prior。
+
+{budget}
+
+两路线都从 T 的 original-premise resolution 生成相同512条一步候选；4096 resolver
+attempts / 100ms generation 上限相同。逐 target A/B 的实际 resolver 次数也相同。
+每条候选最多一次 cheap feature evaluation、一次 sort，共512条；selection 上限50ms，
+H额外512次 prior lookup。两边均验证64步，加共同 TEMPLATE 72步。所有上限均通过；
+不人为填满较快路线的时间，也不将相同上限说成实际计算耗时完全相等。
+
+TARGET 排序固定为：clause width → support-edge common-neighbor count →
+opposite-literal Jeroslow–Wang 权重 → SHA256 tie-break。
+HISTORY 只在同一 tuple 前加既有 `HistoryIndex.scores`：
+`(1+source direct uses)/((1+width)*(1+parent literal count))`，同 clause 多条历史证明取最大值。
+未在 source 中出现时记0分。查询阶段不读 target conflicts、completion proof 或 Gold IDs。
+这检验 **ranking prior**；不声称同时测试了历史驱动 generation 或 mapping 的潜在节省。
+
+本 family 中 width 与 JW 分数相同；TARGET 的非平凡区别主要来自 common neighbors，
+再由哈希打破平局。它是明确的廉价结构 baseline，不是最佳 target-only selector。
+H 的512候选中303/303/309条命中 prior，各 target 选中的64条全部命中。
+prior 是**重建 Resolution DAG 的使用重要性**，不冒充真实 CDCL activity、LBD 或训练过的
+future-utility predictor。最终 ops 是效用指标，本轮未再录制 trajectory。
+
+**Prior-art gate 已在运行前完成。**
+[CrystalBall](https://www.cs.utoronto.ca/~meel/publications/b2hd-SKM19.html) 已研究 solver 数据与 clause
+效用预测框架；[Freezing/reactivating clauses](https://www.cril.univ-artois.fr/~lagniez/papers/AudemardLMS11.pdf)
+利用过去信息判断后续搜索相关性；[ATPG 2007](https://uww.revlib.org/doc/konf/07vlsiDesign.pdf)
+已有相关实例间 learned-information reuse；[CausalSAT](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SAT.2023.28)
+研究 clause utility 与 branching 的关系。这些直接记为 BASELINE，不宣称本轮发明 future prior。
+复用仓库的 resolver、checker、source importance、Evaluator 和 native solver。
+TARGET 使用已知 occurrence-weight / 图邻接特征的固定组合，仅作为基线，不当新算法。
+完整预算与判定阈值见[事前协议](docs/unseen-selector-protocol.md)。
+
+## 3. 额外价值能否覆盖 retrieval / selection / validation 成本？
+
+**Warm：T2/T3 能，T4 不能。三 target 合计仅节省 {saving*1000:.2f}ms。**
+额外 history lookup 已计入选择时间；验证两边相同64条一步支持，差异很小。
+T3 的 HISTORY 虽然优于 TARGET，仍比 TEMPLATE 的总时间慢；不是普遍值得物化。
+
+{costs}
+
+一次性 H proof 加载/检查/index/prior 计算为 **{build:.3f}s**；
+已有完整 prior JSON 的加载和反序列化为 **{loading:.3f}s**。
+表中分别按3个查询摊销，二者是不同部署入口，不重复相加。
+无论从历史 proof 构建，还是直接加载已保存 prior，本次3个查询都无法覆盖成本。
本轮加载的是完整246,003项 source prior；这是当前复用实现的实测成本，不是历史方法
不可降低的成本下界。没有在看过结果后裁剪 prior 或重新调参来救结论。
+冷启动每个查询单独支付时更差。原始历史 proof 生产视为已有历史的 sunk cost，
+未计入额外费用；prior JSON 写盘/归档时间也未计入此构建指标，因此上述冷成本已经偏乐观。
+固定 TEMPLATE 的共同预加载成本 {m['template_prepare_seconds']:.3f}s 对所有路线一致，另列而不混入 warm 对比。
+
+若未来平均 warm 节省恰好保持本次 {saving/3*1000:.2f}ms/query，构建或加载的粗略
+break-even 分别约 {build/(saving/3):.0f} / {loading/(saving/3):.0f} 个查询。
+**这是外推算式，不是已测得的摊销成功；T4 的负收益已说明不能假定每次都节省。**
+
+## 4. 当前主线：ALIVE / WEAK / STOP？
+
+**{audit['verdict']}，不授予 ALIVE。** 事前 ALIVE 门槛要求三个 target 各自至少10% ops 改善、
+5% warm total 改善，并覆盖本次3个 target 的 prior 构建摊销。T4 与摊销两项均未通过。
+目前也不判成“完全没有额外信息”：两个 unseen targets 上的明显收益是真实的，
+不能为了负叙事抹掉。按冻结规则，这类混合结果属于 WEAK，而非稳定成立。
+这些是操作性门槛，不是统计显著性检验。
+
+## 5. 如果 ALIVE，下一步最小实验是什么？
+
+本轮不是 ALIVE，故**不进入主线扩展、selector 调参或 Oracle 优化**。
+若另行决定验证这个 WEAK 信号，最小问题仅是：同一已加载 prior 和完全冻结 selector
+在独立保留的更多同家族查询上，能否重现稳定净收益并真正摊销启动成本。
+本轮不追加这些查询，不换特征、不挑有利子集。
+
+## 6. 如果 STOP，为什么？
+
+本轮不是正式 STOP；明确的阻断原因是 **跨 target 不稳定 + 当前 workload 下成本不能闭合**。
+不能把“赢2个target”包装成稳定 historical-proof-memory，也不能用 offline oracle 的
+剩余空间挽救在线 selector。Oracle 表明仍有可选空间，但没有证明 history 比 target
+features 更可靠地识别这种空间。semantic abstraction、shared proof modules、
+unique history-specific knowledge 的冻结否定结论全部保留。
+
+---
+
+证据：[60次 raw runs](results/unseen_selector/raw.jsonl)、[汇总](results/unseen_selector/summary.csv)、
+[预先冻结的候选/证明/选择](results/unseen_selector/online_frozen.json)、
+[元数据](results/unseen_selector/metadata.json)、[审计](results/unseen_selector/audit.json)。
+源码：[driver](unseen_selector.py)、[audit](audit_unseen_selector.py)、[report](unseen_selector_report.py)。
+审计已复算 H prior、重现在线选择、验证全部 target 候选短证明、核对冻结哈希、512/64预算、
+60次状态/counters 和固定 oracle 记录。Completion 为 solver-reported UNSAT，
+不声称逐份保存完整 completion proof；CNF 临时文件自动清理，DRUP 写 `/dev/null`。
+完整 prior 只做 gzip 无损归档，未压缩内容哈希仍由审计核对，避免再次积累大型原始数据。
+
+复核：`.venv/bin/python audit_unseen_selector.py`；报告：`.venv/bin/python unseen_selector_report.py`。
+驱动拒绝覆盖已有 `online_frozen.json`，以免无意重调/混用缓存；重跑实验应使用单独目录并
+保留现有冻结版本。审计不启动新 target completion，也不变更 selector。
+'''.replace('\n+','\n')
    Path('UNSEEN_SELECTOR_RESULTS.md').write_text(report)
    paths=[Path('UNSEEN_SELECTOR_RESULTS.md'),Path(__file__),Path('audit_unseen_selector.py'),P/'audit.json',P/'summary.json',P/'raw.jsonl',P/'online_frozen.json',P/'metadata.json']
    (P/'report_manifest.json').write_text(json.dumps({str(p):sha(p) for p in paths},indent=2)+'\n')


if __name__=='__main__':main()
