"""Audit and report completed fixed-state surface; no additional solver runs."""
import csv,json
from pathlib import Path
from fixed_state_action_surface import OUT,events,sha,dump
s=json.loads((OUT/'response_surface_summary.json').read_text());rows=s['rows_sorted_by_effect_after_selection'];state=json.loads((OUT/'frozen_state.json').read_text());es=events(OUT/'runs/opportunities.jsonl')
assert len(rows)==s['tested_action_count']==s['legal_action_count']==5
assert state['analysis_ops_at_snapshot']==0 and state['pre_state_hash']=='422271443557180589'
actions=[e for e in es if e['event']=='LEGAL_ACTION'];assert [a['stable_clause_id'] for a in actions]==[831,833,1269,1271,1273]
assert len(list(csv.DictReader((OUT/'legal_actions.csv').open())))==5
assert len(list(csv.DictReader((OUT/'all_action_runs.csv').open())))==5
assert len(list(csv.DictReader((OUT/'local_effects.csv').open())))==5
assert all(e['wait_status']==0 for e in es if e['event']=='CHILD_EXIT')
for tag in ['BASELINE']+[f'ACTION_{i}' for i in range(1,6)]:
 r=json.loads((OUT/'runs'/(tag+'.result.json')).read_text());pre=next(e for e in r['trace'] if e['event']=='PRE_STATE')
 assert pre['hash']==state['pre_state_hash'] and pre['raw_solver_object_hash']==state['raw_solver_object_hash'] and pre['heap_including_inverse_hash']==state['heap_including_inverse_hash']
 assert r['stats']['status']=='UNSAT' and r['proof_validation']=='VERIFIED'
 assert 's VERIFIED' in (OUT/'runs'/(tag+'.proof_check.txt')).read_text()
