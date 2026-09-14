# ACTIVITY / HEAP MEDIATION

**结论：decision22恢复为CONTROL的−259。支持activity/heap对首次branching分叉的局部中介作用；不支持它们完全解释最终35.8%的收益。**

## 1. decision22是否恢复？

| 固定run | decision22 |
|---|---:|
| CONTROL=TEMPLATE | −259 |
| GOLD=TEMPLATE+Gold64 | −260 |
| GOLD_ACTIVITY_RESET | **−259** |

使用原n200_T_r01_s7201、原Gold64与注入顺序、同一Glucose3.0及全部参数。在完成conflict3、前21次decision已执行、传播队列已清空之后，**紧接第22次pickBranchLit调用之前**，执行一次状态移植。未做其他干预。

## 2. activity/heap是否足以解释首次branching分叉？

**在这个固定Gold搜索状态、这个局部时刻，二者联合恢复足以把decision22恢复。** 恢复的是bit-exact activity doubles、heap实际数组及inverse indices；没有调用heapify，也没有恢复CONTROL的trail/reasons/phases等状态。heap comparator仍绑定Gold自己的activity对象。内存地址与buffer capacity不属于变量排序，不跨进程复制。

**更具体地，259与260的activity在三个run中都为2.5625，二者均未赋值且phase都选负。** 差异不是“260分数比259更高”，而是历史操作留下的heap平局顺序。

| pickBranchLit的堆弹出顺序开头 | 行为 |
|---|---|
| CONTROL / RESET：90、261、259… | 90、261已赋值，跳过；259成为首个可选变量 |
| GOLD：261、260… | 261已赋值，跳过；260成为首个可选变量 |

CONTROL与Gold的activity差异仅在90（2.5625→0）、359和505（各1.5625→0）；heap有25个位置不同。该结果支持reason/analysis历史改变activity及heap顺序，最后改变同分候选选择。**本轮联合替换两个字段，不能分离activity单独与heap单独各自是否充分。**

合法性检查全部通过。以下为SHA-256前16位，完整值保存在[audit.json](results/activity_heap_mediation/audit.json)：

| 检查项 | SHA-256前16位 / 结果 |
|---|---|
| RESET干预前完整状态 | `0e2a9c7bf37cf20f` |
| CONTROL完整snapshot | `7a4870f919c345c2` |
| 干预前activity+heap | `c6185cc477aa00c4` |
| CONTROL activity+heap | `1de30e8ad7a1ae30` |
| RESET后activity+heap | `1de30e8ad7a1ae30`，与CONTROL完全相同 |
| RESET前/后其余Gold状态 | 均为`da18bcac841361f2` |

“其余状态”覆盖屏蔽允许字段后的整个Solver对象、全部live向量、trail/assignment/reason、clause allocator内容、watches及dirty metadata、phase、restart队列和native counters。原始对象含进程内指针，故该hash只用于**同一RESET进程前后**比较，不用于CONTROL与Gold跨进程相等判断；另存address-independent逻辑snapshot供跨run核查。干预函数不能访问search栈局部变量，也未修改它们。

恢复后的heap排序与反向索引一致，Gold中未赋值且decision-eligible却缺失于heap的变量为0。正常CONTROL/GOLD的全部native counters、完整decision序列及learned内容/计数与上一轮一致；RESET干预前与正常Gold逻辑snapshot和trace前缀一致。**三条run的完整UNSAT证明均通过drat-trim验证。**

## 3. divergence被推迟到哪里？

| 相对CONTROL的首次分叉 | 原GOLD | GOLD_ACTIVITY_RESET |
|---|---|
| decision literal | decision22：−259 /−260 | **decision23**，conflict4后：+147 /+517 |
| learned content | conflict4 | **仍为conflict4，未推迟** |

因此decision共同前缀从21次延长到22次，只多保持了一次选择。RESET在conflict4学到 `(¬260∨31∨328∨358∨435∨519∨568)`，不同于CONTROL的 `(¬478∨146∨180∨343)`。恢复一次branching并没有同步Gold剩余的reason/propagation状态。后续对齐为事件序号比较，不表示相同搜索状态。

## 4. 如果失败，最可能剩下哪个state difference？

**本次decision22没有失败，无需提出失败后的补救干预。** 在decision22之前，CONTROL与Gold的assignment及decision eligibility完全相同；259/260的phase也相同，因此这些差异不是此次−259/−260选择的必要解释。

但全体phase仍在变量165、478上不同，Gold的reasons、watches及额外clauses也保留。因此不能把decision23及conflict4之后重新分叉唯一归因于phase或某个隐藏字段。本轮没有继续分离这些因素。

## 5. 当前机制链更新成什么？

**reason substitution / analysis路径改变 → activity及heap历史不同 → 同分候选的堆顺序不同 → decision22改变。**

现在最后一段不再只有相关观察：在保持Gold其余状态不变的条件下，联合恢复activity/heap，确实恢复了该decision。这是**局部中介证据**，不是对整段求解加速的完整归因，也不是activity单独或heap单独的证据。

原CONTROL/GOLD/RESET最终ops分别为203,623 /130,718 /174,558，仅作为完成求解与正确性检查记录；不据此计算“activity解释了多少收益”。未运行新target、新subset或其他intervention。

证据：[固定协议与build](results/activity_heap_mediation/protocol.json) · [三条run](results/activity_heap_mediation/runs.json) · [完整哈希/分叉审计](results/activity_heap_mediation/audit.json) · [RESET前snapshot](results/activity_heap_mediation/GOLD_ACTIVITY_RESET.before.json) · [RESET后snapshot](results/activity_heap_mediation/GOLD_ACTIVITY_RESET.after.json)。完整压缩证明和轻量trace保存在同目录。
只读复核：`.venv/bin/python activity_heap_mediation_report.py`。
