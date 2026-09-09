"""Summarize measured second-round results without treating oracle hits as retrieval."""
import json
from pathlib import Path
import statistics
from time import perf_counter

from benchmark import archive
from research import glucose_sat
from round2_permutation import prepare


def main():
    permutation = json.loads(Path('results/round2-permutation.json').read_text())
    matching = json.loads(Path('results/round2-matching.json').read_text())
    motifs = json.loads(Path('results/round2-motif.json').read_text())
    features = json.loads(Path('results/round2-feature-baselines.json').read_text())
    _, queries, _ = prepare(archive('/tmp/satcache-rti.tar.gz'), archive('/tmp/satcache-bms.tar.gz'), 7101, 500)
    baseline = []
    for _ in range(3):
        start = perf_counter()
        for q in queries[:100]:
            assert glucose_sat(q) is not None
        baseline.append(perf_counter()-start)
    Path('results/round2-query-baseline.json').write_text(json.dumps(dict(
        note='Separate measurement: 100 same renamed queries, Glucose plus SAT certificate check; '
             'excludes loading, history preparation, and result serialization.',
        seconds=baseline, median_seconds=statistics.median(baseline)), indent=2)+'\n')
    lines = ['# 第二轮研究结论', '',
             '独立变量重命名后出现了真实的结构检索信号，并产生了经过检查的模型迁移。'
             '但检索覆盖率仍低、匹配开销远高于直接求解；同宽度噪声中的 proof motif 检索尚未明显胜过随机。', '',
             '## 独立重命名：结构信号与 verified reuse', '',
             '使用官方 500 对 RTI/BMS，逐公式独立置换变量、分别打乱历史/查询顺序。隐藏映射'
             '只在评估端使用。三个种子各跑全部 500 个检索查询；下表排名为种子 7101，'
             '端到端匹配为该种子固定的前 100 个打乱后查询，每次最多 3 个候选。', '',
             '| 方法 | 父实例 Recall@3（500） | Recall@8（500） | Verified reuse（100） |',
             '|---|---:|---:|---:|']
    first = permutation['runs'][0]['methods']
    for method in first:
        data = first[method]
        rows = matching['methods'].get(method)
        verified = str(sum(r['accepted'] is not None for r in rows)) if rows is not None else '未扩测（pilot 为 0/20）'
        lines.append(f"| {method} | {data['recall']['3']:.1%} | {data['recall']['8']:.1%} | {verified} |")
    oracle = matching['methods']['oracle_candidate']
    lines += ['', 'WL 在三个置换种子上的 Recall@3 都是 5.4%（27/500），Recall@8 为 10.6%。'
              '随机挑 3 个候选的理论命中率为 3/500=0.6%；这里的描述性提升为 9 倍。'
              '重复置换同一组公式不构成三个独立数据集，不能把样本量算成 1500。', '',
              f"给出正确历史候选、但不给变量映射的对照成功 {sum(r['accepted'] is not None for r in oracle)}/100。"
              '系统真实检索的 WL 成功为 4/100；这 4 个全部有独立复查的映射与 SAT 赋值。'
              '4 对 0 的端到端样本量仍小，不据此声称端到端差异已经得到充分统计验证。', '',
              f"WL 的 100 个查询仅候选匹配/检查就耗时 {sum(r['lookup_seconds'] for r in matching['methods']['wl']):.3f} 秒，"
              f"同批查询直接 Glucose + 模型检查的三轮中位数为 {statistics.median(baseline):.3f} 秒。"
              '这轮没有净加速；主要瓶颈是检索覆盖率与匹配成本。', '',
              '## 把表示与排序方法分开', '',
              '不仅补了原始子句 Jaccard、MinHash、TF-IDF、BM25，还把完全相同的 WL tokens '
              '交给这四个 scorer，以免把表示变化误当成 scorer 的优越性。', '',
              '| 相同 WL 表示上的 scorer | Recall@3 | Recall@8 |', '|---|---:|---:|']
    for method, data in features['methods'].items():
        lines.append(f"| {method} | {data['recall']['3']:.1%} | {data['recall']['8']:.1%} |")
    lines += ['', '当前最好的这一配置就是 WL 特征 + 普通 TF-IDF；没有神经模型，也没有训练。', '',
              '## 非父子公式中的证书 motif', '',
              '24 个不同的最小二元 UNSAT core（6–7 个变量），每个历史/当前公式分别叠加独立'
              '随机可满足上下文，独立重命名。两者不是父子子句集，且全局子句数不同。'
              '每个难度另有 12 个带已检查 SAT 模型的负例。以下只计真实迁移并通过检查的结果。', '',
              '| 方法 | 三元上下文 control | 额外混入二元噪声 |', '|---|---:|---:|']
    for method in motifs['variants']['ternary_context_control']['methods']:
        hits = []
        for variant in ('ternary_context_control', 'mixed_binary_context'):
            rows = motifs['variants'][variant]['methods'][method]['rows']
            hits.append(sum(r['accepted'] is not None for r in rows))
        lines.append(f'| {method} | {hits[0]}/24 | {hits[1]}/24 |')
    lines += ['', '`proof_wl` 索引历史证书前提，查询侧只取所有二元子句；它没有得到隐藏 query core。'
              '`proof_canonical` 对同一局部视图做精确规范化。三元上下文中二元投影几乎直接隔离了 motif，'
              '所以局部 canonical 同样 24/24：这个成功不能说明 WL 超越了显然的局部结构复用。', '',
              '加入同宽度噪声后，proof-WL 7/24、随机 6/24、MinHash 7/24；目前没有证据说明'
              'proof-WL 在这个困难版本明显更好。局部 canonical 此时为 0/24。所有负例均未接受错误 UNSAT。', '',
              '这是人工、较小、二元 motif 的实验，不能外推到工业 UNSAT proof fragments 或任意宽度的隐蔽 motif。', '',
              '## 证据与下一步', '',
              '22 项测试通过，包括子进程超时必须返回未命中；审计脚本重新检查了所有记录的迁移映射、'
              'SAT 模型、UNSAT resolution 证明及负例。检查器没有扩大可信边界。', '',
              '当前证据支持“重命名不变的结构检索可以产生额外合法复用”。还不能支持'
              '“已经学到了比公式相似度更强的通用 certificate transferability”。下一步应把困难混合 motif '
              '作为主评估集，并使用经过检查的候选证书迁移结果作为监督标签；超时不能标成不可迁移。', '',
              '协议：[docs/round2-protocol.md](docs/round2-protocol.md)。原始数据：'
              '[检索](results/round2-permutation.json)、[100 查询映射](results/round2-matching.json)、'
              '[同表示 scorer](results/round2-feature-baselines.json)、[motif](results/round2-motif.json)、'
              '[审计](results/round2-audit.json)。重命名私有映射和 motif oracle 单独保存，不作为系统输入。']
    Path('ROUND2_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('Wrote ROUND2_RESULTS.md; no-cache verified query median:', statistics.median(baseline))


if __name__ == '__main__':
    main()
