# Frozen early-trajectory diagnostic

2026-09-11. Same n200_T_r01_s7201, same Glucose3.0 counted backend,
seed91648253, random frequency0, same preprocessing and source-ID injection order.
No new sets, target, selector, abstraction, history prior, neural model or search.

12 fixed configurations: TEMPLATE; GOLD64,RANKED64,SHORTEST64,USED64,
RANDOM64_17,RANDOM64_29,RANDOM64_43 from gold64_anatomy/selections.json;
L1,L2,L1_L2,L1_L2_L3 from gold_mechanism/runs.json. Bad64 is an alias for
RANDOM64_43, not another sample. All seven64 sets are retained, not screened by
early metrics. K matches among those7. Report width histogram, source derivation
depth, union support inferences, and measured validation cost; do not rematch or
change memberships. CONTROL hasK0, diagnostic combinationsK1/2/3. Do not treat
cross-K pooled patterns as matched64-clause evidence.

Early-only processes stop immediately after analysis of conflict1000, with
native conflict budget1000. Capture checkpoints50,100,200,500,1000. Hash/freeze
ALL early records before joining existing final outcomes. Source-only validator
may read existing H proof to reconstruct selected clauses, but no completion
outcome is read by the prefix collector. No outcomes are used to choose features.
This is retrospective diagnosis of known sets, not a blinded prospective study.
Separate full shadow runs ONLY verify unchanged native counters against existing
outcomes and exact equality of first1000 records; no full-run metric becomes an
early feature. Existing final ops provide labels. No new configurations.

Metrics: cumulative first-UIP analysis ops, native propagation counter and actual
BCP dequeues (including binary-conflict early returns), enqueues, decisions;
mean conflict DL, learned width/LBD, backjump distance; activity top10 mass,
entropy and spread normalized by var_inc; heap insert/pop/decrease calls and
percolation moves; restart indices/count and blocked status; cumulative decision
variable histogram and overlap with TEMPLATE; reason/analysis/minimization source
counts (original,TEMPLATE,injected,learned), per-injected-lemma direct usage.
No full enqueue/proof logs. Only compact conflict rows<=1000 plus checkpoints.
Checkpoints are after learned-clause analysis, before backjump/injection atN.
Counts include the current conflict's analysis. Activity is observed at that same
boundary. Heap counters include initialization (same600 variables in all runs).

Analysis fixed before collection:
- Show all per-metric Spearman correlations with final ops and remaining ops
  (final minus observed cumulative ops), with ties averaged, at everyN.
  These many descriptive correlations have no selection-adjusted significance.
- Fixed univariate baseline log(1+cumulative ops/N).
- Fixed4-feature ridge linear baseline, penalty1, predicting log final ops:
  log(1+ops/N),log(1+actual dequeues/N),meanLBD,meanDL. Train-only standardization,
  unpenalized intercept. No feature/penalty/threshold tuning. Report LOCO rank
  correlation, log MAE versus training-mean baseline and binary accuracy/balanced
  accuracy. Good=fixed final ops<.9*TEMPLATE (onlyGold andpair are good); CONTROL
  is not good. Always report majority baseline and sample/class counts.
- Static3-feature comparator: mean output width,mean source derivation depth,
  log(1+support inferences), same ridge/LOCO. This is a sanity baseline, not a
  proposal for static selection. Timing is not a predictor.
- Primary scalar/ridge LOCO uses all12, but separately report the7 matched-K
  configurations (only1 good) and group-held-out sanity check: hold all4 L1/L2
  configurations together; hold all3 RANDOM sets together. This exposes related
  configuration leakage. No repeat samples or conflict rows treated as samples.
- For each scalar, an operational directional-stability check asks whether both
  good configurations lie beyond all nongood ones in the same direction at both
  N50 and100. This is descriptive separation, not a reliable threshold estimate.
  No neural follow-up recommendation solely from separation or training fit.

Interpretation: distinguish early state difference from useful direction, and
same-state-looking prefixes with different outcomes. N1000 is later diagnostic,
not allowed to rescue absent signals at50/100. No claim of actual attractor basins,
generalization, or unique causal allocation of final savings.
