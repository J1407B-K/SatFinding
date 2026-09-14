"""Freeze ten pre-existing, mechanism-unused targets without reading results."""
import json,hashlib
from pathlib import Path
OUT=Path('results/persistent_imprint_replication'); SOURCE=Path('results/persistent_memory_stream'); TARGETS=[f'T{i}' for i in range(5,15)]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=True); assert not (OUT/'frozen.json').exists()
 rows=[]
 for n in TARGETS:
  p=SOURCE/n/'target.json'; x=json.loads(p.read_text()); rows.append(dict(name=n,seed=x['seed'],input_sha256=sha(p),cnf_sha256=hashlib.sha256(json.dumps(x['cnf'],separators=(',',':')).encode()).hexdigest(),vertices=x['vertices'],clauses=len(x['cnf']),colors=x['colors'],source=str(p)))
 manifest=dict(targets=rows,solver=dict(binary='to_be_built_from_frozen_native_cdcl',seed=0,conflict_budget=1000000),selection='none',results_read_before_freeze=False,prior_art_gate='PERSISTENT_IMPRINT_PRIOR_ART_GATE.md',mechanism_unused_basis='Targets were used by prior selector/memory-stream measurements only; no reason/activity/heap imprint intervention was run on them.')
 (OUT/'frozen.json').write_text(json.dumps(manifest,indent=2)+'\n'); print('frozen',TARGETS)
if __name__=='__main__':main()
