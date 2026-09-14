"""Fixed metrics and narrative from completed four routes; no new experiments."""
import json,csv,hashlib
from pathlib import Path
from high_leverage_discovery import dump,chash
OUT=Path('results/good_bad_conflict_compare')
validation=json.loads((OUT/'run_validation.json').read_text());labels=['GOOD_BASELINE','GOOD_PERTURBED','BAD_BASELINE','BAD_PERTURBED'];data={};flat={}
for label in labels:
 es=[json.loads(x) for x in (OUT/label/'metrics.jsonl').read_text().splitlines()]
 def one(name):return next(e for e in es if e['event']==name)
 b=one('CONFLICT_BEFORE');a=one('ANALYSIS');bt=one('BACKTRACK');im=one('IMMEDIATE');pre=one('HEURISTIC_BEFORE');post=one('HEURISTIC_AFTER')
 window=[]
 for i in range(b['conflict']+1,b['conflict']+11):
  learned=next(e for e in es if e['event']=='WINDOW_LEARNED' and e['conflict']==i);counts=next(e for e in es if e['event']=='WINDOW_COUNTS' and e['conflict']==i)
  window.append({k:v for e in [learned,counts] for k,v in e.items() if k!='event'})
 bumped_hash=hashlib.sha256(json.dumps(a['bumped_variable_set'],separators=(',',':')).encode()).hexdigest()
 row={'conflict_index':b['conflict'],'decision_index':b['decision'],'decision_level':b['level'],'conflict_clause_length':len(b['conflict_clause_literals']),'conflict_clause_canonical_sha256':chash(b['conflict_clause_literals']),'visited_variable_count':a['visited_variable_count'],'visited_sequence_hash_fnv64':a['visited_sequence_hash_fnv64'],'resolution_step_count':a['resolution_steps'],'bumped_variable_count':a['bumped_variable_count'],'bumped_variable_set':a['bumped_variable_set'],'bumped_variable_set_sha256':bumped_hash,'learned_clause_length':len(a['learned_literals']),'learned_lbd':a['lbd'],'asserting_literal':a['asserting_literal'],'backtrack_level':a['backtrack_level'],'decision_level_minus_backtrack_level':a['backjump_levels'],'subsume_or_strengthen_existing_clause':a['subsume_or_strengthen_existing'],'backtrack_trail_length':bt['trail_length'],'backtrack_removed_assignments':bt['removed_assignments'],'learned_immediately_unit':bt['learned_immediately_unit'],'new_propagations_before_next_decision':im['new_propagations_before_next_decision'],'conflict_before_next_decision':im['conflict_before_next_decision'],'next_decision_literal':im['next_decision_literal'],'activity_before_fnv64':pre['activity_hash_fnv64'],'activity_after_fnv64':post['activity_hash_fnv64'],'heap_before_fnv64':pre['heap_hash_fnv64'],'heap_after_fnv64':post['heap_hash_fnv64'],'heap_top10_before':pre['top10_heap_array_variables'],'heap_top10_after':post['top10_heap_array_variables']}
 for key in ['conflict','learned_length','lbd','backtrack_level','propagation_count','decision_count']:row['next10_'+key]=[e[key] for e in window]
 flat[label]=row;data[label]={'fixed_metrics':row,'first_conflict':b,'analysis':a,'backtrack':bt,'immediate':im,'heuristic_before':pre,'heuristic_after':post,'next10_conflicts':window,'validation':validation[label]}
for kind in ['good','bad']:
 x,y=[data[k] for k in labels if k.startswith(kind.upper())]
 assert x['first_conflict']['prior_canonical_conflict_sequence_hash_fnv64']==y['first_conflict']['prior_canonical_conflict_sequence_hash_fnv64']
 assert x['fixed_metrics']['conflict_clause_canonical_sha256']!=y['fixed_metrics']['conflict_clause_canonical_sha256']
 assert x['heuristic_before']==y['heuristic_before']
 dump(OUT/(kind+'_case.json'),{'baseline':x,'perturbed':y,'first_changed_conflict_verified':True,'prior_conflict_hash_gate_equal':True,'pre_analysis_activity_and_heap_equal':True,'scope':'Existing route pair, unchanged intervention; exactly next10 conflicts recorded.'})
