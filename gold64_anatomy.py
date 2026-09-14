"""Gold-64 instrumentation approved in PRIOR_ART_GATE.md; no new SAT machinery."""
import csv
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import random
import sys
from statistics import median
from time import perf_counter

import networkx as nx
from pysat.solvers import Solver
from evaluation_oracle_run import sha
from homologous_template_run import encoding_leaf
import homologous_template_run as backend
from oracle_lemma import prepare, TARGET, HISTORY, TEMPLATE
from oracle_lemma_evaluate import materialize
from round4_core import ancestors

OUT = Path('results/gold64_anatomy')
GOLD = Path('results/oracle_lemma/gold_lemmas.json')


def dump(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')


def csvout(name, rows):
    with (OUT/name).open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def components(ids, supports, threshold=0):
    g = nx.Graph()
    g.add_nodes_from(ids)
    for a, b in combinations(ids, 2):
        intersection = len(supports[a] & supports[b])
        union = len(supports[a] | supports[b])
        if intersection and intersection / union >= threshold:
            g.add_edge(a, b)
    return sorted((sorted(c) for c in nx.connected_components(g)), key=lambda c: (-len(c), c))


def inspect(data, ids, detailed=False):
    h = data['h']
    supports = {}
    records = []
    for i in ids:
        aa = ancestors(h.history, i)
        leaves = {j for j in aa if j < h.leaves}
        inf = aa-leaves
        variables = {abs(x) for j in leaves for x in h.clauses[j]}
        supports[i] = dict(inference=inf, leaves=leaves,
                           output_variables={abs(x) for x in h.clauses[i]},
                           support_variables=variables,
                           encoding_leaves={j for j in leaves if encoding_leaf(h.clauses[j])},
                           edge_leaves={j for j in leaves if not encoding_leaf(h.clauses[j])})
        row = dict(id=i, clause=list(h.clauses[i]), width=len(h.clauses[i]),
                   inference_count=len(inf), leaf_count=len(leaves),
                   output_vertices=len({(abs(x)-1)//3 for x in h.clauses[i]}),
                   support_vertices=len({(x-1)//3 for x in variables}),
                   selected_ancestors=sorted((inf & set(ids))-{i}))
        if detailed:
            local = [h.clauses[j] for j in sorted(leaves)]
            # Check only the local support, avoiding vacuous implication by global UNSAT.
            with Solver(name='g3', bootstrap_with=local) as solver:
                sat = solver.solve()
            with Solver(name='g3', bootstrap_with=local) as solver:
                implied = not solver.solve(assumptions=[-x for x in h.clauses[i]])
            with Solver(name='g3', bootstrap_with=local) as solver:
                rup = not solver.propagate(assumptions=[-x for x in h.clauses[i]])[0]
            assert sat and implied
            row.update(local_support_sat=sat, local_entailment=implied, local_rup=rup,
                       inference_ids=sorted(inf), leaf_ids=sorted(leaves),
                       local_premises=local,
                       decoded_clause=[dict(vertex=(abs(x)-1)//3, color=(abs(x)-1)%3,
                                            positive=x>0) for x in h.clauses[i]])
        records.append(row)
    counts = Counter(j for s in supports.values() for j in s['inference'])
    groups = components(ids, {i:s['inference'] for i,s in supports.items()})
    summary = dict(roots=len(ids), inference_union=len(counts), inference_sum=sum(counts.values()),
                   shared_inference_nodes=sum(v>1 for v in counts.values()),
                   max_inference_multiplicity=max(counts.values(), default=0),
                   inference_multiplicity_histogram=dict(sorted(Counter(counts.values()).items())),
                   component_sizes=[len(g) for g in groups], groups=groups,
                   widths=dict(sorted(Counter(r['width'] for r in records).items())),
                   support_size_histogram=dict(sorted(Counter(r['inference_count'] for r in records).items())),
                   selected_ancestor_pairs=sum(len(r['selected_ancestors']) for r in records))
    return records, supports, summary


def main():
    OUT.mkdir(exist_ok=True)
    old_meta = json.loads(Path('results/oracle_lemma/metadata.json').read_text())
    for p, expected in old_meta['source_files'].items():
        assert sha(p) == expected, p
    data = prepare()
    gold_payload = json.loads(GOLD.read_text())
    assert gold_payload['history_sha256'] == sha(HISTORY)
    ids = gold_payload['sets']['exact_64']['selected_ids']
    assert len(ids)==64 and ids==sorted(set(ids))
    records, supports, anatomy = inspect(data, ids, detailed=True)
    assert anatomy['inference_union']==265
    dump('roots.json', records)
    pairs = []
    sensitivity = []
    for field in next(iter(supports.values())):
        sets = {i: s[field] for i,s in supports.items()}
        for a,b in combinations(ids,2):
            union = len(sets[a]|sets[b])
            pairs.append(dict(kind=field, left=a, right=b, intersection=len(sets[a]&sets[b]),
                              union=union, jaccard=len(sets[a]&sets[b])/union if union else 0))
        for threshold in (0, .1, .25, .5):
            cc = components(ids, sets, threshold)
            sensitivity.append(dict(kind=field, threshold=threshold, components=len(cc),
                                    sizes=[len(c) for c in cc]))
    csvout('pairwise_overlap.csv', pairs)
    dump('sensitivity.json', sensitivity)
    baseline_sets = dict(GOLD64=ids, RANKED64=sorted(data['ranked'][:64]),
                         SHORTEST64=sorted(data['shortest'][:64]), USED64=sorted(data['used'][:64]))
    for seed in (17,29,43):
        p=data['population'].copy()
        random.Random(seed).shuffle(p)
        baseline_sets[f'RANDOM64_{seed}']=sorted(p[:64])
    baseline_anatomy={}
    for label, selected in baseline_sets.items():
        _, _, summary=inspect(data, selected)
        summary['gold_intersection']=len(set(selected)&set(ids))
        baseline_anatomy[label]=summary
    dump('baseline_anatomy.json', baseline_anatomy)
    dump('anatomy.json', anatomy)
    specs=[dict(route='TEMPLATE', ids=[], template=True), dict(route='BLIND', ids=[], template=False)]
    specs += [dict(route=k, ids=v, template=True) for k,v in baseline_sets.items()]
    partitions={'MODULE':anatomy['groups']}
    for seed in (17,29,43):
        shuffled=ids.copy()
        random.Random(seed).shuffle(shuffled)
        offset=0
        groups=[]
        for g in anatomy['groups']:
            groups.append(sorted(shuffled[offset:offset+len(g)]))
            offset+=len(g)
        partitions[f'PARTITION_{seed}']=groups
    for label, groups in partitions.items():
        for j,g in enumerate(groups):
            for mode, selected in [('ONLY',g),('DROP',sorted(set(ids)-set(g)))]:
                specs.append(dict(route=f'{label}_{j:02}_{mode}', ids=selected, template=True))
    # Identical singleton controls reuse the same exact configuration, retaining aliases.
    unique={}
    for spec in specs:
        key=(spec['template'],tuple(spec['ids']))
        if key not in unique:
            unique[key]=dict(spec, aliases=[])
        unique[key]['aliases'].append(spec['route'])
    specs=list(unique.values())
    dump('selections.json', specs)
    dump('partitions.json', partitions)
    backend.DIRECTORY=OUT/'artifacts'
    backend.DIRECTORY.mkdir(exist_ok=True)
    backend.native(list(data['cnf'])+data['templates'],'warmup')
    rows=[]
    with (OUT/'raw.jsonl').open('w') as f:
        for rep in range(3):
            schedule=specs.copy()
            random.Random(20260911+rep).shuffle(schedule)
            for spec in schedule:
                start=perf_counter()
                cnf, proofs, replay=materialize(data,spec)
                row=backend.native(cnf,f'{spec["route"]}_rep{rep}')
                row.update(total_wall_seconds=perf_counter()-start, **replay,
                           route=spec['route'], aliases=spec['aliases'], repetition=rep)
                assert row['status']=='UNSAT'
                rows.append(row)
                f.write(json.dumps(row)+'\n'); f.flush()
            print(f'repetition {rep+1}: {len(schedule)} configurations complete',flush=True)
    summaries=[]
    for spec in specs:
        rr=[r for r in rows if r['route']==spec['route']]
        assert len({(r['analysis_resolution_steps'],r['conflicts'],r['input_sha256']) for r in rr})==1
        r=dict(route=spec['route'], aliases=spec['aliases'], historical_lemmas=len(spec['ids']))
        for k in ('analysis_resolution_steps','conflicts','replay_and_check_seconds','total_wall_seconds','support_inferences','process_seconds'):
            r[k]=median(x[k] for x in rr)
        r.update(wall_min_seconds=min(x['total_wall_seconds'] for x in rr),
                 wall_max_seconds=max(x['total_wall_seconds'] for x in rr))
        summaries.append(r)
    expected=gold_payload['sets']['exact_64']
    actual=next(r for r in summaries if r['route']=='GOLD64')
    assert actual['analysis_resolution_steps']==expected['search_ops']
    assert actual['conflicts']==expected['conflicts']
    dump('summary.json',summaries)
    csvout('summary.csv', summaries)
    dump('metadata.json',dict(source_files={str(p):sha(p) for p in (TARGET,HISTORY,TEMPLATE,GOLD,Path('PRIOR_ART_GATE.md'),Path(__file__))},
                             backend_sha256=sha(backend.NATIVE/'counted'), networkx=nx.__version__,
                             repetitions=3, unique_configurations=len(specs), rows=len(rows),
                             support_checker='PASS', local_entailments='64 PASS; all local supports SAT',
                             completion_status='native solver reported UNSAT; no new full completion conversion',
                             previous_gold_counters_match=True, timing_scope='warm preselected IDs; includes checked replay and native process; excludes offline analysis',
                             offline=data['offline']))
    print(json.dumps(anatomy),flush=True)


def report():
    """Render the frozen measurements; annotations describe known encoding rules."""
    rows=json.loads((OUT/'summary.json').read_text())
    lookup={alias:r for r in rows for alias in r['aliases']}
    roots=json.loads((OUT/'roots.json').read_text())
    anatomy=json.loads((OUT/'anatomy.json').read_text())
    base=lookup['TEMPLATE']['analysis_resolution_steps']
    gold=lookup['GOLD64']['analysis_resolution_steps']
    modules=[]
    for j,ids in enumerate(anatomy['groups']):
        alone=lookup[f'MODULE_{j:02}_ONLY']
        drop=lookup[f'MODULE_{j:02}_DROP']
        modules.append(dict(module=j, ids=ids, size=len(ids),
                            only_ops=alone['analysis_resolution_steps'],
                            drop_ops=drop['analysis_resolution_steps'],
                            only_saving=base-alone['analysis_resolution_steps'],
                            removal_penalty=drop['analysis_resolution_steps']-gold))
    csvout('module_ablation.csv',modules)
    semantic=[]
    for r in roots:
        # Fixed, known 3-color encoding annotation; not a generic motif detector.
        local=r['local_premises']
        alo=[c for c in local if len(c)==3 and all(x>0 for x in c)]
        edges=[c for c in local if len(c)==2 and all(x<0 for x in c)
               and len({(abs(x)-1)//3 for x in c})==2]
        category='other_local_coloring_consequence'
        if r['inference_count'] in (1,2):
            n=r['inference_count']
            assert len(alo)==1 and len(edges)==n and len(local)==n+1
            assert len({(x-1)//3 for x in alo[0]})==1
            eliminated=[]; external=[]
            for edge in edges:
                inside=[-x for x in edge if -x in alo[0]]
                assert len(inside)==1
                eliminated+=inside
                external += [x for x in edge if -x not in alo[0]]
                assert (abs(edge[0])-1)%3 == (abs(edge[1])-1)%3
            assert len(set(eliminated))==n
            assert set(r['clause'])==set(external+[x for x in alo[0] if x not in eliminated])
            category='edge_excludes_one_color' if n==1 else 'two_neighbors_force_remaining_color'
        semantic.append(dict(id=r['id'], category=category, support_vertices=r['support_vertices'],
                             local_support_sat=r['local_support_sat'],
                             local_entailment=r['local_entailment'], local_rup=r['local_rup']))
    csvout('semantic_annotations.csv',semantic)
    stats=dict(categories=dict(Counter(r['category'] for r in semantic)),
               local_rup=sum(r['local_rup'] for r in semantic), local_sat=64, local_entailment=64)
    dump('semantic_summary.json',stats)
    table=['| Route | Search ops | Conflicts | Replay/check ms | Total ms |',
           '|---|---:|---:|---:|---:|']
    for label in ('BLIND','TEMPLATE','GOLD64','RANKED64','SHORTEST64','USED64',
                  'RANDOM64_17','RANDOM64_29','RANDOM64_43'):
        r=lookup[label]
        table.append(f'| {label} | {r["analysis_resolution_steps"]:,} | {r["conflicts"]:,} | '
                     f'{r["replay_and_check_seconds"]*1000:.2f} | {r["total_wall_seconds"]*1000:.2f} |')
    mt=['| Group | IDs | TEMPLATE + group ops | Gold minus group ops |', '|---|---|---:|---:|']
    for m in modules[:2]:
        mt.append(f'| {m["module"]} | {m["ids"]} | {m["only_ops"]:,} | {m["drop_ops"]:,} |')
    text=f'''# Gold-64 proof anatomy

结论：本例支持“多数具有独立廉价推导的 clause，组合后改变搜索”，
**不支持“64 条背后只是少量共享 proof modules”**。
语义独立性没有得到证明，也没有建立 semantic abstraction memory。

本轮先完成 [PRIOR_ART_GATE.md](PRIOR_ART_GATE.md)，读取本地 IPR 论文和实现，
再新增一个实验驱动；所有 traversal、checker、SAT solving 和图连通分量复用现成实现。
源重要性、稀疏 lemma、局部着色规则、模块分组都不作为新贡献。

## Frozen experiment

沿用 n200_T_r01_s7201、历史 G6202、67 个 TEMPLATE 和原 Oracle exact-64。
历史输出排除 TEMPLATE exact duplicates、subsumed clauses 和 encoding-only 推导，
保持原 CNF / TEMPLATE / 源 ID 注入顺序。153 个不同配置，各 3 次，共 459 次；
按固定随机种子打乱执行顺序，单进程依次启动原 native Glucose backend。
所有 search counters 重复一致，Gold 与上一轮完全一致。

下表是**本轮**中位数，包含选中 support 的 replay/check、输入输出和 native process，
不含离线 oracle、加载/索引和全 completion proof 转换。历史支持先独立从当前 CNF
重证，再注入输出；不把未验证历史 clause 当公理。时间随机器负载浮动，完整范围见 CSV。

{chr(10).join(table)}

## DAG 与 source-importance baseline

64 个根的独立 inference 数总和 291，联合 265，共享节省 26 步（8.93%）。
265 个节点中 243 仅服务一个根，18 服务两个，4 服务三个；没有 Gold 根是另一个
Gold 根的 ancestor。共享推导图有 61 个 component：3、2，以及 59 个单根。
这不是少量大模块。相比之下，RANKED64 有 40 个 component，USED64 有 32 个，
它们更共享，但本例目标搜索更差。SHORTEST64 使用现有 width / use-count 排序；
USED64 使用重建 DAG 的直接使用次数，均非真实 LBD 或 activity。

共同 premise 图有 32 组（最大 25），仅 encoding premise 有 33 组（最大 22），
仅 edge premise 有 47 组（最大 11）。输出变量图有 24 组，support 变量图有 12 组。
这些宽松连通关系不能自动叫 proof module：同一个顶点编码可以把不同局部推论串起来。
阈值 0.1 / 0.25 / 0.5 下的完整敏感性分析已导出；inference 图分别为 61 / 62 / 63 组。

**表示限制：**这里是 DRUP 重建出的 Resolution DAG，而非真实 CDCL derivation DAG。
该区别已有 [CP 2020](https://jakobnordstrom.se/docs/publications/UsingProofs_CP.pdf) 明确讨论。
结论只针对当前证书表示；不能由支持不相交推出语义互不相关。

## Module-level ablation

{chr(10).join(mt)}

两个共享组单独使用都不能重现 Gold 的收益，第二组甚至比 TEMPLATE 更差。
但删除任一组都会严重破坏 Gold 的搜索表现。61 组中，删除 60 组增加 ops，
1 组不变；删除 penalty 中位数 {median(m['removal_penalty'] for m in modules):,}，
最大 {max(m['removal_penalty'] for m in modules):,}。
单组加入 TEMPLATE，只有 {sum(m['only_saving']>0 for m in modules)} / 61 组减少 ops。
这是同一启发式轨迹下的条件边际效应，不能把 penalty 相加分配成各组的“贡献比例”。

三组固定种子的同尺寸随机 partition 作为控制；单根集合重复时复用完全相同配置，
保留 aliases。随机 3-clause 组的删除 penalty 也可超过真实共享组，故大 penalty
不是共享结构特有的信号。完整 ONLY / DROP 和控制组数据见 selections、summary、partitions。
这些不是新的 oracle 搜索，也没有因为看到 ablation 结果而调整分组阈值。

## Semantic analysis

局部 premise **64/64 都 SAT**；加上结论取反后 **64/64 UNSAT**，
均用已有 PySAT solver 验证。{stats['local_rup']}/64 可直接由局部 premise 单位传播完成 RUP 检查；
其余仍有已检查的 Resolution 支持。没有用全局 UNSAT 的 target 做空洞 implication 验证。

31 条是一条边加一个顶点 ALO 的一步推论：

`(v0 ∨ v1 ∨ v2) ∧ (¬u1 ∨ ¬v1) ⇒ (¬u1 ∨ v0 ∨ v2)`。

另外 13 条是两条边加一个 ALO 的两步推论：

`(v0 ∨ v1 ∨ v2) ∧ (¬u0 ∨ ¬v0) ∧ (¬w1 ∨ ¬v1) ⇒ (¬u0 ∨ ¬w1 ∨ v2)`。

这 44 条是标准着色传播关系在具体顶点上的实例化。已逐条检查前提形状、颜色一致、
消去变量和最终 clause，而非只凭长度猜测；标注表保留每条 ID。剩余 20 条只描述为
更长的局部着色推论，不强行命名为新 abstraction。局部 support 覆盖 2–10 个顶点。
这类编码/传播研究已有 [Arc Consistency in SAT](https://frontiersinai.com/ecai/ecai2002/p0121.html)。

**TEMPLATE 防火墙仍不充分：**排除那 67 条具体 clause 不等于排除全部通用知识。
这 44 条包含图的特定边，因此不是 encoding-only，却仍是通用关系的 grounded instance。
Oracle 可能在挑适合当前搜索轨迹的实例化位置；本轮没有证明这些信息必须从历史学习。
两个规则描述能概括 44 条，不意味着把 44 个 grounded outputs 替换为两条“抽象”后
还保留收益。没有运行这种替换，也没有证明跨图/跨 encoding transfer。

## What this answers

暂时选择 A 的谨慎版本：大多数 clause 的证书支持独立且便宜，目标收益非加性。
没有证据进入“少量共享模块”的 B 结论；C 只有既有通用语义的描述，没有 abstraction
压缩或迁移实证。单 target 的同目标 oracle 选择偏差仍在，不能推广到其他实例。

若后续继续，研究设计首先需要控制这些廉价通用规则的具体实例化位置，并测试
未参与选择的 target；该实验要再次过 literature challenge。当前不新增 detector、
模块 selector 或 abstraction 算法，也不继续全量 DRUP→Resolution 工程。

## Artifacts and validation

- [Driver](gold64_anatomy.py), [plot](results/gold64_anatomy/anatomy.png), [PDF](results/gold64_anatomy/anatomy.pdf)
- [Audit](results/gold64_anatomy/audit.json), [Metadata / hashes](results/gold64_anatomy/metadata.json), [raw runs](results/gold64_anatomy/raw.jsonl), [summary](results/gold64_anatomy/summary.csv)
- [Per-root proof IDs and local premises](results/gold64_anatomy/roots.json), [overlaps](results/gold64_anatomy/pairwise_overlap.csv), [threshold sensitivity](results/gold64_anatomy/sensitivity.json)
- [Module ablation](results/gold64_anatomy/module_ablation.csv), [semantic annotations](results/gold64_anatomy/semantic_annotations.csv)

所有 replay 均通过已有 checker；completion 为 native solver 报告 UNSAT。
本轮未重新把 459 份 completion 展成纯 Resolution；原 Gold-64 的完整证书审计
沿用上一轮，原始 DRUP 保留供复查。相关现有 14 个单元测试通过。

Reproduce: `MPLCONFIGDIR=/private/tmp/satfinding-mplconfig PYTHONPATH=/private/tmp/satfinding-plotdeps .venv/bin/python gold64_anatomy.py`。
同一环境下加 `--report-only` 只重建报告和图。测量程序版本哈希记录于 metadata，
最终含报告代码版本另记于 report_manifest，不覆盖测量时的 provenance。
'''
    Path('GOLD64_ANATOMY_RESULTS.md').write_text(text)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,3,figsize=(15,4.4))
    sizes=Counter(r['inference_count'] for r in roots)
    ax[0].bar(list(sizes),list(sizes.values()),color='#467ca8')
    ax[0].set(xlabel='Inference steps per Gold root',ylabel='Number of roots',title='44 / 64 need only 1–2 steps')
    labels=['TEMPLATE','GOLD64','RANKED64','SHORTEST64','USED64']
    ax[1].barh(labels,[lookup[x]['analysis_resolution_steps']/1000 for x in labels],color=['#888888','#30896b','#467ca8','#467ca8','#467ca8'])
    ax[1].invert_yaxis()
    ax[1].set(xlabel='Completion resolution ops (thousands)',title='Source importance ≠ target utility')
    ax[2].scatter([m['only_saving']/1000 for m in modules],[m['removal_penalty']/1000 for m in modules],c=['#c56b32' if m['size']>1 else '#467ca8' for m in modules],alpha=.8)
    ax[2].axvline(0,color='grey',linewidth=.8)
    ax[2].axhline(0,color='grey',linewidth=.8)
    ax[2].set(xlabel='Savings when used alone (thousand ops)',ylabel='Penalty when removed (thousand ops)',title='Effects depend on the other clauses')
    fig.tight_layout()
    fig.savefig(OUT/'anatomy.png',dpi=180)
    fig.savefig(OUT/'anatomy.pdf')
    plt.close(fig)
    dump('report_manifest.json',dict(driver_sha256=sha(__file__),summary_sha256=sha(OUT/'summary.json'),
                                     report_sha256=sha('GOLD64_ANATOMY_RESULTS.md')))


if __name__=='__main__':
    if '--report-only' not in sys.argv:
        main()
    report()
