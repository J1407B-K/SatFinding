"""Read-only consequence cross-tabs for the existing two mixed states."""
import csv,json,hashlib
from pathlib import Path
from collections import Counter
OUT=Path('results/consequence_abstraction_v1')
SOURCES={'T10':Path('results/fixed_state_action_surface'),'T8':Path('results/multi_state_action_surface/S5')}
FLAGS={'propagation_changed':'propagation_diverged','next_conflict_changed':'conflict_diverged','learned_clause_changed':'learned_diverged','next_decision_changed':'decision_diverged'}
CANDIDATES={'CONFLICT_FRONTIER_CHANGE':['next_conflict_changed'],'LEARNING_CHANGE':['learned_clause_changed'],'DECISION_CHANGE':['next_decision_changed'],'LOCAL_PENETRATION':['next_conflict_changed','learned_clause_changed','next_decision_changed']}
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fraction(n,d):return {'satisfied':n,'total':d,'fraction':n/d if d else None,'percent':100*n/d if d else None}
def main():
 OUT.mkdir(exist_ok=False)
 dump(OUT/'protocol.json',{'states':{t:str(p) for t,p in SOURCES.items()},'candidates':CANDIDATES,'combination':'OR only for preregistered LOCAL_PENETRATION; no additional rule','comparison':'Per state, HIGH satisfaction proportion strictly greater than ZERO in both states; also report exact separation independently. No fitted thresholds.','labels':'Existing HIGH_LEVERAGE abs(delta)>=10%, ZERO existing actual0%; unchanged','posterior_cohort_check':'Only if candidate found:existing15 conflict-changing events effect distribution,HIGH ratio,directions; not prospective evaluation and no retraining','solver_runs':0})
 rows=[];inputs={}
 for t,src in SOURCES.items():
  snapshot=json.loads((src/'frozen_state.json').read_text());runs={r['action_id']:r for r in csv.DictReader((src/'all_action_runs.csv').open())}
  local=list(csv.DictReader((src/'local_effects.csv').open()))
  assert len(local)==len(runs)
  for l in local:
   r=runs[l['action_id']];delta=float(r['relative_ops_delta_percent']);high=r['HIGH_LEVERAGE']=='True';assert high==(abs(delta)>=10)
   assert high or delta==0
   row={'target':t,'exact_state_id':t+'_S','pre_state_hash':snapshot['pre_state_hash'],'action_id':l['action_id'],'final_ops_delta_percent':delta,'label':'HIGH_LEVERAGE' if high else 'ZERO',**{k:l[v]=='True' for k,v in FLAGS.items()}}
   assert row['next_conflict_changed']==(l['next_conflict_hash']!=l['baseline_next_conflict_hash'])
   assert row['learned_clause_changed']==(l['learned_hash']!=l['baseline_learned_hash'])
   assert row['next_decision_changed']==(l['next_decision_literal']!=l['baseline_next_decision_literal'])
   rows.append(row)
  for name in ['frozen_state.json','all_action_runs.csv','local_effects.csv']:inputs[str(src/name)]=sha(src/name)
 assert len(rows)==11
 with (OUT/'mixed_state_consequence_table.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 rates={}
 for t in SOURCES:
  rates[t]={}
  for flag in FLAGS:
   rates[t][flag]={label:fraction(sum(r[flag] for r in rows if r['target']==t and r['label']==label),sum(r['target']==t and r['label']==label for r in rows)) for label in ['HIGH_LEVERAGE','ZERO']}
 candidates={}
 for name,fs in CANDIDATES.items():
  bystate={}
  for t in SOURCES:
   props={label:fraction(sum(any(r[f] for f in fs) for r in rows if r['target']==t and r['label']==label),sum(r['target']==t and r['label']==label for r in rows)) for label in ['HIGH_LEVERAGE','ZERO']}
   props['high_more_often_than_zero']=props['HIGH_LEVERAGE']['fraction']>props['ZERO']['fraction']
   props['perfect_separation_in_observed_state']=props['HIGH_LEVERAGE']['fraction']==1 and props['ZERO']['fraction']==0
   bystate[t]=props
  candidates[name]={'by_state':bystate,'consistent_cross_cnf_direction':all(v['high_more_often_than_zero'] for v in bystate.values()),'perfect_separation_in_both_observed_states':all(v['perfect_separation_in_observed_state'] for v in bystate.values())}
 accepted=[k for k,v in candidates.items() if v['consistent_cross_cnf_direction']]
 result={'classification':'CANDIDATE_CONSEQUENCE_ABSTRACTION' if accepted else 'NO_SIMPLE_CONSEQUENCE_ABSTRACTION','rates_by_target':rates,'preregistered_candidates':candidates,'accepted_descriptive_candidates':accepted,'candidate_flag_vectors_identical_on_this_dataset':len({tuple(any(r[f] for f in fs) for r in rows) for fs in CANDIDATES.values()})==1,'counts':{'actions':len(rows),'HIGH':sum(r['label']=='HIGH_LEVERAGE' for r in rows),'ZERO':sum(r['label']=='ZERO' for r in rows)},'inputs_sha256':inputs,'scope':'Post-action descriptive relation on2 selected exact states; not pre-action predictor, prospective validation or independent sample estimate.','solver_runs':0}
 dump(OUT/'cross_cnf_comparison.json',result)
 cohort={'performed':False,'reason':'No candidate; posterior check not authorized by conditional protocol.'}
 if accepted:
  path=Path('results/state_sensitivity_cohort/cohort_summary.json');old=json.loads(path.read_text());rs=old['rows'];assert len(rs)==15 and all(r['conflict_changed'] for r in rs)
  dist=Counter(r['relative_ops_delta_percent'] for r in rs)
  high=[r for r in rs if r['HIGH_LEVERAGE']]
  cohort={'performed':True,'source_sha256':sha(path),'count':15,'all_selected_on_conflict_change':True,'effect_distribution':[{'delta_percent':d,'events':n} for d,n in sorted(dist.items())],'effect_min_percent':min(dist),'effect_max_percent':max(dist),'HIGH_LEVERAGE':fraction(len(high),15),'directions':{direction:fraction(sum(r['direction']==direction for r in rs),15) for direction in ['speedup','slowdown','unchanged']},'HIGH_directions':{direction:fraction(sum(r['direction']==direction for r in high),len(high)) for direction in ['speedup','slowdown']},'per_target':{t:{'count':5,'HIGH_LEVERAGE':fraction(sum(r['HIGH_LEVERAGE'] for r in rs if r['target']==t),5),'directions':dict(Counter(r['direction'] for r in rs if r['target']==t))} for t in SOURCES.keys()|{'T13'}},'counterexample_to_sufficiency':[r['event'] for r in rs if r['relative_ops_delta_percent']==0],'rows':[{'event':r['event'],'delta_percent':r['relative_ops_delta_percent'],'HIGH_LEVERAGE':r['HIGH_LEVERAGE'],'direction':r['direction']} for r in rs],'interpretation':'Conflict change is not sufficient for>=10% leverage or a favorable direction. All15 were selected on conflict change, so necessity cannot be established. Ratios are descriptive, not predictor performance. Samples overlap mixed surfaces and share trajectory prefixes.'}
 dump(OUT/'cohort_consistency.json',cohort)
 lines=['# Consequence Abstraction v1','',
'**CANDIDATE_CONSEQUENCE_ABSTRACTION。** 在现有T10/T8两个mixed states中，四个预注册候选均完全分开HIGH与ZERO；仅propagation reorder不能区分。这个结果是post-action描述性规律，不是predictor。','',
'只读取既有local_effects、action-run labels和snapshot manifests；未运行solver、未新增target/action/feature、未改10%阈值。T10共5个action（3 HIGH/2 ZERO），T8 S5共6个action（1 HIGH/5 ZERO）；ZERO均为原有实际0%。','',
'| Target | Consequence | HIGH satisfied | ZERO satisfied |','|---|---|---:|---:|']
 for t in SOURCES:
  for flag in FLAGS:
   x=rates[t][flag];h=x['HIGH_LEVERAGE'];z=x['ZERO']
   lines.append(f"| {t} | {flag} | {h['satisfied']}/{h['total']} ({h['percent']:.0f}%) | {z['satisfied']}/{z['total']} ({z['percent']:.0f}%) |")
 lines+=['',
'逐action总表：','',
'| Action | Label | Propagation | Conflict | Learned | Decision |','|---|---|---|---|---|']
 for r in rows:lines.append('| '+r['target']+'/'+r['action_id']+' | '+r['label']+' | '+' | '.join('1' if r[f] else '0' for f in FLAGS)+' |')
 lines+=['',
'预注册候选逐项判定：','',
'| Candidate | Definition | T10 HIGH / ZERO | T8 HIGH / ZERO | 结论 |','|---|---|---|---|---|']
 for name,fs in CANDIDATES.items():lines.append('| '+name+' | '+' OR '.join(fs)+' | 100% / 0% | 100% / 0% | 描述性候选 |')
 lines+=['',
'四条候选在这11个action上的真假向量完全相同，不能视为4份独立证据，也不能据此判断conflict、learning、decision哪一层才是机制。propagation在T10两类均100%，T8 ZERO也有4/5改变，故仅改变dequeue顺序没有同样区分力。','',
'候选成立后，按要求检查既有15个conflict-changing cohort events：','',
'- ≥10% HIGH_LEVERAGE：10/15（66.67%）。',
'- 方向：speedup5/15（33.33%）、slowdown9/15（60%）、zero1/15（6.67%）。',
'- HIGH子集：5个speedup、5个slowdown，均50%。',
'- 效应范围−46.918%至+49.038%；另外4个为+8.375%，未达到HIGH阈值。','',
'| Cohort delta | Event count |','|---:|---:|']
 for x in cohort['effect_distribution']:lines.append(f"| {x['delta_percent']:+.6f}% | {x['events']} |")
 lines+=['',
'反例T13_P329已经改变next conflict，但final ops仍为0%变化。所以“改变next conflict”不是大效应的充分条件，更不是好坏方向的充分条件。这15个event本来就按conflict change入选，无法用该后验样本证明它是普遍必要条件；10/15也不是独立prospective测试的预测准确率。cohort含有本轮surface的重叠事件，且多条共享轨迹，不应当作独立复制验证。','',
'更合适的定位是**候选必要筛选层**：在这两个mixed states中，HIGH都穿透到conflict/learning/decision，ZERO没有；更大cohort说明穿透之后仍可为zero、moderate或HIGH，方向也不确定。尚无理由根据“穿透”直接决定实际激活action。','',
'可以考虑下一阶段用短micro-rollout评估这一筛选层：必须比较同pre-state的baseline与候选分支。跑到首个conflict并完成analysis即可测CONFLICT_FRONTIER_CHANGE/LEARNING_CHANGE；DECISION_CHANGE可能要继续到后续实际decision，不能假定在首个conflict边界已知。本轮仅提出可检验方向，没有运行rollout、训练规则或自动激活。','',
'文件：[mixed_state_consequence_table.csv](mixed_state_consequence_table.csv)、[cross_cnf_comparison.json](cross_cnf_comparison.json)、[cohort_consistency.json](cohort_consistency.json)。','',
'1. **HIGH和ZERO能否被next-conflict/learned/decision consequence稳定区分？** 在现有两个mixed states中可以：HIGH三项均100%，ZERO均0%；仅propagation改变不行。','',
'2. **是否存在跨CNF simple consequence abstraction？** CANDIDATE_CONSEQUENCE_ABSTRACTION；A/B/C/D均符合，但在当前数据上完全等价，只能称描述性候选。','',
'3. **更像必要筛选层，还是足以预测leverage？** 更像候选必要筛选层，普遍必要性尚未证明，更不充分：cohort中conflict change仍有zero和moderate，也不能决定方向。','',
'4. **是否有理由考虑下一阶段短micro-rollout？** 有，值得检验其作为候选筛选层；尚不能据此直接决定激活。本轮未新增solver run或实验，完成后停止。','']
 (OUT/'CONSEQUENCE_ABSTRACTION_V1.md').write_text('\n'.join(lines))
 print(json.dumps({'classification':result['classification'],'rates':rates,'cohort_HIGH':cohort.get('HIGH_LEVERAGE'),'cohort_directions':cohort.get('directions')},indent=2))
if __name__=='__main__':main()
