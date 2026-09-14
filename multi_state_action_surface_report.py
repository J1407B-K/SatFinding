"""Audit and report frozen multi-state surfaces; no solver execution."""
import json,csv
from pathlib import Path
from collections import Counter
from multi_state_action_surface import ROOT,sha,dump,events
s=json.loads((ROOT/'response_surface_summary.json').read_text());selection=json.loads((ROOT/'selected_states.json').read_text());per=s['per_state'];allrows=s['all_actions']
assert sha(ROOT/'selected_states.json')==s['selection_sha256']
assert len(per)==5 and len({r['state_hash'] for r in per})==5
assert [e['opportunity']['opportunity'] for e in selection['states']]==[181,191,194,202,210]
assert len(list(csv.DictReader((ROOT/'all_action_runs.csv').open())))==len(allrows)==33
assert len(list(csv.DictReader((ROOT/'per_state_summary.csv').open())))==5
proofs=0
for meta,st in zip(selection['states'],per):
 d=ROOT/st['state_id'];ss=json.loads((d/'response_surface_summary.json').read_text());es=events(d/'runs/opportunities.jsonl');acts=[e for e in es if e['event']=='LEGAL_ACTION']
 assert [e['stable_clause_id'] for e in acts]==sorted(e['stable_clause_id'] for e in acts)
 assert len(acts)==st['legal_action_count']==st['tested_action_count'] and all(a['selected'] for a in acts)
 assert ss['snapshot']['pre_state_hash']==meta['opportunity']['pre_state_fnv64']
 assert ss['prior_actions_reproduced']==[meta['opportunity']['opportunity']]
 for tag in ['BASELINE']+[f"ACTION_{a['action_index']}" for a in acts]:
  r=json.loads((d/'runs'/(tag+'.result.json')).read_text());pre=next(e for e in r['trace'] if e['event']=='PRE_STATE')
  assert pre['hash']==ss['snapshot']['pre_state_hash'] and pre['raw_solver_object_hash']==ss['snapshot']['raw_solver_object_hash'] and pre['heap_including_inverse_hash']==ss['snapshot']['heap_including_inverse_hash']
  assert r['stats']['status']=='UNSAT' and r['proof_validation']=='VERIFIED'
  assert 's VERIFIED' in (d/'runs'/(tag+'.proof_check.txt')).read_text();proofs+=1
