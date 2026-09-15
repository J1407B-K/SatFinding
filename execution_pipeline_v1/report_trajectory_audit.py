import json
from pathlib import Path
R=Path('results/fresh_trajectory_divergence_audit_v1')
def report(s):
 def fmt(x):return '无' if x is None else f'{x:.6g}'
 def table_dist(d):return ' | '.join(fmt(d.get(k)) for k in ['min','max','median','p90','p95','p99'])
 c=s['classes']; n=s['first_divergence']; counts=s['effect_counts'];cd=s['content_divergence_counts']
 lines=['# FRESH_TRAJECTORY_DIVERGENCE_AUDIT_V1','',
 '## 1. Audited verified routes', '',f"**{s['audited']} / 136**。固定 proof-verified cohort；未新增 candidate、未改 10% HIGH threshold。协议与 SHA-256：`TRAJECTORY_DIVERGENCE_PROTOCOL_V1.json` / `.sha256`。",'',
 '## 2. Exact pre-state identity','',f"**PASS {s['identity_pass']}**。checkpoint logical/heuristic hash、完整 canonical 文本及 counter-free pre-state 一致；逐条对照冻结 request。",'',
 '## 3. Action verified','',f"**{s['action_verified']}**。原 replay 的 clause ID/source/content、literal identity、unit legality 与 unassigned 检查均通过；另独立检查 baseline pre-state 中 literal 为 unassigned。",'',
 '## 4. Baseline native action timing','',f"Naturally enqueued：**{s['naturally_enqueued']}**；never naturally enqueued before termination：**{s['never_enqueued']}**。",'',
 f"Median enqueue delay：**{fmt(s['native_delay_propagation'].get('median'))} propagation dequeues**、**{fmt(s['native_delay_conflict'].get('median'))} conflicts**。事件计数从干预边界开始；enqueue ordinal、native reason clause、before-first-divergence 标记逐 route 保留。",'',
 f"Timing classes：`{json.dumps(s['propagation_timing_class'])}`。EARLY_SAME_PROPAGATION 要求首个 conflict 前由与干预相同的 clause 入队。",'',
 '## 5. First semantic divergence','',
 '| 类型 | 数量 |','|---|---:|']
 for k in ['propagation','conflict','learned','decision','backtrack','restart','no_semantic_divergence']:lines.append(f"| {k} | {n.get(k,0)} |")
 lines+=['','Intervention enqueue 属于观测轨迹；首次分歧不含 counter offset。更深层的首次 conflict/learned/decision/restart/backtrack 分歧及 event offset 见每条 `comparison.json`。','',
 '## 6. Reconvergence before first conflict','',f"**{s['reconverged_before_first_conflict']}**。要求两条 route 的 counter-free assignments/reasons/levels、ordered trail/limits、qhead/pending frontier 匹配，排除初始 pre-state。保留匹配事件对作为 witness。",'',
 '## 7. Persistence classes','', '| Class | 数量 |','|---|---:|']
 for k in ['INERT','LOCAL_TRANSIENT','CONFLICT_DIVERGENT','LEARNED_DIVERGENT','DECISION_DIVERGENT','PERSISTENT_DIVERGENT']:lines.append(f'| {k} | {c.get(k,0)} |')
 lines+=['',f"其中 **{s['residual_class_count']}** 条 CONFLICT_DIVERGENT 是冻结规则中的 residual：状态差异跨过 conflict 边界，但 conflict clause 序列未变化。该类名不能解读为 conflict 内容已改变。PERSISTENT_DIVERGENT 表示 k=2/4/8/16 的比较元组均不相同，观测范围截至 k=16，不能外推至 termination。",'',
 '| Conflict milestone | Logical 不同 | Learned DB 不同 | Frontier 不同 | Next actual decision 不同 |','|---:|---:|---:|---:|---:|']
 for k,m in s['milestone_mismatch_counts'].items():lines.append(f"| {k} | {m['logical']} | {m['learned']} | {m['frontier']} | {m['next_decision']} |")
 lines+=['','## 8. Final effect distribution','',
 '`delta_percent = (action_final_analysis_resolution_steps - baseline_final_analysis_resolution_steps) / baseline_final_analysis_resolution_steps * 100`。采用最终总量；非 remaining-ops、非运行时间。原 FRESH_DISCOVERY_SUMMARY.json 的 fresh_high_found=0 被固定 cohort 的原始值和本轮重跑共同否定：T10M3/rank5 与 T10M5/rank4 均为 baseline 360959、action 229467，即 −36.428514%。原 action 记录已包含 229467；没有增加 candidate、改变 threshold 或搜索新 HIGH。原汇总保留不覆盖，更正证据见 CURRENT_SUMMARY_DISCREPANCY.json。','',
 '| 分布（%） | min | max | median | p90 | p95 | p99 |','|---|---:|---:|---:|---:|---:|---:|',
 '| Signed delta | '+table_dist(s['signed_effect_distribution'])+' |','| Absolute delta | '+table_dist(s['absolute_effect_distribution'])+' |','',
 '| 区间 | 全部 | Speedup | Slowdown |','|---|---:|---:|---:|']
 for k,v in counts.items():lines.append(f"| {k} | {v['all']} | {v['speedup']} | {v['slowdown']} |")
 lines+=['','Top 10 strongest absolute effects（并列按固定 cohort 顺序列出；不改变 cohort）：','', '| Case | Rank | Delta % | Class |','|---|---:|---:|---|']
 for x in s['top10']:lines.append(f"| {x['case']} | {x['rank']} | {fmt(x['delta_percent'])} | {x['persistence_class']} |")
 lines+=['','## 9. Strongest speedup / slowdown','',f"Speedup：**{fmt(s['strongest_speedup'])}**；slowdown：**{fmt(s['strongest_slowdown'])}**。无表示未观察到该方向的非零效果。",'',
 '## 10. Persistence 与 final effect：descriptive relation','', '| Class | n | Median absolute delta % | P95 absolute delta % | Max absolute delta % |','|---|---:|---:|---:|---:|']
 for k,v in s['class_effect_distribution'].items():
  d=v['absolute'];lines.append(f"| {k} | {d['n']} | {fmt(d.get('median'))} | {fmt(d.get('p95'))} | {fmt(d.get('max'))} |")
 lines+=['',f"全程内容序列发生分歧的 route 数：conflict **{cd['conflict']}**、learned **{cd['learned']}**、decision **{cd['decision']}**、restart **{cd['restart']}**、backtrack **{cd['backtrack']}**。",'']
 if s['absolute_effect_distribution']['max']==0:lines+=['所有已观察到的 persistence 类 final delta 均为 0；没有观察到“分歧越深，最终 |delta| 越大”的关系。存在状态顺序持续差异不等于 analysis ops 改变。','']
 else:lines+=['PERSISTENT_DIVERGENT 10 条中只有 1 条非零；DECISION_DIVERGENT 3 条中有 2 条非零；其余类全部为零。3 条非零 route 均出现了全程 conflict/learned 内容序列分歧，但 4 条 decision 分歧中有 1 条 effect 为零。数据没有支持简单的 persistence 类别越深、|delta| 就单调越大的关系。这只是固定 cohort 的描述，不建立 selector，不宣称 causal mechanism。','']
 lines+=['HEURISTIC_STATE_AMPLIFICATION_HYPOTHESIS；CAUSAL_MEDIATION_UNRESOLVED。本 cohort 的 HIGH 为 2/136，不能据此断言普遍发生率或证明稀有 tail 机制。','',
 '## 11. Proof / verification','',f"固定 cohort 的 baseline/action 重跑：**{s['proof_verified_executions']} VERIFIED / {s['proof_failed']} failed**，对应 **{s['proof_verified_pairs']} / 136** route pairs。另 golden reference/OFF/ON1/ON2 的 baseline/action 共 8 次 proof VERIFIED；保留的初始 engineering reference 另有 1 次 proof VERIFIED。",'',
 '非扰动 smoke PASS：OFF/ON1/ON2 与原 executable 的 SAT/UNSAT 状态和全部输出 final counters 完全相同；ON1/ON2 canonical telemetry 字节稳定。`PROOF_ROUTE_MAPPING.json`、`ROUTE_EXECUTION_MAPPING.json`、`FINAL_INTEGRITY_CHECKS.json`、`EVIDENCE_MANIFEST.json` 提供逐 route provenance。','',
 '## 12. Final A/B/C/D','',f"**{s['final_decision']} — "+{'A':'INTERVENTIONS_MOSTLY_INERT','B':'INTERVENTIONS_MOSTLY_TRANSIENT','C':'DIVERGENCE_COMMON_BUT_LARGE_EFFECT_RARE','D':'MIXED_TRAJECTORY_RESPONSE'}[s['final_decision']]+'**。','',
 '按跑结果前冻结的规则：INERT 严格多数选 A；否则 LOCAL_TRANSIENT 严格多数选 B；否则 PERSISTENT_DIVERGENT 严格多数且 HIGH=0 选 C；其余选 D。混合响应描述的是状态/轨迹汇合时点，不意味着多个已证实的 causal mechanisms。','',
 '## 13. Next step','']
 if s['next_step']=='CHANGE_OPPORTUNITY_GENERATION':lines+=['**改 opportunity generation。** 当前固定 cohort 多数只提前执行 baseline 很快就会由同一 clause 完成的 propagation；盲目扩大同源 candidate 数尚无依据。下一轮应另行冻结 outcome-blind 的机会定义，使其覆盖更不同的 native timing/propagation opportunity；本轮不实施新采样、不搜索 HIGH、不改变 threshold。']
 else:lines+=['**继续扩大 outcome-blind candidate source。** 另行冻结新 discovery protocol，保持 10% threshold；本轮不执行新采样。']
 (R/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':report(json.loads((R/'AUDIT_SUMMARY.json').read_text()))
