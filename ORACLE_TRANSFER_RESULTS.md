# Oracle Transfer：天然实例筛选完成，严格上界实验仍未决

**结论：EXPERIMENT_INCONCLUSIVE。不能据此宣布历史 proof 没有价值，更不能杀掉整个假设。**

本轮没有沿用或改造已停止的 Round 4 generator。没有实现 retrieval、WL、自动 mapping、
SUPPORT-ONLY、五路线 runner 或 cascade。新增的是天然图着色输入筛选、DRUP→纯
Resolution 的生产端 adapter，以及一个给定对应关系下的两路线可行性 pilot。

## 1. 输入是真正独立的图问题实例，尚不等于已有最佳映射

每个 CNF 从独立 seed 生成的 regular graph 编码得到，变量表示 `(vertex, color)`，
边表示相邻顶点颜色不同。没有植入 proof、保留历史 core 或替换 proof leaves；H/T
边数相同、拓扑不同，CNF 双向非子集。没有 symmetry-breaking 单位子句。

第一批固定六个 5-regular 图全为 SAT，模型均已检查，全部保留并排除出 UNSAT 测量。
随后在任何 transfer 结果出现前，固定六个 6-regular 图做第二批筛选。这是公开记录的
选题阶段适配，不是确认性实验；没有按 history 收益重采样或排除输入。

| 顶点数 | H / T seeds | CaDiCaL preprocessing | CaDiCaL solve H / T | Glucose proof H / T |
|---:|---|---|---:|---:|
| 120 | 6200 / 6201 | 均 UNRESOLVED | 5.09 / 4.20 ms | 5.10 / 4.50 ms |
| 200 | 6202 / 6203 | 均 UNRESOLVED | 68.12 / 44.38 ms | 93.74 / 111.48 ms |
| 320 | 6204 / 6205 | 均 UNRESOLVED | 2.201 / 4.099 s | 8.584 / 8.688 s |

120 顶点仅是工程控制，200 顶点难度有限；不能因为 preprocessing 未判定就称为 hard。
320 顶点更符合本轮的难度要求。这里原生 UNSAT 仍是 solver 自身结果，不能冒充纯
Resolution checker PASS。

## 2. 证明输入边界

Glucose 导出 DRUP，adapter 在生产端执行 RUP 重构，显式记录每次二元归结的父节点
与 pivot。中间可能导出更强的子句；只保留真正推导出的子句，不用 weakening 或
未证明的历史结论作为公理。删除可忽略，但不支持的非 RUP addition 会拒绝。
最终 checker 仍然只是现有 Resolution replay，不调用 solver。

| 历史图规模 | sliced leaves | sliced inference nodes | 重构时间 | 检查 |
|---:|---:|---:|---:|---|
| 120 | 1,068 | 19,560 | 0.264 s | PASS |
| 200 | 2,237 | 251,420 | 16.370 s | PASS |
| 320 | 未得到完整 artifact | 未测量 | 触及 60 s cap | 未完成，非 REJECT |

完整重构 DAG 在生成时经过检查，保存的 ancestor slice 又经独立审计重放与可达性检查。
重构时间不等于历史 solver 的 proof-search 时间；inference 节点数也不等于搜索成本。
没有给 transfer worker 目标 T 的 DRUP、refutation 或 repair witness。

## 3. 给定对应下的 pilot，不是“最佳映射”的数学上界

本次免费给出 `(vertex,color)` 的 identity 对应。这省掉了找映射的成本，但对独立随机图，
**没有证据表明它就是最佳顶点对齐**。因此这项 pilot 尚未实现用户提出的严格
“最佳映射 + 正确历史 proof”上界实验。

同一个现有 ResolutionSearch 内核，400,000 次全局尝试上限；每个 oracle 局部 repair
最多 2,000 次尝试。双方相同 250,000 pending candidates / 50,000 nodes 的内存政策、
20 s worker 时限；外层 40 s watchdog。局部 repair 顺序与邻域规则在测量前固定，
不声称是最优 repair。旧步骤直接重放不收取新搜索尝试，但检查与时间计入开销。

| 目标 | BLIND attempts / stop | Oracle direct replay | Oracle attempts / stop | repair successes |
|---|---|---:|---|---:|
| n120 T | 10,653 / MEMORY_POLICY | 27 / 19,560 | 400,000 / GLOBAL_BUDGET | 0 / 876 |
| n200 T | 12,296 / MEMORY_POLICY | 57 / 251,420 | 400,000 / GLOBAL_BUDGET | 0 / 1,074 |

两路均 MISS，没有反驳完成。直接 replay 比例约 0.138% / 0.0227%，仅针对这个给定对应。
历史中分别有 845 / 1,761 个 leaf 不存在于 T。失败搜索产生的全部 nodes、duplicate / 
tautology 尝试和共享全局预算都已保留。MISS 不表示目标为 false。

**`new Resolution search attempts saved = null`。**
不能拿 BLIND 的内存截断点当成从零完成成本；也不能拿 oracle 用了更多预算、却仍失败，
解释为它比已完成的从零 search 更差。当前枚举式内核无法承担这些天然实例的完整比较。
320 顶点没有进入 transfer，是因为历史证明 adapter 超限，不能作为 transfer negative。

## 4. 审计与下一步边界

- 12 个 screened inputs 的生成图、编码、输入/DRUP/source hashes 和 SAT models 已复核。
- 两份历史 Resolution slice：checker PASS，全部节点均在反驳祖先切片内。
- 四个 partial proof DAG：仅使用当前 CNF 与显式 Resolution，全数检查通过。
- 822,949 次 search attempts：独立逐事件重算，包括失败、重复、重言式、所有局部调用。
- 原生 solver、转换 timeout、预算 MISS、checker 接受严格区分。
- 新增九项相关测试通过，包括实际 Glucose proof 重构、禁止偷用缺失 leaf、预算篡改拒绝。

这轮结果不足以回答 YES/NO。真正上界实验还缺少：

1. 可辩护的 oracle 对应定义。独立随机图的同编号顶点不自动构成最佳结构映射；
   可以选择有明确领域对应的天然实例族，或明确上界所优化的映射集合。
2. 能完成 BLIND 的可计费 proof-search 内核，以及能取得 hard 输入完整 Resolution DAG
   的生产接口。现有 Python 枚举队列与 DRUP adapter 的能力不足已被直接测出。

不为跨过这些限制再次回到 planted leaf-repair benchmark；本轮也没有调低 baseline。

## Artifact 与复现

- [筛选协议](docs/oracle-transfer-protocol.md)、[第二批筛选说明](docs/oracle-transfer-unsat-screen.md)
- [pilot 的固定限制](docs/oracle-transfer-pilot.md)
- [第一批 SAT 筛选](results/oracle_transfer/screen.json)、[第二批筛选](results/oracle_transfer_6regular/screen.json)
- [证明转换状态](results/oracle_transfer_6regular/reconstruction_status.json)
- [transfer raw 文件索引](results/oracle_transfer_6regular/transfer.json)
- [独立审计](results/oracle_transfer_6regular/audit.json)

```sh
.venv/bin/python -m unittest test_resolution_import test_oracle_transfer -q
.venv/bin/python audit_oracle_transfer.py
```

重新筛选与运行命令见 `oracle_transfer_screen.py --help` 与
`resolution_import.py --help`；`oracle_transfer_run.py` 运行现有 checked artifact 上的
两路线 pilot。第一批原始 source snapshot 单独保存，以免后续 screening 参数接口修改
破坏该批的 source hash。所有结果仅来自本机的探索性单次运行，不提供统计泛化结论。
