"""Read-only verification of old seals; bind new mechanistic evidence and report."""
import difflib,sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from analyze import *
sys.path.insert(0,str(ROOT))
import cleanup_repository
def readcsv(name):return list(csv.DictReader((OUT/name).open()))
def main():
 r=load(OUT/'MECHANISM_RESULT.json');audit=load(OUT/'MECHANISM_DATASET_AUDIT.json')
 fate=readcsv('baseline_fate_tracking.csv');controls=readcsv('matched_control_fate_tracking.csv');restore=readcsv('branch_restoration_results.csv');suppress=readcsv('branch_suppression_results.csv');divs=load(OUT/'FIRST_DIVERGENCE.json')
 assert all(int(x['next_decisions_observed'])==8 for x in fate+controls)
 assert all(x['fate']=='B_NATURAL_PROPAGATION' and int(x['decisions_until_fate'])==0 for x in fate)
 assert all(x['first_downstream']['baseline']['decisions']==0 and x['first_downstream']['treatment']['decisions']==0 for x in divs if x['HIGH'])
 assert all(x['raw_after_injection_omitted']['type']=='PROPAGATION_FIRST' for x in divs if x['HIGH'])
 active=cleanup_repository.verify_active();assert active['passed']
 dump(OUT/'SEALED_ARTIFACT_INTEGRITY.json',active)
 routechecks=[]
 for d in [OUT/'runs',OUT/'historical_runs']:
  for p in d.rglob('result.json'):
   m=load(p);target=m.get('action',{}).get('source')
   builddir=OUT/('build_'+('T10' if m['state_id']=='HIST_T10_FIXED' else 'T8')) if 'state_id' in m else BUILD
   assert sha(builddir/'run')==m['binary_sha256'] and sha(builddir/'manifest.json')==m['build_manifest_sha256']
   proof=p.parent/'proof.drup' if 'state_id' not in m else p.parent.parent/(m['tag']+'.drup')
   assert sha(proof)==m['proof_sha256'] and m['proof']=='VERIFIED'
   log=proof.with_name('proof.log') if 'state_id' not in m else proof.with_suffix('.proof.log')
   assert 's VERIFIED' in log.read_text()
   routechecks.append({'route':str(p.relative_to(ROOT)),'binary_sha256':m['binary_sha256'],'proof_sha256':m['proof_sha256'],'verified':True})
 patchrows=[]
 for target,original,built,inc in [
  ('v3',ROOT/'harness_v3/glucose-3.0',BUILD/'glucose-3.0',ROOT/'harness_v3/observer.inc'),
  ('T10',Path('/private/tmp/satfinding-fixed-state-action-surface/glucose-3.0'),OUT/'build_T10/glucose-3.0',ROOT/'fixed_state_action_surface.inc'),
  ('T8',Path('/private/tmp/satfinding-multi-state-action-surface/glucose-3.0'),OUT/'build_T8/glucose-3.0',ROOT/'multi_state_action_surface.inc')]:
  diffs=[]
  for rel in ['core/Solver.cc','core/Solver.h','mtl/Heap.h']:
   diffs.extend(difflib.unified_diff((original/rel).read_text().splitlines(True),(built/rel).read_text().splitlines(True),fromfile=str(original/rel),tofile=str(built/rel)))
  diffs.extend(difflib.unified_diff(inc.read_text().splitlines(True),(built.parent/'observer.inc').read_text().splitlines(True),fromfile=str(inc),tofile=str(built.parent/'observer.inc')))
  path=OUT/f'{target}_instrumentation.patch';path.write_text(''.join(diffs));patchrows.append({'target':target,'patch':path.name,'sha256':sha(path)})
 validation={'active_integrity_checks':len(active['checks']),'active_integrity_passed':active['passed'],'sealed_artifacts_modified':0,'final_routes_verified':len(routechecks),'route_checks':routechecks,'instrumentation_patches':patchrows,'invalid_attempts_excluded':['invalid_rank_index_attempt','initial_observer_runs','initial_historical_runs','pre_binding_runs','pre_binding_historical_runs'],'engineering_corrections':['semantic_order returns one-based variable IDs; first observer attempt had off-by-one rank/top lookup and is excluded','CF hooks preserve exactly one native RNG draw per branch; canonical activity mode required','final retained builds bind every reported route by binary and source-manifest hashes'],'alignment':'Raw event mismatch retained. A separate diagnostic omits one baseline natural enqueue corresponding to the early injection, then compares ordered downstream events with no resynchronization. Both classify all five HIGH actions as PROPAGATION_FIRST. Complete continuation counters/proofs are verified beyond bounded 10000-event observer.'}
 dump(OUT/'FINAL_MECHANISM_AUDIT.json',validation)
 lines=['# Branch-displacement mechanism v1','',
 'B — **BRANCH_DISPLACEMENT_NOT_PRIMARY_MECHANISM**。这是 exploratory mechanistic causal study，未改变任何旧 scientific label。结论限于这 3 个 exact states / 5 个 HIGH actions：证据不支持“提前移走一个即将发生的高优先级 branch”是初始主要 carrier；不排除后续 branch choices 对成本的中介作用。','',
 '协议在本轮 native outcomes 前冻结：N_DECISIONS=8、RESTORE_DECISIONS=1、SUPPRESS_DECISIONS=1，fate/trace horizon=10000 semantic events。50% effect attenuation 是预先冻结的 substantial-restoration 标准，不是事后寻找阈值。','',
 '## Dataset and baseline fate','',
 '纳入正式 v3 的 1 state / 1 HIGH，以及历史 T10 fixed 的 3 HIGH、T8 S5 的 1 HIGH。三个 state 只有两个 CNF targets，且 T10 两个 state 共用 baseline trajectory；不能当作五个独立复制。三个 matched NON-HIGH 均按同状态最低 frozen action rank 选取，效果均为 0%。','',
 '| State / action | Implied literal | Activity | Activity rank | Native heap rank | Baseline natural fate (dequeues) | Next-8 decision positions |',
 '|---|---:|---:|---:|---:|---:|---|']
 for f in fate:lines.append(f"| {f['state_id']} / {f['action_id']} | {f['implied_literal']} | {float(f['activity']):.7g} | {f['activity_rank']} | {f['heap_rank']} | {f['dequeues_until_fate']} | {f['next_decision_positions']} |")
 lines+=['','全部 5/5 implied variables 都在 baseline 的第一次新 decision、conflict 或 restart 前自然赋值。Next 1/2/4/8 decisions 的覆盖数为 0/1/1/1。唯一有近期 branch relevance 的是 v3 var 27：先自然传播，经过 backtrack 后在 decision #2 和 #8 被选择。HIGH 保留 #2，到 #8 才把 baseline +27 改为 -204；这已在 6 次 conflict 之后。','',
 '历史 activity 全部为 0；300.5 是 600 个变量的并列平均名次，不代表高优先级。这些 native ranks 来自原 build 的受保护 replay 与独立 observer 副本：旧 binary/source hashes 匹配、原 operational checkpoint guard/heap+inverse guard 不变、frozen legal actions 完全一致、baseline/action 完整 counters 和 proof bytes 复现。旧 snapshot 没有 canonical serialization，因此 `canonical_cross_build_rank=unavailable`；本研究没有把旧 hash 升级为 canonical identity。历史值只作为经等价 replay 绑定的 native context，不能制造跨 build 的优先级标尺。','',
 '| Matched NON-HIGH | Activity rank / native heap rank | Fate dequeues | Next-8 implied-variable decision |','|---|---|---:|---|']
 for c in controls:lines.append(f"| {c['state_id']} / {c['action_id']} | {c['activity_rank']} / {c['heap_rank']} | {c['dequeues_until_fate']} | {c['next_decision_positions']} |")
 lines+=['','## First downstream divergence','',
 'HIGH：PROPAGATION_FIRST=5，BRANCH_FIRST=0，CONFLICT_FIRST=0，OTHER_FIRST=0。注入本身不计为机制结论。FIRST_DIVERGENCE.json 保留只去掉 injection 的原始首次 mismatch、单次自然 enqueue 对齐诊断、assignment/decision/conflict/learned/heap 各层投影。两种对齐都得到相同分布；诊断中的首次真实 dequeue 变化全部发生在新 decision 和新 conflict 之前。','',
 'v3 的 baseline 在 dequeue -432 时依次 enqueue 430、126、27；HIGH 把 27 提前放入队列，因此后续第 2 个 dequeue 由 430 变为 27。两边第一新 decision 仍为 188。该队列顺序差异早于 branch skeleton 差异。另记录后续不同 implication、conflict、learned clause 与 heuristic state，不把“最深改变层”误当作“最早分歧层”。','',
 'NON-HIGH 也可能产生 propagation-order 差异而没有长期效果；因此 PROPAGATION_FIRST 本身不是 sensitivity descriptor。本轮没有建立任何预测规则。','',
 '## Legal counterfactuals','',
 '在每个 action 的 next-8 skeleton 中选择第一处不同的 baseline decision。历史案例针对第 1 个新 decision（T10 +176、T8 -441），v3 针对第 8 个新 decision（+27）。它们都是 downstream mediation interventions；历史目标不是 implied variable，且第一次 learned-clause 差异已经发生，不能冒充直接取消 implied-variable branch 的实验。','',
 'RESTORE1 只在目标变量仍未赋值且 decision eligible 时强制 baseline polarity。保留其 heap lazy-assignment removal，后续 native scan 会跳过 assigned entry。SUPPRESS1 在该变量成为真实 native choice 时，继续扫描下一个未赋值 eligible heap candidate，再 native reinsert 被跳过变量。每个 branch 保留一次 native RNG draw。全部 counterfactual 完整 UNSAT continuation 经独立 proof verification；不存在非法赋值或撤销 implication。','',
 '| Action | Baseline remaining ops | HIGH effect | HIGH+RESTORE1 effect | Attenuation | SUPPRESS1 effect | Signed HIGH shift reproduced |','|---|---:|---:|---:|---:|---:|---:|']
 for a,s in zip(restore,suppress):lines.append(f"| {a['action_id']} | {a['baseline_remaining_ops']} | {float(a['high_effect_percent']):+.2f}% | {float(a['counterfactual_effect_percent']):+.2f}% | {100*float(a['attenuation_fraction']):.1f}% | {float(s['counterfactual_effect_percent']):+.2f}% | {100*float(s['signed_high_shift_reproduced']):.1f}% |")
 lines+=['','RESTORE1：5 次合法且实际改变选择的实验，5/5 部分削弱效果，但 0/5 达到冻结的 50% substantial attenuation；HIGH 的大部分效果保留。','',
 'SUPPRESS1：5 个 action 对照、3 个不同的 baseline interventions；T10 三个 HIGH 共享同一个 +176 suppression。4/5 对照产生至少一半的同方向成本变化（对应 2/3 独特 suppression）。但 0/5 复现 HIGH 最早改变的 learned clause，0/5 复现完整 next-8 skeleton；SUPPRESS1 的首次分歧为 BRANCH_FIRST，而 HIGH 为 PROPAGATION_FIRST。成本相似支持后续 branch 对成本敏感，不能据此证明 early enqueue 通过直接移走 branch 起效。','',
 '## Strict interpretation and limits','',
 'A 的必要条件不满足：高 activity 模式未在历史 positives 复制，历史 implied vars 不在 next 8 decisions，全部 HIGH 先出现传播分歧，单 decision restoration 未显著消除效果。B 有跨 state 的方向一致证据，并非因为 counterfactual 缺失而硬判。C 不适用：exact guarded/equivalent replay 和合法 counterfactual 都执行成功。','',
 '这里否定的是所提出的直接 high-priority branch-displacement 主导解释。单次 restoration 不能排除多个后续 decisions 的中介作用；只按 ordinal 对齐的 branch forcing 也不能恢复此前已经改变的 implication/learned state。此限制使“部分削弱”具有意义，但不等于整个 CDCL trajectory 被复原。下一方向为 propagation-order / implication-graph bifurcation，本轮不继续第二大实验。','',
 '## Evidence and reproducibility','',
 f"最终 {len(routechecks)} 个 route 完整 continuation / proof VERIFIED。Observer 的 baseline 与原 HIGH/NON-HIGH counters、proof hashes 复现；所有最终 route 绑定当前 retained binary/source manifest。Active sealed integrity {len(active['checks'])}/{len(active['checks'])} PASS，sealed artifacts modified=0。",
 '',
 '新代码位于 `branch_displacement_mechanism_v1/`；原生副本与全部 raw outputs 在本结果目录。`final_runs.py` 要求全新的 runs/historical_runs 目录，防止无声覆盖证据。之后运行 `analyze.py`、`finalize.py`。`FINAL_MECHANISM_AUDIT.json` 列出 excluded engineering attempts；它们没有参与结果计算。`*_instrumentation.patch` 可逐行审查 observer 与 decision hook。`MECHANISM_ARTIFACT_MANIFEST.json` 绑定最终证据；协议 hash 自冻结后未改变。','']
 (OUT/'BRANCH_DISPLACEMENT_MECHANISM_V1.md').write_text('\n'.join(lines))
 (OUT/'NEXT_MECHANISM_HYPOTHESIS.md').write_text('''# Next mechanism hypothesis: propagation-order / implication-graph bifurcation

本轮 B：5/5 HIGH 为 PROPAGATION_FIRST；全部 implied vars 先自然传播，历史 HIGH 没有高 activity / next-8 branch 的共同模式。单 decision restoration 保留大部分效果；suppression 能产生近似成本变化，却不复现最早改变的 learned clause。

候选链为：legal early enqueue → FIFO / watcher processing order changes → implication edge or reason changes → conflict cone / learned clause changes → later heuristic and decision divergence。当前证据支持先后顺序，不足以证明其中每一条因果边。

下一轮应冻结并检查：

1. Action 是否改变 upcoming propagation closure 的集合、顺序或 reason；把只重排同一 closure 与改变 closure 区分。
2. 第一条改变的 implication edge，以及其是否进入第一处不同 conflict cone。
3. 第一次 learned clause 的内容、asserting literal、backtrack 与活动更新分歧。
4. Watcher traversal / watched-literal swap 是否保存了早期顺序变化，并在后续重新激活。
5. 对这些边或顺序做最小 solver-legal 因果实验，保留 exact replay 与完整 proof verification。

同状态 NON-HIGH 也可能发生传播次序变化，必须保留 matched controls，不能把 PROPAGATION_FIRST 当作 predictor。不要进行 ML、gate、controller 或 rank cutoff search。本轮没有执行上述第二大实验。
''')
 excluded=set(validation['invalid_attempts_excluded'])
 files={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.relative_to(OUT).parts[0] not in excluded and p.name not in ['MECHANISM_ARTIFACT_MANIFEST.json','MECHANISM_ARTIFACT_MANIFEST.sha256'] and '__pycache__' not in p.parts}
 manifest={'protocol_sha256':sha(OUT/'BRANCH_DISPLACEMENT_PROTOCOL_V1.json'),'files':files,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in HERE.glob('*') if p.is_file()},'excluded_engineering_attempts':sorted(excluded)}
 dump(OUT/'MECHANISM_ARTIFACT_MANIFEST.json',manifest);(OUT/'MECHANISM_ARTIFACT_MANIFEST.sha256').write_text(sha(OUT/'MECHANISM_ARTIFACT_MANIFEST.json')+'\n')
 print(json.dumps({'active_checks':len(active['checks']),'final_verified_routes':len(routechecks),'manifest_files':len(files),'result':r['verdict']}))
if __name__=='__main__':main()
