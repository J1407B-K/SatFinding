"""Report existing frozen frontier results only; no solver/probe execution."""
import csv,json
from pathlib import Path
from collections import Counter
from conflict_frontier_discovery import OUT,OLD,sha,dump,events,chash
s=json.loads((OUT/'discovery_summary.json').read_text());full=json.loads((OUT/'full_run_summary.json').read_text());frozen=json.loads((OUT/'frozen_event.json').read_text())
rows=list(csv.DictReader((OUT/'local_probe_summary.csv').open()))
assert len(rows)==181 and all(r['target']=='T8' for r in rows)
assert [int(r['opportunity']) for r in rows]==list(range(1,182))
assert [int(r['opportunity']) for r in rows if r['conflict_diverged']=='True']==[181]
count=0
for i in range(1,182):
 comparison=json.loads((OUT/'T8'/f'P{i}.comparison.json').read_text())
 for role,key in [('BASELINE','baseline'),('EARLY','early')]:
  e=events(OUT/'T8'/f'P{i}_{role}.trace.jsonl')
  assert sum(x['event']=='LOCAL_RESULT' for x in e)==1
  assert sum(x['event']=='EARLY_ENQUEUE' for x in e)==(role=='EARLY')
  assert all(x['event'] not in ['FINISH','NEXT_DECISION'] for x in e)
  count+=1
 assert comparison['baseline']['pre']==comparison['early']['pre']
assert count==362 and sha(OUT/'frozen_event.json')==full['frozen_event_sha256']
for role in ['BASELINE','EARLY']:
 assert 's VERIFIED' in (OUT/'full'/f'P181_{role}.proof_check.txt').read_text()
