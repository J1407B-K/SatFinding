# L1 / L1+L2 event-level diagnosis

Same frozen target/TEMPLATE/Glucose/seed/source-ID order. A adds24458; B adds
24458 and30149. No other sets. Existing expected totals345592 /169858.

Natural tracing first. Record enqueue literal and content-based reason identities,
first-UIP/minimization visits, exact variable-bump results, heap state hashes,
learned content, decisions and restart queues. Full event detail is bounded to
conflicts<=900 (past the known firstdecision/restart forks); all L2 successful
reason/analysis/minimization/conflict uses are logged through completion. Record
L2 watch inspection and watch movement separately: inspecting/storing a redundant
clause is not the same as affecting assignment/reason/analysis. Explicitly separate
the unavoidable input/watch/simplification-budget difference at initialization.

Each event has per-run globalevent, completed/current conflict c, decision count d,
global enqueue e and within-(conflict,event-type) ordinal k. Enqueues before next
conflict use completed count; analysis/conflict/learned rows use current1-based
count. Alignment compares same logical event kind and ordinal; after divergence
ordinal pairing does not imply equal state. State hashes are64-bit FNV summaries,
not cryptographic proof; exact logical snapshots plus SHA256 provide verification
at critical events. No snapshot hashes compare raw CRef addresses across runs.

Snapshots: input initialized; immediately before/after enqueue28916 (known first
L2 reason from earlier bounded observation); endanalysis199; beforeanalysis656;
beforedecision828; plus the first differing variable-bump/heap event identified
by this natural trace. Natural replay for snapshot capture is allowed, not a new
intervention. Include assignments, active reasons, exact activity doubles/var_inc,
heap array+indices, phases, learned ordered IDs/content, restart queue state,
watch identities/order where practical. Snapshots encode literals rather than
allocator offsets. Source/hash ledger and full native counter match required.

Only after natural comparison may one state mediator intervention be specified
and frozen. At most one. If unsupported, do not intervene. Do not rescue results.
If used, check local state legality, unchanged nonallowed logical fields, and
native completion proof with existing drat-trim. No claim that any local chain
accounts for final175734 ops difference without a supported counterfactual.
