"""Rerun only the two known actions; record the frozen local feature set."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/same_action_context_compare').resolve()
BUILD=Path('/private/tmp/satfinding-same-action-context')
CASES=[('C130_NEGATIVE','/private/tmp/satfinding-l2-priming-vs-trigger','TRIGGER_PRE','observe.inc'),('C656_POSITIVE','/private/tmp/satfinding-original-early-prop','TARGET_PRE','snapshot.inc')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def build(name,basepath,target,snapfile):
 base=Path(basepath);b=BUILD/name;root=b/'glucose-3.0';shutil.copytree(base/'glucose-3.0',root,dirs_exist_ok=True)
 for p in base.glob('*.inc'):shutil.copy2(p,b/p.name)
 # Replace the full-state snapshot body with this task's small fixed snapshot.
 p=b/snapfile;s=p.read_text();lo=s.index('void Solver::lt_snapshot(');hi=s.index('void Solver::lt_restart_json(',lo)
 s=s[:lo]+'void Solver::lt_snapshot(const std::string& name){cx_snapshot(name);}\n'+s[hi:];p.write_text(s)
 if (b/'sp.inc').exists():
  p=b/'sp.inc';s=p.read_text();lo=s.index('void Solver::sp_record(');hi=s.index('void Solver::sp_post(',lo)
  s=s[:lo]+'void Solver::sp_record(const char*,Lit,CRef){}\n'+s[hi:];p.write_text(s)
 inc=b/'context.inc';inc.write_text('#define CX_TARGET "'+target+'"\n'+Path('same_action_context_compare.inc').read_text())
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void lt_snapshot(const std::string&);',
  '    void cx_snapshot(const std::string&);\n    void cx_clause(FILE*,CRef);\n    void cx_enqueue(Lit,CRef);\n    void cx_dequeue(Lit);\n    void cx_conflict(CRef);\n    void lt_snapshot(const std::string&);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(base)+'/',str(b)+'/')
 # All prior helper includes precede the source constructor. Append this include
 # directly after the final helper include, so it has access to read-only helpers.
 lines=s.splitlines(True);last=max(i for i,l in enumerate(lines) if l.startswith('#include "') and str(b) in l)
 lines.insert(last+1,'#include "'+str(inc)+'"\n');s=''.join(lines)
 s=replace_once(s,'    starts++;','    starts++;\n    cx_epoch_start=conflicts;')
 s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    cx_enqueue(p,from);\n    assigns[var(p)] = lbool(!sign(p));')
 s=replace_once(s,"        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.","        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate.\n        cx_dequeue(p);")
 s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;','\t  conflicts++; conflictC++;conflictsRestarts++;\n          cx_conflict(confl);');cc.write_text(s)
 shutil.copy2(base/'driver.cc',b/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(b/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(b/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/(name+'.build.log')).write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/(name+'.build.json'),{'command':cmd,'binary_sha256':sha(b/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('same_action_context_compare.inc'),inc,cc,h,b/snapfile,b/'driver.cc']}})
 return b

def hash_clauses(x):
 if isinstance(x,dict):
  if 'literals' in x and 'cref' in x:x['hash_sha256']=hashlib.sha256((' '.join(map(str,sorted(x['literals'])))+' 0\n').encode()).hexdigest()
  for v in list(x.values()):hash_clauses(v)
 elif isinstance(x,list):
  for v in x:hash_clauses(v)

def run(case):
 name,base,target,snapfile=case;b=build(*case);d=OUT/name;d.mkdir()
 cmd=[str(b/'run'),str(OUT/'A.cnf'),str(d/'proof.drup'),'1000000']
 if name=='C130_NEGATIVE':cmd += [str(d),'1'];expected=Path('results/l2_priming_vs_trigger/UNPRIMED_EARLY_566/result.json')
 else:cmd += ['ORIGINAL_EARLY_PROP',str(d/'pulse.jsonl'),str(d/'events.jsonl'),str(d/'audit.jsonl'),'0',str(d),'0'];expected=Path('results/original_clause_early_prop/ORIGINAL_EARLY_PROP/result.json')
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(d/'stdout.txt').write_text(r.stdout+r.stderr);r.check_returncode()
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')));old=json.loads(expected.read_text())['stats'];assert all(stats[k]==v for k,v in old.items() if k!='seconds')
 check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(d/'proof.drup')],capture_output=True,text=True,timeout=180)
 (d/'proof_check.txt').write_text(check.stdout+check.stderr);assert check.returncode==0 and 's VERIFIED' in check.stdout
 with gzip.open(d/'proof.drup.gz','wb') as f:f.write((d/'proof.drup').read_bytes())
 snapshot=json.loads((d/'context.raw.json').read_text());future=[json.loads(x) for x in (d/'future.jsonl').read_text().splitlines()]
 assert future[0]['event']=='ENQUEUE' and future[0]['literal']==566
 assert future[-1]['event']=='FIRST_CONFLICT'
 snapshot.update(context=name,immediate_future={'enqueued_literals':[x['literal'] for x in future if x['event']=='ENQUEUE'],'propagated_literals':[x['literal'] for x in future if x['event']=='PROPAGATE'],'first_conflict':future[-1],'event_sequence':future},validation={'final_stats':stats,'all_frozen_non_time_counters_match':True,'proof_validation':'VERIFIED','proof_sha256':sha(d/'proof.drup'),'no_full_state_snapshot':True})
 hash_clauses(snapshot)
 out='c130_snapshot.json' if name=='C130_NEGATIVE' else 'c656_snapshot.json';dump(OUT/out,snapshot)
 print(name,json.dumps(stats),'future',json.dumps(future[-1]),flush=True);return snapshot

def flatten(x,prefix=''):
 out={}
 if isinstance(x,dict):
  for k,v in x.items():out.update(flatten(v,prefix+'.'+k if prefix else k))
 else:out[prefix]=json.dumps(x,ensure_ascii=False,separators=(',',':'))
 return out

def main():
 OUT.mkdir(exist_ok=False);shutil.copy2('results/l2_pulse_window/A.cnf',OUT/'A.cnf')
 dump(OUT/'protocol.json',{'cases':['C130_NEGATIVE','C656_POSITIVE'],'action':'Replay existing one-time early enqueue566 from original2589; snapshot before it, then no new intervention; retain positive existing future-disable semantics','frozen_features':{'global':['conflict','decision','level','trail length','qhead','pending count','inflight literal','next queued/native propagation','restart epoch','conflicts since restart'],'variables565566567':['assignment','level','trail position','reason id/hash/literals','activity','heap position','phase','decision or propagated'],'clause2589':['literals','values','unit explanation','watch positions','native access timing or UNAVAILABLE'],'reason_dag':'roots565/567; depth0 roots, parents depth1, grandparents depth2; no expansion at depth2','neighborhood':['occurrences','binary','ternary','long','original','learned','unit','almost_unit'],'future':['enqueue sequence','dequeue/propagate sequence','first conflict clause','propagation count to conflict']},'definitions':{'unit':'no true literal, exactly1 unassigned','almost_unit':'no true literal, exactly2 unassigned','heap_position':'native heap array index, -1 if absent; not sorted activity rank','future_counts':'Dequeue events after snapshot; current in-flight trigger was dequeued before snapshot and excluded. Enqueue count includes the fixed action.','next_access':'Queue position is exact at snapshot but absolute future clause visit can be preempted; report UNAVAILABLE without simulation'},'interpretation':'observational feature contrast only; no causal claim or adaptive feature selection'})
 a,b=[run(c) for c in CASES]
 # Expand the pre-registered per-variable/neighborhood/DAG fields into rows.
 def features(s):
  v={k:s[k] for k in ['global','clause2589']}
  for item in s['variables']:v['variable'+str(item['variable'])]=item
  for item in s['neighborhood']:v['neighborhood'+str(item['variable'])]=item
  v['local_reason_dag']=s['local_reason_dag']
  v['immediate_future']={k:s['immediate_future'][k] for k in ['enqueued_literals','propagated_literals','first_conflict']}
  return flatten(v)
 x,y=features(a),features(b)
 with (OUT/'context_feature_diff.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['feature','C130 negative','C656 positive','different?'])
  for k in sorted(set(x)|set(y)):w.writerow([k,x.get(k,'UNAVAILABLE'),y.get(k,'UNAVAILABLE'),x.get(k)!=y.get(k)])

if __name__=='__main__':main()