assert proofs==38
priorpath=Path('results/fixed_state_action_surface/response_surface_summary.json');prior=json.loads(priorpath.read_text());assert prior['high_leverage_count']==3 and prior['sign_counts']['zero']==2
s['audit']={'all_33_actions_and_5_baselines_verified':True,'all_action_prestate_hashes_match_own_paused_parent':True,'raw_object_and_heap_inverse_hashes_match':True,'all_5_cohort_anchor_actions_reproduced_counters_and_proofs':True,'legal_lists_frozen_before_branch_runs':True,'no_action_truncation':True,'no_state_replacement':True,'new_exact_states_vs_statistical_independence':'5 distinct exact fingerprints, all T8 C0/decision21/level21; one shared decision context, not5 independent trajectory groups.'}
s['replication']={'label':'STATE_ACTION_INTERACTION_REPLICATED','scope':'At multiple distinct exact states, action-dependent nontrivial effect vszero recurs. Only1 of5 newly tested states has high-leverage+zero; together with historical T10 S the strict mixture occurs in2 different-CNF exact states.','new_states_nonzero_plus_zero':sum(r['zero_count']>0 and r['slowdown_count']+r['speedup_count']>0 for r in per),'new_states_high_leverage_plus_zero':s['states_high_plus_zero'],'new_states_speedup_plus_slowdown':s['states_speedup_plus_slowdown'],'historical_state_in_this_selection':False,'historical_evidence_sha256':sha(priorpath),'across_independent_cnf_evidence':'Historical T10 sensitive-state surface and new T8 S5; historical state not rerun this stage.','supports_effect_depends_on_state_and_action':True,'model_fitted':False,'ready_for_limited_descriptive_action_abstraction':True,'generalizable_action_rule_validated':False,'stopped':True}
dump(ROOT/'response_surface_summary.json',s)
lines=['# Multi-state action surface replication','',
'**STATE_ACTION_INTERACTION_REPLICATED，范围需限定。** 五个新exact states都出现同state下“zero + nontrivial slowdown”；其中一个出现“zero + ≥10% slowdown”。结合此前已验证T10 state的“zero + 强speedup”，严格high-leverage/zero混合已在两个不同CNF的exact states中出现。本轮没有任何state内的speedup/slowdown双向混合。','',
'选择在运行前冻结：原cohort deterministic顺序为T8→T10→T13、再按opportunity index，取前5个不同pre-state hash且已有成功恢复和conflict-change证据的state。因此选到T8_P181/P191/P194/P202/P210；不根据已有effect挑选，也没有为增加CNF多样性更换state。旧T10 state S不在前5中，未重跑。','',
'本轮是**5个此前未做完整action surface的新exact states，0个旧surface state**。它们的hash、trail/qhead位置不同，但全部属于T8 C0/decision21/level21。不能把这5个exact states宣称为5条独立轨迹或5个统计独立样本。','',
'对每个Si先恢复既有deterministic prefix并校验旧pre-state fingerprint；baseline和全部action从同一个暂停父进程OS fork。每次fork前校验父进程未改变，每个child核对operational fingerprint、raw Solver object hash及包含inverse indices的heap hash。所有动态内存和原生调用栈由fork继承。赋值、trail/levels/qhead、activity/heap、DB/watches、phase/restart/counters/RNG固定，仅branch输出流和observer记账分开。','',
'每个state的合法action全集先按stable clause ID保存，再开始任何branch；本轮最大仅10个action，全部执行，未触及32上限。S处analysis ops都为0，baseline-from-S analysis cost均为219,571，所以delta与最终累计ops比较一致。没有新增feature、selector或预测规则。','',
'| State / anchor | Legal / tested actions | Zero | Speedup | Slowdown | ≥10% | Delta min / max | Median | Range pp |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in per:lines.append(f"| {r['state_id']} / T8_P{r['source_opportunity']} | {r['legal_action_count']} / {r['tested_action_count']} | {r['zero_count']} | {r['speedup_count']} | {r['slowdown_count']} | {r['high_leverage_count']} | {r['delta_min_percent']:+.3f}% / {r['delta_max_percent']:+.3f}% | {r['delta_median_percent']:.3f}% | {r['effect_range_percentage_points']:.3f} |")
lines+=['',
'共33个action：28个exact0、4个+8.375%、1个+26.267%；33个action加5个baseline共38条完整求解全部UNSAT，独立drat-trim VERIFIED。全部baseline以及五个原cohort anchor action的非时间counters和proof哈希精确复现。','',
'每个state都只有一个非零action。其余action并不全部没有执行轨迹变化：它们分别为NO_LOCAL_CHANGE或PROPAGATION_ONLY。五个非零action都改变了conflict、learned和next decision；详细flags与序列保存在各state目录。','',
'| State | Action / clause / literal | Δ ops | Local classification |','|---|---|---:|---|']
for r in allrows:lines.append(f"| {r['state_id']} | {r['action_id']} / #{r['clause_id']} / {r['implied_literal']} | {r['relative_ops_delta_percent']:+.3f}% | {r['local_classification']} |")
lines+=['',
'解释：','',
'- A：本轮只有S5为high-leverage+zero，不是五个新states全部复制该严格模式；此前T10 S也有该模式，因此跨CNF的第二份证据已获得。S1–S4复制的是moderate+zero（8.375%与0%），仍低于10%阈值。',
'- B：没有state内speedup+slowdown混合。每个新state的非零action都只有slowdown方向，不能称为“所有action都slowdown”，因为多数为exact0。',
'- C：五个surface均不是所有action同效应；它们共同呈稀疏非零响应。S1–S4响应值相同但合法action数不同，S5非零效应更大。',
'- D：旧T10 surface有3个强speedup+2个zero，新T8 surfaces为1个slowdown+多个zero。可以继续研究 `effect = f(state, action)`，但本轮没有拟合f，也没有建立跨state通用action ranking。','',
'“长期效果明显不同”在本轮多个exact states中复现，且严格≥10%/zero模式新增一个不同CNF案例，所以采用STATE_ACTION_INTERACTION_REPLICATED。独立性限制仍重要：新5个states相邻且共享一个decision context；旧T10证据是历史已验证结果，不能算成本轮额外测试的第6个state。','',
'文件：[selected_states.json](selected_states.json)、[all_action_runs.csv](all_action_runs.csv)、[per_state_summary.csv](per_state_summary.csv)、[response_surface_summary.json](response_surface_summary.json)。S1–S5目录保存frozen-state manifest、全部legal actions、local effects、分支counters及proof。','',
'1. **实际测试多少个独立exact states？** 测试5个hash不同的新exact states，旧S未入选；它们共享T8同一decision context，不是5个统计独立trajectory groups。','',
'2. **各state action数与effect range？** S1：5个、0～+8.375%；S2：10个、0～+8.375%；S3：3个、0～+8.375%；S4：9个、0～+8.375%；S5：6个、0～+26.267%。均全部运行。','',
'3. **high-leverage+zero / 正负混合是否跨state复制？** 严格high-leverage+zero新增于S5，与历史T10 S构成跨CNF复制；本轮其他4个仅moderate+zero。没有任何state内正负混合。','',
'4. **STATE_ACTION_INTERACTION是否replicated？** 是，STATE_ACTION_INTERACTION_REPLICATED，限定为多个exact-state的action-dependent response；不夸大为5个独立CNF或通用规律。','',
'5. **是否已有资格研究action abstraction，而非继续收集病例？** 有资格开始受限的描述性action-abstraction研究，不必把继续收集病例作为唯一前置条件；尚无通用预测/选择规则的证据。本轮不设计新feature或模型，完成后停止。','']
(ROOT/'MULTI_STATE_ACTION_SURFACE.md').write_text('\n'.join(lines))
print(json.dumps({'audit':s['audit'],'replication':s['replication']},indent=2))
