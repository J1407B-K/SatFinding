"""Frozen C660 pre-decision imprint experiment; legality checked before mutation."""
import gzip, json, shutil, subprocess, hashlib
from pathlib import Path
from build_native_cdcl import replace_once
from evaluation_oracle_run import sha
from unseen_selector import dump
from activity_heap_mediation import HEAP_METHODS
P=Path('results/persistent_state_imprint')
B=Path('/private/tmp/satfinding-persistent-imprint')
BASE=Path('/private/tmp/satfinding-decision828-l2-remove')

def build():
 P.mkdir(exist_ok=True); B.mkdir(exist_ok=True)
 root=B/'glucose-3.0'; shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'mtl/Heap.h'; h.write_text(replace_once(h.read_text(),'    Heap(const Comp& c) : lt(c) { }','    Heap(const Comp& c) : lt(c) { }\n'+HEAP_METHODS))
 h=root/'core/SolverTypes.h'; h.write_text(replace_once(h.read_text(),'    OccLists(const Deleted& d) : deleted(d) {}',r'''
 void ah_audit(FILE* f) const {
 int n=occs.size();fwrite(&n,sizeof(n),1,f);
 for(int k=0;k<n;++k){int m=occs[k].size();fwrite(&m,sizeof(m),1,f);if(m)fwrite(&occs[k][0],sizeof(occs[k][0]),m,f);}
 n=dirty.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&dirty[0],sizeof(char),n,f);
 n=dirties.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&dirties[0],sizeof(Idx),n,f);
 }
 OccLists(const Deleted& d) : deleted(d) {}
'''))
 h=root/'core/BoundedQueue.h'; h.write_text(replace_once(h.read_text(),'public:',r'''public:
 void ah_audit(FILE* f) const {int n=elems.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&elems[0],sizeof(T),n,f);}
'''))
 h=root/'core/Solver.h'; h.write_text(replace_once(h.read_text(),'    void ctx_remove_l2();','    void ctx_remove_l2();\n    void ah_dump(const char*);\n    void ps_hook();'))
 # Reuse the previously audited full object/live-buffer byte dump, including
 # allocator, watch dirty state, queues, all native counters. No old hook runs.
 audit=Path('activity_heap_mediation.inc').read_text()
 audit=audit[:audit.index('void Solver::ah_hook()')]
 trace=(BASE/'trace.inc').read_text()
 hook=Path('persistent_state_imprint.inc').read_text()
 trace=trace.replace('Lit Solver::da_pick(){',audit+'\n'+hook+'\nLit Solver::da_pick(){\n ps_hook();',1)
 trace=replace_once(trace,'if(cp && lt_run=="B_REMOVE_L2")ctx_remove_l2();','if(cp && lt_run.find("B_REMOVE_L2")==0)ctx_remove_l2();')
 (B/'trace.inc').write_text(trace)
 src=root/'core/Solver.cc'; src.write_text(replace_once(src.read_text(),str(BASE/'trace.inc'),str(B/'trace.inc')))
 shutil.copyfile(BASE/'driver.cc',B/'driver.cc')
 for n in ['A','B']: shutil.copyfile(Path('/private/tmp/satfinding-decision828-context')/(n+'.cnf'),B/(n+'.cnf'))
 (P/'requests.txt').write_text('')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(B/'driver.cc'),str(src),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(B/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True); assert r.returncode==0,r.stderr
 return dict(binary_sha256=sha(B/'run'),sources={str(p):sha(p) for p in [Path(__file__),Path('persistent_state_imprint.inc'),B/'trace.inc',src]},checkpoint='first native pick with completed conflicts==660, qhead==trail.size()',significant='joint reset >=250000 ops triggers only activity-only and heap-only split',legality='candidate heap comparator/inverse indices and recipient eligible coverage checked BEFORE write; illegal candidate aborts, no repair')

def run(n):
 p=B/(n+'.drup'); inp=B/('A.cnf' if n=='A' else 'B.cnf')
 r=subprocess.run([str(B/'run'),str(inp),str(p),'1000000',n,str(P.resolve()),str(P/'requests.txt')],capture_output=True,text=True,timeout=180)
 if r.returncode:
  row=dict(status='ABORTED_BEFORE_MUTATION' if r.returncode==71 else 'FAILED',returncode=r.returncode,stderr=r.stderr); dump(P/(n+'.result.json'),row); return row
 st=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{'))); assert st['status']=='UNSAT'
 assert (P/(n+'.ps_before.snapshot.json')).exists(),'C660 native pick not reached; no reset performed'
 ck=subprocess.run(['/private/tmp/satfinding-drat-trim',str(inp),str(p)],capture_output=True,text=True,timeout=90); (P/(n+'.proof_check.txt')).write_text(ck.stdout+ck.stderr); assert ck.returncode==0 and 'VERIFIED' in ck.stdout
 with gzip.open(P/(n+'.drup.gz'),'wb') as f:f.write(p.read_bytes())
 row=dict(status='PASS',stats=st,proof_verified=True,proof_sha256=sha(p))
 if n in ['A','B','B_REMOVE_L2']:
  old=Path('results/decision828_context' if n in ['A','B'] else 'results/decision828_l2_remove')/(n+'.result.json'); ref=json.loads(old.read_text())
  assert {k:v for k,v in st.items() if k!='seconds'}=={k:v for k,v in ref['stats'].items() if k!='seconds'}
  assert sha(p)==ref['proof_sha256'];row['frozen_counters_proof_identical']=True
 for l in gzip.open(P/(n+'.events.jsonl.gz'),'rt'):json.loads(l)
 hashes={t:{f:sha(P/(n+'.'+t+'.'+f+'.bin')) for f in ['allowed','other']} for t in ['before','after']}
 assert hashes['before']['other']==hashes['after']['other'];row['hashes']=hashes
 before=json.loads((P/(n+'.ps_before.snapshot.json')).read_text());after=json.loads((P/(n+'.ps_after.snapshot.json')).read_text())
 assert all(before[k]==after[k] for k in before if k not in ['activity','heap'])
 if n not in ['A','B','B_REMOVE_L2']:
  ctrl=json.loads((P/'B_REMOVE_L2.ps_before.snapshot.json').read_text());assert before==ctrl
  donor=json.loads((P/'A.ps_before.snapshot.json').read_text())
  for field in ['activity','heap']:
   use=n=='B_REMOVE_L2_ACTIVITY_HEAP_RESET' or (field=='activity' and n=='B_REMOVE_L2_ACTIVITY_RESET') or (field=='heap' and n=='B_REMOVE_L2_HEAP_RESET')
   assert after[field]==(donor[field] if use else before[field])
  row['pre_state_matches_natural']=True
 dump(P/(n+'.result.json'),row);print(n,st,flush=True);return row

def main():
 assert not (P/'protocol.json').exists(),'frozen experiment exists'
 dump(P/'protocol.json',build());runs={}
 for n in ['A','B','B_REMOVE_L2']:runs[n]=run(n);assert runs[n]['status']=='PASS'
 n='B_REMOVE_L2_ACTIVITY_HEAP_RESET';runs[n]=run(n);dump(P/'runs.json',runs)
 if runs[n]['status']=='PASS' and runs[n]['stats']['analysis_resolution_steps']>=250000:
  for n in ['B_REMOVE_L2_ACTIVITY_RESET','B_REMOVE_L2_HEAP_RESET']:runs[n]=run(n);dump(P/'runs.json',runs)
if __name__=='__main__':main()