assert full['baseline_matches_original_counters'] and full['local_replay_matches_stage1'] and full['same_pre_state_by_os_fork']
s['audit']={'local_pairs':181,'local_children_stopped_after_first_analysis':362,'full_runs':2,'full_proofs_verified':2,'all_local_pairs_identical_pre_state_by_os_fork':True,'full_replays_match_frozen_local_traces':True,'discovery_stopped_at_first_conflict_change':True,'extra_targets_run':False,'parent_bookkeeping_recovery':'parent_bookkeeping_recovery.json'}
s['conclusion']={'second_conflict_perturbation_case_found':True,'second_independent_high_leverage_case_found':False,'effect':'slowdown','relative_ops_delta_percent':full['relative_ops_delta_percent'],'interpretation':'Conflict/learned/next decision changed; final cost increased8.375%, below10% threshold but not approximately zero. Do not force the near-zero interpretation.','eligible_to_compare_two_high_leverage_positive_cases':False,'stopped':True}
dump(OUT/'discovery_summary.json',s)
b=full['baseline'];p=full['early'];o=full['opportunity'];bl=b['trace']['local'];pl=p['trace']['local']
lines=['# Conflict-frontier discovery','',
'**在 T8 的第 181 个合法机会找到首个 conflict-changing event（L3）。完整求解为 slowdown 8.375%，未达到冻结的 ≥10% high-leverage 阈值。** 已停止 discovery，没有运行 T10/T13，也没有继续寻找效应更大的事件。','',
'协议在运行前保存于 `protocol.json`：每个 target 上限 500 个机会；按完成 enqueue 后及 search-loop 入口的真实观察顺序枚举新出现的合法 clause/literal episode，同一时点按 stable allocation ID 排序，连续合法 episode 不重复计数。没有 clause/literal/feature 筛选，没有查看最终 ops 来选点。该“顺序”是指定安全观察位置的顺序，不声称覆盖 native 指令之间所有瞬间。','',
'每个局部 probe 在暂停的 baseline 父进程中执行两次顺序 OS fork。父进程等待期间没有 solver mutation，因此两条分支继承相同 solver 内存、指针和调用栈；除输出流及 observer 元数据外，未做状态重建或 transplant。双方 pre-state 指纹一致，perturb 分支在唯一一次 uncheckedEnqueue 前重新检查真实 unit 和 native layout。局部 child 在下一 conflict 的 analyze 返回 learned clause 后立即退出；不做之后的 backtrack、next decision 或完整求解。','',
'| Target | 已检查机会 | L0 | L1 | L2 | L3 | 停止原因 |','|---|---:|---:|---:|---:|---:|---|',
'| T8 | 181 | 45 | 135 | 0 | 1 | 首个 next-conflict canonical hash 改变 |',
'| T10 | 0 | — | — | — | — | 按命中停止规则未运行 |',
'| T13 | 0 | — | — | — | — | 按命中停止规则未运行 |','',
'前 180 个事件中没有 conflict change；第 181 个立即保存为 `frozen_event.json`，随后才执行 Stage 2。362 个 local children 均仅运行到首个 conflict analysis 结束；完整 solver 只运行被冻结事件的两条分支。','',
'冻结事件：','',
f"- target / opportunity：T8 / 181；completed conflict / decision / level：{o['conflict']} / {o['decision']} / {o['level']}。",
f"- pre-state FNV64：`{o['pre_state_fnv64']}`；原 enqueue event 计数 {o['global_enqueue']}，early enqueue 为 {o['global_enqueue']+1}。",
f"- 合法原始 reason clause：#{o['reason_id']} `{o['reason_literals']}`；implied literal `{o['literal']}`。",
f"- reason canonical SHA-256：`{o['reason_canonical_sha256']}`。",
'- 在线合法性：变量100未赋值，literal −562 为 false，因此 clause 当前唯一未赋值 literal 为 −100；二元 clause 满足原生 reason layout。只提前 enqueue 一次 −100，没有 clause/watch/heuristic 修改。','',
'| 观察 | BASELINE | EARLY_PROP |','|---|---|---|',
f"| Dequeue 序列开头 | `{bl['dequeue_literals'][:8]}` | `{pl['dequeue_literals'][:8]}` |",
f"| 到 conflict 的 dequeue 数 | {len(bl['dequeue_literals'])} | {len(pl['dequeue_literals'])} |",
f"| Next conflict index | {bl['conflict_index']} | {pl['conflict_index']} |",
f"| Conflict clause | #{bl['conflict_clause_id']} `{bl['conflict_clause_literals']}` | #{pl['conflict_clause_id']} `{pl['conflict_clause_literals']}` |",
f"| Learned clause | `{bl['learned_clause_literals']}` | `{pl['learned_clause_literals']}` |",
f"| Conflict 后 next decision | {b['next_decision']['literal']} | {p['next_decision']['literal']} |",' ',
'这里的 next decision 都出现在 completed conflict 2 后：conflict 1 后还有一次 conflict，随后才产生实际 decision。没有将断言传播当作 decision。两条完整分支的局部序列、conflict、learned 与 Stage 1 精确复现。完整局部序列与 canonical hashes 见 `T8/P181.comparison.json` 和 `full_run_summary.json`。','',
'| 完整求解 | BASELINE_FULL | EARLY_PROP_FULL |','|---|---:|---:|']
for label,key in [('Analysis ops','analysis_resolution_steps'),('Conflicts','conflicts'),('Decisions','decisions'),('Propagations','propagations')]:lines.append(f"| {label} | {b['stats'][key]:,} | {p['stats'][key]:,} |")
lines+=['| Status | UNSAT | UNSAT |','| Independent drat-trim | VERIFIED | VERIFIED |',f"| Relative ops delta | 0% | +{full['relative_ops_delta_percent']:.6f}% |",'| HIGH_LEVERAGE ≥10% | — | false |','',
'BASELINE_FULL 的所有非时间 counters 与原 T8 baseline 一致。Stage 2 再次从共同前缀 OS fork 两条完整分支，proof 使用相同精确前缀并分写文件。两份 proof 均独立验证通过。墙钟计时包含父进程等待，不作性能比较。','',
'执行记录：两条 full child 成功完成后，父进程误检查 child-only flag，进入局部文件读取分支，报 `MISSING_LOCAL_RESULT`。已有 child counters、局部 trace 和 proofs 均完整。恢复仅读取并验证这些文件，没有重跑 solver。原执行源码和哈希、错误输出、恢复说明已保留；源码修正仅将父进程完成判断换为 full-mode 参数，修正版本未追加执行。详见 `parent_bookkeeping_recovery.json`。','',
'结果没有落入“完整效应约0%”分支：ops 增加18,389（8.375%）是可见的长期 search-cost 变化，只是低于预注册10%阈值。不能据此声称改变一次 conflict 没有长期作用，也不能事后降低阈值将它命名为第二个 high-leverage case。','',
'1. **是否找到独立 conflict-changing event？** 是，T8 第181个合法机会；next conflict 与 learned clause 均改变，Stage2 的 next decision 也不同。','',
'2. **是否得到第二个独立 ≥10% high-leverage case？** 没有：219,571 → 237,960 ops，slowdown8.375%，低于10%。','',
'3. **本轮支持什么解释？** 合法单次 early propagation 可以在另一CNF中改变 conflict frontier，并产生低于阈值的长期成本变化。不能套用“final约0%”的强阴性解释，也不能据此判断稀有性。','',
'4. **是否已有资格比较两个 high-leverage positive case 抽共性？** 尚无。已得到第二个 conflict-changing case，但仍缺第二个符合冻结阈值的 high-leverage case；本阶段已停止，不追加实验。','']
(OUT/'CONFLICT_FRONTIER_DISCOVERY.md').write_text('\n'.join(lines))
print(json.dumps(s['audit'],indent=2))
