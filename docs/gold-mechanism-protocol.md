# Fixed Gold mechanism observation

2026-09-11. n200_T_r01_s7201, original Gold exact64 in source-ID order.
CONTROL = original target CNF +67 TEMPLATE. TREATMENT = CONTROL +Gold64.
No benchmark, selector, K, order, preprocessing, or solver strategy changes.
Expected native analysis steps203623 /130718, conflicts5325 /3584. The reduction
against this CONTROL is35.8%, not50% (the BLIND comparison is a different anchor).

Build an independent Glucose observer from the counted frozen source. Require
all native deterministic counters to match uninstrumented backend for each
measured configuration. Never interpret traced execution seconds as native speed.
Default identical Glucose seed, no random decisions, original preprocessing and
certifiedUNSAT=true. Proof completion output /dev/null, candidate support checked
with the existing replay checker before injection.

Log every conflict's counters, width/LBD/backjump and all decisions; top10 activity
at first64 conflicts and every100 thereafter; restart points. Save enqueue reason
edges and analysis antecedents only before/at conflict64. Store aggregated Gold
unit-enqueue/reason/analysis/minimization/conflict uses over the full run, and each
clause-content's first activation. No full propagation or completion-proof logs.
Conflict indices at enqueue mean completed conflicts (0=before first conflict);
conflicts/learned events are1-based. Unit triggers mean successful BCP enqueues,
not all unit conditions or watch visits. Reason is assignments, not graph lifetime.
Native Glucose propagation counter misses dequeues on binary-conflict early
returns; record actual dequeues additionally without changing the native counter.

Earliest divergence definitions: first unequal ordered BCP-enqueue literal;
also separately reason/antecedent/order divergence and first different propagated
assignment event. First unequal decision literal by decision ordinal, first
conflict clause content/trail state by conflict ordinal, and learned content.
Ordinal alignment after divergence is descriptive, not same-state intervention.
Reason-graph ancestors demonstrate executed dependency paths, not necessity.

Small diagnostic interventions, chosen from existing singletons/LOO observations:
L1=24458,L2=30149 (existing nonadditive pair),L3=210136(high direct use).
Run single L1,L2,L3,pair L1+L2,triple L1+L2+L3. Also single and Gold-minus
2772(high LOO importance),150191(low use),96687(minimum use),210136(high use).
No new subset search. One additional pair/triple may be chosen ONLY from the
first early Gold-conflict reason graph with multiple distinct Gold ancestors,
to test that specific observed path, not optimize final ops. Freeze chosen IDs
before these diagnostic solves; no iteration if results are negative.
Join all64 existing singletons/LOO to newly observed use counts; distinguish
rare<=1,low<=16,unused=0 successful reason enqueues. Counts are observational;
LOO changes later trajectory. No claim that penalties add or low counts imply
no role. Require actual implication graph evidence for collective activation,
and report failure if small runs do not demonstrate it.

Report3–10 concrete early path cases if available, verify reason premises and
chronological edges. Decompose ops savings into common conflict-prefix and
CONTROL's extra tail arithmetically, not causal attribution by conflict ordinal.
Question is why this chosen deterministic run differs; no generalization from
an oracle-selected single-target set or claims of attention/phase transition.
