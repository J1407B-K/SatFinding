# Round 4 开发门检：停止当前 benchmark family

**Negative result：普通 CNF 预处理已经解决全部开发正例，当前构造不值得进入正式 history 比较。**

固定四个开发 seeds（4100–4103），每个包含 L0、L1、L2 请求 5% broken leaves、
L2 请求 15% broken leaves，共 16 个正例，另有四个带检查模型的 SAT controls。
小 support 的破损数向上取整，实际比例保存在逐例报告中；不冒称精确 5%/15%。

| CNF-only 方法 | 正例 UNSAT | worker 耗时中位数 |
|---|---:|---:|
| Unit propagation | 0/16 | 0.009 ms |
| 无子句增长 BVE | 4/16 | 0.381 ms |
| CaDiCaL preprocessing | 16/16 | 6.768 ms |
| CaDiCaL solving | 16/16 | 6.750 ms |

worker 耗时包含方法所需的导入/初始化；进程启动另列，预处理的进程总耗时中位数为
36.641 ms。CaDiCaL 的 UNSAT 是 solver 自身输出，不标成 Resolution checker PASS。
四个 BVE 成功均有 checked Resolution；全部正例还各有 evaluation-only 的组合证明，
用于确认输入与替换 witness 的正确性，不能算成算法 transfer 成功。

没有调大规模、调整 baseline、筛掉失败例或换 generator 追求正结果。
这仅否定当前小变量随机 core + 局部替换构造的实验价值，不否定一般 proof reuse 假设。

## 已完成与停止边界

- 复用现有 Step/Certificate/checker；实现历史祖先切片并保留完整成功搜索 trace。
- 实现可继续搜索的互补文字索引 Resolution 内核与可共享全局 Budget。
- 实现最小生成器、字段 schema、隔离的 CNF-only shortcut workers。
- 实现独立 Round 4 开发审计，逐事件重算尝试数、重复/重言式/新节点与 support。
- 80 行结果审计 PASS；检查 15 份局部替换 witness、16 份评估组合反驳和四个 SAT controls。
- 新增八项测试与已有 25 项相关回归通过，包括篡改计费与前向父引用拒绝。

按照先做 shortcut gate、触发条件立即停止的要求，**没有继续实现 partial mapping/replay、
SUPPORT-ONLY 或正式五路线 runner**。BASELINE / BLIND / SUPPORT-ONLY / REPLAY /
REPLAY+REPAIR 没有完成正式比较。主指标 `new_search_attempts_saved = null`，表示未测量，
不是零收益，也不是 history 与 BLIND 无差异。

## 证据与复现

- [固定开发协议](docs/round4-protocol.md)、[字段 schema](round4_schema.json)
- [逐例 attempts 与完整报告](results/round4_dev/report.md)
- [原始 80 行结果](results/round4_dev/gate_raw.jsonl)、[运行元数据](results/round4_dev/gate_metadata.json)
- [独立审计](results/round4_dev/audit.json)、[audit 实现](audit_round4.py)

```sh
.venv/bin/python round4_generate.py
.venv/bin/python round4_gate.py
.venv/bin/python audit_round4.py
.venv/bin/python -m unittest test_round4 test_satcache test_adversarial test_proofmodule -q
```

算法 worker 只收到 CNF；私有映射、leaf 替换位置与 witnesses 仅由生成/评估进程读取。
独立审计复用已有逻辑 checker，不声称是第二套 checker 实现；计时也不是证明认证的结论。
