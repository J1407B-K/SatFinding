"""Frozen stream analysis, audit and plots; never calls solve(T)."""
import csv
import json
import math
from pathlib import Path
import random
from statistics import mean,median
from evaluation_oracle_run import sha
from unseen_selector import digest
from satcache import normalize

P=Path('results/persistent_memory_stream')


def load(name):return json.loads((P/name).read_text())
def dump(name,obj):(P/name).write_text(json.dumps(obj,indent=2)+'\n')
def csvout(name,rows):
    with (P/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(head,rows):
    return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def crossing(curve,cost):
    first=next((i+1 for i,v in enumerate(curve) if v>=cost),None)
    sustained=next((i+1 for i in range(len(curve)) if min(curve[i:])>=cost),None)
    return dict(first=first,sustained=sustained,final_margin=curve[-1]-cost,
        fell_below_after_first=first is not None and any(v<cost for v in curve[first:]))
def ci(values):
    rng=random.Random(20260911)
    med=[];avg=[]
    for _ in range(10000):
        sample=rng.choices(values,k=len(values));med.append(median(sample));avg.append(mean(sample))
    med.sort();avg.sort()
    return dict(median_95=[med[249],med[9749]],mean_95=[avg[249],avg[9749]])


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    meta=load('metadata.json');frozen=load('online_frozen.json');policy=load('measurement_policy.json')
    amendment=load('protocol_amendment.json');execution=load('execution_start.json')
    validity=load('template_validity.json')
    assert sha(P/'online_frozen.json')==meta['online_frozen_sha256']
    for path,h in meta['sources'].items():
        checked=(P/'pre_amendment_driver.py.txt' if Path(path).name=='persistent_memory_stream.py' else
                 P/'pre_amendment_protocol.md' if Path(path).name=='persistent-memory-stream-protocol.md' else Path(path))
        assert sha(checked)==h,path
    for path,h in (meta['frozen_sources']|amendment['amended_sources']|amendment['originals']).items():assert sha(path)==h,path
    assert execution['protocol_amendment_sha256']==sha(P/'protocol_amendment.json')
    assert execution['template_validity_sha256']==sha(P/'template_validity.json')
    assert amendment['recorded_utc']<execution['utc']
    raw=[json.loads(l) for l in (P/'raw.jsonl').read_text().splitlines()]
    assert len(raw)==750
    lookup={};rows=[];failures=[]
    for i,(target,fr) in enumerate(frozen.items(),1):
        instance=load(f'{target}/target.json')
        assert digest(normalize(instance['cnf']))==fr['cnf_sha256']
        for route in ['TEMPLATE','TARGET','HISTORY']:
            rr=[r for r in raw if r['target']==target and r['route']==route]
            assert len(rr)==5 and {r['repeat'] for r in rr}==set(range(5))
            completed=[r for r in rr if r['status']=='UNSAT']
            bad=[r for r in rr if r['status']!='UNSAT']
            failures.extend(bad)
            assert len(completed)>=3
            assert all(r['error']=="RuntimeError('Fixed selection wall cap exceeded')" for r in bad)
            assert len({(r['input_sha256'],r['analysis_resolution_steps'],r['conflicts']) for r in completed})==1
            assert all(all(r[k]==v for k,v in validity[target].items()) for r in completed)
            if route!='TEMPLATE':
                assert all(r['selected_ids']==fr['online'][route] and r['candidates_examined']==512 and r['validation_steps']==64 and r['feature_evaluations']==512 and r['sorts']==1 for r in completed)
                assert all(r['resolver_attempts']==fr['generation']['resolver_attempts'] and r['outputs_sha256']==fr['generation']['outputs_sha256'] for r in completed)
            row=dict(query=i,target=target,seed=fr['seed'],route=route,repetitions=5,completed=len(completed),budget_failures=len(bad))
            for k in ['analysis_resolution_steps','conflicts','solver_seconds','total_seconds','generation_seconds','selection_seconds','validation_seconds']:
                if k in ['analysis_resolution_steps','conflicts','solver_seconds','total_seconds']:
                    row[k]=median(r[k] if r['status']=='UNSAT' else math.inf for r in rr)
                else:row[k]=median(r.get(k,0) for r in completed)
            row.update(total_min=min(r['total_seconds'] for r in completed),total_max=max(r['total_seconds'] for r in completed),
                successful_only_total_median=median(r['total_seconds'] for r in completed),template_outputs=completed[0]['template_outputs'],
                template_valid_count=validity[target]['template_valid_count'],
                invalid_template_ids=json.dumps(validity[target]['invalid_template_ids']),
                valid_template_hash=validity[target]['valid_template_hash'])
            lookup[target,route]=row;rows.append(row)
    csvout('summary.csv',rows)
    assert failures==load('analysis_failure_policy.json')['failures']
    assert sha(P/'raw.jsonl')==load('analysis_failure_policy.json')['raw_sha256']
    comparisons=[];curve=[];cumulative=0
    for i,target in enumerate(frozen,1):
        a,b=lookup[target,'TARGET'],lookup[target,'HISTORY']
        saving=a['total_seconds']-b['total_seconds'];cumulative+=saving;curve.append(cumulative)
        comparisons.append(dict(query=i,target=target,seed=frozen[target]['seed'],target_ops=a['analysis_resolution_steps'],history_ops=b['analysis_resolution_steps'],
            ops_ratio=b['analysis_resolution_steps']/a['analysis_resolution_steps'],ops_improvement=1-b['analysis_resolution_steps']/a['analysis_resolution_steps'],
            target_total=a['total_seconds'],history_total=b['total_seconds'],time_improvement=1-b['total_seconds']/a['total_seconds'],
            saving_seconds=saving,cumulative_saving_seconds=cumulative,template_outputs=a['template_outputs'],**validity[target]))
    csvout('per_query.csv',comparisons)
    ops=[r['ops_improvement'] for r in comparisons];tim=[r['time_improvement'] for r in comparisons];save=[r['saving_seconds'] for r in comparisons]
    blocks=[sum(save[i:i+10]) for i in range(0,50,10)]
    positive=sorted([v for v in save if v>0],reverse=True)
    negative=sorted([-v for v in save if v<0],reverse=True)
    gross=sum(positive);loss=sum(v for v in save if v<0)
    repeat_curves=[];failed_repetitions=[]
    for rep in range(5):
        current=0;seq=[]
        for target in frozen:
            a=next(r for r in raw if r['target']==target and r['route']=='TARGET' and r['repeat']==rep)
            b=next(r for r in raw if r['target']==target and r['route']=='HISTORY' and r['repeat']==rep)
            if a['status']!='UNSAT' or b['status']!='UNSAT':
                failed_repetitions.append(rep);seq=[];break
            current+=a['total_seconds']-b['total_seconds'];seq.append(current)
        if seq:repeat_curves.append(seq)
    wins=sum(v>0 for v in ops);ties=sum(v==0 for v in ops);time_wins=sum(v>0 for v in tim)
    alive=wins>25 and median(ops)>0 and median(tim)>0 and cumulative>=.82
    stop=(median(ops)<=0 and median(tim)<=0) or (cumulative<=0 and sum(v<=0 for v in blocks)>=3)
    verdict='ALIVE' if alive else 'STOP' if stop else 'WEAK'
    metrics=dict(queries=50,ops_win_tie_loss=[wins,ties,50-wins-ties],ops_win_rate=wins/50,
        time_win_tie_loss=[time_wins,sum(v==0 for v in tim),sum(v<0 for v in tim)],
        median_ops_improvement=median(ops),mean_ops_improvement=mean(ops),median_time_improvement=median(tim),mean_time_improvement=mean(tim),
        ops_bootstrap=ci(ops),time_bootstrap=ci(tim),cumulative_saving_seconds=cumulative,
        load=crossing(curve,.82),build=crossing(curve,3.87),
        exact_load=crossing(curve,meta['frozen_prior_load_seconds']),exact_build=crossing(curve,meta['frozen_prior_build_seconds']),
        gross_positive_saving=gross,negative_saving=loss,block10_savings=blocks,
        top_gains={str(k):dict(seconds=sum(positive[:k]),share_of_gross=sum(positive[:k])/gross if gross else 0,
            share_of_net=sum(positive[:k])/cumulative if cumulative>0 else None,remaining_net=cumulative-sum(positive[:k])) for k in [1,5,10]},
        mean_winning_saving=mean(positive) if positive else 0,mean_losing_cost=mean(negative) if negative else 0,
        top_loss_shares={str(k):sum(negative[:k])/sum(negative) if negative else 0 for k in [1,5,10]},
        repetition_final_savings=[c[-1] for c in repeat_curves],
        repetition_load_first_crossings=[crossing(c,.82)['first'] for c in repeat_curves],
        max_cumulative=max(curve),min_cumulative=min(curve),final_verdict=verdict,
        amortized_build_pass=alive and cumulative>=3.87,
        budget_failures=len(failures),completed_runs=len(raw)-len(failures),failed_repetition_indices=failed_repetitions,
        successful_only_cumulative_saving_seconds=sum(lookup[t,'TARGET']['successful_only_total_median']-lookup[t,'HISTORY']['successful_only_total_median'] for t in frozen),
        total_target_seconds=sum(r['target_total'] for r in comparisons),total_history_seconds=sum(r['history_total'] for r in comparisons))
    dump('metrics.json',metrics)
    fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True)
    x=list(range(1,51));ratios=[r['ops_ratio'] for r in comparisons]
    axes[0].plot(x,ratios,color='slategray',lw=.8)
    axes[0].scatter(x,ratios,c=['tab:green' if r<1 else 'tab:red' if r>1 else 'gray' for r in ratios],s=22)
    axes[0].axhline(1,color='black',ls='--',lw=1)
    axes[0].set(ylabel='HISTORY / TARGET search ops',title='Frozen historical prior: all 50 unseen queries')
    for seq in repeat_curves:axes[1].plot(x,seq,color='tab:blue',alpha=.15,lw=.8)
    axes[1].plot([0]+x,[0]+curve,color='tab:blue',label='Cumulative saving (per-query median totals)')
    axes[1].axhline(0,color='gray',lw=.8)
    axes[1].axhline(.82,color='tab:orange',ls='--',label='Frozen load cost: 0.82 s')
    axes[1].axhline(3.87,color='tab:red',ls='--',label='Frozen build cost: 3.87 s')
    axes[1].set(xlabel='Query index (T5 through T54, frozen seed order)',ylabel='Cumulative warm saving (s)',xlim=(0,50))
    axes[1].legend(fontsize=8)
    zoom=axes[1].inset_axes([.08,.35,.52,.55])
    for seq in repeat_curves:zoom.plot(x,seq,color='tab:blue',alpha=.15,lw=.7)
    zoom.plot([0]+x,[0]+curve,color='tab:blue',lw=1.2)
    zoom.axhline(0,color='gray',lw=.7)
    zoom.set(title='Zoom: cumulative warm saving',xlim=(0,50),ylabel='Seconds')
    zoom.tick_params(labelsize=7);zoom.title.set_fontsize(8);zoom.yaxis.label.set_size(7)
    fig.tight_layout();fig.savefig(P/'stream.png',dpi=180);fig.savefig(P/'stream.pdf');plt.close(fig)
    citable=lambda v:'未跨过' if v is None else f'第 {v} 个 query（T{v+4}）'
    numbertable=table(['指标','结果'],[
        ['Ops 胜 / 平 / 负',f'{wins} / {ties} / {50-wins-ties}'],['Ops 胜率',f'{wins/50:.1%}'],
        ['Median ops improvement',f'{median(ops):+.2%}'],['Mean ops improvement',f'{mean(ops):+.2%}'],
        ['Warm total 胜 / 平 / 负',str(metrics['time_win_tie_loss'])],['Median warm total improvement',f'{median(tim):+.2%}'],['Mean warm total improvement',f'{mean(tim):+.2%}'],
        ['50-query TARGET / HISTORY warm total',f"{metrics['total_target_seconds']:.3f}s / {metrics['total_history_seconds']:.3f}s"],['Cumulative saving(50)',f'{cumulative:+.4f}s']])
    prior_note='Baseline：**frozen TEMPLATE-67 source set with per-target soundness filtering**。用户确认后，对全部50个target统一过滤原67条中失效的TEMPLATE；三路线共享同一有效子集。原候选生成仍排除原67条，prior、候选池、两条选择结果与冻结版完全一致。'
    concentration=table(['最大的正节省','占全部正节省','删除这些 winner 后净节省（诊断）'],[
        [k,f"{metrics['top_gains'][str(k)]['share_of_gross']:.2%}",f"{metrics['top_gains'][str(k)]['remaining_net']:+.4f}s"] for k in [1,5,10]])
    biggest=sorted(comparisons,key=lambda r:r['saving_seconds'],reverse=True)
    dump('largest_gains.json',biggest[:10])
    action=('下一步最小实验：保持相同 prior/selector/预算，另冻结一条不重叠的50-query同家族流，独立复制胜率、中位数及load回本；不训练或调参。' if verdict=='ALIVE' else
            '明确停止当前冻结 selector/prior 路线；不换特征、挑 seeds、加 Oracle 或重组模块挽救结论。' if verdict=='STOP' else
            '本轮未达到ALIVE；保留WEAK，不启动selector调参或Oracle优化。本次流本身不能支持可摊销的长期价值。')
    report=f'''# Persistent memory stream results

**判定：{verdict}。** {'AMORTIZED_BUILD_PASS。' if metrics['amortized_build_pass'] else ''}
50个query最终累计节省 {cumulative:+.4f}s，load/build均未回本。

## 1–3. 50个 unseen targets 中 History 赢多少？ops 与 warm total 是否改善？

{numbertable}

改善定义为 `1 - HISTORY/TARGET`，正数表示 History 更好。mean 是50个逐target改善率的
算术平均，不是比值的比值；warm累计则是绝对秒数之和。每个 target/route 取5次中位数。
750次测量尝试全部保留，749次完成、1次在solver启动前触发原selection wall cap。
失败为T44/HISTORY/repeat3（第4次复测），实际失败前耗时61.31ms；没有重试或替换。
主统计把未完成尝试的completion ops/conflicts/time评分设为正无穷，再取5次中位数。
这是一项失败惩罚，**不是声称测得无穷耗时**；T44/HISTORY另4次有完整结果，因此5次
保守中位数仍有限。成功尝试单独计算时，累计节省为
{metrics['successful_only_cumulative_saving_seconds']:+.4f}s，供敏感性核对，不替代主结果。
三路线为 TEMPLATE、TARGET、HISTORY，无 Oracle。不能声称所有预算guard都通过；
预算失败率为1/750（HISTORY为1/250），原cap及失败记录均未修改。

Median ops bootstrap95%区间：[{metrics['ops_bootstrap']['median_95'][0]:+.2%}, {metrics['ops_bootstrap']['median_95'][1]:+.2%}]；
median warm total：[ {metrics['time_bootstrap']['median_95'][0]:+.2%}, {metrics['time_bootstrap']['median_95'][1]:+.2%} ]。
固定seed重采样10000次，按target成对抽样；它不把同源图变成独立benchmark家族，也不
把5次相同deterministic counters当成250个独立样本。
两个median区间均跨0，不能把点估计略正说成稳定正收益。

协议与完整性：T5–T54固定seeds9205–9254，沿用H6202、n200、6-regular、3-coloring、1% drift。
50个输入与T1–T4及旧同家族输入不重复。所有候选和在线输出在任何completion前冻结；
原selector源码、prior内容及native binary哈希均匹配上一轮。K64、512候选、原生成和
选择预算保持，五次复测全局固定随机打乱、单进程顺序运行。

**TEMPLATE适用性说明：** {prior_note}
严格原TEMPLATE预检查有10个target缺前提，记录保留于template_preflight.json。
这不是按性能筛除query；全部50个seeds照跑，未补齐TEMPLATE、未重新选K。
40个target保留67条，另10个保留60–66条。本文结论限定在这一获准的soundness处理规则下。
Amendment在 {amendment['recorded_utc']} UTC 记录；执行阶段在 {execution['utc']} UTC 启动。
二者通过[amendment哈希记录](results/persistent_memory_stream/protocol_amendment.json)及
[执行记录](results/persistent_memory_stream/execution_start.json)关联。原协议和driver版本另行保留，
未覆盖准备阶段的provenance。每个target的三个必需字段见
[template_validity.json](results/persistent_memory_stream/template_validity.json)和每次raw测量。

## 4. Cumulative saving 曲线是什么形状？

![History ratio and cumulative saving](results/persistent_memory_stream/stream.png)

流顺序严格为预先固定seed顺序；测量作业的随机顺序不用于重排累计曲线。
累计为 `Σ(median TARGET_total - median HISTORY_total)`，不重复扣一次性prior费用。
终值 **{cumulative:+.4f}s**，前缀范围 [{min(curve):+.4f}, {max(curve):+.4f}]s。
曲线反复上升和回吐，后段转负，未形成持续增长；内嵌放大图显示小幅变化，外图保留两条成本线。
每10query区段净节省依次为：{', '.join(f'{v:+.4f}s' for v in blocks)}。
细淡线为4个全部完成的复测编号各自的累计，不是额外求解；repeat3因含未完成query
无法形成有限的完整累计线，明确不绘制该线，失败仍在主统计中按上述规则惩罚。其余终值为
{', '.join(f'{v:+.4f}s' for v in metrics['repetition_final_savings'])}。

## 5–6. Prior load / build 第几个query回本？

- 0.82s load：**{citable(metrics['load']['first'])}**；从此一直保持回本的起点：{citable(metrics['load']['sustained'])}。
  第50题净余量 {metrics['load']['final_margin']:+.4f}s；首次越线后是否跌回：{metrics['load']['fell_below_after_first']}。
- 3.87s build：**{citable(metrics['build']['first'])}**；持续回本起点：{citable(metrics['build']['sustained'])}。
  第50题净余量 {metrics['build']['final_margin']:+.4f}s；首次越线后是否跌回：{metrics['build']['fell_below_after_first']}。

用上一轮未四舍五入成本0.822510125s / 3.870796375s，首次越线分别为
{citable(metrics['exact_load']['first'])} / {citable(metrics['exact_build']['first'])}。
本次无损gzip prior加载+校验+解析计 {meta['current_archive_load_seconds']:.3f}s，另记，
不替换用户冻结的成本线，也不把一次加载费用重复摊到每个query。
固定TEMPLATE/目标输入已在内存；warm总时间包含候选生成、选择/检索、验证、solver进程
及临时输入I/O。历史proof生产仍是已有历史的sunk cost，未重新生成prior。

## 7. 收益是否由少数outlier主导？

所有正节省合计 {gross:.4f}s，所有负节省合计 {loss:.4f}s，净值 {cumulative:+.4f}s。

{concentration}

最大正节省来自 {biggest[0]['target']}：{biggest[0]['saving_seconds']:+.4f}s。
正收益分布在27题，最大单题只占正节省的{metrics['top_gains']['1']['share_of_gross']:.2%}，
最大5题占{metrics['top_gains']['5']['share_of_gross']:.2%}。这里并不存在“少量巨大winner撑起
正均值”：均值和净值本身就是负的。赢题平均省{metrics['mean_winning_saving']*1000:.2f}ms，
输题平均多花{metrics['mean_losing_cost']*1000:.2f}ms，较大的损失抵消了略多的胜局。
最大5个loss占全部负耗时的{metrics['top_loss_shares']['5']:.2%}；完整数据保留这些不利样本。
这只是敏感性分析，正式指标没有删除任何样本。每条ratio、绝对节省和累计值均在per_query.csv。

## 8–10. 最终判定与后续

**{verdict}**。ALIVE的四个门槛（ops多数胜、median ops正、median warm正、最终覆盖load）
分别为：{wins>25} / {median(ops)>0} / {median(tim)>0} / {cumulative>=.82}。
Build摊销为额外标记，不用mean收益替代median，也不用某次短暂越线替代最终回本。
判定规则在任何completion前写入协议，未根据结果降低。
STOP触发的是“累计无法形成持续增长”：终值≤0，且5个十题区段中3个净节省非正；
同时mean ops和mean warm改善率为负。不是仅因50题尚未覆盖load而将正aggregate误判STOP。

{action}

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
'''
    Path('PERSISTENT_MEMORY_STREAM_RESULTS.md').write_text(report)
    dump('report_manifest.json',{str(p):sha(p) for p in [Path(__file__),Path('audit_persistent_memory_stream.py'),Path('PERSISTENT_MEMORY_STREAM_RESULTS.md'),P/'raw.jsonl',P/'metadata.json',P/'metrics.json',P/'online_frozen.json',P/'measurement_policy.json',P/'protocol_amendment.json',P/'template_validity.json',P/'execution_start.json',P/'analysis_failure_policy.json',P/'audit.json']})
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
