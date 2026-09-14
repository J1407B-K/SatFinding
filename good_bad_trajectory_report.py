"""Render bounded early-prefix results without further solving or fitting."""
import csv
import gzip
import json
import os
from pathlib import Path
from good_bad_trajectory import OUT,BASESETS,PAIRS
from good_bad_trajectory_analyze import HORIZONS
from evaluation_oracle_run import sha
from unseen_selector import dump

def main():
    outcomes=json.loads((OUT/'outcomes.json').read_text());static=json.loads((OUT/'static.json').read_text())
    checks=json.loads((OUT/'checkpoints.json').read_text());lookup={(r['configuration'],r['n']):r for r in checks}
    scores=list(csv.DictReader((OUT/'predictor_scores.csv').open()))
    sm={(r['cohort'],int(r['N']),r['model'],r['split']):r for r in scores}
    corr=list(csv.DictReader((OUT/'all_correlations.csv').open()))
    cm={(r['cohort'],int(r['N']),r['metric']):r for r in corr}
    differences=json.loads((OUT/'pair_early_differences.json').read_text())
    audit=json.loads((OUT/'audit.json').read_text());assert audit['status']=='PASS'
    os.environ.setdefault('MPLCONFIGDIR','/private/tmp/satfinding-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    palette={'GOLD64':'tab:green','L1_L2':'tab:cyan','L1':'tab:red','L2':'tab:orange','L1_L2_L3':'tab:purple','RANDOM64_43':'tab:brown','RANKED64':'tab:blue','RANDOM64_17':'tab:pink'}
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for ax,N in zip(axs.flat,(50,100,200,500)):
        for name in outcomes:
            x=lookup[name,N]['ops'];y=outcomes[name]['total_ops'];color=palette.get(name,'gray')
            ax.scatter(x,y,color=color,s=45 if outcomes[name]['good'] else 22,marker='*' if outcomes[name]['good'] else 'o')
            if name in ('GOLD64','L1','L1_L2','RANDOM64_43'):ax.annotate(name,(x,y),xytext=(4,3),textcoords='offset points',fontsize=7)
        ax.set(title=f'First {N} conflicts',xlabel='Early cumulative analysis ops',ylabel='Existing final total ops');ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'early_vs_final.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    fields=('ops','mean_lbd','mean_dl','activity_top10_mass')
    for name in ('GOLD64','RANKED64','RANDOM64_17','RANDOM64_43'):
        for ax,field in zip(axs.flat,fields):ax.plot(HORIZONS,[lookup[name,N][field] for N in HORIZONS],'-o',label=name,color=palette[name],ms=3)
    for ax,field in zip(axs.flat,fields):ax.set(xlabel='Observed conflicts',ylabel=field,title=field);ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'good_bad_prefixes.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    styles={'L1':'-','L2':'--','L1_L2':':','L1_L2_L3':'-.'}
    for name in PAIRS:
        for ax,field in zip(axs.flat,('ops','mean_lbd','restart_count','decisions')):
            ax.plot(HORIZONS,[lookup[name,N][field] for N in HORIZONS],styles[name],label=f"{name} (final {outcomes[name]['total_ops']:,})",color=palette[name],lw=2)
    for ax,field in zip(axs.flat,('ops','mean_lbd','restart_count','decisions')):ax.set(xlabel='Observed conflicts',ylabel=field);ax.legend(fontsize=6);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'nonadditive_prefixes.png',dpi=180);plt.close(fig)
    lines=['# GOOD / BAD TRAJECTORY ANALYSIS','',
        '**结论：有早期轨迹差异，但没有发现稳定、可用的“方向”信号。前50/100 conflicts的45个标量指标可以完全相同，最终search length却相差一倍。500附近有局部信号，跨配置、跨观察窗口不稳；当前不支持立即上learned/neural predictor。**','',
        '固定原n200_T_r01_s7201、原Glucose3.0及参数。12个已有配置，先运行独立prefix进程，精确止于conflict1000；全部早期数据冻结后才join已有final labels。完整shadow运行仅核对原生counters及prefix逐项一致，未把未来指标加入特征。研究者已知这些集合的旧结局，因此这是预先固定分析的回顾性诊断，不是盲测。没有搜索新集合。','',
        '“good”固定定义为最终ops低于TEMPLATE的90%：只有Gold64和L1+L2两个；Bad64是RANDOM64_43的别名，不重复计样本。7个K64配置仅有一个good。不能把60个checkpoint或12,000个conflicts当作独立样本。','',
        '| 配置 | K | 平均width | 平均推导depth | support inferences | validation ms¹ | 最终ops（已有） |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for name in outcomes:
        s=static[name];lines.append(f"| {name}{' / Bad64' if name=='RANDOM64_43' else ''} | {s['K']} | {s['mean_width']:.2f} | {s['mean_depth']:.2f} | {s['support_inferences']} | {1000*s['validation_seconds']:.2f} | {outcomes[name]['total_ops']:,} |")
    lines+=['','¹ 当前一次warm selected-support验证，不含共同TEMPLATE/source-index加载，不作为预测特征或精确性能比较。K64匹配；width/depth/cost没有完全匹配，尤其随机集合更宽、推导更深。为保留固定成员没有重配集合。完整分布见[static.json](results/good_bad_trajectory/static.json)。','',
        '## 1. Gold与Bad/Random/Ranked最早在哪些early metrics上分叉？','',
        '**最早检查点N=50已不同。** Gold相对这三个对照的ops、dequeues和平均LBD较低，但decisions/DL并非一致更低。这个观察不能推出整个配置集合中的好坏方向。','',
        '| N=50 | ops | 实际BCP dequeues | decisions | 平均conflict DL | 平均LBD | injected reason次数 |','|---|---:|---:|---:|---:|---:|---:|']
    for name in ('GOLD64','RANKED64','RANDOM64_17','RANDOM64_43'):
        s=lookup[name,50];lines.append(f"| {name} | {s['ops']} | {s['dequeues']} | {s['decisions']} | {s['mean_dl']:.2f} | {s['mean_lbd']:.2f} | {sum(v[0] for v in s['injected_usage'].values())} |")
    lines+=['',
        '方向很快出现反例：N200时Ranked平均LBD6.62，优于Gold6.88，但最终Ranked209,416 ops而Gold130,718；N1000时Ranked的injected reason使用5,116次，远多于Gold2,966次，仍更慢。“更低LBD”或“更多直接使用”均不是跨配置可靠规则。','',
        'activity top10/spread、heap操作/移动、decision变量重叠、reason来源均已采集，详见[全部45个标量](results/good_bad_trajectory/early_features.csv)及[包含top10/来源/逐lemma使用的checkpoints](results/good_bad_trajectory/checkpoints.json)。activity按var_inc归一化；heap_moves是percolation中元素移动次数，不是概念性的“换了一个basin”。','',
        '![prefixes](results/good_bad_trajectory/good_bad_prefixes.png)','',
        '## 2. 哪些只是轨迹不同，哪些与短轨迹稳定相关？','',
        '**没有一个被检查的标量能在N50和100都把两个good与所有nongood严格分开。** activity/heap距离、reason来源变化只证明trajectory不同；当前未证明它们的变化方向等于future utility。','',
        '预先固定的四项指标与最终ops的Spearman相关如下（12配置；正值表示指标越大，最终越长）：','',
        '| N | early ops/conflict | BCP dequeues/conflict | 平均LBD | 平均DL |','|---:|---:|---:|---:|---:|']
    for N in HORIZONS:
        values=[float(cm['all12',N,m]['spearman_total']) for m in ('ops_per_conflict','dequeues_per_conflict','mean_lbd','mean_dl')]
        lines.append(f'| {N} | '+' | '.join(f'{v:+.3f}' for v in values)+' |')
    lines+=['',
        'N500的early ops相关约+0.56是一个局部信号，应保留；它在N1000降到+0.27，不能解释为随观察加深而稳定增强。对remaining ops（最终减去已观察ops）的相关也全部导出，避免把“总量包含前缀”误当预测力。45指标×5窗口的完整结果公开，没有挑出最大相关当结论，也不提供未做多重比较校正的显著性声明。','',
        '## 3. L1/L2/L1+L2非加性：早期状态有何不同？','',
        '**L1与L1+L2在N50、N100：45/45标量相同，activity top10及decision变量直方图也完全相同。** 最终L1为345,592 ops，pair为169,858。相同的是这些观测，不是完整solver状态：额外lemma的存在、watches等仍不同。','',
        '| 配置 | ops@50 | ops@100 | ops@200 | ops@500 | ops@1000 | 最终ops |','|---|---:|---:|---:|---:|---:|---:|']
    for name in PAIRS:lines.append(f"| {name} | "+' | '.join(f"{lookup[name,N]['ops']:,}" for N in HORIZONS)+f" | {outcomes[name]['total_ops']:,} |")
    lines+=['',
        'N200 pair比L1仅少1个analysis op，dequeues与decisions完全相同；N500只少5 ops，平均LBD/DL仍相同。N1000时pair早期ops反而比L1高267，但最终约少一半。加L3的前1000 ops更低（37,797 vs pair38,590），最终却更差（224,926 vs169,858）。','',
        '已有reason路径实验解释了L2可在L1造成的上下文中替代reason；本轮说明**该上下文的长期好坏，未被这些早期聚合量编码充分**。不能声称已经解释了为什么pair最终恰好更短，也不能把传播次数或早期LBD当作隐藏的“好basin坐标”。','',
        '![nonadditive](results/good_bad_trajectory/nonadditive_prefixes.png)','',
        '## 4. 前50/100/200/500 conflicts能粗略预测最终search length吗？','',
        '**目前不能稳定预测。** 固定4特征的ridge线性sanity baseline：log(1+ops/N)、log(1+实际dequeues/N)、meanLBD、meanDL；penalty1，train-only标准化，预测log final ops。未调特征、惩罚或good阈值。','',
        '| N | LOCO log-MAE↓ | held-out预测ρ | balanced accuracy | good识别 | 分组holdout log-MAE↓ | 分组预测ρ |','|---:|---:|---:|---:|---:|---:|---:|']
    for N in HORIZONS:
        a=sm['all12',N,'early4','LOCO'];b=sm['all12',N,'early4','group_holdout']
        lines.append(f"| {N} | {float(a['log_mae']):.3f} | {float(a['spearman']):+.3f} | {float(a['balanced_accuracy']):.2f} | {round(2*float(a['good_recall']))}/2 | {float(b['log_mae']):.3f} | {float(b['spearman']):+.3f} |")
    lines+=['',
        'LOCO训练均值基线log-MAE=0.214；全预测nongood已有83.3% accuracy、balanced accuracy0.5，不能把83.3%当成功。N500模型识别Gold但漏掉pair，overall rank仍接近0。组留出把4个L1/L2配置整体留出、3个random配置整体留出，其余逐个留出；N500有所改善，N1000又变差。LOCO均值基线的rankρ=−1来自“移除更大的标签就降低训练均值”的代数效应，不是反向预测证据；因此均值基线主要比较MAE。','',
        '补充结果也不能省略：','',
        '- 单一early-ops回归在N500的LOCO log-MAE=0.148、rankρ=+0.315，优于均值，但N50/100/200/1000均未稳定优于均值。',
        '- **只看7个K64配置，N200出现较好结果：4特征LOCO rankρ=+0.643、7/7分类正确。** 但只有一个positive（Gold），N50/100不成立，N500/1000又漏Gold。这是值得保留的局部观察，不是跨集合稳定预测证据。',
        '- 固定静态width/depth/support三特征LOCO log-MAE=0.242，差于均值0.214；未找到可用的简单静态基线。',
        '- 两个good、一个target、来自已知结局的固定sets，样本量不足以估计泛化误差。没有conflict-row随机split，也没有把重复采集当新样本。','',
        '![early-final](results/good_bad_trajectory/early_vs_final.png)','',
        '## 5. 当前最可信解释是什么？','',
        '**多因素反馈，其中branching-state shaping已有局部干预证据；“反馈朝好还是朝坏”仍未充分解释。** 注入clauses改变reason/propagation与conflict analysis，进而改写activity/heap、learned数据库和restart状态；这些变化相互影响后续搜索。低维前缀统计丢失了哪些具体clauses、变量与future conflicts发生交互的信息。','',
        'restart提供一个时间线而非充分解释：Gold在215发生restart；L1和pair都在756 restart，但只有坏L1在807再次restart，三元组合前1000没有restart。不能据此推断“越早/越多restart越好”：两个good的时点不同，坏run也restart。没有做restart干预，不能给它分配最终收益比例。','',
        '因此数据支持context-dependent的非加性search effect，不支持已经发现真实动力学basin、简单单调进度量，或“某类静态lemma天生把solver推好”的机制。','',
        '## 6. 是否值得下一步做learned/neural predictor？','',
        '**目前不值得直接启动神经模型训练。** 此样本没有稳定的50/100-conflict方向信号，pair反例明确，较晚窗口的局部成功又不稳定。更复杂模型容易记住configuration或唯一Gold，无法弥补positive数量和独立评估不足。','',
        '这不等于证明任何早期表示都不可能预测：本轮只否定“当前聚合runtime指标已经足够支持预测器”的判断。若以后继续，应先验证更完整的早期状态表示在严格隔离的固定配置上是否带来可重复增量信息，再决定是否训练；本轮没有启动该扩展。','',
        '## 7. 如果未来值得建模，真正应预测什么target？','',
        '应预测**给定target、具体注入集合、已观察搜索状态和固定solver后的剩余search work及其不确定性**，而非“轨迹离CONTROL多远”、activity改变量、直接使用量或不可观测的basin标签。已有完整同target对照时，可评估相对固定CONTROL的净future-work改善；要用于online决策，还必须扣除验证和早期探测成本。','',
        '本轮没有证明这个更丰富的条件目标可预测；不把它当作已获支持的下一路线。','',
        '证据：[冻结协议](docs/good-bad-trajectory-protocol.md) · [early freeze](results/good_bad_trajectory/early_frozen.json) · [逐配置/预算汇总](results/good_bad_trajectory/checkpoint_summary.csv) · [全部相关](results/good_bad_trajectory/all_correlations.csv) · [LOCO与分组预测](results/good_bad_trajectory/predictor_scores.csv) · [每个held-out预测](results/good_bad_trajectory/predictions.csv) · [pair相同/不同指标](results/good_bad_trajectory/pair_early_differences.json) · [audit](results/good_bad_trajectory/audit.json)。',
        '原生propagations计数有binary-conflict早退漏记口径，另报actual dequeues；source数组顺序为original/TEMPLATE/injected/learned，逐lemma数组为reason/BCP/analysis/minimization/conflict。早期进程返回UNKNOWN是预算停止，完整shadow为solver-reported UNSAT并匹配原结果。',
        '只读复核：`.venv/bin/python good_bad_trajectory_analyze.py`，`.venv/bin/python good_bad_trajectory_report.py`。']
    Path('GOOD_BAD_TRAJECTORY_ANALYSIS.md').write_text('\n'.join(lines)+'\n')
    dump(OUT/'report_manifest.json',dict(report_sha256=sha('GOOD_BAD_TRAJECTORY_ANALYSIS.md'),reporter_sha256=sha(__file__),
        artifacts={p.name:sha(p) for p in OUT.glob('*.png')}))
    print('DONE: seven answers, three figures, full scalar/prediction tables')

if __name__=='__main__':main()
