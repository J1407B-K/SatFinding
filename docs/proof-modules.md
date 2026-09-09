# Extended-resolution ProofModule

实现：[proofmodule.py](../proofmodule.py)。无新增第三方依赖。

```python
ProofModule(
    assumptions=...,             # 排序后的有符号文字 tuple
    extension_definitions=...,   # 按拓扑顺序排列的 AND 定义
    premises=...,                # 有序子句 tuple，不能重排证明索引
    conclusion=...,              # 一个子句，包括可能的空子句
    derivation=...,              # 有序二元 resolution 步骤
)
```

## 定义与索引

第一版的扩展定义为 `ExtensionDefinition(y, a, b)`，含义是
`y <-> (a AND b)`，a、b 可以是有符号文字。检查器自己生成以下三个子句，不接受
生产者任意指定的“定义公理”：

    (-y OR a), (-y OR b), (y OR -a OR -b)

y 必须是正的新变量；a、b 必须来自当前上下文或更早的定义。禁止自引用、前向引用、
重复定义和与已用名字冲突。即使 a=b 等退化情形造成子句重复，也保留三个索引槽位。
定义不会递归展开成表达式树。

推导的初始数据库顺序固定为：

1. `premises` 按原顺序。
2. `assumptions` 中各文字对应的单位子句，按原顺序。
3. 每个扩展定义的三个子句，按定义顺序。

每个 `Step(left, right, pivot, clause)` 只能引用先前索引，左右父句必须分别含 pivot
和 -pivot，输出必须恰好为二元 resolvent。最后的 `conclusion` 必须实际出现在该数据库中。
不能把未经推导的结论当作额外输入。

## 映射与变量作用域

模板所有未被本地 extension_definitions 绑定的变量构成基础接口。
`instantiate(template, mapping, context)` 要求给出完整单射，可进行基础变量极性翻转。
映射目标可以是当前基础变量，也可以是先前 module 已合法引入的扩展变量。
本地扩展变量不能由检索器任意映射到现有名字，而是从当前最大已用编号之后重新分配。

`ProofContext(..., reserved_variables=...)` 还能保留当前未出现在子句中的声明变量，
避免与它们碰撞。该实现是单线程证明会话；实例化并不预留名字。若两个候选在同一状态
实例化，第一个提交后，第二个的过期名字会在重新检查时被拒绝。失败不会改变上下文。

## 前提和假设

premises 只能是当前上下文中的显式子句，或在本 module 的 assumptions 下化简后的
上下文子句。更一般的语义蕴含不会在此调用 SAT solver 解决；需要先用别的 module
推导相应前提。assumptions 必须使用已存在的变量，且彼此一致。

检查通过的局部判断是：

    current_context AND assumptions AND new_definitions entails conclusion.

提交时追加的是下列不带局部假设的 guarded clause，而不是无条件追加 conclusion：

    (OR of negated assumptions) OR conclusion.

例如在 F=(a) 下，以 assumption NOT a 推出空子句，只会提交子句 (a)，
`proves_unsat` 为 false。只有 guarded clause 本身为空，才报告全局不可满足。

## 含扩展变量的结论

若 C 含新扩展变量，检查器可接受它，但 ProofContext 必须保留定义与 guarded clause。
后续 module 可以同时使用它们。不能丢弃定义后把 C 当作原词汇上的事实。

`CheckedConclusion` 返回：

- `assumptions`、局部 `conclusion` 和实际提交的 `guarded_clause`。
- 本次引入的 `extension_definitions`。
- `root_clause`：只有 guarded clause 完全使用最初 root vocabulary 时才给出，否则为 None。
- `proves_unsat`：仅当 guarded clause 为空。

root_clause 是关于最初输入公式的结论；其余扩展词汇上的结果只能在保留定义的上下文
中使用。调用者不能直接把自己构造的 CheckedConclusion 提交为证据：apply 只接受并
重新验证完整 ProofModule。

## 最小用法

```python
from demo_module import example_module
from proofmodule import ProofContext, ProofModuleCache
from satcache import normalize

cache = ProofModuleCache()
cache.add(example_module())
ctx = ProofContext(normalize([[11, 23], [17, 23], [4, 100]]))
candidate = cache.lookup(ctx)
if candidate is not None:
    result = ctx.apply(candidate.module)
    print(candidate.base_mapping)       # {1: 11, 2: 17, 3: 23}
    print(candidate.extension_mapping)  # {4: 101}
    print(result.guarded_clause)        # (23, 101)
    print(result.root_clause)           # None：此结论含扩展变量
```

`python3 demo_module.py` 还展示了消费上述扩展结论、导出 root-language 子句的后续
module，以及分支 UNSAT 的正确处理。

缓存 add 在模块自己声明的前提下验证它是合法引理；这不代表那些前提对未来查询成立。
lookup 使用现有结构直方图排序和有预算的单射/极性枚举，并在当前上下文中重新检查。
apply 再次检查后才提交。这是接口原型，尚未接入第二轮 LAD matcher 或生产求解器。
可以替换排序和候选映射器，不能替换为“相信相似度”的接受条件。

## Soundness 论证

令 F0 为最初公式，Fi 为已提交的上下文。归纳不变式是：Fi 包含已有定义及其合法
guarded lemmas；每个 F0 的模型都能扩展成 Fi 的模型。

对新 module：

1. 当前前提和按 A 化简的前提都由 Fi AND A 蕴含。
2. 新定义 D 使用 fresh variables、无环且为双向定义。任何 Fi 的模型都可按定义顺序
   唯一赋值给新变量并满足 D。这个论证不要求 A 为真。
3. 初始推导数据库均由 Fi AND A AND D 蕴含。归结保持蕴含，因此接受意味着它蕴含 C。
4. 命题逻辑的假设消去给出 Fi AND D entails (NOT A OR C)，因此加入 guarded clause
   不会再排除任何 Fi AND D 的模型。
5. 新上下文 Fi+1 继续满足归纳不变式。若 guarded clause 只含 root vocabulary，
   则 F0 本身蕴含它；若该子句为空，F0 不可满足。

这是一份有限数据算法的数学论证，不是机器验证的 Python 实现精化证明。
可信边界新增了门定义编码、freshness/作用域处理、归结检查和上下文提交；检索器、
候选映射器及历史来源仍不需要被信任。任意 Python 代码执行和并发修改不在数据威胁模型内。

## 成本和目前没有证明的事

检查/提交的成本是当前显式上下文与 module 编码长度的多项式。每个门只生成三个常数
宽度子句；即使嵌套定义很多，也不展开对应表达式树。测试覆盖了 1000 个嵌套定义。
这不说明上下文或 module 对所有原始 SAT 输入都只有多项式大小，也不保证找到模块
或变量映射的成本。当前没有实现任意循环/递归宏，没有声称通用指数证明压缩或新净加速。

运行纯标准库模块测试：`python3 -m unittest test_proofmodule -v`。
完整回归（安装项目实验依赖后）：`.venv/bin/python -m unittest -v`。
