# Frozen L2 delayed amplification experiment

Only frozen n200_T_r01_s7201 A=TEMPLATE+24458 and B=A+30149.
Injection points: 0,100,150,180,190,198,200,220,250,300,400,600.
0 is ordinary static B with original injection order. Positive boundary is after
conflict processing (analysis, backjump, learned installation, decay), before
next propagate. No new points or sets after observing outcomes.
Ghost A samples L2 truth status after every enqueue and completed cancelUntil;
logs transitions plus exact c,d,e,event position, never installs L2.
Dynamic insertion preserves nonfalse watches; watches on false literals choose
highest levels. A unit is asserted at highest antecedent level (necessary
backtrack recorded); a violated clause is processed as conflict at highest
literal level. Already satisfied single true above all false antecedents also
requires backtrack/assertion to avoid losing propagation on future backtracking.
No gratuitous restart/root reset, simplification, activity bump or heap rebuild.
DRUP explicitly adds validated L2; validate against original A input.
Forced A/B runs: normal native pickBranchLit at decision828, then substitute
-570/-187 only if undef and decision eligible. Native heap pop remains normal;
no copied state. Snapshot before native pick equals its own natural run;
snapshot immediately before/after local literal override must be identical.
Abort illegal interventions, do not repair or add alternatives.
Natural counters must match frozen results, learned/decision prefix must match
previous event ledger, all completed proofs must verify. Outputs are conditional
on this fixed pair and injection implementation; no claim of complete final
benefit mediation. No ML, selector, history, new targets or aggregate predictor.
