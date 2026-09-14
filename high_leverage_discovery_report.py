"""Audit and report already completed frozen discovery; never runs solver."""
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path('results/high_leverage_discovery')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
s=json.loads((ROOT/'discovery_summary.json').read_text())
protocol=json.loads((ROOT/'protocol.json').read_text())
assert sha(ROOT/'protocol.json')==s['protocol_sha256']
assert protocol['spacing']==250 and protocol['targets_in_order']==['T8','T10','T13']
rows=[];verified=0;proof_equal={};counter_changes=[]
for t in protocol['targets_in_order']:
 d=ROOT/t;ts=s['targets'][t]
 if ts['status']=='NOT_RUN_STOP_RULE':continue
 assert ts['status']=='COMPLETE'
 baseline=json.loads((d/'BASELINE.result.json').read_text())
 assert baseline['proof_validation']=='VERIFIED' and baseline['stats']['status']=='UNSAT'
 assert 's VERIFIED' in (d/'BASELINE.proof_check.txt').read_text();verified+=1
 grid=json.loads((d/'frozen_samples.json').read_text())
 assert [v['bucket'] for v in grid]==list(range(250,baseline['stats']['conflicts']+1,250))
 assert len(grid)==len(ts['rows']);proof_equal[t]=0
 for sample,row in zip(grid,ts['rows']):
  assert row['sample_conflict_bucket']==sample['bucket'];rows.append(row)
  if sample['status']=='NO_OPPORTUNITY':assert row['status']=='NO_OPPORTUNITY';continue
  tag=f"EARLY_PROP_C{sample['bucket']}";r=json.loads((d/(tag+'.result.json')).read_text())
  assert r['stats']['status']=='UNSAT' and r['proof_validation']=='VERIFIED'
  assert 's VERIFIED' in (d/(tag+'.proof_check.txt')).read_text();verified+=1
  op=[e for e in r['events'] if e['event']=='OPPORTUNITY'];enq=[e for e in r['events'] if e['event']=='EARLY_ENQUEUE']
  assert op==[sample['opportunity']] and len(enq)==1
  assert enq[0]['global_enqueue']==op[0]['global_enqueue']+1
  assert all(enq[0][k]==op[0][k] for k in ['literal','reason_id'])
  assert [e for e in r['events'] if e['event']=='TOTAL'][0]['interventions']==1
  assert row['valid'] and row['same_deterministic_pre_state']
  assert row['HIGH_LEVERAGE']==(abs(row['relative_ops_delta_percent'])>=10)
  proof_equal[t]+=r['proof_sha256']==baseline['proof_sha256']
  delta={k:[v,r['stats'][k]] for k,v in baseline['stats'].items() if k!='seconds' and v!=r['stats'][k]}
  if delta:counter_changes.append({'target':t,'bucket':sample['bucket'],'counters':delta})
