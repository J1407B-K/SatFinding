"""Audit and report existing pre-action-only comparison; no solver execution."""
import json,csv
from pathlib import Path
from action_abstraction_v1 import OUT,NUM,U,sha,dump
s=json.loads((OUT/'cross_cnf_comparison.json').read_text());features=list(csv.DictReader((OUT/'action_features.csv').open()));ranks=list(csv.DictReader((OUT/'within_state_rankings.csv').open()))
assert len(features)==11 and len(ranks)==11*len(NUM)
assert sha(OUT/'action_features.csv')==s['preaction_features_sha256'] and sha(OUT/'within_state_rankings.csv')==s['rankings_sha256']
assert sha(OUT/'protocol.json')==s['protocol_sha256']
assert s['label_counts']=={'T10':{'HIGH_LEVERAGE':3,'ZERO':2},'T8':{'HIGH_LEVERAGE':1,'ZERO':5}}
coverage={}
for field in NUM:
 coverage[field]={}
 for t,n in [('T10',5),('T8',6)]:
  rr=[r for r in ranks if r['state']==t and r['feature']==field];assert len(rr)==n
  known=sum(r['raw_value']!=U for r in rr);coverage[field][t]={'known':known,'total':n,'complete_ranking':known==n}
  if known<n:assert all(r['rank_ascending_among_all_actions']==U and r['normalized_rank']==U for r in rr)
  else:
   for r in rr:
    values=[float(x['raw_value']) for x in rr];v=float(r['raw_value']);rank=1+sum(x<v for x in values)+(sum(x==v for x in values)-1)/2
    assert float(r['rank_ascending_among_all_actions'])==rank and abs(float(r['normalized_rank'])-(rank-1)/(n-1))<1e-12
