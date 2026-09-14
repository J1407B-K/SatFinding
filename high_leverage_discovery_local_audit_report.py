"""Validate saved local comparisons and report; no solver executions."""
import csv,json
from collections import Counter
from pathlib import Path
ROOT=Path('results/high_leverage_discovery_local_audit')
s=json.loads((ROOT/'summary.json').read_text());rows=s['rows']
classes=['L0_NO_LOCAL_DIVERGENCE','L1_PROPAGATION_ONLY','L2_CONFLICT_DIVERGED','L3_LEARNED_DIVERGED','L4_DECISION_DIVERGED']
for v in [s['aggregate'],*s['per_target'].values()]:
 v['classification_counts']={c:v['classification_counts'].get(c,0) for c in classes}
assert len(rows)==84 and len(list(csv.DictReader((ROOT/'all_84_local_divergence.csv').open())))==84
verified=0;traces=0
for t in ['T8','T10','T13']:
 for p in (ROOT/t).glob('*.result.json'):
  r=json.loads(p.read_text());assert r['final_counters_match_original'] and r['same_proof_hash_as_original'] and r['proof_validation']=='VERIFIED'
  assert 's VERIFIED' in (ROOT/t/(r['route']+'.proof_check.txt')).read_text();verified+=1
  for e in r['events']:
   if e['event']=='LOCAL_TRACE':assert e['conflict_index'] and e['learned_seen'] and e['next_decision_literal'] is not None;traces+=1
assert verified==87 and traces==168
s['audit']={'reruns':87,'verified_proofs':87,'same_proof_sha256_as_original':87,'complete_local_windows':168,'counter_mismatches':0,'missing_windows':0,'unavailable_learned_or_next_decision':0}
s['interpretation']={'majority_no_observed_local_divergence':True,'zero_ops_cases':{'L0':70,'L1':13,'L2_L3_L4':0},'rarity_supported':False,'conclusion':'70/84 (83.33%) unchanged at all four observed layers;14/84 change dequeue order only. This protocol does not supply evidence for rarity of fixed-case high leverage.','next_stage_performed':False}
(ROOT/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
lines=['# High-leverage discovery local trajectory audit','',
'**70/84 为 L0，14/84 为 L1；L2/L3/L4 全部为 0。** 本轮只复跑已有事件，不更换采样点，不执行新 intervention。','',
'比较从原 intervention 的 pre-action event 开始，记录到下一 conflict 的 dequeue literal 序列、该 conflict 的 stable clause ID / canonical SHA-256、analysis 输出的 learned clause canonical SHA-256，以及该 conflict 后第一条实际 branch decision literal。如果中间还有 conflict 或 restart，只等待那条 next decision，不 dump 中间轨迹。','',
'`propagation_diverged` 按实际 dequeue 序列比较，不把 enqueue 调用提前这一事实自动判为分叉。`conflict_diverged` 在 stable ID 或 canonical hash 不同时为 true；learned 按 canonical hash 比较；decision 按 literal 比较。canonical hash 对 signed literals 排序后计算，因此不把同一 learned clause 的内部排列差异当作 learned divergence。四个 flags 独立保留，classification 取最深层。L0 仅表示这四项观察相同，不声称完整 solver 内部状态相同。','',
'所有复跑在计算 flags 前均检查非时间 final counters 与各自原始 route 一致；3 个 baseline 和 84 个 intervention 共 87 份 UNSAT proof 重新由独立 drat-trim VERIFIED，且 proof SHA-256 全部与原实验一致。168 个局部窗口全部记录到 conflict、learned clause 和 next decision，无缺失。没有遗漏的明显 final divergence。','',
'| Target | 样本 | Propagation不同 | Conflict不同 | Learned不同 | Decision不同 | L0 | L1 | L2 | L3 | L4 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for t,v in [*s['per_target'].items(),('合计',s['aggregate'])]:
 f=v['flag_counts'];c=v['classification_counts'];values=[v['count'],*f.values(),*c.values()]
 lines.append('| '+t+' | '+' | '.join(map(str,values))+' |')
lines+=['',
'14 个真正发生 dequeue 分叉的 intervention 中，13 个 final ops delta 为 0%；仅 T8/C4250 为 −1 op（219,571 → 219,570，−0.00045543355%）。全部基本为 0%，但没有任何样本到达 conflict / learned / decision 分叉，因此不能套用“大量 L2/L3/L4 后仍无长期收益”的解释。','',
'| Target | Dequeue 分叉桶 | Final ops delta 分布 |','|---|---|---|']
for t in ['T8','T10','T13']:
 rr=[r for r in rows if r['target']==t and r['propagation_diverged']]
 dist='4 × 0%；1 × −0.00045543355%' if t=='T8' else f'{len(rr)} × 0%'
 lines.append('| '+t+' | '+', '.join('C'+str(r['bucket']) for r in rr)+' | '+dist+' |')
lines+=['',
'83 个 final ops 完全不变的样本可拆成 **70 个 L0 + 13 个 L1**。因此主体现象是没有改变所观测的局部轨迹；另有少数改变 dequeue 顺序，但随后所观测的 conflict、learned 和 next decision 相同。这里的相同不等价于证明其它未记录内部状态完全重合。','',
'这次 sanity check 限制了上一轮阴性结果的解释：84 次未命中 ≥10% 的结果不能用来支持 fixed-case phenomenon 稀有。按预注册边界，如果要继续 discovery，需重新设计能真正改变 propagation order 的协议；本轮仅报告这一方向，没有设计或运行下一阶段。','',
'逐样本完整 flags、最深分类、clause hashes、next decisions 和 ops delta 见 [all_84_local_divergence.csv](all_84_local_divergence.csv)。各 target 的 `C*.local_comparison.json` 保留 baseline / intervention 两条完整局部 dequeue 序列；`*.result.json` 和 `*.proof_check.txt` 保留 counters 与 proof 验证。','',
'1. **84 次 intervention 中多少次真正改变了 propagation trajectory？** 14 次（16.67%）改变实际 dequeue 序列；70 次（83.33%）在四项观察上均无差异。','',
'2. **多少次进一步改变 conflict / learned / next decision？** 分别为 0 / 0 / 0；14 次均仅为 L1_PROPAGATION_ONLY。','',
'3. **83 次 0% final ops 更像未打中 trajectory，还是改了但无长期 leverage？** 主要是前者：70 次 L0。另有 13 次改变 dequeue 顺序但没有 final ops 收益。不存在大量更深局部分叉后仍无 leverage 的证据。','',
'4. **当前证据是否足以说 fixed-case high-leverage event 稀有？** 不足。当前协议大部分合法 early enqueue 未改变观察到的 propagation/conflict trajectory，不能据此支持稀有性；本阶段完成后停止。','']
(ROOT/'HIGH_LEVERAGE_DISCOVERY_LOCAL_AUDIT.md').write_text('\n'.join(lines))
print(json.dumps({'aggregate':s['aggregate'],'audit':s['audit']},indent=2))