assert len(list(csv.DictReader((ROOT/'all_samples.csv').open())))==len(rows)==s['sample_count']
s['outcomes']={'high_leverage':sum(bool(r.get('HIGH_LEVERAGE')) for r in rows),'speedup_any_magnitude':sum(r.get('relative_ops_delta_percent',0)<0 for r in rows),'slowdown_any_magnitude':sum(r.get('relative_ops_delta_percent',0)>0 for r in rows),'zero_ops_delta':sum(r.get('relative_ops_delta_percent')==0 for r in rows),'no_opportunity':sum(r['status']=='NO_OPPORTUNITY' for r in rows),'failures':sum(r['status']!='NO_OPPORTUNITY' and not r['valid'] for r in rows)}
s['audit']={'verified_proofs_including_baselines':verified,'single_enqueue_and_baseline_event_match_count':sum(r['valid'] for r in rows),'same_proof_hash_as_baseline_by_target':proof_equal,'non_time_counter_changes':counter_changes,'fingerprint_scope':'FNV64 operational state fingerprint including assignment/trail/levels/reasons/qhead/activity/heap/clauses/watches/phase/restart queues/seed and principal counters; not a formal whole-memory identity proof.'}
s['conclusion']='在当前 trajectory-wide sampling protocol 下，未发现第二个 independent high-leverage propagation case。'
s['discovery_stopped']=True
s['eligible_for_two_positive_case_comparison']=False
dump(ROOT/'discovery_summary.json',s)
lines=['# High-leverage propagation trajectory-wide discovery','',s['conclusion'],'',
'冻结顺序为 T8 → T10 → T13，间隔 250 conflicts。T8 全部无命中后才运行 T10；T10 全部无命中后才运行 T13。没有增加采样点、换事件或扩展 target。阈值保持 `abs(intervention_ops / baseline_ops - 1) >= 0.10`。','',
'每个桶从对应 conflict 完成后的首个 search-loop 入口（调用 propagate 前）开始，随后在每次 enqueue 完成处只读检查。首个真实 unit 且 implied literal 未赋值、native reason layout 合法的状态即入选；同时多个候选按最小 stable clause allocation ID 决胜。二元 clause 使用 solver 原有二元 reason 处理，长 clause 要求 implied literal 位于 index 0。没有重排 clause。','',
'基线结束后、任何 intervention 结果产生前，各 target 的完整采样列表保存为 `frozen_samples.json`。每条 rerun 仅执行一次 native uncheckedEnqueue，记录的事件、clause、literal、pre-action 指纹均与 baseline 一致。状态指纹覆盖主要 solver 状态，属于复跑一致性校验，不等于完整内存的形式化 bit-exact 证明。','',
'| Target | 冻结桶范围 | 样本数 | Baseline ops | Intervention ops | ≥10% 命中 |','|---|---|---:|---:|---:|---:|']
for t,ts in s['targets'].items():
 rr=ts['rows'];values=sorted(set(r['intervention_ops'] for r in rr));vs=' / '.join(f'{v:,}' for v in values)
 lines.append(f"| {t} | C250–C{rr[-1]['sample_conflict_bucket']} / 250 | {len(rr)} | {ts['baseline']['analysis_resolution_steps']:,} | {vs} | 0 |")
lines+=['',
'84/84 采样点有合法 opportunity，84/84 单次 intervention 有效，0 个缺失机会、0 个 run/proof/state-match failure。三个 baseline 精确复现既有非时间 counters。3 个 baseline 加 84 个 intervention 共 87 份 UNSAT proof 均由独立 drat-trim VERIFIED；proof、校验日志、输入和哈希已保存。','',
'83 个 intervention 的 ops 完全不变。唯一非零结果为 T8/C4250：219,571 → 219,570，变化 −0.00045543355%，远低于 10%。T10/C4750 的 propagations 从 770,564 变为 770,555，但 ops、conflicts、decisions 不变。其它非时间 counters 的变化记录于 discovery_summary.json。','',
'该协议在结果选择上是盲选，但并非在所有合法 propagation 事件上均匀随机采样：每 250 conflicts 只取首个观察到的机会，同一状态以 stable ID 决胜。84 个阴性结果不能估计所有 CNF/所有事件中的真实发生率，也不能排除稀有的高杠杆窗口。没有根据结果新增 feature 或修改选择规则。','',
'完整逐点记录见 [all_samples.csv](all_samples.csv)，每条 proof 与事件日志位于对应 target 目录。下表保留所有样本：','',
'| Target | Bucket | Actual conflict / decision / level | Clause ID | Literal | Ops | Δ ops % | Status / proof |','|---|---:|---|---:|---:|---:|---:|---|']
for r in rows:
 lines.append(f"| {r['target']} | {r['sample_conflict_bucket']} | {r['actual_conflict']} / {r['decision']} / {r['level']} | {r['clause_id']} | {r['implied_literal']} | {r['intervention_ops']} | {r['relative_ops_delta_percent']:.9f} | {r['status']} / {r['proof_validation']} |")
lines+=['',
'1. **是否发现第二个独立 ≥10% high-leverage propagation？** 没有。在当前 trajectory-wide sampling protocol 下，未发现第二个 independent high-leverage propagation case。','',
'2. **如果发现，是 speedup 还是 slowdown，效应多大？** 没有符合阈值的 speedup 或 slowdown。最大绝对 ops 变化仅为 T8/C4250 的 −1 op（−0.00045543355%）。','',
'3. **如果未发现，fixed-case phenomenon 是否可能是稀有事件？** 可能；也可能集中在当前首机会采样未覆盖的状态。结果与稀有性相容，不能据此证明稀有或给出发生率。','',
'4. **下一步是否已有资格比较两个 positive case 并抽共性？** 没有，仍缺第二个独立 positive case。本阶段已停止 discovery。','']
(ROOT/'HIGH_LEVERAGE_DISCOVERY.md').write_text('\n'.join(lines))
print(json.dumps({'outcomes':s['outcomes'],'audit':s['audit']},indent=2))
