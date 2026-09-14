"""Read-only analysis of the existing15 events. No solver execution."""
import csv,json,hashlib,statistics
from collections import defaultdict
from pathlib import Path
SRC=Path('results/state_sensitivity_cohort')
OUT=Path('results/state_action_decomposition')
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writecsv(p,rows):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def main():
 OUT.mkdir(exist_ok=False)
 source=json.loads((SRC/'cohort_summary.json').read_text());rs=source['rows'];assert len(rs)==15
 exact={};coarse={};matrix=[];groups=defaultdict(list)
 for r in rs:
  ek=(r['target'],r['pre_state_hash']);ck=(r['target'],r['conflict'],r['decision'],r['level'])
  if ek not in exact:exact[ek]=f'CTX{len(exact)+1:02d}'
  if ck not in coarse:coarse[ck]=f'DG{len(coarse)+1:02d}'
  d=r['relative_ops_delta_percent'];sign='speedup' if d<0 else 'slowdown' if d>0 else 'zero'
  m={'context_id':exact[ek],'decision_group_id':coarse[ck],'event':r['event'],'target':r['target'],'opportunity_index':r['opportunity_index'],'pre_state_hash':r['pre_state_hash'],'conflict_index':r['conflict'],'decision_index':r['decision'],'decision_level':r['level'],'trail_length':r['trail_length'],'qhead':r['qhead'],'pending_propagation_count':r['pending_propagation_count'],'action_clause_id':r['clause_id'],'action_clause_hash':r['clause_hash'],'action_clause_literals':r['clause_literals'],'implied_literal':r['implied_literal'],'relative_ops_delta_percent':d,'sign':sign,'magnitude_abs_percent':abs(d),'high_leverage':abs(d)>=10,'baseline_next_conflict_hash':r['baseline_next_conflict_hash'],'next_conflict_hash':r['perturb_next_conflict_hash'],'baseline_learned_hash':r['baseline_learned_hash'],'learned_hash':r['perturb_learned_hash'],'baseline_next_decision_literal':r['baseline_next_decision'],'next_decision_literal':r['perturb_next_decision']}
  assert m['high_leverage']==r['HIGH_LEVERAGE'];matrix.append(m);groups[exact[ek]].append(m);groups[coarse[ck]].append(m)
 # Existing metadata confirm hash grouping; no new state instrumentation.
 for cid in exact.values():
  rr=groups[cid]
  for key in ['target','pre_state_hash','conflict_index','decision_index','decision_level','trail_length','qhead','pending_propagation_count']:
   assert len({r[key] for r in rr})==1,(cid,key)
  if len(rr)>1:
   full=[json.loads((SRC/r['target']/f"event_{r['opportunity_index']}"/'full_result.json').read_text()) for r in rr]
   assert len({x['event']['opportunity']['global_enqueue'] for x in full})==1
   assert all(x['full_runs'][0]['trace']['local']==full[0]['full_runs'][0]['trace']['local'] for x in full)
 summaries=[]
 for level,ids in [('EXACT_CONTEXT',exact.values()),('DECISION_GROUP',coarse.values())]:
  for cid in ids:
   rr=groups[cid];ds=[r['relative_ops_delta_percent'] for r in rr];ms=[abs(d) for d in ds];sg={r['sign'] for r in rr};action_count=len({(r['target'],r['action_clause_hash'],r['implied_literal']) for r in rr})
   summaries.append({'grouping_level':level,'context_id':cid,'decision_group_id':rr[0]['decision_group_id'],'target':rr[0]['target'],'pre_state_hash':rr[0]['pre_state_hash'] if level=='EXACT_CONTEXT' else None,'event_count':len(rr),'exact_context_count':len({r['context_id'] for r in rr}),'action_count':action_count,'speedup_count':sum(r['sign']=='speedup' for r in rr),'slowdown_count':sum(r['sign']=='slowdown' for r in rr),'zero_count':sum(r['sign']=='zero' for r in rr),'high_leverage_count':sum(r['high_leverage'] for r in rr),'effect_min_percent':min(ds),'effect_max_percent':max(ds),'effect_mean_percent':statistics.mean(ds),'effect_median_percent':statistics.median(ds),'observed_sign_consistent':len(sg)==1,'multi_action_comparison_available':action_count>1,'magnitude_spread_percentage_points':max(ms)-min(ms),'speedup_and_slowdown':{'speedup','slowdown'}<=sg,'high_leverage_and_zero':any(r['high_leverage'] for r in rr) and 'zero' in sg,'events':[r['event'] for r in rr]})
 writecsv(OUT/'event_matrix.csv',matrix);writecsv(OUT/'context_summary.csv',summaries)
 ex=[r for r in summaries if r['grouping_level']=='EXACT_CONTEXT'];dg=[r for r in summaries if r['grouping_level']=='DECISION_GROUP'];multi=[r for r in ex if r['multi_action_comparison_available']];assert len(ex)==14 and len(dg)==5 and len(multi)==1
 shared=multi[0];assert shared['events']==['T10_P226','T10_P227']
 action_contexts=defaultdict(set)
 for r in matrix:action_contexts[(r['target'],r['action_clause_hash'],r['implied_literal'])].add(r['context_id'])
 summary={'input_files_sha256':{str(p):sha(p) for p in [SRC/'cohort_summary.json',SRC/'all_conflict_changing_events.csv',SRC/'frozen_cohort.json']},'method':{'exact_context_key':['target','pre_state_hash'],'decision_group_key':['target','conflict_index','decision_index','decision_level'],'hash_limit':'Existing FNV64 operational solver-state fingerprint; exact-context label follows the requested grouping convention, not a fresh full-memory equality proof. Same-hash pair also shares existing enqueue count, trail length, qhead, pending queue and baseline local trace.','no_new_features':True,'no_solver_runs':True,'high_leverage_threshold_percent':10,'singleton_sign_consistency':'Descriptively true, but not evidence of action-invariant sign.','independence':'15 events,14 distinct hashed contexts,5 coarse decision groups. Coarse groups are not identical solver states, and same deterministic trajectory does not establish statistical independence.'},'counts':{'event_samples':15,'exact_contexts':14,'decision_context_groups':5,'singleton_exact_contexts':13,'multi_action_exact_contexts':1,'actions_observed_in_multiple_exact_contexts':sum(len(v)>1 for v in action_contexts.values())},'within_exact_context':{'shared_context':shared,'mixed_speedup_slowdown_contexts':sum(r['speedup_and_slowdown'] for r in ex),'mixed_high_leverage_zero_contexts':sum(r['high_leverage_and_zero'] for r in ex),'same_state_action_magnitude_effect_observed':True},'exact_context_summaries':ex,'decision_group_summaries':dg,'conclusion':{'classification':'INSUFFICIENT','reason':'Only one same-state action comparison and no crossed repeated-action contexts. It shows action-dependent magnitude, but cannot determine state dominance, action dominance, or a general state×action interaction.','next_priority':'Compare actions within an already sensitive exact state. This is an analysis priority only; no new experiments performed.','stopped':True}}
 dump(OUT/'state_action_summary.json',summary)
 lines=['# State vs action decomposition','',
'**结论：INSUFFICIENT。15个event对应14个exact pre-state contexts，而此前5组是较粗的decision-context分组。** 只有一个exact context包含两个action，足以显示action会影响幅度，但不足以判断state/action/interaction谁主导长期effect。','',
'本轮仅读取现有cohort及其full_result文件，没有rerun solver、新target、新intervention、新feature或阈值调整。exact context按 `(target, pre_state_hash)` 分组；现有FNV64是主要solver状态的操作性指纹，不是重新获取的全内存等价证明。同hash配对另由现有global enqueue count、trail length、qhead、pending queue以及baseline局部trace一致性辅助确认。','',
'必须区分三种样本口径：','',
'- **15个event-level样本**：每条合法单次propagation action的效应。',
'- **14个exact-context样本标签**：13个单action context，1个双action context。不同标签仍不保证统计独立。',
'- **5个decision-context分组**：由target/conflict/decision/level定义；用于coarse层面汇总，组内trail/qhead通常变化，不能称为5个exact states。同一target的不同组仍共享确定性轨迹，不能直接宣称5个组统计独立。','',
'| context_id | decision group | event / action | ops_delta | sign | high_leverage |','|---|---|---|---:|---|---|']
 for r in matrix:lines.append(f"| {r['context_id']} | {r['decision_group_id']} | {r['event']} / #{r['action_clause_id']} → {r['implied_literal']} | {r['relative_ops_delta_percent']:+.3f}% | {r['sign']} | {'yes' if r['high_leverage'] else 'no'} |")
 lines+=['',
'完整matrix包括clause/hash、pre-state辅助字段、next conflict/learned hash及next decision：[event_matrix.csv](event_matrix.csv)。[context_summary.csv](context_summary.csv)包含14行EXACT_CONTEXT和5行DECISION_GROUP，必须按grouping_level分别读取，不能合计为19个context。','',
'唯一可进行严格同state action对照的是CTX09：','',
'- T10_P226：clause#831 `[-231,-471]`，提前−231，effect **−26.201%**，next decision −466。',
'- T10_P227：clause#833 `[-42,-471]`，提前−42，effect **−46.918%**，next decision −289。',
'- 两者pre-state hash均为`422271443557180589`，C0/decision18/level18，global enqueue263、trail263、qhead252、pending11完全一致；其baseline局部trace也相同。',
 f"- 两个action均为high-leverage speedup；signed effect min/max/mean/median为 {shared['effect_min_percent']:.6f}% / {shared['effect_max_percent']:.6f}% / {shared['effect_mean_percent']:.6f}% / {shared['effect_median_percent']:.6f}%。幅度spread为 **{shared['magnitude_spread_percentage_points']:.6f}个百分点**。",'',
'这组数据符合“方向一致”，但幅度差20.716个百分点，不能称为接近。它直接表明同state下action选择会改变幅度；同时没有出现speedup+slowdown或high-leverage+zero混合。其余13个singleton context的sign一致性只是单样本恒真，不能计作13次state-dominance证据。','',
'五个coarse decision groups的描述性汇总：','',
'| Group | Target / C / decision / level | Events / exact contexts | Speedup / slowdown / zero | High | Min / max % | Mean / median % | Magnitude spread pp |','|---|---|---|---|---:|---|---|---:|']
 for x in dg:
  r=groups[x['context_id']][0]
  lines.append(f"| {x['context_id']} | {r['target']} / {r['conflict_index']} / {r['decision_index']} / {r['decision_level']} | {x['event_count']} / {x['exact_context_count']} | {x['speedup_count']} / {x['slowdown_count']} / {x['zero_count']} | {x['high_leverage_count']} | {x['effect_min_percent']:+.3f} / {x['effect_max_percent']:+.3f} | {x['effect_mean_percent']:+.3f} / {x['effect_median_percent']:+.3f} | {x['magnitude_spread_percentage_points']:.3f} |")
 lines+=['',
'DG02、DG03、DG04的已观察action全部大效应；DG01为4个moderate slowdown加1个high slowdown；DG05仅一个zero。五组均未观察到正负混合。但这些只是该group已入选的conflict-changing action结果，不代表该state中所有合法action：cohort本身已经按conflict change筛选。DG01/02各自内部实际包含多个不同pre-states，因此固定方向不能单独归因于state。','',
'当前设计也无法识别ACTION_DOMINANT或正式的state×action interaction：15个action（按target+clause hash+implied literal识别）没有跨exact contexts重复，缺少交叉对照。唯一同state配对支持“action会影响幅度”，但它既不证明action在跨state时主导，也不能估计同一action的effect如何随state变化。没有模型拟合或p-value。','',
'1. **15个event实际对应多少个exact contexts？** 14个。此前5组是decision-context分组，不是5个相同pre-state；15个event也不是15个独立solver states。','',
'2. **同一context内不同action的effect方向是否一致？** 唯一双action exact context中一致，均为speedup；幅度−26.201%与−46.918%，相差20.716个百分点。其余13个context无法检验跨action方向稳定性。','',
'3. **更支持哪一类？** **INSUFFICIENT**。已有局部action-dependent magnitude证据，尚不能在STATE_DOMINANT、ACTION_DOMINANT或一般STATE_ACTION_INTERACTION之间可靠归类。','',
'4. **下一阶段优先研究什么？** 优先比较已知敏感exact state中的不同action：这是目前能直接固定state、区分action影响的方向。它是后续研究优先级，不是已建立的action选择规则；本轮未执行新实验，完成后停止。','']
 (OUT/'STATE_ACTION_DECOMPOSITION.md').write_text('\n'.join(lines))
 print(json.dumps({'counts':summary['counts'],'shared_context':shared,'classification':summary['conclusion']['classification']},indent=2))
if __name__=='__main__':main()
