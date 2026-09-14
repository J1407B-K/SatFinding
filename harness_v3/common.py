import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
PROTOCOL=ROOT/'results/prospective_temporal_state_cohort/frozen_temporal_protocol_v1_1.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def freeze(p,x):
 dump(p,x);Path(str(p)+'.sha256').write_text(sha(p)+'\n')
def frozen(p):
 assert sha(p)==Path(str(p)+'.sha256').read_text().strip(),('FREEZE_HASH',str(p));return load(p)
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def route_id(p,action):
 identity=sha(p/'package_manifest.json')+(':BASELINE' if action is None else f':ACTION:{action["rank"]}:{action["id"]}')
 return hashlib.sha256(identity.encode()).hexdigest()
def tree_hashes(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
