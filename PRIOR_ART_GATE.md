# Prior-art boundary audit — Gold-64 anatomy

Date: 2026-09-11. Gate completed before creating this round's analysis code.

**PASS for bounded instrumentation and case analysis only. No new selector, solver,
proof calculus, clustering algorithm, or abstraction algorithm is approved.**
`EXISTING_WORK` and `DUPLICATE_RISK` apply to broad claims of proof memory,
small useful lemma sets, source-proof ranking, and validate/adapt/discard reuse.
The present question is the structure of this frozen, target-selected Gold-64 set;
an answer on one target establishes neither a novel mechanism nor generalization.

## Component decisions

| Idea / Component | Existing Work | What Existing Work Already Solves | Can Reuse Existing Tool? | Needed By Current Experiment? | What SatFinding Adds | Decision |
|---|---|---|---|---|---|---|
| Incremental SAT / learned information reuse | [PySAT solvers](https://pysathq.github.io/docs/api/solvers.html), [ATPG 2007](https://doi.org/10.1109/VLSID.2007.137) | Assumption-based solving; safe reuse across related fault instances | Yes; existing native backend / PySAT | Backend only | Frozen target measurements | REUSE |
| Old UNSAT proof to future implied literals | [Mining Backbone Literals, SAT 2015](https://cris.technion.ac.il/en/publications/mining-backbone-literals-in-incremental-sat-a-new-kind-of-increme-2/) | Proof analysis supplies implied literals for subsequent formulae | Published method; artifact not verified | Conceptual comparator | No backbone implementation | BASELINE |
| Sparse source proof / reconstruction | [Proof Skeletons, TACAS 2023](https://link.springer.com/chapter/10.1007/978-3-031-30823-9_17) | Select important clauses and reconstruct proofs | [Public artifact](https://github.com/amazon-science/unsat-proof-skeletons) | Conceptual comparator | Changed-target conditional utility measurement | BASELINE |
| LBD, activity, reason usage, size | Proof Skeletons; [CP 2020](https://jakobnordstrom.se/docs/publications/UsingProofs_CP.pdf) | Existing clause quality and proof statistics | Reuse existing recorded features | Size/use available; LBD/activity absent | No renamed selector | BASELINE |
| Reconstructed proof-use ranking | CP 2020; existing `oracle_lemma.prepare` | DAG usage counts and their limitations | Yes, existing `used`, `shortest`, `ranked` | Yes | Compare against target-selected Gold | BASELINE |
| Clause deletion / ML selection | CDCL literature; Proof Skeletons | Managing clauses within solver runs | Existing solvers | No new implementation needed | None | STOP_DUPLICATE |
| CAR/PDR proof-state validation and adaptation | [Local IPR paper](artifact_/IPR_long.pdf), [artifact README](artifact_/Readme.md) | Changed property, fixed system; reuse, repair, discard, resumed search | Local CAR/PDR/Kind2 code supplied | Strong conceptual comparator | None to these mechanisms | STOP_DUPLICATE |
| Changed-model inductive clause repair | [FuseIC3 artifact](https://github.com/rohitdureja/FuseIC3) | Related models, fixed property; invariant checking/drop/repair | Yes, VMT/MathSAT interface | Conceptual comparator | CNF change alone adds no novelty | STOP_DUPLICATE |
| Proof-derived abstraction/interpolation | [McMillan/Amla proof-based abstraction](https://www.cs.utexas.edu/~hunt/FMCAD/2004/accepted/38.html) | Proofs determine relevant abstractions | Existing techniques | Interpretation only | No new abstraction extractor | BASELINE |
| XOR/cardinality/gate recovery and preprocessing | [CryptoMiniSat](https://github.com/msoos/cryptominisat), [CaDiCaL](https://github.com/arminbiere/cadical), [Factoring Learned Clauses, SAT 2026](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SAT.2026.28) | Existing structure recovery / factoring / preprocessing | Yes | No detector needed | None | REUSE |
| DRAT/LRAT processing and trimming | [drat-trim](https://github.com/marijnheule/drat-trim), [lrat-trim](https://github.com/arminbiere/lrat-trim); repo proof tools | Proof checking, dependency output, trimming | Yes | Reuse already stored Resolution DAG | No ecosystem rewrite | REUSE |
| Gold-64 ancestor/support annotations | `round4_core.ancestors`, `HistoryIndex.materialize`, `ProofContext` | Traversal and checked support replay already exist | Yes | Yes | Per-selected-root measurements tied to this target | EXTEND |
| Ancestor-overlap grouping | [NetworkX components](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.connected_components.html); proof analysis literature | Generic connected components | Yes | Yes, experimental instrument | Overlay Gold outputs on existing DAG | REUSE |
| Module ablation | Existing oracle evaluation and native backend | Fixed-order completion and counters | Yes | Yes | Measure target cost after removing/adding a group | EXTEND |
| Persistent mined lemmas / future relevance | [Kaliszyk–Urban 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4599631/), [ProofWatch 2018](https://arxiv.org/abs/1802.04007) | Historical proof mining and guidance of future conjectures | Existing ATP systems | Literature boundary | Broad memory/relevance claim is occupied | BASELINE |
| Persistent constraint memory | [Green, FSE 2012](https://doi.org/10.1145/2393596.2393665), [ReCal thesis](https://susi.usi.ch/usi/documents/318899) | Reuse via normalized constraints / equivalence / implication | Existing systems in their settings | Literature boundary | Persistence alone is not new | BASELINE |
| Target-conditioned utility | IPR; [Reusing Solutions Modulo Theories](https://doi.org/10.1109/TSE.2019.2898199); ProofWatch | Benefit/relevance-aware reuse in neighboring settings | Reuse frozen measurement harness | Yes | Conditional ops/conflicts and checked support cost on this case | EXTEND |
| Known coloring semantics | [Arc Consistency in SAT, ECAI 2002](https://frontiersinai.com/ecai/ecai2002/p0121.html); repo encoding | Standard CSP/SAT propagation | Existing encoding annotations + PySAT | Yes | Describe local supports, not discover a new gate language | EXTEND |
| Cross-instance module mapping / semantic memory algorithm | ATPG, IPR, FuseIC3, Green, theorem-proving lemma mining | Substantial parts of transfer and memory already covered | Setting-dependent | Not needed to characterize Gold | Not cleared as a new algorithm | STOP_DUPLICATE |

## Literature challenges before implementation

These are comparisons, not assertions that unmentioned capabilities are absent.
No search proves novelty; unresolved algorithm proposals remain outside this gate.

**Idea 1:** Group the 64 outputs when their reconstructed inference supports overlap,
then measure completion with each group alone and removed. Closest works:

| Work | Input setting | Reusable artifact | Transfer | Validation | Objective / boundary |
|---|---|---|---|---|---|
| Proof Skeletons | Same formula | Selected clauses | Guide reconstruction | Reconstructed proof | Proof compression; grouping is not new |
| CP 2020 | A solver run | Actual derivation DAG | Analysis, not changed-target transfer | Resolution trace | Source statistics; reconstructed DAG must be labeled |
| Kaliszyk–Urban 2015 | Formal theorem library | Mined lemmas at multiple granularities | Relevance filtering for new conjectures | ATP/ITP proof infrastructure | Future proving utility and useful granularity already studied |
| IPR | Same system, changed property | Proof-state objects | Validate/adapt/discard | Current model checks | Search savings from few useful objects already observed |

Decision: existing graph algorithms plus repository-specific annotations and
conditional ablations. Neither ancestor Jaccard nor graph components are contributions.

**Idea 2:** Interpret clauses and their local premises in the known coloring encoding.
No automatic general-purpose abstraction compression is proposed.

| Work | Input setting | Artifact | Transfer | Validation | Objective / boundary |
|---|---|---|---|---|---|
| ATPG 2007 | Related circuit faults | Learned information | Circuit correspondence / reuse | Valid clause dependencies | Avoid repeat solving; correspondence is existing work |
| FuseIC3 | Changed systems, same property | Inductive clauses | Check/drop/repair | Target induction checks | Multi-model verification |
| IPR | Changed property | Cubes/cores/frames/states | Adaptation | Target checks | Multi-property verification |
| Proof-based abstraction | Verification task | Relevant predicates/constraints | Abstraction refinement | Proof / refinement machinery | Proof-to-abstraction is occupied |
| Arc Consistency in SAT | Encoded CSP | Constraints / support encodings | Encoding and propagation | Logical encoding | Local coloring implications are standard reasoning |

Decision: report observed support motifs and local implication checks. A shared
description is not a compressed reusable representation. No transfer experiment or
abstraction-memory success may be inferred from this annotation alone.

**Idea 3:** Measure future utility conditional on TEMPLATE and compare memory units.

| Work | Input setting | Artifact | Transfer | Validation | Objective / boundary |
|---|---|---|---|---|---|
| IPR | Related properties | Proof-state | Validation/adaptation | Target system | End-to-end benefit |
| SAT 2015 backbone mining | Incremental SAT | Proof-derived literals | Analysis of old UNSAT proof | Implication conditions | Accelerate later solving |
| ProofWatch | New theorem conjecture | Historical proofs | Watchlist matching | Sound prover deductions | Target search guidance |
| Kaliszyk–Urban 2015 | Large theorem corpus | Selected historical lemmas | Learned relevance | Proof infrastructure | Future theorem success |
| Reusing Solutions Modulo Theories | Symbolic analysis queries | Models / UNSAT information | Candidate selection and reuse tests | Current query checks | Avoid solver work |

Decision: case-specific measurement only. The conjunction “persistent + target-aware
+ revalidated” does not itself establish novelty. Distance, representation comparison,
and out-of-sample retrieval remain unanswered.

## Local artifact inspection

Read `artifact_/IPR_long.pdf` (anonymous supplied manuscript; no venue/acceptance
claim), README, and PDR `checkAndCollectValidCubes` in
[IC3.cpp](artifact_/code/PDR/IC3.cpp). The implementation checks saved cubes,
uses UNSAT cores, attempts extension under the new property, discards failures,
and reloads accepted cubes into frames. The paper also includes Kind2/Lustre;
it is not restricted to hardware. Its discussion explicitly recognizes nonlinear
search benefits of a small usable lemma set. These mechanisms are EXISTING_WORK.

The provided CAR/PDR interfaces consume transition-system models (AIG; Kind2 uses
Lustre). FuseIC3 uses VMT with MathSAT. They are not drop-in solvers for this frozen
generic CNF completion experiment. Their published results are conceptual evidence,
not directly comparable timings; no local performance reproduction is claimed.

## Frozen protocol and permitted new file

`gold64_anatomy.py` is permitted as a thin experiment driver.
**WHY_EXISTING_TOOL_INSUFFICIENT:** existing tools already provide traversal,
checking, solving and components, but do not join this repository's frozen Gold IDs,
TEMPLATE exclusion, per-root supports, conditional ablation configurations and
native counters into an auditable dataset. Reuse those tools; implement only this
join, measurements and report serialization. No mature component is reimplemented.

1. Freeze target, history, template and exact-64 IDs from the previous experiment;
   hash input files. Use existing ancestors and checked materialization.
2. Report per-root inference ancestors including the root, premise leaves, output
   variables and support variables. Separate shared encoding leaves from edge leaves.
   Report union vs sum, multiplicities and pairwise Jaccard.
3. Primary grouping: connected components of outputs sharing at least one inference
   node. Shared axioms alone do not create primary module edges. Sensitivity graphs:
   inference, leaves, output variables and support variables, thresholds >0 and
   Jaccard >=0.1, 0.25, 0.5. Do not tune thresholds against target performance.
4. Run TEMPLATE, Gold-64, each component alone and removed; same-size random
   partitions (seeds 17,29,43) provide controls. If components are singletons, say so.
   Keep clause insertion in source-ID order. Use three sequential randomized
   repetitions, fresh native solver processes; report ops, conflicts, replay/check,
   and total wall time. Offline indexing/selection excluded, as in prior evaluation.
5. Compare existing ranked/shortest/used top-64 and seeded random-64. These are
   BASELINE features from a reconstructed proof, not native activity or LBD.
6. Semantic checks use each root's local support only and existing PySAT. Check
   that local premises are SAT before implication testing; the globally UNSAT target
   cannot establish informative semantic equivalence. Annotate known one-hot coloring
   literals and premises. No generic structure detector or abstraction extractor.
7. Search counters are deterministic, wall time is not. Ablation effects are
   context-dependent and non-additive. This is one target selected by an expensive
   oracle, with no claim of online selection quality or out-of-sample utility.
8. The DAG was reconstructed from DRUP into Resolution. CP 2020 warns that this can
   differ from the actual CDCL derivation DAG. Sharing is representation-dependent;
   do not call reconstructed fan-out native activity or infer semantic independence
   from disjoint derivations. Do not expand another giant proof in this round.

The allowed conclusion is empirical: independent replay supports, shared proof
supports, or evidence requiring a later semantic representation experiment. None
may be forced into the more abstract category merely because it sounds promising.