s['audit']={'all_legal_actions_run':True,'selection_frozen_before_any_child':True,'all_six_children_from_same_paused_parent':True,'parent_state_rechecked_before_each_fork':True,'operational_raw_object_and_heap_inverse_hashes_match_in_all_children':True,'baseline_and_two_prior_controls_reproduced':True,'verified_proofs':6,'additional_state_or_target':False}
s['interpretation']={'classification':'STATE_ACTION_INTERACTION','basis':'Preregistered same-state high-leverage+zero criterion satisfied:3 strong speedups,2 exact0 actions.','has_speedup_and_slowdown':False,'has_high_leverage_and_zero':True,'scope':'Action-dependent response at this single exact state; not a cross-state factorial interaction estimate or a universal action-ranking rule.','next_priority':'action selection within a fixed sensitive state','next_stage_executed':False,'stopped':True}
dump(OUT/'response_surface_summary.json',s)
lines=['# Fixed-state action response surface','',
'**同一个exact state S下，5个合法action产生3个强speedup与2个exact0，效应范围−46.918%至0%。** 满足预注册的“同state下high-leverage + zero”判据，支持本状态的STATE_ACTION_INTERACTION。没有slowdown。','',
'S是既有T10_P226/P227共享的状态：pre-state hash `422271443557180589`，completed conflict0、decision18、level18、trail263、qhead252、pending11、global enqueue263。此次只恢复这个既有prefix，未搜索新state或target。','',
'baseline和全部action均从同一个暂停父进程执行OS fork，继承同一内存与原生调用栈，而非分别重建state。父进程在每次fork前检查原operational fingerprint和raw Solver object hash，所有child在任何action前核对这两项及包含inverse indices的heap hash。fork同时保持动态内存内容，因此assignment/trail/levels/qhead、activity、heap+inverse、clause DB/watches、phase/restart、counters及RNG固定；仅输出流和observer记账按branch分开。`frozen_state.json`是这份内存快照的审计manifest，不是可单独加载的序列化checkpoint。','',
'在S处只读扫描全部active original/learned clauses，枚举所有真实unit、implied literal未赋值且native reason layout合法的action。全部5个均是原始二元clause，implied literal位于index0，其余literal为false。按stable clause ID先冻结完整列表，再执行baseline及所有action；未达到32上限，无筛选或替换。效应排序仅发生在完整结果产生后。','',
'| 选择顺序 | Clause ID | Clause literals | 提前literal | 原生unit/layout |','|---:|---:|---|---:|---|']
for a in actions:lines.append(f"| {a['action_index']} | {a['stable_clause_id']} | `{a['clause_literals']}` | {a['implied_literal']} | VERIFIED |")
lines+=['',
'baseline-from-S为360,959 analysis ops。S处analysis ops为0，因此这里的“从S剩余ops”与最终累计ops相同；其它final counters继续使用solver原生累计计数，未reset任何counter。每个action只执行一次native uncheckedEnqueue，然后原生求解。','',
'按最终effect排序的response surface（排序未参与选择）：','',
'| Action | Clause / literal | Final ops | Δ ops | Sign | ≥10% | Local classification |','|---|---|---:|---:|---|---|---|']
for r in rows:lines.append(f"| {r['action_id']} | #{r['clause_id']} → {r['implied_literal']} | {r['ops']:,} | {r['relative_ops_delta_percent']:+.3f}% | {r['sign']} | {'yes' if r['HIGH_LEVERAGE'] else 'no'} | {r['local_classification']} |")
lines+=['',
'5个action加1个baseline均UNSAT，6份proof独立drat-trim VERIFIED。baseline复现既有T10的全部非时间counters和proof哈希；#831与#833两条原有action也精确复现各自旧counters及proof哈希。','',
'| Action | Dequeue不同 | Conflict不同 | Learned不同 | Next decision不同 | Next decision |','|---|---|---|---|---|---:|']
for r in s['local_effects']:lines.append(f"| {r['action_id']} | {r['propagation_diverged']} | {r['conflict_diverged']} | {r['learned_diverged']} | {r['decision_diverged']} | {r['next_decision_literal']} |")
lines+=['',
'三个强speedup均改变到next decision层；两个zero action只改变dequeue序列，下一conflict、learned与decision均与baseline相同。因此在该S处，仅知道“state曾对某些action敏感”不足以预测所有合法action都会产生大效应。这里3/5为大效应，不能描述为只有极少数action有效，也没有观察到连续响应分布或正负混合。','',
'**STATE_ACTION_INTERACTION**按本轮预注册判据成立：同一exact state出现high-leverage与zero。该结论具体指响应取决于S下执行哪个action；本实验只有一个state，不是跨多个state的交叉设计，不能估计正式的跨state interaction项或推广出全局action排序规则。也没有依据把无slowdown解释为该state下所有可能的扰动都安全。','',
'数据文件：[frozen_state.json](frozen_state.json)、[legal_actions.csv](legal_actions.csv)、[all_action_runs.csv](all_action_runs.csv)、[local_effects.csv](local_effects.csv)、[response_surface_summary.json](response_surface_summary.json)。完整dequeue序列、conflict/learned hash和next decision均已保留；没有添加新abstraction feature。','',
'1. **S下共有多少个合法latent actions？** 5个，全部运行，无截断。','',
'2. **不同action的effect range？** −46.917517%至0%，跨度46.917517个百分点；三个speedup分别−26.201%、−33.076%、−46.918%。','',
'3. **是否存在同state下speedup / slowdown / zero混合？** 有speedup与zero混合（3对2），没有slowdown；明确存在high-leverage与zero。','',
'4. **更支持哪一类？** 按预注册标准为STATE_ACTION_INTERACTION，限定于该exact state下的action-dependent response，不做跨state推广。','',
'5. **下一步优先研究state还是action selection？** 优先action selection：已知敏感state仍包含无长期效应和大幅speedup的合法action。尚无通用选择规则，本轮未开展后续研究，完成后停止。','']
(OUT/'FIXED_STATE_ACTION_SURFACE.md').write_text('\n'.join(lines))
print(json.dumps(s['interpretation'],indent=2))
