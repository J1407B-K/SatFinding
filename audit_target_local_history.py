import json
import csv
from collections import Counter
from pathlib import Path
from target_local_history import OUT
from oracle_lemma import prepare,strip_template
from round4_core import decode,ancestors
from replay_budget import HistoryIndex
from proofmodule import ProofContext,ProofModule
from evaluation_oracle_run import sha
p=OUT
proof=decode(json.loads((p/'target_pool_proof.json').read_text()))
assert ProofContext(proof.premises).check(ProofModule((),(),proof.premises,proof.steps[-1].clause,proof.steps)) is not None
cost={i:sum(j>=len(proof.premises) for j in ancestors(proof,i)) for i in range(len(proof.premises),len(proof.premises)+len(proof.steps))}
assert set(cost.values())<={1,2}
d=prepare();idx=HistoryIndex(proof);population,_=strip_template(idx,d['cnf'],d['templates'])
history_clauses={d['h'].clauses[i] for i in d['population']}
meta=json.loads((p/'metadata.json').read_text())
assert all(sha(f)==h for f,h in meta['sources'].items())
summary=dict(all_target_steps_checked=True,max_independent_target_cost=max(cost.values()),
 target_pool_cost_histogram=dict(Counter(cost[i] for i in population)),
 target_pool_history_overlap=sum(idx.clauses[i] in history_clauses for i in population),source_hashes_match=True)
classification=json.loads((p/'classification.json').read_text())
lookup={c:i for i,c in enumerate(idx.clauses)}
for row in classification:
 c=tuple(row['clause'])
 assert (c in lookup)==(row['category']=='LOCAL')
 if c in lookup: assert cost[lookup[c]]==row['target_steps']
raw=[json.loads(l) for l in (p/'raw.jsonl').read_text().splitlines()]
for route in {r['route'] for r in raw}:
 rr=[r for r in raw if r['route']==route]
 assert len(rr)==5 and all(r['status']=='UNSAT' and r['checker']=='PASS' for r in rr)
 assert len({(r['input_sha256'],r['analysis_resolution_steps'],r['conflicts']) for r in rr})==1
summary['final_repetitions_checked']=len(raw)
if (p/'oracles.json').exists():
 oracle=json.loads((p/'oracles.json').read_text())
 assert len(oracle)==6 and all(r['unique_evaluations'] in (1378,1379) for r in oracle)
 for r in oracle:
  rows=[json.loads(l) for l in (p/f"oracle_{r['label']}_{r['seed']}"/'search.jsonl').read_text().splitlines()]
  assert len(rows)==r['unique_evaluations'] and all(x['status']=='UNSAT' for x in rows)
  for k,winner in r['exact'].items():
   assert len(winner['selected_ids'])==int(k)
   assert any(x['input_sha256']==winner['input_sha256'] and x['analysis_resolution_steps']==winner['analysis_resolution_steps'] for x in rows)
 summary['matched_oracle_evaluations_checked']=sum(r['unique_evaluations'] for r in oracle)
with (p/'progressive.csv').open() as f: progress=list(csv.DictReader(f))
assert len(progress)==8*65
for order in {r['order'] for r in progress}:
 assert {int(r['k']) for r in progress if r['order']==order}==set(range(65))
with (p/'pairs.csv').open() as f: pairs=list(csv.DictReader(f))
assert len({(r['a'],r['b']) for r in pairs})==128
summary['all_prefixes_and_distinct_pairs_checked']=True
if (p/'one_step/oracles.json').exists():
 one=json.loads((p/'one_step/oracles.json').read_text())
 assert len(one)==3 and all(r['unique_evaluations']==1379 for r in one)
 for r in one:
  for k,winner in r['exact'].items():
   assert len(winner['selected_ids'])==int(k)
   assert all(cost[i]==1 for i in winner['selected_ids'])
 rr=[json.loads(l) for l in (p/'one_step/raw.jsonl').read_text().splitlines()]
 assert len(rr)==15 and all(r['status']=='UNSAT' and r['checker']=='PASS' for r in rr)
 for route in {r['route'] for r in rr}:
  group=[r for r in rr if r['route']==route]
  assert len(group)==5 and len({(r['input_sha256'],r['analysis_resolution_steps'],r['conflicts']) for r in group})==1
 summary['one_step_budget_and_15_repetitions_checked']=True
if (p/'selections.json').exists():
 rows=[]
 for name,(label,ids) in json.loads((p/'selections.json').read_text()).items():
  source=idx if label=='target' else d['h']; cert=source.history;n=source.leaves
  supports=[{j for j in ancestors(cert,i) if j>=n} for i in ids]
  row=dict(route=name,count=len(ids),independent_support=sum(map(len,supports)),union_support=len(set().union(*supports)) if supports else 0)
  if label=='target':row['cost_histogram']=dict(Counter(cost[i] for i in ids))
  rows.append(row)
 summary['selected_costs']=rows
(p/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(summary)
