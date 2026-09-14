import json
from pathlib import Path
from evaluation_oracle_run import sha
P=Path('results/l2_delayed_amplification')
def read(p):return json.loads(p.read_text())
a=read(P/'analysis.json');runs=read(P/'runs.json');valid=read(P/'forced_valid/runs.json')
old=read(Path('results/l1_l2_latent/natural_proof_checks.json'))
for n in ['A','B']:assert runs[n]['proof_sha256']==old[n]['proof_sha256']
for n,r in runs.items():assert r['proof_verified']
for n,r in valid.items():assert r['proof_verified']
for p in [P/'protocol.json',P/'forced_valid/protocol.json']:
 proto=read(p);sources=proto.get('sources',proto.get('build',{}).get('sources',{}))
 assert all(sha(k)==v for k,v in sources.items()),p
ledger=dict(natural_proofs_byte_identical_to_previous=True,all_11_dynamic_proofs_verified_against_A=True,all_four_valid_forced_comparison_proofs_verified=True,all_dynamic_pre_states_match_A=True,all_dynamic_injections_changed_only_clause_storage_and_watches=True,forced_prefix_and_snapshot_checks=a['forced'],source_hashes_unchanged=True,invalid_initial_forced_attempts='invalid_forced_runs.json',authoritative_forced_runs='forced_valid/runs.json')
(P/'audit.json').write_text(json.dumps(ledger,indent=2))
rows=[]
for r in a['injections']:
 s=r['stats'];e=r['first_l2'];l=r['first_learned_vs_A']['run'];d=r['first_decision_vs_A']['run']
 rows.append(f"| {r['point']} | {s['analysis_resolution_steps']:,} | {s['conflicts']:,} | {s['decisions']:,} | {e['c']} / {e['d']} / {e['e']} | {l['c']} | {d['d']}（c{d['c']}） |")
table='\n'.join(rows)
frows=[]
for n in ['A','A_FORCED','B','B_FORCED']:
 s=valid[n]['stats'];frows.append(f"| {n} | {('-570' if n in ['A_FORCED','B'] else '-187')} | {s['analysis_resolution_steps']:,} | {s['conflicts']:,} | {s['decisions']:,} |")
