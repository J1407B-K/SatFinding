"""Deterministic target-only resolution lemma builder, depth <=2."""
import json,hashlib,itertools
from pathlib import Path
from round4_core import ProofDB,Budget
K=64;DEPTH=2;MAX_LEN=12

def canon(c):return tuple(sorted(set(c)))
def resolve(a,b,p):
 if p not in a or -p not in b:return None
 c=canon((set(a)-{p})|(set(b)-{-p}))
 return None if any(-x in c for x in c) else c
def build(cnf):
 original={canon(c) for c in cnf}; nodes=list(cnf); steps=[]; seen=set(original); one=[]
 for i,a in enumerate(cnf):
  for j,b in enumerate(cnf):
   if i>=j:continue
   for p in sorted(set(a)&{-x for x in b}):
    c=resolve(a,b,p)
    if c and c not in seen and len(c)<=MAX_LEN: one.append((c,i,j,p));seen.add(c)
 for c,i,j,p in sorted(one,key=lambda x:(x[0],x[1],x[2],x[3]))[:K]: steps.append(dict(clause_id=len(steps)+1,depth=1,parents=[i,j],pivot=p,intermediate=[],lemma=list(c)))
 return steps
def check(cnf,steps):
 # independent replay implementation (does not call producer resolve())
 original={canon(c) for c in cnf}
 for s in steps:
  a,b=canon(cnf[s['parents'][0]]),canon(cnf[s['parents'][1]]); p=s['pivot']
  assert p in a and -p in b
  out=canon([x for x in a if x!=p]+[x for x in b if x!=-p])
  assert out==canon(s['lemma']) and not any(-x in out for x in out) and out not in original
  assert s['depth']==1 and s['intermediate']==[]
 return True
def main():
 target='T5'; src=Path('results/persistent_memory_stream/T5/target.json'); x=json.loads(src.read_text()); cnf=[canon(c) for c in x['cnf']]; steps=build(cnf); assert len(steps)>=K; steps=steps[:K]; assert check(cnf,steps)
 out=Path('results/persistent_imprint_replication/T5_lemmas');out.mkdir(parents=True,exist_ok=True)
 lem=[canon(s['lemma']) for s in steps]; payload=dict(target=target,input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),K=K,max_depth=DEPTH,max_clause_length=MAX_LEN,sort='canonical lexical (clause, parents, pivot)',lemmas=[list(c) for c in lem],certificates=steps)
 (out/'certificates.json').write_text(json.dumps(payload,indent=2)+'\n');
 with open(out/'treatment.cnf','w') as f:
  f.write(f'p cnf 600 {len(cnf)+K}\n');[f.write(' '.join(map(str,c))+' 0\n') for c in cnf+lem]
 report=dict(status='PASS',independent_replay=True,original_clauses=len(cnf),lemmas=len(lem),non_tautological=all(not any(-v in c for v in c) for c in lem),not_original=all(c not in set(cnf) for c in lem),treatment_sha256=hashlib.sha256((out/'treatment.cnf').read_bytes()).hexdigest())
 (out/'checker_report.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
