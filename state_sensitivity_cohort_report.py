"""Descriptive report and artifact audit only; no additional solver execution."""
import json,csv
from pathlib import Path
from collections import Counter,defaultdict
from state_sensitivity_cohort import OUT,sha,dump,events
s=json.loads((OUT/'cohort_summary.json').read_text());rows=s['rows'];frozen=json.loads((OUT/'frozen_cohort.json').read_text())
assert sha(OUT/'frozen_cohort.json')==s['frozen_cohort_sha256']
assert sha(OUT/'protocol.json')==s['protocol_sha256']
assert len(rows)==len(frozen)==15 and len(list(csv.DictReader((OUT/'all_conflict_changing_events.csv').open())))==15
proofgroups=defaultdict(list);verified=0;localpairs=0
for t,ts in s['target_summaries'].items():
 es=events(OUT/t/'local/opportunities.jsonl');hits=[e['opportunity'] for e in es if e['event']=='CONFLICT_CHANGING_EVENT']
 assert hits==ts['selected_indices'] and len(hits)==5 and ts['opportunities_scanned']<=500
 probes=json.loads((OUT/t/'all_local_probes.json').read_text());assert [p['opportunity'] for p in probes]==list(range(1,ts['opportunities_scanned']+1))
 assert [p['opportunity'] for p in probes if p['conflict_diverged']]==hits;localpairs+=len(probes)
 for rank,i in enumerate(hits,1):
  result=json.loads((OUT/t/f'event_{i}/full_result.json').read_text());r=result['row'];assert r in rows and r['selected_rank']==rank
  assert result['selection_hash']==s['frozen_cohort_sha256'] and result['same_pre_state_by_os_fork'] and result['full_local_replay_matches']
  for run in result['full_runs']:
   assert run['proof_validation']=='VERIFIED' and run['stats']['status']=='UNSAT'
   assert 's VERIFIED' in (OUT/t/f'event_{i}'/f"P{i}_{run['route']}.proof_check.txt").read_text();verified+=1
  assert r['HIGH_LEVERAGE']==(abs(r['relative_ops_delta_percent'])>=10)
  proofgroups[(t,result['full_runs'][1]['proof_sha256'])].append(r['event'])
assert verified==30 and localpairs==766
high=[r for r in rows if r['HIGH_LEVERAGE']];firsthigh=high[0];firstspeed=next(r for r in high if r['direction']=='speedup')
s['audit']={'local_pairs':localpairs,'local_children':2*localpairs,'full_runs':30,'independent_proofs_verified':verified,'local_and_full_prestate_match':True,'full_local_outcomes_match_frozen_probes':True,'no_selection_changes':True,'unique_target_prestate_hashes':len(set((r['target'],r['pre_state_hash']) for r in rows)),'target_conflict_decision_level_contexts':len(set((r['target'],r['conflict'],r['decision'],r['level']) for r in rows)),'repeated_early_proof_groups':[v for v in proofgroups.values() if len(v)>1]}
s['first_additional_high_leverage_event']=firsthigh['event'];s['first_additional_high_leverage_speedup']=firstspeed['event']
s['descriptive_conclusion']={'second_independent_high_leverage_found':True,'high_leverage_speedups':sum(r['direction']=='speedup' for r in high),'high_leverage_slowdowns':sum(r['direction']=='slowdown' for r in high),'learned_changed_count':sum(r['learned_changed'] for r in rows),'decision_changed_count':sum(r['decision_changed'] for r in rows),'reusable_prestate_pattern_validated':False,'sufficient_for_descriptive_case_comparison':True,'sufficient_for_reusable_state_sensitivity_abstraction':False,'limitation':'insufficient positive state-sensitivity samples: independent, diverse state/control coverage remains limited despite10 threshold-positive events.','stopped':True}
dump(OUT/'cohort_summary.json',s)
lines=['# State sensitivity cohort','',
'**已冻结并完成15个 conflict-changing events，其中10个达到原定 ≥10% HIGH_LEVERAGE：5个speedup、5个slowdown。** 另有4个8.375% slowdown和1个0%事件。病例库已建立，但冻结pre-state descriptors尚不能稳定区分效应类别。','',
'所有target的选择先于本轮任何full-run cost查看完成；只依据next conflict canonical hash变化，按原机会顺序取前5个。局部probe继承同一OS-fork pre-state，原生unit/layout检查与单次uncheckedEnqueue语义不变。三个target均在500个上限内收满5个，没有扩展上限、调整事件、改10%阈值或运行fixed GOOD case。','',
'| Target | 扫描合法机会 | 冻结事件indices | 收集数 |','|---|---:|---|---:|']
for t,ts in s['target_summaries'].items():lines.append(f"| {t} | {ts['opportunities_scanned']} | {', '.join(map(str,ts['selected_indices']))} | 5 |")
lines+=['',
'共766个local probe pairs（1532个child，仅到下一conflict analysis），随后仅对15个入选事件执行30条full routes。30条均UNSAT并由独立drat-trim VERIFIED；所有baseline非时间counters及proof哈希与既有baseline一致。full阶段的pre-state、descriptors和local conflict/learned outcome均复现冻结probe。','',
'| Event | Conflict / decision / level | Literal | Baseline ops | Early ops | Δ ops | HIGH_LEVERAGE |','|---|---|---:|---:|---:|---:|---|']
for r in rows:lines.append(f"| {r['event']} | {r['conflict']} / {r['decision']} / {r['level']} | {r['implied_literal']} | {r['baseline_ops']:,} | {r['perturb_ops']:,} | {r['relative_ops_delta_percent']:+.3f}% | {'yes' if r['HIGH_LEVERAGE'] else 'no'} |")
lines+=['',
'完整cohort表：[all_conflict_changing_events.csv](all_conflict_changing_events.csv)。其中包含全部冻结descriptors、clause id/hash/literals、pre-state hash、baseline/perturbed conflict与learned hash、next decision、final counters和proof状态。每个target目录保存local机会序列、`frozen_events.json`、全部probe分类及每个入选事件的完整结果和proof。','',
'| Target | Exact0 | Nonzero <1% | 1–5% | 5–10% | ≥10% speedup | ≥10% slowdown |','|---|---:|---:|---:|---:|---:|---:|']
for t in ['T8','T10','T13']:
 rr=[r for r in rows if r['target']==t];counts=Counter(r['effect_bin'] for r in rr)
 vals=[counts['exact0'],counts['nonzero_abs_lt1pct'],counts['abs_1_to5pct'],counts['abs_5_to10pct'],sum(r['HIGH_LEVERAGE'] and r['direction']=='speedup' for r in rr),sum(r['HIGH_LEVERAGE'] and r['direction']=='slowdown' for r in rr)]
 lines.append('| '+t+' | '+' | '.join(map(str,vals))+' |')
