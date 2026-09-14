"""Render frozen measurements; no experiments or adaptive selection here."""
import csv
import json
from pathlib import Path
from statistics import median
from collections import Counter
from evaluation_oracle_run import sha

P=Path('results/target_local_history')


def readcsv(name): return list(csv.DictReader((P/name).open()))
def load(name): return json.loads((P/name).read_text())
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary={r['route']:r for r in readcsv('summary.csv')}
    ops=lambda route:int(summary[route]['analysis_resolution_steps'])
    b,l,n,g=[ops(r) for r in ['TEMPLATE','LOCAL','NONLOCAL','Gold64']]
    progressive=readcsv('progressive.csv')
    oracles=load('oracles.json')
    one=load('one_step/oracles.json')
    one_summary={r['route']:r for r in readcsv('one_step/summary.csv')}
    audit=load('audit.json')
    meta=load('metadata.json')
    fig,axes=plt.subplots(1,2,figsize=(13,4.8))
    for order in dict.fromkeys(r['order'] for r in progressive):
        rr=[r for r in progressive if r['order']==order]
        axes[0].plot([int(r['k']) for r in rr],[int(r['ops']) for r in rr],label=order,
                     alpha=.5 if order.startswith('random') else 1,lw=1 if order.startswith('random') else 1.7)
    axes[0].axhline(b,color='black',ls='--',lw=1,label='TEMPLATE')
    axes[0].set(xlabel='Gold subset size (canonical injection order)',ylabel='Search ops',title='Gold64 progressive subsets')
    axes[0].legend(fontsize=7,ncol=2)
    for label,color in [('history','tab:orange'),('target','tab:blue')]:
        for r in oracles:
            if r['label']==label:
                axes[1].plot([16,32,64],[r['exact'][str(k)]['analysis_resolution_steps'] for k in [16,32,64]],
                             color=color,alpha=.35,lw=1)
        axes[1].plot([16,32,64],[ops(f'{label}Oracle_{k}') for k in [16,32,64]],
                     'o-',color=color,label=f'{label}: best of 3')
    axes[1].axhline(b,color='black',ls='--',lw=1,label='TEMPLATE')
    axes[1].plot([16,32,64],[int(one_summary[f'targetOneStepOracle_{k}']['analysis_resolution_steps'])
                 for k in [16,32,64]],'s-',color='tab:green',label='target 1-step: best of 3')
    axes[1].scatter([64],[g],marker='*',s=100,color='red',label='Frozen Gold64 (older budget)')
    axes[1].set(xlabel='Exact K',ylabel='Search ops',title='Matched finite offline oracles',xticks=[16,32,64])
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(P/'comparison.png',dpi=180)
    fig.savefig(P/'comparison.pdf')
    plt.close(fig)
    main_table=table(['Route','Ops','Conflicts','Validation ms','Total ms [min, max]'],[
        [r,f"{ops(r):,}",summary[r]['conflicts'],f"{float(summary[r]['replay_and_check_seconds'])*1000:.2f}",
         f"{float(summary[r]['total_wall_seconds'])*1000:.2f} [{float(summary[r]['time_min'])*1000:.2f}, {float(summary[r]['time_max'])*1000:.2f}]"]
        for r in ['TEMPLATE','LOCAL','NONLOCAL','Gold64','LOCAL_target_proof']])
    oracle_table=table(['K','History seeds 17 / 29 / 43','Target seeds 17 / 29 / 43','Best H','Best T','T vs H'],[
        [k,*[' / '.join(f"{r['exact'][str(k)]['analysis_resolution_steps']:,}" for r in oracles if r['label']==label)
                for label in ['history','target']],f"{ops(f'historyOracle_{k}'):,}",f"{ops(f'targetOracle_{k}'):,}",
         f"{(ops(f'targetOracle_{k}')/ops(f'historyOracle_{k}')-1)*100:+.2f}%"] for k in [16,32,64]])
    timing_table=table(['Route','Ops','Conflicts','Validation ms','Total ms'],[
        [r,f'{ops(r):,}',summary[r]['conflicts'],f"{float(summary[r]['replay_and_check_seconds'])*1000:.2f}",
         f"{float(summary[r]['total_wall_seconds'])*1000:.2f}"] for k in [16,32,64] for r in [f'historyOracle_{k}',f'targetOracle_{k}']])
    marg=readcsv('marginals.csv');pairs=readcsv('pairs.csv')
    positive=sum(int(r['singleton_gain'])>0 for r in marg)
    penalties=[int(r['deletion_penalty']) for r in marg]
    interactions=[int(r['interaction_gain']) for r in pairs]
    trajectory={r['route']:r for r in load('trajectory.json') if r['binary']=='trajectory'}
    def meanhist(t,key):
        d=t['trajectory'][key];return sum(int(k)*v for k,v in d.items())/sum(d.values())
    trajectory_table=table(['指标','TEMPLATE','Gold64'],[
        ['conflicts',trajectory['TEMPLATE']['stats']['conflicts'],trajectory['Gold64']['stats']['conflicts']],
        ['decisions',trajectory['TEMPLATE']['stats']['decisions'],trajectory['Gold64']['stats']['decisions']],
        ['不同 decision variables',len(trajectory['TEMPLATE']['trajectory']['decision_variables']),len(trajectory['Gold64']['trajectory']['decision_variables'])],
        *[[label,*[f'{meanhist(trajectory[r],key):.3f}' for r in ['TEMPLATE','Gold64']]]
          for label,key in [('learned clause 平均宽度','learned_width'),('平均 backjump 目标层','backjump_level'),('平均回跳距离','backjump_distance')]],
        ['propagations',trajectory['TEMPLATE']['stats']['propagations'],trajectory['Gold64']['stats']['propagations']]])
    costs=table(['Route','独立 support steps','联合 support steps','1/2-step 数量（target）'],[
        [r['route'],r['independent_support'],r['union_support'],str(r.get('cost_histogram','—'))]
        for r in audit['selected_costs'] if 'Oracle' in r['route']])
    one_table=table(['K','一步 Target seeds 17 / 29 / 43','Best ops','相对 Best History','Validation ms','Total ms'],[
        [k,' / '.join(f"{r['exact'][str(k)]['analysis_resolution_steps']:,}" for r in one),
         one_summary[f'targetOneStepOracle_{k}']['analysis_resolution_steps'],
         f"{(int(one_summary[f'targetOneStepOracle_{k}']['analysis_resolution_steps'])/ops(f'historyOracle_{k}')-1)*100:+.2f}%",
         f"{float(one_summary[f'targetOneStepOracle_{k}']['replay_and_check_seconds'])*1000:.2f}",
         f"{float(one_summary[f'targetOneStepOracle_{k}']['total_wall_seconds'])*1000:.2f}"] for k in [16,32,64]])
    progress_table=table(['Order','K=16','K=32','K=48','K=63','K=64'],[
        [order,*[f"{int(next(r['ops'] for r in progressive if r['order']==order and int(r['k'])==k)):,}"
                   for k in [16,32,48,63,64]]] for order in dict.fromkeys(r['order'] for r in progressive)])
    t=trajectory['Gold64']['trajectory']
    text=f'''# Target local vs history

结论：**本 target 上 Gold64 的价值明显非加性，但不能归因于 history-specific unique knowledge。**
LOCAL 与 NONLOCAL 单独都使搜索变差，组合才有收益；匹配离线预算后，
target-only 与 history oracle 的差距远小于旧 Gold64 相对 TEMPLATE 的收益。
当前最稳妥的解释是 **candidate prioritization + trajectory shaping 的混合**。
停止强 history-specific claim，也不把本例提升为跨 target 的 synergy 理论。

## A. Prior-art gate：已有机制直接 REUSE / BASELINE

[固定协议](docs/target-local-protocol.md) 在测量前写入。检索了用户指定的四类问题，
没有把“未找到完全相同实验”当作 novelty 证据。

| 问题 | 已有工作 | 本轮处理 |
|---|---|---|
| cross-instance learned information | [ATPG 2007](https://uww.revlib.org/doc/konf/07vlsiDesign.pdf) | BASELINE：相关 SAT 实例间复用已存在 |
| historical state 改变后续 search | [Incremental Glucose](https://www.cril.univ-artois.fr/articles/xmain.pdf) | BASELINE：本实验用 fresh processes，只传 clauses，不传 activity/phase |
| clause utility 与 branching 相互影响 | [CausalSAT, SAT 2023](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SAT.2023.28) | BASELINE：本轮只做集合干预和聚合观测，不冒充因果中介分析 |
| target cheap consequences | [Een–Biere SAT 2005](https://fmv.jku.at/papers/EenBiere-SAT05.pdf), [Vivification](https://arxiv.org/abs/1807.11061) | REUSE：廉价 resolution/propagation 不是历史独有知识 |
| 非线性和顺序敏感性 | [Biere 的 butterfly-effect 讨论](https://cca.informatik.uni-freiburg.de/sat/ss23/08/)，上一轮已读本地 IPR | BASELINE：检查注入顺序，不扩大理论 claim |

没有重新写 generic preprocessor。新增的只是调度与实验胶水：一、二步候选调用既有
`ProofDB.resolve`，验证用 `HistoryIndex.materialize` / `ProofContext`，
离线筛选用 `Evaluator`，completion 用原 native Glucose 3.0。

## B. LOCAL / NONLOCAL 各贡献多少？

固定 n200_T_r01_s7201、H=G6202、67 TEMPLATE outputs 和原 Gold64 IDs。
成本单位是**从原始 target CNF 得到该 exact clause 的 binary resolution inference 数**，
不把历史 certificate 长度当最短 target 成本；不使用 TEMPLATE 充当前提。
先枚举 premise/premise，再枚举一步产物/premise。它穷尽了 <=2-step resolution
证明的两种形状；不是任意推理系统下的“语义最短证明”，也不计免费 weakening。
分类得到 **44 LOCAL（31×1 + 13×2），20 NONLOCAL（无 <=2-step exact derivation）**。
这次完整 target 检查与冻结的 44/20 分类一致。

每项 5 次，打乱配置执行顺序、单进程顺序计时；search counters 五次相同。
下表为中位数。Validation 含 TEMPLATE 及所选 support replay/check；Total 含
validation、输入写入、native process 与结果读取，**不含离线候选生成、索引和 oracle**。

{main_table}

- LOCAL 单独 gain = {b-l:,} ops（相对 TEMPLATE {(b-l)/b*100:.2f}%）。
- NONLOCAL 单独 gain = {b-n:,} ops（{(b-n)/b*100:.2f}%）。
- Gold64 联合 gain = **{b-g:,} ops（{(b-g)/b*100:.2f}%）**。
- 条件交互量 `ops(L)+ops(N)-ops(∅)-ops(L∪N)` = **{l+n-b-g:,} ops**。
- 已有 NONLOCAL 时再加 LOCAL，节省 {n-g:,}；已有 LOCAL 时再加 NONLOCAL，节省 {l-g:,}。

因此不能说“68.75% 的 clauses 很便宜，所以贡献了 68.75% 收益”，也不能将负的
standalone gain 分配成知识价值比例。**LOCAL 单独没有正收益；联合收益中
LOCAL 的可分摊比例不可识别。** LOCAL_target_proof 用 target-only 的短证明重证相同
44 个 outputs，注入顺序相同，得到完全相同 counters；历史来源不影响这些 clause 的含义。
31+26=57 是独立推导总数，target 证明联合 56 步，历史联合 57 步；都不构成模块论据。

## C. HistoryOracle vs TargetOracle

Target pool 在打开 H 和 TEMPLATE **之前**仅由 T 产生：
{meta['poolmeta']['first_step']:,} 个一步、{meta['poolmeta']['second_step']:,} 个新增二步 consequence，
共 {meta['poolmeta']['budget']['attempts']:,} 次已有 resolver 调用，
生成耗时 {meta['poolmeta']['seconds']:.3f}s（不含序列化/索引）。之后统一做 TEMPLATE exact/subsumption
及 encoding-only 排除。Target 剩 **{meta['target_population']:,}**，History 剩
**{meta['history_population']:,}**；target pool 中 {audit['target_pool_history_overlap']:,} 条也在 history pool。
过滤后的 target 成本分布见 audit：{audit['target_pool_cost_histogram']}。

“同等廉价推导预算”这里严格指每个候选 <=2 resolution steps，exact-K 集合独立
support <=2K。没有强制所有 K 都保持 Gold LOCAL 的 31:13 比例或平均 57/44 步；
完整选中成本列在下方，便于看清这一区别。HistoryOracle 按问题定义允许 NONLOCAL。
候选池规模不是相同的，但 **选择器预算相同**；不偷偷把旧 Gold 当 history 的起点。

三组搜索种子 17/29/43；每组每侧 512 singleton screens、每 K 96 随机集合和一个
singleton-best 集合、64→16 backward（每层 8 proposals）、每 K 4×16 swaps。
每侧每 seed 均为 1,379 个 proposals。Target 三组各 1,379 unique calls；
History 为 1,379 / 1,378 / 1,378（两组各一个重复 proposal 复用缓存），总共 8,272 unique calls。
相同 TEMPLATE、solver、objective（ops，然后 conflicts，然后该池稳定 ID），
选中集合按该池的稳定生成/source ID 注入。**这是有限预算 heuristic offline oracle，
不是全局最优；三次搜索种子也不是三个独立 target。**

{oracle_table}

负的 T vs H 表示 Target 更好。**best-of-three 的 Target 在三个 K 全部略优，
逐 seed/K 的 9 个比较中赢 6 个。当前按“相近或略优”处理，非统计等效性证明。**
逐 seed 的原始结果保留，不能用 best-of-three 冒充统计显著性。
旧高预算 Gold64 = {g:,} ops 是独立参考：旧流程有 18,409 unique evaluations，
包括 8,192 singleton screens，本轮 H/T 分别合计 4,135 / 4,137 unique calls，
不能拿它直接压过本轮 TargetOracle 后宣称历史知识不可替代。

重新验证和求解每个 best-of-three winner 各 5 次：

{timing_table}

独立 support 与联合 support（不含固定 TEMPLATE 的 72 步）：

{costs}

离线过程成本另见每个 `oracle_*_*.json` 的 wall / sum-process seconds，
history 加载、检查、索引等本次共同 preparation 为 {meta['prepare_seconds']:.2f}s。
final timings 是已选 ID 的 warm 使用成本，不是可部署的在线 selector 成本。

### 更严格的预算补充：仅一步 target consequences

主实验完成后发现 target winners 的二步占比高于 Gold LOCAL，因此在查看这组结果前
写入单独 protocol，追加**仅从 3,561 个一步候选选择**的保守控制。不使用之前 winner，
仍是相同三个 seeds、同一搜索函数和每 seed 1,379 calls；完整三组结果全部报告。
这是补充敏感性分析，不取代主实验，也不把额外预算伪装成原来的搜索。
每个 exact-K 集合独立/联合 derivation 都恰好 K 步，比 Gold LOCAL 的平均 57/44 更低。
每个 best winner 再顺序测量 5 次。

{one_table}

它直接检查主比较是否依赖二步候选比例更高。这个 baseline 的验证成本更小，仍可
与 history 竞争；因此“便宜候选够用”的判断不限于较宽松的 <=2K 集合预算。
不据此声称所有 target 都能用一步推导替代历史。

## D. Gold64 是否明显 non-additive？

**本 target、固定 solver/config 下，是；稳定的大小阈值或跨 target 规律尚未建立。**

- 64 singleton 只有 {positive} 条改善 TEMPLATE。
- leave-one-out 删除 {sum(x>0 for x in penalties)}/64 条使 Gold64 变差；
  penalty 中位数 {median(penalties):,.0f}，最大 {max(penalties):,}。其余为零。
- singleton gains 相加为 {sum(int(r['singleton_gain']) for r in marg):,}，
  全集合实际 gain 为 {b-g:,}，加性预测明显失败。
- 随机抽 128 个 pair（不是枚举 2^64）：
  `I(i,j)=ops(i)+ops(j)-ops(∅)-ops(i,j)`，
  {sum(x>0 for x in interactions)}/128 为正，中位数 {median(interactions):,.1f}，
  范围 [{min(interactions):,}, {max(interactions):,}]。正负都有，不支持统一单调互补性。

![Subset size versus ops](results/target_local_history/comparison.png)

{progress_table}

所有 0..64 prefix 都已测量。singleton-best 并不能稳定构建好集合；leave-one-out-best
在较大集合上表现好，但排序本身读取了完整 Gold 的目标效用，是 oracle 信息泄漏式
的诊断，不是可泛化 selector。random 路径反复上下波动；部分路径到最后一条才大幅
改善。**共同终点是同一个被 oracle 选中的 Gold64，不是八次独立复制 synergy。**
旧 Gold 经过 backward/swaps 挑选，本就有局部最优选择偏差；leave-one-out 的强 penalty
不能单独证明结构性 threshold。

另外对四组固定成员用 5 个种子重排实际 injection order，所有 ops/conflicts 都与
原顺序一致（见 insertion_controls.csv）。这排除了本次五个排列下的注入顺序解释；
没有排除换 branching seed、变量编号或 target 后的 butterfly effects。
不追加跨 target 理论，不再做 proof-module clustering。

## E. 直接传播还是 trajectory shaping？

独立编译观察版，冻结原 binary 不改。TEMPLATE / Gold64 在观察版和原版的
status、ops、conflicts、decisions、propagations 及两种 minimization counters 完全一致。
只保存 histogram、Gold ID 使用计数、前 128 个 decision literals 和滚动 hash，
没有巨大 raw trajectory logs。观察版耗时不混入上面的性能表。

{trajectory_table}

Gold64 中 **{len(t['gold_reason_enqueue'])}/64** 条用作非 learned 输入 clause 的 enqueue reason，
累计 **{sum(t['gold_reason_enqueue'].values()):,}** 次；
**{len(t['gold_analysis_antecedent'])}/64** 条在 first-UIP analysis 中作为初始 conflict
或 reason antecedent 被访问，累计 **{sum(t['gold_analysis_antecedent'].values()):,}** 次。
这里按 clause 内容匹配 Gold，检查 `!learnt()`，不会把后来重学出的相同 clause 算进去。
最小化阶段的 Gold reason 访问没有单独统计；这不是全部使用量。

前 21 次 decision literal 相同，第 22 次由 TEMPLATE 的 -259 变为 Gold 的 -260。
直接 reason 使用与随后的 branching/conflict 分布变化都被观测到。
这些 clauses 是逻辑冗余但传播上有用的 shortcuts：预先可用会改变 implication graph、
first-UIP clause、活动与后续分支；数条一起改变到达的搜索状态，所以 singleton 中
未出现的使用机会可以在集合中出现。这是与数据一致的机制解释，**没有识别具体
因果链，也没有将直接传播和间接 trajectory 效果分解为百分比**。

## F. 当前定位与下一格矩阵

1. **unique knowledge：不支持。** 44/64 在 T 上极便宜，其余仅在指定二步 calculus
   下 NONLOCAL；更长历史支持不等于语义唯一性。匹配预算比较不支持稳定的历史优势。
2. **candidate prioritization：支持作为当前工作解释。** H 提供候选与出现位置，
   但真正把它们挑成 Gold 的是昂贵 same-target oracle；未证明 source ranking 自己就有效。
3. **trajectory shaping：有观测支持。** clauses 被直接使用且改变搜索序列；
   尚不能证明这种改变一定是收益的因果中介。合适定位是两者混合。
4. **下一格：unseen target × matched cheap candidate selection budget。**
   冻结 target-only 生成器与选择规则，在未用于挑 Gold 的 targets 上比较 T-only cheap、
   history-local、history-nonlocal；固定 K 并额外匹配总 derivation steps，报告在线总成本。
   先看 history 是否在这些控制后稳定胜出，再决定是否继续 historical transfer。
   只有非加性形态也跨 target 重复，才把 set synergy 提升为下一阶段对象。

当前触发停止强 history-specific claim；不把单 target 的 repeatability 说成跨实例显著性。
不进入 abstraction、clustering 或 proof-module compression。

## Artifacts / reproduction / limits

- [Protocol](docs/target-local-protocol.md), [driver](target_local_history.py),
  [trajectory builder](target_trajectory.py), [audit](audit_target_local_history.py),
  [report generator](target_local_report.py)。
- [Summary](results/target_local_history/summary.csv), [all 55 final runs](results/target_local_history/raw.jsonl),
  [selections](results/target_local_history/selections.json), [oracles](results/target_local_history/oracles.json)。
- [Classification](results/target_local_history/classification.json),
  [target-only checked proof](results/target_local_history/target_pool_proof.json),
  [audit](results/target_local_history/audit.json), [provenance](results/target_local_history/metadata.json)。
- [Singleton / leave-one-out](results/target_local_history/marginals.csv),
  [pairs](results/target_local_history/pairs.csv), [all prefixes](results/target_local_history/progressive.csv),
  [injection controls](results/target_local_history/insertion_controls.csv),
  [trajectory aggregates](results/target_local_history/trajectory.json),
  [PDF plot](results/target_local_history/comparison.pdf)。
- [一步预算控制代码](target_one_step_baseline.py),
  [全部三组一步 oracle](results/target_local_history/one_step/oracles.json),
  [15 次补充 final runs](results/target_local_history/one_step/raw.jsonl)。

运行：`.venv/bin/python target_local_history.py`；随后
`.venv/bin/python target_trajectory.py`、`.venv/bin/python audit_target_local_history.py`。
一步预算补充：`.venv/bin/python target_one_step_baseline.py`。
画图：`MPLCONFIGDIR=/private/tmp/satfinding-mplconfig PYTHONPATH=/private/tmp/satfinding-plotdeps .venv/bin/python target_local_report.py`。
19 个相关单元测试通过；全部 target 候选 proof steps 经现有 checker 验证，
所有选中输出经现有 materializer 重证。源哈希匹配冻结输入。
Completion 是 native solver 报告 UNSAT，本轮不保存/转换成千上万份完整 DRUP；
旧 Gold 的完整 completion certificate 沿用先前审计，不把此次新增运行说成逐份完整认证。
oracle 搜索缓存支持重用；final timing 会重新运行。
'''
    Path('TARGET_LOCAL_VS_HISTORY.md').write_text(text)
    (P/'report_manifest.json').write_text(json.dumps({str(f):sha(f) for f in
        [Path('target_local_report.py'),Path('target_one_step_baseline.py'),Path('target_trajectory.py'),
         Path('audit_target_local_history.py'),Path('test_target_local_history.py'),
         Path('TARGET_LOCAL_VS_HISTORY.md'),P/'summary.csv',P/'oracles.json',P/'audit.json',
         P/'one_step/oracles.json',P/'one_step/summary.csv']},indent=2))


if __name__=='__main__': main()
