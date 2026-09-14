"""Read-only audit and report of the frozen generation experiment; no solves."""
from collections import defaultdict
import csv
import gzip
import json
from pathlib import Path
from statistics import median

from history_guided_generation import OUT, BUDGETS, ROUTES, generate
from evaluation_oracle_run import sha
from round4_core import decode
from replay_budget import HistoryIndex
from satcache import normalize
from unseen_selector import digest, dump, select


def main():
    meta=json.loads((OUT/'amendment.json').read_text())
    for path,h in meta['sources'].items():assert sha(Path(path))==h,path
    assert sha(OUT/'targets.json')==meta['targets_sha256']
    online=json.loads((OUT/'online_manifest.json').read_text())
    assert sha(OUT/'online_frozen.json.gz')==online['sha256']
    with gzip.open(OUT/'online_frozen.json.gz','rt') as f:frozen=json.load(f)
    instances=json.loads((OUT/'targets.json').read_text())
    hints=[(tuple(a),tuple(b),p) for a,b,p in json.loads((OUT/'hints.json').read_text())]
    for name,obj in instances.items():
        obj['cnf']=normalize(obj['cnf']);assert digest(obj['cnf'])==meta['cnf_hashes'][name]
    for k,v in frozen.items():
        name,b,route=k.split('/');obj=instances[name]
        assert v['generation']['pair_universe_sha256']==frozen[f'{name}/{b}/TARGET-GEN']['generation']['pair_universe_sha256']
        idx,pop,g=generate(obj,[],int(b),hints if route=='HISTORY-GEN' else None)
        assert g['pool_sha256']==v['generation']['pool_sha256']
        assert g['schedule_sha256']==v['generation']['schedule_sha256']
        ids,_=select(obj,idx,pop);ids.sort(key=lambda i:idx.clauses[i])
        _,clauses,stats=idx.materialize(obj['cnf'],ids)
        assert [list(c) for c in clauses]==v['selected_clauses']
        assert stats['support_inferences']==len(ids)==min(64,len(pop))
        assert digest(v['proof'])==digest(__import__('dataclasses').asdict(idx.history))
    raw=[json.loads(x) for x in (OUT/'raw.jsonl').read_text().splitlines()]
    assert len(raw)==600
    groups=defaultdict(list)
    for r in raw:
        assert r['status']=='UNSAT' and r['resolver_attempts']==r['budget']
        assert r['generation_seconds']<=.1 and r['selection_seconds']<=.05
        assert r['selected_K']==r['validation_steps'] and r['template_steps']==0
        f=frozen[f"{r['target']}/{r['budget']}/{r['route']}"]
        assert r['pool_sha256']==f['generation']['pool_sha256']
        groups[r['target'],r['budget'],r['route']].append(r)
    metrics=('unique_candidates_generated','candidates_retained','selected_K','generation_seconds',
        'retrieval_seconds','selection_seconds','validation_seconds','conflicts',
        'analysis_resolution_steps','solver_seconds','screen_process_seconds','total_warm_seconds')
    cells=[];lookup={}
    for (t,b,r),rr in sorted(groups.items()):
        assert sorted(x['repeat'] for x in rr)==[0,1,2]
        for field in ('analysis_resolution_steps','conflicts','input_sha256'):
            assert len({x[field] for x in rr})==1,(t,b,r,field)
        row=dict(target=t,budget=b,route=r,**{m:median(x[m] for x in rr) for m in metrics})
        cells.append(row);lookup[t,b,r]=row
    with (OUT/'per_target.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(cells[0]));w.writeheader();w.writerows(cells)
    summary=[];ratios={}
    cost=json.loads((OUT/'history_cost.json').read_text())
    overhead=cost['build_seconds']+cost['load_seconds']
    for b in BUDGETS:
        aa=[lookup[t,b,ROUTES[0]] for t in instances]
        hh=[lookup[t,b,ROUTES[1]] for t in instances]
        op=[h['analysis_resolution_steps']/a['analysis_resolution_steps'] for a,h in zip(aa,hh)]
        tm=[h['total_warm_seconds']/a['total_warm_seconds'] for a,h in zip(aa,hh)]
        ratios[b]=op
        a_time=sum(a['total_warm_seconds'] for a in aa);h_time=sum(h['total_warm_seconds'] for h in hh)
        summary.append(dict(budget=b,median_ops_ratio=median(op),
            ops_wins=sum(x<1 for x in op),ops_wins_10pct=sum(x<=.9 for x in op),
            warm_wins_5pct=sum(x<=.95 for x in tm),median_warm_ratio=median(tm),
            aggregate_warm_ratio=h_time/a_time,amortized_ratio=(h_time+overhead)/a_time,
            target_ops=median(a['analysis_resolution_steps'] for a in aa),
            history_ops=median(h['analysis_resolution_steps'] for h in hh),
            target_candidates=median(a['candidates_retained'] for a in aa),
            history_candidates=median(h['candidates_retained'] for h in hh),
            target_k=median(a['selected_K'] for a in aa),history_k=median(h['selected_K'] for h in hh),
            target_warm_ms=1000*a_time/20,history_warm_ms=1000*h_time/20,
            target_generation_ms=1000*median(a['generation_seconds'] for a in aa),
            history_generation_ms=1000*median(h['generation_seconds'] for h in hh),
            history_retrieval_ms=1000*median(h['retrieval_seconds'] for h in hh)))
    gates=all(s['ops_wins_10pct']>=16 and s['warm_wins_5pct']>=16 and
        s['median_ops_ratio']<=.9 and s['aggregate_warm_ratio']<=.95 for s in summary[:2])
    verdict=('ALIVE' if all(s['amortized_ratio']<1 for s in summary[:2]) else 'WEAK') if gates else 'STOP'
    dump(OUT/'summary.json',dict(verdict=verdict,budgets=summary,history_cost=cost))
    dump(OUT/'audit.json',dict(status='PASS',raw_runs=600,targets=20,cells=200,
        source_hashes_checked=True,all_candidate_pools_regenerated=True,
        all_selected_proofs_checked=True,shared_pair_universe=True,
        solver_counters_deterministic=True,completion='solver-reported UNSAT'))
    import os
    os.environ.setdefault('MPLCONFIGDIR','/private/tmp/satfinding-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for route,color in zip(ROUTES,('tab:blue','tab:orange')):
        for t in instances:
            axs[0].plot(BUDGETS,[lookup[t,b,route]['analysis_resolution_steps'] for b in BUDGETS],color=color,alpha=.12,lw=.7)
        axs[0].plot(BUDGETS,[median(lookup[t,b,route]['analysis_resolution_steps'] for t in instances) for b in BUDGETS],'-o',color=color,label=route)
    axs[0].set(xlabel='Resolver attempts',ylabel='Final search ops',title='20 frozen targets; bold = median')
    axs[0].legend()
    for j,t in enumerate(instances):axs[1].plot(BUDGETS,[ratios[b][j] for b in BUDGETS],color='gray',alpha=.25,lw=.8)
    axs[1].plot(BUDGETS,[s['median_ops_ratio'] for s in summary],'-o',label='Median paired ops ratio')
    axs[1].plot(BUDGETS,[s['aggregate_warm_ratio'] for s in summary],'-s',label='Aggregate warm time ratio')
    axs[1].axhline(1,color='black',ls='--',lw=1)
    axs[1].set(xlabel='Generation budget (attempts)',ylabel='HISTORY / TARGET (lower is better)',title='Gap across discovery budgets')
    axs[1].legend(fontsize=8)
    for ax in axs:ax.set_xscale('log',base=2);ax.set_xticks(BUDGETS,labels=BUDGETS);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'discovery_curves.png',dpi=180);fig.savefig(OUT/'discovery_curves.svg');plt.close(fig)
    lines=['# HISTORY GUIDED GENERATION RESULTS','',f'**判定：{verdict}。** 20 个冻结的新同家族 targets × 5 档预算 × 2 路线 × 3 次顺序重复，共600次求解；无调参、无 Oracle。','',
        '1. **相同 resolver budget 下谁的 candidates 更有用？** 见下表。ops 比值为逐 target H/T 的中位数；小于1表示 History 更好。两路仅探索顺序不同，后续使用原有 target rank。K 上限64，池不足时取全部。','',
        '| attempts | 候选数 T/H（中位） | K T/H（中位） | ops H/T | H胜 /20 | ≥10%胜 /20 |',
        '|---:|---:|---:|---:|---:|---:|']
    for s in summary:lines.append(f"| {s['budget']} | {s['target_candidates']:g}/{s['history_candidates']:g} | {s['target_k']:g}/{s['history_k']:g} | {s['median_ops_ratio']:.3f} | {s['ops_wins']} | {s['ops_wins_10pct']} |")
    best=min(summary,key=lambda s:s['median_ops_ratio'])
    lines+=['',f"2. **History 是否在小 budget 优势最大？** 最低中位 ops 比值出现在 {best['budget']} attempts（{best['median_ops_ratio']:.3f}）；64/128 分别为 {summary[0]['median_ops_ratio']:.3f}/{summary[1]['median_ops_ratio']:.3f}。不据单一最优预算调参。512候选上限使1024档仍保留前512个，因此512→1024的ops平台是协议所致，不是自然收敛证据。",'',
        f"3. **优势是否跨 unseen targets 稳定？** 64/128 档达到≥10% ops改善的分别为 {summary[0]['ops_wins_10pct']}/20、{summary[1]['ops_wins_10pct']}/20；预注册要求两档均≥16/20。20个 targets 共享一个历史源，不能当作20个独立家族。",'',
        '![预算与 search ops / 路线差距](results/history_guided_generation/discovery_curves.png)','',
        '4. **加上 retrieval/generation 成本后是否值得？** warm 已计入逐次 history lookup、全部调度与生成、排序、验证、solver进程及I/O。下表warm时间是20个 target各自3次中位数的均值，generation/retrieval则取跨target中位数；摊销把一次H索引构建+加载完整分摊给20个 targets，未按预算或重复次数稀释。','',
        '| attempts | generation T/H ms | H retrieval ms（已含） | warm T/H ms | warm H/T | 摊销后 H/T | ≥5% warm胜 /20 |',
        '|---:|---:|---:|---:|---:|---:|---:|']
    for s in summary:lines.append(f"| {s['budget']} | {s['target_generation_ms']:.2f}/{s['history_generation_ms']:.2f} | {s['history_retrieval_ms']:.2f} | {s['target_warm_ms']:.2f}/{s['history_warm_ms']:.2f} | {s['aggregate_warm_ratio']:.3f} | {s['amortized_ratio']:.3f} | {s['warm_wins_5pct']} |")
    lines+=['',f"H索引构建 {cost['build_seconds']:.3f}s，加载 {cost['load_seconds']:.4f}s；{cost['hint_pairs']} 条原始parent-pair hints。旧H证明本身为既有成本。",'',
        f'5. **判定：{verdict}。** '+('本轮未通过预注册的跨target稳定小预算净收益门槛；停止这版 history-guided discovery，不调整history score救结果。结论限定于已冻结的一步parent-pair baseline。' if verdict=='STOP' else '按预注册门槛判定，详见逐target记录与协议。'),'',
        '先例 gate：已有 [Prover9 hints](https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/hints.html) / [Prooftrans](https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/prooftrans.html) 从相关问题的证明引导后续推导。本轮是其受限parent-pair baseline，不是Prover9复现或新机制声明。','',
        '求解前合法性修订：固定旧TEMPLATE在新target上缺前提，因此保留全部seeds、两路统一去掉TEMPLATE；当时尚无新target求解。原冻结和修订哈希均保留。新颖性审计限于仓库可用记录。候选短证明已重验，completion仅solver-reported UNSAT。计时未做机器隔离（本轮同时准备绘图库），小幅wall差距不作强证据；STOP同时由确定性ops的跨target不稳定支持。','',
        '证据：[协议](docs/history-guided-generation-protocol.md) · [冻结身份](results/history_guided_generation/frozen.json) · [求解前修订](results/history_guided_generation/amendment.json) · [在线冻结](results/history_guided_generation/online_manifest.json) · [逐target全部指标](results/history_guided_generation/per_target.csv) · [600条原始测量](results/history_guided_generation/raw.jsonl) · [审计](results/history_guided_generation/audit.json)。',
        '复核（不求解）：`.venv/bin/python history_guided_generation_report.py`。']
    Path('HISTORY_GUIDED_GENERATION_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(verdict=verdict,summary=summary),indent=2))


if __name__=='__main__':main()