with (OUT/'comparison.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['metric']+labels)
 for k in flat[labels[0]]:w.writerow([k]+[json.dumps(flat[l][k]) if isinstance(flat[l][k],(list,bool)) else flat[l][k] for l in labels])
lines=['# Good vs bad conflict outcome comparison','',
'**第一场 changed conflict 的 learned 长度/LBD 变化方向与最终成本变化一致，但后续10-conflict窗口不保持该方向；尚未建立简单、可复用的 conflict-quality 解释。**','',
'GOOD 使用原有 BEFORE_PROP_BASELINE（345,571 ops）与 ORIGINAL_EARLY_PROP（174,433 ops）；BAD 使用 T8 #181 的 baseline（219,571 ops）与 perturbation（237,960 ops，slowdown8.375%）。本轮未更改 intervention 或10%阈值，也未寻找新case。','',
'GOOD 前655个 conflict 的 canonical-clause序列指纹相同，C656的 conflict clause不同；BAD 在C1已不同。这将比较锁定在各自首个不同的 conflict。四路所有非时间final counters精确复现原实验，四份proof重新由独立drat-trim VERIFIED，proof SHA-256也全部与原实验一致。','',
'| metric | GOOD_BASELINE | GOOD_PERTURBED | BAD_BASELINE | BAD_PERTURBED |','|---|---:|---:|---:|---:|']
for name,key in [('conflict index','conflict_index'),('decision index','decision_index'),('decision level','decision_level'),('conflict clause length','conflict_clause_length'),('visited variable count','visited_variable_count'),('resolution steps','resolution_step_count'),('bumped variable count','bumped_variable_count'),('learned length','learned_clause_length'),('learned LBD','learned_lbd'),('asserting literal','asserting_literal'),('backtrack level','backtrack_level'),('backjump levels','decision_level_minus_backtrack_level'),('backtrack trail length','backtrack_trail_length'),('removed assignments','backtrack_removed_assignments'),('learned immediately unit','learned_immediately_unit'),('new propagations before next decision','new_propagations_before_next_decision'),('conflict before next decision','conflict_before_next_decision'),('next decision literal','next_decision_literal'),('subsume / strengthen existing','subsume_or_strengthen_existing_clause')]:
 lines.append('| '+name+' | '+' | '.join(str(flat[l][key]) for l in labels)+' |')
lines+=['',
'完整固定对照表（包括所有hash、bumped sets、heap前10项及10-conflict序列）位于 [comparison.csv](comparison.csv)。结构化四个outcome及原始局部记录分别保存在 [good_case.json](good_case.json)、[bad_case.json](bad_case.json)。没有dump完整activity向量。','',
'第一层结构差异：GOOD 从 ternary conflict `[103,105,104]` 转向 binary conflict `[-11,-152]`，analysis访问变量42→33，resolution29→24，learned13→9、LBD6→4；BAD 两边都是binary conflict，但访问变量13→40，resolution8→27，learned5→13、LBD3→8。因此“首场learned长度/LBD变小对应good、变大对应bad”是两例都吻合的弱候选方向，不是已验证的因果或可复用规则。','',
'更深backtrack没有支持：GOOD两边均12→10，BAD两边均21→20；各自backtrack后的trail长度也相同。removed assignments略增（GOOD147→150，BAD159→163）来自进入conflict时trail更长，不能解读为backtrack层级更深。','',
'更多immediate propagation也不是GOOD的区分信号：GOOD两边均154；BAD153→140。四路learned都在backtrack后立即unit，并在next decision前再次conflict。GOOD的next decision发生于C657之后（−187 vs −570），BAD发生于C2之后（−441 vs100）。','',
'activity与heap方面，两例各自analysis前的hash和heap前10项完全相同，analysis后均不同。GOOD、BAD都发生了heuristic重排；hash只证明差异，不度量差异强弱，不能据此声称GOOD重排“更明显”。native heap数组不是全序排行榜，K固定为10：','',
'| heap前10项 | GOOD_BASELINE | GOOD_PERTURBED | BAD_BASELINE | BAD_PERTURBED |','|---|---|---|---|---|']
for name,k in [('before','heap_top10_before'),('after','heap_top10_after')]:lines.append('| '+name+' | '+' | '.join(str(flat[l][k]) for l in labels)+' |')
lines+=['',
'固定后续窗口为GOOD C657–666、BAD C2–11，均不包含首个changed conflict。以下仅汇总预先固定的长度/LBD，不新增筛选指标：','',
'| 后续10 conflicts | GOOD_BASELINE | GOOD_PERTURBED | BAD_BASELINE | BAD_PERTURBED |','|---|---:|---:|---:|---:|']
for label,key in [('learned length均值','next10_learned_length'),('LBD均值','next10_lbd')]:lines.append('| '+label+' | '+' | '.join(f'{sum(flat[l][key])/10:.1f}' for l in labels)+' |')
lines+=['',
'窗口内GOOD平均长度/LBD反而14.7/5.3→15.8/6.0，BAD反而14.6/7.1→12.9/6.3。首场的方向没有稳定延续。这个结果不排除“首场learned clause本身很关键”，但不能把一次方向吻合升级为足以解释最终search cost的简单规律。窗口中的conflict已来自不同状态，不能把相同相对编号当成严格对应的同一推理任务。','',
'**NO_SIMPLE_CONFLICT_QUALITY_EXPLANATION**：本轮没有建立“更短/更低LBD、更深backtrack、更多即时传播或更大heuristic变化”可以稳定、共同解释两例最终效应的规则。首场learned长度/LBD提供一个弱候选观察，但这里只有两个case，且10-conflict窗口不支持持续的quality排序。','',
'口径：visited count为主resolution循环检查到的不同变量数；sequence hash保留重复访问及顺序，不含minimization遍历。bumped set记录本场完整analyze内实际varBumpActivity调用，包含原生后处理bump。resolution steps沿用既有sf_analysis计数。activity/heap的after点在backtrack、learned断言enqueue及decay结束后。immediate propagation指此后到首个实际decision前新增enqueue，排除本场自身asserting enqueue，包含后续conflict的asserting enqueue；“再次conflict”明确指next decision前再次conflict。10-conflict propagation count为前一conflict结束后到当前conflict的真实dequeue数，decision count为对应计数增量。subsume/strengthen未使用额外clause扫描，保留UNAVAILABLE。','',
'1. **good和bad第一次changed conflict最显著的差异？** 首场learned长度/LBD及analysis规模方向相反：GOOD更小（13/6→9/4），BAD更大（5/3→13/8）；backtrack深度没有变化。','',
'2. **是否存在可复用的conflict-quality abstraction候选？** 只有“首场learned长度/LBD变化方向”这一弱候选，尚无可复用性证据。固定10-conflict窗口的方向反转，不能视为稳定解释：NO_SIMPLE_CONFLICT_QUALITY_EXPLANATION。','',
'3. **下一步是否应该转向state sensitivity而不是conflict quality？** 值得优先考察state sensitivity，而不是继续将粗略clause quality当作充分机制；这是后续方向，本轮未实施。完成后停止。','']
(OUT/'GOOD_BAD_CONFLICT_COMPARE.md').write_text('\n'.join(lines))
print('Verified four outcomes, prior-conflict gate, fixed10 windows; report and comparison.csv written.')
