"""Read-only reverse-transplant audit and report."""
import gzip,json,hashlib
from pathlib import Path
P=Path('results/heuristic_reverse_transplant');OLD=Path('results/persistent_state_imprint');N='A_WITH_B_HEURISTIC'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def events(p):return list(map(json.loads,gzip.open(p,'rt')))
r=read(P/(N+'.result.json'));proto=read(P/'protocol.json')
assert all(sha(Path(p))==h for p,h in proto['sources'].items())
with gzip.open(P/(N+'.drup.gz'),'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==r['proof_sha256']
assert 's VERIFIED' in (P/(N+'.proof_check.txt')).read_text()
a=read(OLD/'A.ps_before.snapshot.json');b=read(OLD/'B_REMOVE_L2.ps_before.snapshot.json');pre=read(P/(N+'.ps_before.snapshot.json'));post=read(P/(N+'.ps_after.snapshot.json'))
assert pre==a and post['activity']==b['activity'] and post['heap']==b['heap']
assert {k:v for k,v in pre.items() if k not in ['activity','heap']}=={k:v for k,v in post.items() if k not in ['activity','heap']}
assert sha(P/(N+'.before.other.bin'))==sha(P/(N+'.after.other.bin'))
assert sha(P/(N+'.after.allowed.bin'))==sha(OLD/'B_REMOVE_L2.before.allowed.bin')
leg=read(P/(N+'.legality.json'));assert leg['heap_valid'] and leg['missing_eligible']==0
runs=read(OLD/'runs.json');runs={k:runs[k] for k in ['A','B','B_REMOVE_L2','B_REMOVE_L2_ACTIVITY_HEAP_RESET']};runs[N]=r
ledgers={k:events((P if k==N else OLD)/(k+'.events.jsonl.gz')) for k in runs}
comparisons={}
for k in runs:
 if k=='A':continue
 out={}
 for typ,field in [('D','v'),('L','r')]:
  left=[v for v in ledgers['A'] if v.get('t')==typ and (v['d']>=830 if typ=='D' else v['c']>660)]
  right=[v for v in ledgers[k] if v.get('t')==typ and (v['d']>=830 if typ=='D' else v['c']>660)]
  mismatch=next(((x,y) for x,y in zip(left,right) if x[field]!=y[field]),None)
  out[typ]=dict(A=mismatch[0],other=mismatch[1]) if mismatch else None
 comparisons[k]=out
# Exact recorded pre-hook event ledger equality (600..660 window); deterministic
# identical input/search code through hook additionally guarantees the earlier prefix.
assert [x for x in ledgers[N] if 'g' in x and x['g']<=pre['global']]==[x for x in ledgers['A'] if 'g' in x and x['g']<=pre['global']]
audit=dict(status='PASS',checkpoint={k:pre[k] for k in ['c','d','dl','qhead']},legality=leg,hashes=r['hashes'],donor_allowed_sha256=sha(OLD/'B_REMOVE_L2.before.allowed.bin'),pre_snapshot_matches_A=True,observed_prefix_matches_A=True,proof_verified_on_A_input=True,comparisons_to_A_after_checkpoint=comparisons,source_hashes_valid=True)
(P/'audit.json').write_text(json.dumps(audit,indent=2))
rows=[]
for n,v in runs.items():
 st=v['stats'];d=comparisons.get(n,{}).get('D');l=comparisons.get(n,{}).get('L')
 ds='—' if not d else f"d{d['A']['d']}: {d['A']['v']:+d} → {d['other']['v']:+d}"
 ls='—' if not l else f"C{l['A']['c']}"
 rows.append(f"| {n} | {st['analysis_resolution_steps']:,} | {st['conflicts']:,} | {st['decisions']:,} | {ds} | {ls} | VERIFIED |")
print(json.dumps(comparisons[N],indent=2))
report='''# Heuristic state reverse transplant

**B_REMOVE_L2 的 joint activity+heap 可以合法移植到 A，并将 A 从 345,592 ops 降至 174,360 ops。** 比 B_REMOVE_L2 的 174,427 少 67 ops；本固定 checkpoint 上有强 transfer-sufficiency evidence，但不等于复制了 B 的完整轨迹，也不支持跨 target 普遍结论。

## 1. 合法移植与 audit

唯一干预为 `A_WITH_B_HEURISTIC`。与上一轮完全相同：完成 C660、传播清空、d830 的 native pick 之前，dl=8，qhead=trail.size=57。donor 是冻结 B_REMOVE_L2 的同一 checkpoint，recipient 从原 A 输入运行，未安装 L2。

移植前在副本上验证 heap 排序、inverse indices 和 eligible unassigned variable coverage，全部合法，missing=0；没有 heapify、修改 phase、补变量或移动时刻。activity doubles、heap array/inverse indices 完整复制，comparator 仍引用 A 自己的 activity vector。var_inc 等其余 metadata 保留 A。

A 的 pre-hook logical snapshot 与自然 A 完全相同；保存的 C600 至 hook 的逐事件前缀完全相同，更早前缀由相同输入/求解代码保证，未保存整段逐事件日志。移植后 allowed bytes 与 B_REMOVE_L2 donor 完全相同，非目标完整对象与 live buffer SHA-256 不变。覆盖 assignments/trail/levels/reasons、原始/learned DB、allocator 内容、watch/dirty metadata、phase、restart queues 和 native counters；指针原始字节 hash 只用于同进程前后审计，不用于跨进程比较。search 栈局部变量不被 hook 修改。

完整 UNSAT proof 在 **A.cnf** 上通过 drat-trim；不是在含 L2 的输入上验证。构建时曾因 donor 文件缺失在写入前退出，修复文件交付后才完成唯一配置，时刻和字段未变。未追加 intervention。

## 2. 五条固定配置

最后两列分叉以自然 A 为参照，只比较移植时刻以后；B 类轨迹此前已有分叉，不应把这里的后缀比较误作全程首次分叉。

| run | ops | conflicts | decisions | 首个 post-checkpoint decision 差异 vs A | 首个 post-checkpoint learned 内容差异 vs A | proof |
|---|---:|---:|---:|---|---|---|
'''+ '\n'.join(rows)+'''

前四行使用上轮冻结且 proof-verified 的结果；本轮只增加反向移植配置。

## 3. 是否复制短轨迹，carrier 如何分类？

A 的 ops 减少 171,232（约49.55%），获得自然 A→B_REMOVE_L2 收益的约100.04%。67 ops 差别不代表更优方法；这里只能说搜索长度非常接近。conflicts/decisions 并不相同，未证明逐事件复制 B_REMOVE_L2。

结合前轮拿走 B heuristic state 后 174,427→292,662，以及本轮给 A 后 345,592→174,360，这对联合 activity+heap 是 **necessary-like 且 sufficient-like carrier** 的强局部证据。更准确说，它在此 A recipient context 中足以转移大量收益；不是形式逻辑必要性或对任意 context 的充分性。其余 A state 并非无关，而是在本次受控替换中保留不动。

activity-only / heap-only 的前轮候选因排序不变量失败而中止；不能根据联合结果判定哪一个单独更关键。

## 4. 机制链更新

`L2 改变 reason/analysis history → C660 时形成 joint activity+heap imprint → 即使无 L2，也可将该 imprint 转交 A → 后续选择/学习反馈改变 → 长尾搜索大幅缩短`。

本轮直接干预支持后半链的 transfer sufficiency。reason/analysis 如何精确写出这一 imprint、每一次后续 learned 如何避免具体长尾，仍需事件级解释；本轮没有完整识别这些步骤。不能把全部171k收益归因于单个 bump 或单个 branch。

## 5. 下一步唯一最小工作

只读对齐 A_WITH_B_HEURISTIC 与 B_REMOVE_L2 的 d830 后第一个 learned/decision 分叉，检查两者为何在不同 learned/reason DB 下仍到达近似长度的短轨迹。先定位首个不同 antecedent 与 bump，暂不增加字段移植。

证据：[audit.json](results/heuristic_reverse_transplant/audit.json)、[result](results/heuristic_reverse_transplant/A_WITH_B_HEURISTIC.result.json)、[protocol](results/heuristic_reverse_transplant/protocol.json)。复核入口：`python3 heuristic_reverse_report.py`。
'''
Path('HEURISTIC_STATE_REVERSE_TRANSPLANT.md').write_text(report)