assert not s['candidate_features'] and s['classification']=='NO_SIMPLE_ACTION_LOCAL_ABSTRACTION'
s['coverage']=coverage;s['interpretation']={'fully_observed_numeric_features':sum(all(v['complete_ranking'] for v in state.values()) for state in coverage.values()),'total_numeric_features':len(NUM),'result':'NO_SIMPLE_ACTION_LOCAL_ABSTRACTION','limitation':'No consistent separation among fully observable features. Missing heap/signed-almost-unit/antecedent coverage prevents testing the entire frozen set. Do not interpret missing data as negative evidence.','deeper_relational_structure':'Possible, not established by this incomplete descriptive comparison.','effect_sign_analyzed':False,'predictor_tested':False,'stopped':True}
solver=Path('/private/tmp/satfinding-fixed-state-action-surface/glucose-3.0/core/Solver.cc');s['input_sha256'][str(solver)]=sha(solver)
dump(OUT/'cross_cnf_comparison.json',s)
lines=['# Action Abstraction v1','',
'**NO_SIMPLE_ACTION_LOCAL_ABSTRACTION。** 完整可比较的pre-action字段没有在T10、T8两组内一致区分HIGH-LEVERAGE与ZERO；部分指定字段无法从现有artifact可靠恢复，结论受覆盖限制，不能把UNAVAILABLE当作“无区分力”的证据。','',
'本轮仅使用两个既有mixed states：T10 hash `422271443557180589`（5个action，3 HIGH / 2 ZERO）与T8 S5 hash `13866032343213679985`（6个action，1 HIGH / 5 ZERO）。没有新增target、intervention、solver rerun或instrumentation；未分析effect sign。HIGH标签沿用≥10%，ZERO全部为原有实际0%，未改变任何标签。','',
'计算顺序固定：先输出pre-action feature表与组内rankings，再加载已有action-run标签作比较。合法action全集不变。rank按各state独立计算：raw值升序、并列用平均rank；normalized rank=(rank−1)/(N−1)。全部并列时为0.5。heap raw字段是原生数组位置，较小表示更靠前，不冒充按activity排序的rank。若任一action缺少该feature，则该state整列排名均为UNAVAILABLE，避免用不完整分母制造分离。','',
'数据可用性与来源：','',
'- 现有frozen_state.json明确是内存snapshot的manifest，不是完整可加载的assignment/heap dump；hash不能反解出缺失字段。',
'- 两个state均为C0、analysis ops0。输入CNF没有unit clause、tautology或重复literal，初始root assignment为空，因此首次conflict前active DB成员仍是原始CNF；watch重排不改变occurrence。使用其2600条原始clause计算active occurrence及fan-out。',
'- 固定solver的rnd-init=false且driver未覆盖；activity初始化为0，bump发生于analyze。两个snapshot都在首次analysis前，因此所有候选activity可靠为0。',
'- heap/antecedent只采用相同pre-state hash的既有descriptor记录。T10覆盖#831/#833；T8覆盖#381/#1014/#1734/#1736。没有借用相邻不同state的数据。',
'- 旧almost-unit统计只按variable汇总，没有正反极性拆分，不能替代本轮signed counts。仅利用合法action审计已保存的pre-assignment facts计算确实可确定的条目；其余UNAVAILABLE。','',
'| Frozen numeric feature | T10 raw覆盖 | T8 raw覆盖 | 完整跨state组内rank比较 |','|---|---:|---:|---|']
for field,c in coverage.items():lines.append(f"| {field} | {c['T10']['known']}/5 | {c['T8']['known']}/6 | {'可比较' if all(v['complete_ranking'] for v in c.values()) else 'UNAVAILABLE'} |")
lines+=['',
'original/learned这一categorical字段11/11可用，全部original。14个numeric子字段中7个完整覆盖，7个未完整覆盖；没有添加替代feature。','',
'完整可比较字段的within-state结果：','',
'| Feature | T10 HIGH vs ZERO | T8 HIGH vs ZERO | 是否一致区分 |','|---|---|---|---|',
'| clause length | 全部2；normalized rank均0.5 | HIGH=2，rank0.3；ZERO=2/3，rank0.3/0.9 | 否，有并列 |',
'| original / learned | 全部original | 全部original | 否 |',
'| activity | 全部0；rank0.5 | 全部0；rank0.5 | 否 |',
'| active occurrence / fan-out | 全部9；rank0.5 | 全部9；rank0.5 | 否 |',
'| binary occurrences | 全部8；rank0.5 | 全部8；rank0.5 | 否 |',
'| ternary occurrences | 全部1；rank0.5 | 全部1；rank0.5 | 否 |',
'| long occurrences | 全部0；rank0.5 | 全部0；rank0.5 | 否 |','',
'没有直接把不同CNF的raw数值硬比。上表先判断每个state内部的类别位置，再检验两个state是否出现相同方向的严格分离。raw值恰好相同不构成跨CNF预测规则。','',
'部分可观测字段也不能制造候选：T10缺少两个ZERO action和一个HIGH action的heap/antecedent信息，无法形成完整比较；T8四个已记录action的antecedent level都为21，同时包含HIGH和ZERO。T8两个positive-literal action的same-literal almost-unit count可确定为0，因为各自唯一positive clause就是已审计unit clause，并非almost-unit；其它signed counts未确定，因此不据此下结论。','',
'预注册判定逐项保留全部结果：完整numeric feature须在两个state中均满足HIGH整体严格高于ZERO，或均严格低于ZERO；跨类并列不算分离。不拟合cutoff，不组合feature，不因最终标签追加字段。categorical source也无区分。没有通过该判定的候选。','',
'结果说明的是：**现有可可靠观测的action-local字段未找到简单abstraction**。不能宣称完整冻结feature set已全部被检验并证伪。更深的state×action关系可能重要，但缺失信息本身不能证明这个机制。本轮不继续硬凑局部feature、评分公式或predictor。','',
'文件：[action_features.csv](action_features.csv)、[within_state_rankings.csv](within_state_rankings.csv)、[cross_cnf_comparison.json](cross_cnf_comparison.json)。feature/rank表不含final ops或effect sign；标签与逐feature比较保存在comparison JSON。','',
'1. **HIGH与ZERO的pre-action局部特征有何稳定差异？** 在完整可比较字段中没有稳定差异；activity、occurrence/fan-out及clause来源都并列，clause length也不能分开类别。heap、signed almost-unit和antecedent coverage不完整，不能据此补强结论。','',
'2. **是否存在跨CNF一致的simple action-local abstraction？** 本轮未找到；缺失字段尚未得到完整检验，不视为阴性证据。','',
'3. **结果是哪一类？** NO_SIMPLE_ACTION_LOCAL_ABSTRACTION，限定为现有可用artifact支持的描述性比较。','',
'4. **是否进入prospective test？** 没有候选，本轮未测试predictor，也未新增任何实验。完成后停止。','']
(OUT/'ACTION_ABSTRACTION_V1.md').write_text('\n'.join(lines))
print(json.dumps(s['interpretation'],indent=2))
