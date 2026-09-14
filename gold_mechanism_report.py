"""Generate the requested compact mechanism report and four figures."""
import csv
import json
import os
from pathlib import Path
from statistics import mean
from difflib import SequenceMatcher
from gold_mechanism_analyze import load,clause,paths,simple,divergent,check_graph
from gold_mechanism_run import OUT
from evaluation_oracle_run import sha
from unseen_selector import dump

def rolling(rows,field,n=100):
    return ([rows[i]['c'] for i in range(0,len(rows),n)],
            [mean(r[field] for r in rows[i:i+n]) for i in range(0,len(rows),n)])

def ctext(c):return '('+' ∨ '.join(('¬'+str(-v) if v<0 else str(v)) for v in c)+')'

def main():
    meta=json.loads((OUT/'frozen.json').read_text())
    for p,h in meta['sources'].items():assert sha(p)==h,p
    assert sha(OUT/'inputs.json')==meta['inputs_sha256']
    assert sha('/private/tmp/satfinding-native-cdcl/counted')==meta['build']['baseline_binary_sha256']
    runs=[]
    for f in ('runs.json','window_runs.json','followup_runs.json'):runs+=json.loads((OUT/f).read_text())
    rr={r['name']:r for r in runs}
    for r in runs:
        assert sha(OUT/(r['name']+'.trace.jsonl.gz'))==r['trace_sha256']
        assert {k:v for k,v in r['stats'].items() if k!='seconds'}=={k:v for k,v in r['trace_stats'].items() if k!='seconds'}
    A,B=load('CONTROL'),load('TREATMENT')
    catalogs=[{(q['label'],tuple(q['clause'])):q for q in g['Q']} for g in (A,B)]
    activation=[]
    for key in sorted(set(catalogs[0])|set(catalogs[1])):
        row=dict(label=key[0],clause=list(key[1]))
        for name,catalog in zip(('CONTROL','TREATMENT'),catalogs):
            q=catalog.get(key,{})
            for field in ('first_reason','first_analysis','first_conflict'):
                row[name+'_'+field]=q.get(field,-1)
        activation.append(row)
    with (OUT/'clause_activation.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(activation[0]));w.writeheader();w.writerows(activation)
    diff=json.loads((OUT/'divergence.json').read_text())
    usage=json.loads((OUT/'lemma_usage.json').read_text())
    state=json.loads((OUT/'state_summary.json').read_text())
    cases=json.loads((OUT/'case_studies.json').read_text())
    extended={}
    for name in ('WINDOW_L1','WINDOW_L1_L2','FOLLOWUP_L1','FOLLOWUP_L1_L2'):
        g=load(name);check_graph(g);records=[]
        for s in g['S']:
            local=dict(g);local['events']={r['e']:dict(r,t='E') for r in s['nodes']}
            local['E']=list(local['events'].values());local['C']=[];check_graph(local)
            cc=g['C'][s['c']-1]
            cc=dict(cc,deps=[next(r['e'] for r in s['nodes'] if r['lit']==-v) for v in clause(g,cc['r'])])
            targets=[cc]
            if s['c']==199:targets+=[dict(r,t='E') for r in s['nodes'] if r['lit'] in (565,-427)]
            for event in targets:
                pp=paths(local,event)
                records.append(dict(conflict_index=s['c'],event=simple(g,event),
                    paths=[dict(gold=k,nodes=[simple(local,local['events'][i]) for i in p]) for k,p in pp.items()]))
        extended[name]=records
    dump(OUT/'pair_path_cases.json',extended)
    PA,PB=load('WINDOW_L1'),load('WINDOW_L1_L2')
    pd=dict(decision=divergent(PA,PB,'D',lambda g,r:r['lit']),
        conflict=divergent(PA,PB,'C',lambda g,r:clause(g,r['r'])),
        learned=divergent(PA,PB,'L',lambda g,r:clause(g,r['r'])))
    dump(OUT/'pair_divergence.json',pd)
    blocks=[]
    for lo in range(1,max(len(A['C']),len(B['C']))+1,100):
        row=dict(start=lo,end=lo+99)
        for name,g in [('C',A),('T',B)]:
            ds=[r for r in g['D'] if lo-1<=r['c']<lo+99]
            ls=[r for r in g['L'] if lo<=r['c']<=lo+99]
            row[name+'_decision_vars']=sorted({abs(r['lit']) for r in ds})
            for field in ('width','lbd','dl'):
                row[name+'_'+field]=mean(r[field] for r in ls) if ls else None
        x,y=set(row['C_decision_vars']),set(row['T_decision_vars'])
        row['decision_variable_jaccard']=len(x&y)/len(x|y) if x and y else None
        blocks.append(row)
    dump(OUT/'search_state_blocks.json',blocks)
    activity=[]
    for a,b in zip(A['L'],B['L']):
        if 'top' in a and 'top' in b:
            x,y={v for v,w in a['top']},{v for v,w in b['top']}
            activity.append(dict(conflict=a['c'],jaccard=len(x&y)/len(x|y)))
    dump(OUT/'activity_overlap.json',activity)
    os.environ.setdefault('MPLCONFIGDIR','/private/tmp/satfinding-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(13,4.5))
    labels=['Reason changes: same lit159','BCP literal order changes','Same conflict, different trail','First different conflict clause','Decision22 changes','First different learned clause']
    xs=[0,0,1,3,3,4]
    axs[0].plot(xs,list(range(6)),'o-',color='tab:orange')
    for i,(x,l) in enumerate(zip(xs,labels)):axs[0].annotate(l,(x,i),xytext=(8,0),textcoords='offset points',fontsize=8,va='center')
    axs[0].set(xlabel='Conflict index (0 = before first)',xlim=(-.2,7),ylim=(5.6,-.6),yticks=[],title='Earliest divergences')
    axs[1].plot([r['conflict'] for r in activity],[r['jaccard'] for r in activity],label='Activity top10 overlap',alpha=.7)
    bb=[r for r in blocks if r['decision_variable_jaccard'] is not None]
    axs[1].plot([r['start'] for r in bb],[r['decision_variable_jaccard'] for r in bb],label='Decision-variable set overlap /100 conflicts')
    axs[1].set(xlabel='Conflict index (ordinal alignment)',ylabel='Jaccard overlap',ylim=(0,1.05),title='Search-state separation');axs[1].legend(fontsize=7)
    fig.tight_layout();fig.savefig(OUT/'divergence_timeline.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for name,g,color in [('CONTROL',A,'tab:blue'),('TREATMENT',B,'tab:orange')]:
        ls=g['L'];xs=[r['c'] for r in ls];ys=[r['ops'] for r in ls]
        xs=xs+[g['C'][-1]['c']];ys=ys+[g['C'][-1]['ops']]
        axs[0,0].plot(xs,ys,label=name,color=color)
        for c in g['R']:axs[0,0].axvline(c['c'],color=color,alpha=.2,ls=':')
        for ax,field in [(axs[0,1],'width'),(axs[1,0],'lbd')]:
            xx,yy=rolling(ls,field);ax.plot(xx,yy,label=name,color=color)
        costs=[];last=0
        for r in ls:costs.append(dict(c=r['c'],cost=r['ops']-last));last=r['ops']
        xx,yy=rolling(costs,'cost');axs[1,1].plot(xx,yy,label=name,color=color)
    for ax,title,y in [(axs[0,0],'Cumulative search ops; dotted = restarts','Analysis resolution steps'),
        (axs[0,1],'Learned width, mean /100 conflicts','Width'),(axs[1,0],'Learned LBD, mean /100 conflicts','LBD'),
        (axs[1,1],'Analysis work per conflict, mean /100','Ops / conflict')]:
        ax.set(title=title,xlabel='Conflict index',ylabel=y);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'conflicts_vs_ops.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for name,g,color in [('CONTROL',A,'tab:blue'),('TREATMENT',B,'tab:orange')]:
        cs=g['C'];ls=g['L']
        axs[0,0].plot([r['c'] for r in cs],[r['props'] for r in cs],label=name,color=color)
        axs[0,1].plot([r['c'] for r in cs],[r['dequeues'] for r in cs],label=name+' dequeues',color=color)
        axs[0,1].plot([r['c'] for r in cs],[r['enqueues'] for r in cs],ls='--',label=name+' enqueues',color=color,alpha=.6)
        xx,yy=rolling(ls,'dl');axs[1,0].plot(xx,yy,label=name,color=color)
        xx,yy=rolling([dict(r,jump=r['dl']-r['bt']) for r in ls],'jump');axs[1,1].plot(xx,yy,label=name,color=color)
    for ax,title in zip(axs.flat,['Native propagations counter','Actual BCP work (includes early returns)','Conflict decision level, mean /100','Backjump distance, mean /100']):
        ax.set(title=title,xlabel='Conflict index');ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'propagation_comparison.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(14,7),gridspec_kw={'height_ratios':[2,1]})
    ordered=sorted(usage,key=lambda r:r['reason'])
    for off,field,label_,color in [(-.26,'reason','Successful BCP / reason','tab:blue'),(0,'analysis','First-UIP clause visits','tab:orange'),(.26,'minimization','Minimization reason visits','tab:green')]:
        axs[0].bar([i+off for i in range(64)],[r[field] for r in ordered],width=.26,label=label_,color=color)
    axs[0].set_yscale('symlog',linthresh=1);axs[0].set_xticks(range(64),[str(r['id']) for r in ordered],rotation=90,fontsize=6)
    axs[0].set(title='Gold direct usage over the complete TREATMENT run',ylabel='Count (symlog)');axs[0].legend(fontsize=8)
    axs[1].scatter([r['reason'] for r in usage],[r['deletion_penalty'] for r in usage],s=20)
    for r in usage:
        if r['id'] in (96687,150191,2772,210136):axs[1].annotate(str(r['id']),(r['reason'],r['deletion_penalty']),fontsize=8)
    axs[1].set(xlabel='Successful reason enqueues',ylabel='Gold-minus-one ops penalty',title='Usage frequency is not an additive contribution');axs[1].grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'lemma_direct_usage.png',dpi=180);plt.close(fig)
    total=203623-130718;account=state['accounting']
    direct=sum(r['reason'] for r in usage);ana=sum(r['analysis'] for r in usage)
    lines=['# GOLD MECHANISM ANALYSIS','',
        '**当前最可信的解释：提前加入 valid lemmas 改变了 propagation 的顺序和 reason，进而改变 conflict analysis 经过的变量、activity 与 branching；之后 learned clauses 和搜索长度继续分叉。不是“每条 Gold 独立剪掉一份搜索”。**', '',
        '固定 n200_T_r01_s7201；CONTROL=TEMPLATE，TREATMENT=TEMPLATE+原 Gold64。CNF、注入顺序、Glucose3.0、seed91648253、random frequency0、preprocessing及求解参数完全一致。支持证明已重验。独立 observer 与原 counted backend 在18次运行中全部原生计数一致；其中14种配置，另4次只补有限观察窗口。未新建 selector、调K或搜索 subset。','',
        '**此对照降幅是35.80%，不是50%。** CONTROL203,623 ops → Gold130,718；相对BLIND289,664才是54.87%。以下不混用基线。','',
        '## 1. 最早从哪里分叉？','',
        '| 事件 | 位置 | CONTROL → TREATMENT |','|---|---|---|',
        '| reason 首次不同 | conflict前，DL15；第107次BCP enqueue / 全部赋值事件122 | 同为159=true；(157∨158∨159) → Gold30632=(¬136∨158∨159) |',
        '| propagation literal序列首次不同 | conflict前，DL18；第212次BCP enqueue / 事件230 | −492 → +89（Gold24458） |',
        '| conflict状态首次不同 | conflict1 | 同一(¬532∨¬343)，trail314 → 320；actual dequeues300 → 299 |',
        '| conflict clause首次不同 | conflict3 | (88∨89∨90) → Gold24458=(¬261∨88∨89) |',
        '| decision首次不同 | 第22次decision，完成3个conflicts后 | −259 → −260 |',
        '| learned content首次不同 | conflict4 | width4/LBD3 → width12/LBD6；backjump18→16 /18→17 |','',
        '最早的变化是**同一个赋值的证明理由改变**，不是立即得到了不同真值。首次literal差异首先表示队列顺序不同，不能由此宣称BCP闭包变强。前21次decision literals及前3条learned contents一致；冲突编号对齐在分叉后不等于相同搜索状态。','',
        '![divergence](results/gold_mechanism/divergence_timeline.png)','',
        '## 2. Gold 通过什么路径起作用？','',
        '**最清楚的短链在conflict1。** CONTROL在first-UIP分析中访问(88∨89∨90)，再用(¬261∨¬90)消去90；Gold直接使用已物化的(¬261∨88∨89)。得到的learned clause完全相同，但analysis steps32→31。变量90在CONTROL的activity top10中为1，在Gold top10中消失。这是同一结论、不同reason/analysis路径的直接证据；到conflict3累计ops89→85，再出现decision22分叉。不能把每次activity差异唯一归因于某一条lemma，因为还有watch顺序、phase saving和heap状态。','',
        '以下6个早期case均从真实enqueue依赖边回溯，已逐边检查“所有reason其余文字为false”和事件先后。数字是DIMACS变量，不是Gold ID。完整clause、分支前提和路径见case_studies.json；表中只列一条最短路径。','',
        '| conflict | Gold与传播路径（箭头为实际reason依赖） | conflict clause |','|---:|---|---|']
    for c in cases:
        p=c['paths'][0]
        chain=' → '.join(str(n['lit']) for n in p['nodes'])
        lines.append(f"| {c['conflict']['c']} | G{p['gold']}: {chain} | {ctext(c['conflict']['clause'])} |")
    lines+=['',
        'case1/3的learned仍与CONTROL相同；case4已经进入不同branch。case5/6/7展示后续依赖链，不是独立反事实证明。更早进入reason graph的实例包括Gold24458直接赋值89，随即原始(¬479∨¬89)推出−479，接上原始ALO clause并到达conflict1。case3由Gold24458本身报conflict，trail286而CONTROL294。各clause首次reason/conflict index同时保留；分叉之后“更早”仅是轨迹上的时间描述。','',
        '## 3. 有多少 Gold 被直接使用？','',
        f'**64/64有成功BCP enqueue并作为reason；63/64进入first-UIP分析；0条从未直接使用。** 合计{direct:,}次Gold reason enqueue、{ana:,}次first-UIP clause访问。这里“unit触发次数”定义为成功enqueue，故与reason赋值次数相同，不是所有unit条件或watch扫描次数。每条的首次生效、conflict、minimization计数见[lemma_usage.csv](results/gold_mechanism/lemma_usage.csv)。','',
        '## 4. 是否存在“几乎不使用但影响整体”的lemma？','',
        '**“很多几乎不用却重要”不成立。** 事先定义reason≤1为极少、≤16为低频：极少只有96687；低频另有150191。','',
        '| Gold ID | reason/BCP | first-UIP | minimization reason访问 | Gold删除后ops | 解读 |','|---:|---:|---:|---:|---:|---|',
        '| 96687 | 1 | 0 | 0 | 130,718（不变） | 1899个conflicts之后首次使用；没有发现删除损害 |',
        '| 150191 | 11 | 6 | 806 | 170,026（+39,308） | 传播低频，实际minimization直接参与很多，不是几乎没用 |',
        '| 210136 | 417 | 266 | '+str(next(r['minimization'] for r in usage if r['id']==210136))+' | 225,183（+94,465） | 高频且删除影响大 |',
        '| 2772 | 186 | 21 | '+str(next(r['minimization'] for r in usage if r['id']==2772))+' | 284,028（+153,310） | LOO重要，单独加入却是209,942，差于CONTROL |','',
        '全部64条LOO/singleton表复用既有记录，本轮只重跑协议中4个代表的删除干预。LOO改变整个未来轨迹，penalty不能相加当贡献。minimization计数为reason访问，不含二元watch候选扫描；没有把低BCP频率误当总使用量。','',
        '![usage](results/gold_mechanism/lemma_direct_usage.png)','',
        '## 5. 是否有联合激活和1+1>2？','',
        '**有非加性search effect与共同reason祖先；没有证明某个必要unit/conflict只能靠组合出现。** 固定L1=24458、L2=30149、L3=210136：','',
        '| 配置（均加TEMPLATE） | ops | 相对CONTROL的gain |','|---|---:|---:|']
    for name in ('CONTROL','L1','L2','L1_L2','L1_L2_L3'):
        ops=rr[name]['stats']['analysis_resolution_steps'];lines.append(f'| {name} | {ops:,} | {203623-ops:+,} |')
    lines+=['',
        'L1、L2单独的gain合计−178,782，合用却是+33,765，交互差额**+212,547 ops**；加L3后收益消失。这是确定性search的非加性实例，不是对lemma价值的普遍排序。','',
        '在pair的conflict199快照，实际链为：','',
        '`G24458 ⇒ 89 ⇒ −299 ⇒ 298 ⇒ −505 ⇒ 507；G30149=(¬507∨565∨566) ⇒ 565；原始(¬565∨¬427) ⇒ −427`。','',
        '**关键反检查：** L1单独也在同一enqueue序号28916赋值565，并在28950赋值−427，只是用原始(565∨566∨567)作reason。因此这里支持reason图的共同依赖/替代，不支持“组合才提前unit”。','',
        '随后pair与L1在conflict291首次报不同conflict：L1为(565∨566∨567)，pair为原始(¬565∨¬427)。pair的G30149先推出565并直接进入这次analysis；实际dequeues累计少19、当前trail少18。两路learned contents直到655仍相同；656才分别学出width13/LBD6与width9/LBD4的不同clause，pair当次路径为 `G30149 ⇒ 566 ⇒ −23 ⇒ 22 ⇒ −151 ⇒ 152 → conflict(¬152∨¬11)`。decision直到第828次、完成657个conflicts后才变成−187 /−570。','',
        '这给出“reason替代 → 部分传播更早截断 → 后续learned/branching分叉”的可检查实例。**未证明conflict199那条共同祖先链必然导致最终33,765 ops收益**；291和656的即时图只含L2，L1的作用也可能经此前搜索状态传递。补trace只取196–206、291、656，没有枚举更多subset。','',
        '## 6. search reduction主要发生在哪个阶段？','',
        f'总差额{total:,} ops。在双方都有的前3,584个conflicts内，CONTROL累计{account["control_ops_at_common"]:,}，Gold{account["treatment_final_ops"]:,}，差{account["prefix_savings"]:,}（总差额的{100*account["prefix_savings"]/total:.1f}%）。CONTROL之后多出1,741个conflicts，耗费{account["extra_control_tail"]:,} ops（{100*account["extra_control_tail"]/total:.1f}%）。**数值上主要是Gold较早结束、少走了一段长尾，而不是每次analysis便宜一半。** 这是按ordinal的算术分解，不是同一搜索空间的阶段因果分摊。','',
        '| 指标 | CONTROL | TREATMENT |','|---|---:|---:|']
    for label_,field in [('Conflicts','conflicts'),('Decisions','decisions'),('Native propagations','propagations')]:
        lines.append(f"| {label_} | {rr['CONTROL']['stats'][field]:,} | {rr['TREATMENT']['stats'][field]:,} |")
    for label_,field in [('实际BCP dequeues','actual_dequeues'),('Enqueues','enqueues'),('平均learned width','mean_width'),('平均LBD','mean_lbd'),('平均conflict DL','mean_dl'),('平均backjump距离','mean_backjump')]:
        lines.append(f"| {label_} | {state['CONTROL'][field]:,.3f} | {state['TREATMENT'][field]:,.3f} |")
    lines+=['| Restart conflicts | 1865, 2119 | 215, 2265 |','',
        'native propagations未计入binary-conflict早退路径的本次dequeues，这是原代码计数口径；额外actual-dequeues观察器没有修改它。曲线同时给出两者。更低平均width/LBD是结果描述，不能证明学到的每条clause更好；第一条不同的Gold learned反而更宽、LBD更高。','',
        '![ops](results/gold_mechanism/conflicts_vs_ops.png)','',
        '![propagation](results/gold_mechanism/propagation_comparison.png)','',
        '## 7. 当前最可信解释是什么？','',
        '以**D（activity / branching轨迹改写）为主线、A/B/C共同出现**的描述最贴近证据：物化短推论提供替代reason，部分分析链更短、冲突检测更早；first-UIP访问变量不同，使activity/branching不同；之后learned clauses、restart位置与搜索长度一起改变。最有区分力的观察是：前3条learned仍相同，activity已不同，branching先于learned内容分叉。','',
        '这解释了“为什么会走不同、最后更短的路”，尚未完整解释“为何这条路恰好更短35.8%”。Gold来自同target的既有oracle选择，本轮是事后机理诊断，不提供跨target稳定性，也没有量化A–D各自贡献比例。','',
        '## 8. 哪些解释被排除或不受支持？','',
        '- 排除本次差异由solver/seed/preprocessing变动或observer改变计数导致；全部native counters匹配。',
        '- 排除“首次获益必须先学出不同或更好的clause”：learned改变之前reason、activity、decision已不同。',
        '- 不支持“很多Gold完全没用却神秘地改善搜索”；64条均直接reason使用，低BCP的150191还有806次minimization访问。',
        '- 排除该小例中的简单收益相加：两个负单独gain合成正gain，三条又反转。',
        '- 不支持“主要只是每次conflict成本减半”、或“更大backjump解释全部”：每conflict工作与平均jump相近，主要算术差额在少掉的长尾。',
        '- 未排除真正的传播增强、phase-saving、watch顺序、heap tie-break和restart反馈；未用干预分离它们。共同reason祖先不等于组合必要性。','',
        '## 9. 下一步最小验证实验是什么？','',
        '仍只用这一个target和两个固定输入，在conflict3结束、decision22之前，做一次诊断性分支：把Gold run的**activity向量及order heap完整状态**同步为CONTROL当时状态，其他保持Gold原状态，检查decision22是否恢复为−259，以及首次分叉是否推迟。保留正常Gold作对照。若不恢复，再报告赋值/phase差异而不继续调参。这能直接检验activity/heap路径的中介作用；本轮未执行，也不承诺总ops必然恢复。','',
        '证据：[冻结协议](docs/gold-mechanism-protocol.md) · [输入与build哈希](results/gold_mechanism/frozen.json) · [compact divergence](results/gold_mechanism/divergence.json) · [6条路径case](results/gold_mechanism/case_studies.json) · [pair窗口case](results/gold_mechanism/pair_path_cases.json) · [逐条usage](results/gold_mechanism/lemma_usage.csv) · [按conflict块的状态](results/gold_mechanism/search_state_blocks.json) · [audit](results/gold_mechanism/audit.json)。全量搜索只保留conflict/decision轻量记录与clause聚合；传播边限前64个conflicts及13个补充conflict位置（两配置共26个快照），压缩trace约12MiB，无完整completion proof。Completion为solver-reported UNSAT；valid redundant lemmas通过已有support checker验证。','',
        '复核分析与图（不solve）：`.venv/bin/python gold_mechanism_analyze.py`，再运行 `.venv/bin/python gold_mechanism_report.py`。']
    Path('GOLD_MECHANISM_ANALYSIS.md').write_text('\n'.join(lines)+'\n')
    dump(OUT/'audit.json',dict(status='PASS',measurements=len(runs),distinct_configurations=14,
        native_counters_match=True,frozen_sources_checked=True,baseline_binary_unchanged=True,
        reason_graph_audit=json.loads((OUT/'graph_audit.json').read_text()),window_graphs_checked=True,
        full_usage_gold_count=len(usage),report_sha256=sha('GOLD_MECHANISM_ANALYSIS.md'),
        report_builder_sha256=sha(__file__),analysis_sha256=sha('gold_mechanism_analyze.py')))
    print('PASS: report, four figures, source/counter/graph audits')

if __name__=='__main__':main()