ft='\n'.join(frows)
report=f'''# L2 delayed amplification：198不是必要窗口，828是依赖上下文的重要分叉

固定 `n200_T_r01_s7201`，A=TEMPLATE+L1（24458），B=A+L2（30149，`[-507,565,566]`）。没有新 target、subset、参数、selector 或 ML。预先指定的12个注入点全部完成；没有根据结果补点。

**主要结果：L2 到 conflict600 才注入，仍为169,863 ops；B 把 decision828 改为-187，则变成330,644 ops。A 单独改为-570仍需331,444 ops。** 因而不能把机制写成“198的早期扰动不可缺少地累积到828”；更接近“L2在更晚阶段仍能形成有效的搜索上下文，而828的选择对该上下文中的后续长尾很重要”。

## 1. L2 在 A 轨迹上什么时候第一次有机会生效？

Ghost 不安装 clause、不写 solver 字段。每次 enqueue 和完整 backtrack 后检查 L2 的三个 literals；记录 satisfied / inactive（无真且至少两个未赋值）/ unit / conflict 的状态转移。逐事件转移 ledger 见 [A.events.jsonl.gz](results/l2_delayed_amplification/A.events.jsonl.gz)，摘要见 [analysis.json](results/l2_delayed_amplification/analysis.json)。稳定状态不重复打印；backtrack 作为一次完成操作监控，不记录其内部逐变量撤销的瞬间。

| A 上的第一次机会 | 精确位置 | 状态 |
|---|---|---|
| ghost unit | c166后，d235，e23434，g47398 | 507=true，565=false，566未赋值；可推出566 |
| ghost conflict | c290后，d383，e42870，g85735 | 507=true，565=false，566=false |

`c` 在传播时指已完成 conflict 数；`d` 是累计 decision 序号，`e` 为累计 enqueue，`g` 为本 ledger 独立事件号，含 ghost 转移，不能与旧 ledger 的g直接相减。

第一段 unit 机会从 e23434 持续至 C167 回跳（e23442，g47641），随后变为inactive。A/B 当时都先遇到原有 conflict，没有把566按L2推出；旧 B 的该段没有 L2 watcher 检查事件。因此“赋值状态已使 clause unit”不等于传播队列已经处理它，更不等于它会成为实际 reason。

## 2. 真实首次激活与 ghost activation 是否一致？

**第一次可能 unit（c166）与首次真实 reason（c198）不一致。** 但 c198 的实际使用落在对应 ghost-unit 区间内：

- A 在 c198/d271/e28889，g58131 已使 L2 unit，可推出565。
- A 在 e28916、g58159 由原始 `[565,566,567]` 推出565，ghost转为satisfied。
- B 在相同 c198/d271/e28916，由L2推出565（B g58093）。

即首次实际 reason substitution 与这一后续机会对应，相隔27个 enqueue 序号；它不是最早的逻辑机会。前100 conflicts 仍没有 ghost unit / conflict，这与此前冻结的前期结果一致。

Ghost自然A的所有完整 native counters 与旧A一致，**完整 UNSAT proof 的 SHA256也与旧A相同**；自然B同样重现。前900 conflicts的全部 learned内容和decision事件与旧ledger相同。监控没有形成新的实验性扰动。

## 3. 是否存在 critical injection window？

**在预定的0…600范围，没有找到收益消失的 critical window；尤其198不是必要窗口。** c600注入仍得到169,863 ops，相比静态B只多5 ops。

正数注入点严格定义为：该 conflict 的分析、回跳、learned安装及decay完成后，下一次propagate前。0为按原顺序静态安装L2的自然B。每条正数run此前都按纯A运行；其注入前完整逻辑snapshot与自然A同边界匹配。11个实际注入现场L2的三个literals均非false；均只安装clause和watches，**没有发生额外回跳、立即unit断言或立即conflict**。因此本批收益不是注入附带强制restart或root reset造成的。

| 注入c | 最终ops | conflicts | decisions | L2首次reason c / d / e | 首次learned不同于A：c | 首次decision不同于A：d |
|---:|---:|---:|---:|---|---:|---|
{table}

全部动态run的**完整有序 learned-content 序列都与B一致**。0/100/150/300/400/600的完整decision-literal序列也与B一致；180…250组并非逐decision完全相同，首次与B不同在d1635/c1336（B=358，该组=-359），但最终learned序列、conflicts和decisions总数仍相同。不能仅凭相同总数声称完整微状态一致。

180…250才安装的L2，甚至没有复现c198的第一次reason使用，而在c290后才第一次成为reason，仍保留几乎全部收益。到600才安装则在c604/d773/e89962首次成为reason，同样在C656出现learned分叉、d828出现branching分叉。这直接反驳“必须先经历C199的那次activity/heap扰动才会得到短轨迹”。它不排除600之后存在尚未测试的截止窗口。

所有首次reason、learned/decision divergence的完整事件记录及SHA审计见 [analysis.json](results/l2_delayed_amplification/analysis.json)；表格数据见 [injection_summary.csv](results/l2_delayed_amplification/injection_summary.csv)。

## 4. decision828 是否真正影响长尾？

**在B的上下文中影响很大；不是能从B搬到A的充分开关。** 合法结果如下：

| run | decision828 | 最终ops | conflicts | decisions |
|---|---:|---:|---:|---:|
{ft}

- A→强制-570：少14,148 ops（4.09%），仍接近A，远未复制B的短轨迹。
- B→强制-187：多160,786 ops（94.66%），回到接近A的长轨迹。
- B的这次改变数值上撤回了原A/B差距的91.49%。这只是当前成对反事实差值，**不是“decision828解释了91.49%的因果中介比例”**。

两方向干预都在c657、d828发生；A的e98056，B的e98013。干预前累计ops分别为25,286 /25,256，仅差30；自然run剩余搜索为320,306 /144,602 ops。175,734的最终差距中175,704发生在这一位置之后，但时间上的位置本身不证明归因。

两条强制run相对各自自然run，第一次learned内容分叉都在C659。该处还出现可检查的局部交换：A_FORCED的C659 learned hash等于自然B；B_FORCED等于自然A。然而A_FORCED最终仍长，说明复制一个branch及其邻近的单条learned结果，仍不等于复制完整后续搜索。

合法性：两个目标变量都未赋值且decision-eligible，传播队列已清空；前827次decision和此前全部learned内容分别与本run自然对照一致，decision828前逻辑snapshot逐字段相同。有效实现从选支入口直接返回指定literal，保留自身heap，后续由原有lazy pop处理已赋值变量；不把任何未赋值eligible变量丢出heap。保留native同一次RNG推进（当前随机选变量概率为0、无随机polarity），没有复制对方activity、heap、phase、reason或数据库。override前后snapshot完全相同；RNG单独记录，推进前后值与自然pick一致。四条有效run的UNSAT proof全部验证通过。

**实现审计记录：** 初版“先native pop再替换literal”会遗留未选中的变量在heap外，不满足eligible变量覆盖约定；两条结果作废。仅修正这一实现错误后重跑同两个预定干预，没有修改指定literal或新增条件。即使初版proof通过，也不把它作为合法intervention evidence。权威结果是 [forced_valid/runs.json](results/l2_delayed_amplification/forced_valid/runs.json)，作废记录见 [invalid_forced_runs.json](results/l2_delayed_amplification/invalid_forced_runs.json)。

## 5. 当前最合理的链条是什么？

原链条需要两处修正：**198不是必要起点；fork的效果依赖当时及后续的L2上下文。** 当前最可信的描述是：

`L2在搜索中获得传播/证明机会（可以晚至600之后）`

`→ 不同reason / analysis，以及后续learned与其他内部状态`

`→ 在C656附近形成不同learned结果，d828进入不同分支`

`→ 在B上下文中，这个分支选择显著影响后续搜索长度。`

“long-tail avoidance”在这里仅指观察到的剩余ops大幅变少；尚未识别具体哪些子树、重复冲突或证明片段被避免。不能把第一处reason substitution、单条learned内容、activity或某个decision literal单独称为完整解释。

A_FORCED不复制B收益，至少说明branch literal本身不足；剩余差异可能来自此前形成的learned/phase/activity/watch状态，以及**B中L2后续仍然存在并继续使用**。本轮没有区分“此前状态”与“后续继续可用的L2”，不能只归因于前者。

## 6. 哪一段已有 intervention evidence？

- **L2不需要从198前一直存在：** 延迟到600仍取得B类结果，且此前严格是A。这是对早期激活必要性的直接反证。
- **晚加入L2仍能改变最终搜索：** c600注入对照A，345,592→169,863 ops；所有注入前状态匹配，没有附带回跳。
- **B状态下改变decision828会改变长尾：** 强制-187使169,858→330,644 ops；不是只有轨迹ID不同而长度不变。
- **单独给A同一literal不足以复现B：** A_FORCED仍为331,444 ops，提供不充分性的成对证据。

这是固定target、固定两配置、固定注入与选支语义下的证据，不作跨target推广。

## 7. 哪一段仍是相关观察？

自然B的`C199 reason→analysis/activity/heap`已有可检查的局部执行链，但“这一早期写入累积并决定最终收益”已不再得到支持。`C656 learned差异→d828选择差异`与`哪些既有状态使-570在B中有效`，本轮没有独立交换对应state，因此仍不能分离归因。

所有延迟run复现B的learned-content序列很强，但不证明整个state相同，也不证明每次L2直接使用都必要。B_FORCED变长也不证明该fork唯一必要、更不能说明其余L2作用没有贡献。当前证据排除“198是唯一关键窗口”和“branching差异纯粹无关紧要”，不支持“只换828就能让任意上下文变好”。

自然A/B的proof与上一轮逐字节相同；11条动态注入proof含显式L2添加，均在**原始A输入**上由drat-trim验证，而非靠先把L2放入checker输入放宽验证。全部构建/输入hash、注入前快照、合法强制前后快照和proof检查见 [audit.json](results/l2_delayed_amplification/audit.json)。注入protocol在运行前冻结，修正后的强制实现也单独冻结。

## 8. 下一步最小实验是什么？

下一轮只预冻结一个 **c657注入L2** 的run，与现有A及c600注入对照：它位于首次learned内容分叉C656之后、decision828之前。检验越过这一位置后是否仍能取得短轨迹，从而把问题从已排除的198窗口收缩到learned/branch分叉附近。若收益仍保留，则C656也不是必要窗口；若不保留，仅支持这个边界敏感，不能立即断言某条learned是唯一mediator。

**本轮未执行c657或其他新增注入点。** 当前回答是：一条冗余L2能够在较晚阶段改变证明与搜索上下文，并使后续某次branch选择对长尾产生很大影响；已经有条件性的干预证据，但仍不是最终50.85%差距的完整逐事件解释。
'''
Path('L2_DELAYED_AMPLIFICATION.md').write_text(report)
print('Report and audit written; source/proof/snapshot checks passed')
