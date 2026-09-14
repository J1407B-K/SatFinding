# Next mechanism hypothesis: propagation-order / implication-graph bifurcation

本轮 B：5/5 HIGH 为 PROPAGATION_FIRST；全部 implied vars 先自然传播，历史 HIGH 没有高 activity / next-8 branch 的共同模式。单 decision restoration 保留大部分效果；suppression 能产生近似成本变化，却不复现最早改变的 learned clause。

候选链为：legal early enqueue → FIFO / watcher processing order changes → implication edge or reason changes → conflict cone / learned clause changes → later heuristic and decision divergence。当前证据支持先后顺序，不足以证明其中每一条因果边。

下一轮应冻结并检查：

1. Action 是否改变 upcoming propagation closure 的集合、顺序或 reason；把只重排同一 closure 与改变 closure 区分。
2. 第一条改变的 implication edge，以及其是否进入第一处不同 conflict cone。
3. 第一次 learned clause 的内容、asserting literal、backtrack 与活动更新分歧。
4. Watcher traversal / watched-literal swap 是否保存了早期顺序变化，并在后续重新激活。
5. 对这些边或顺序做最小 solver-legal 因果实验，保留 exact replay 与完整 proof verification。

同状态 NON-HIGH 也可能发生传播次序变化，必须保留 matched controls，不能把 PROPAGATION_FIRST 当作 predictor。不要进行 ML、gate、controller 或 rank cutoff search。本轮没有执行上述第二大实验。