lines+=['',
'效应双向，范围−46.918%到+49.038%。按冻结target/event顺序，第一个新增阈值positive是 **T8_P210：219,571→277,245，+26.267%**；第一个新增强speedup是 **T10_P204：360,959→241,568，−33.076%**。因此已在fixed case以外再次获得独立CNF上的≥10%效应。4个5–10%事件均属T8且最终ops相同，不应宣称是4次独立状态复制。','',
'冻结descriptors的描述性比较如下。“near0”预先定义为绝对变化<1%，实际这里只有一个exact0；没有从结果追加字段或拟合规则。','',
'| Descriptor | ≈0，n=1 | 5–10%，n=4 | ≥10%，n=10 |','|---|---|---|---|']
groups=[[r for r in rows if abs(r['relative_ops_delta_percent'])<1],[r for r in rows if r['effect_bin']=='abs_5_to10pct'],high]
for name,key in [('current conflict','conflict'),('decision index','decision'),('decision level','level'),('trail length','trail_length'),('qhead','qhead'),('pending queue','pending_propagation_count'),('restart epoch','restart_epoch'),('conflicts since restart','conflicts_since_restart'),('candidate activity','candidate_activity_hex'),('heap array position','heap_array_position'),('clause length','clause_length'),('antecedent level distribution','antecedent_level_distribution'),('almost-unit neighbors','almost_unit_neighbor_count'),('clause fan-out','local_clause_fanout')]:
 vals=[]
 for g in groups:
  values=[r[key] for r in g]
  if key=='antecedent_level_distribution':rep='; '.join(sorted(set(json.dumps(v,sort_keys=True) for v in values)))
  elif key=='candidate_activity_hex':rep='0'
  else:rep=', '.join(map(str,sorted(set(values))))
  vals.append(rep)
 lines.append('| '+name+' | '+' | '.join(vals)+' |')
lines+=['',
'没有出现重复、能分开三类效果的pre-state模式：','',
'- candidate activity全部为0、fan-out全部9、restart epoch全部1，不能在本cohort中区分效应。',
'- queue长度、almost-unit邻居数、clause长度和antecedent层级分布跨组重叠。例如queue=5同时出现在0%和强正/负效应事件中；二元/三元clause均可触发强效应。',
'- 层级或conflict index的表面分组与target和扫描时段混杂：15个事件只覆盖5组 `(target, conflict, decision, level)`，全部集中在completed conflict0–2。只有一个zero对照，不能把它的level17、heap位置18等偶然独有值提升成规律。',
'- T10_P226与P227甚至共享完全相同的pre-state hash及大部分descriptors，但candidate不同，最终分别−26.201%与−46.918%。这说明当前粗粒度状态描述并未唯一决定效应大小，不能只按全局context标签归因。','',
'15个事件不是15个统计独立状态：只有14个不同的target/pre-state指纹，并有多组early proof完全相同（例如T10_P204/P210/P225、T13_P179/P191、T13_P234/P239）。这不影响每个单次intervention的合法性和效应验证，但降低了可用于抽象的独立多样性。','',
'作为已要求记录的post-action结果，10/15改变learned canonical hash，14/15改变next decision；唯一0%事件T13_P329两者都没变。T13另4个强slowdown的learned canonical hash也没变，而next decision改变。该观察可用于描述病例，不是新增pre-state selector，也不能基于一个zero样本推出预测规则。','',
'1. **共发现多少个conflict-changing events？** 15个，T8/T10/T13各5个；共检查766个合法机会，全部在冻结上限内。','',
'2. **final search-cost effect分布？** 1个exact0；4个+8.375%；10个≥10%（5个speedup、5个slowdown），总范围−46.918%至+49.038%，全部结果保留且proof VERIFIED。','',
'3. **是否出现第二个独立≥10% high-leverage case？** 是。按顺序首次为T8_P210（+26.267%）；另在T10出现强speedup，首次T10_P204（−33.076%）。','',
'4. **是否已有足够样本开始抽象state sensitivity？** 已足够建立病例库并开始探索性描述比较，但不足以提出可复用的state-sensitivity抽象。只有5组相近的decision contexts、1个zero对照，多组事件结果重复；冻结descriptors没有形成跨组稳定区分。','',
'5. **insufficient positive state-sensitivity samples**：这里指独立、多样且有对照的state样本仍不足，而不是没有阈值positive。已有10个≥10%事件这一事实不变。本阶段已完成并停止，不追加实验。','']
(OUT/'STATE_SENSITIVITY_COHORT.md').write_text('\n'.join(lines))
print(json.dumps({'audit':s['audit'],'conclusion':s['descriptive_conclusion']},indent=2))
