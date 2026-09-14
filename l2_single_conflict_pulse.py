"""C656-only local gate and, only if equal, one-conflict pulse comparison."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import gzip
from build_native_cdcl import replace_once

OUT=Path('results/l2_single_conflict_pulse').resolve()
BASE=Path('/private/tmp/satfinding-l2-pulse-window')
BUILD=Path('/private/tmp/satfinding-l2-single-conflict')
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jhash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 # Reuse only read-only dump helpers, not the old generic event machinery.
 for rel in ['mtl/Heap.h','core/BoundedQueue.h']:
  base=(root/rel).read_text();old=(Path('/private/tmp/satfinding-l1-l2-latent/glucose-3.0')/rel).read_text()
  if rel.startswith('mtl'):
   helper=old[old.index('    void lt_dump('):old.index('    Heap(const Comp&')]
   base='#include <cstdio>\n'+replace_once(base,'    Heap(const Comp& c) : lt(c) { }',helper+'    Heap(const Comp& c) : lt(c) { }')
  else:
   helper=old[old.index(' void lt_dump('):old.index('\n bqueue(void)')]
   base=replace_once(base,'public:','public:\n'+helper)
  (root/rel).write_text(base)
 old=Path('l1_l2_latent_trace.inc').read_text()
 prefix=old[:old.index('void lt_init(')]
 # Removes unused globals/hash funcs only indirectly; none is connected to events.
 funcs=old[old.index('void lt_intvec('):old.index('LU Solver::lt_restart_hash()')]
 needle='fprintf(f,",\\"watches\\":[");'
 extra=r'''fprintf(f,",\"original_db\":[");
 for(int i=0;i<clauses.size();++i){Clause& c=ca[clauses[i]];fprintf(f,"%s{\"ref\":%u,\"l2\":%s,\"lits\":[",i?",":"",clauses[i],lt_l2(c)?"true":"false");for(int j=0;j<c.size();++j)fprintf(f,"%s%d",j?",":"",lt_int(c[j]));fprintf(f,"]}");}
 fprintf(f,"],\"learned_layout\":[");
 for(int i=0;i<learnts.size();++i){Clause& c=ca[learnts[i]];fprintf(f,"%s{\"ref\":%u,\"lbd\":%u,\"activity\":\"%a\",\"can_delete\":%s,\"lits\":[",i?",":"",learnts[i],c.lbd(),(double)c.activity(),c.canBeDel()?"true":"false");for(int j=0;j<c.size();++j)fprintf(f,"%s%d",j?",":"",lt_int(c[j]));fprintf(f,"]}");}
 fprintf(f,"],\"counters\":{\"conflicts\":%llu,\"decisions\":%llu,\"propagations\":%llu,\"ops\":%llu,\"redundancy\":%llu,\"binary\":%llu},\"random_seed\":\"%a\",\"cla_inc\":\"%a\",\"var_decay\":\"%a\",\"simpDB_assigns\":%d,\"allocator_size\":%u,\"allocator_wasted\":%u,\"raw_levels\":[",(LU)conflicts,(LU)decisions,(LU)propagations,sf_analysis,sf_redundancy,sf_binary,random_seed,cla_inc,var_decay,simpDB_assigns,ca.size(),ca.wasted());
 for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",level(v));fprintf(f,"]");
 '''
 funcs=replace_once(funcs,needle,extra+needle)
 local=prefix+funcs+Path('l2_single_conflict_pulse.inc').read_text()
 (BUILD/'local.inc').write_text(local)
 h=root/'core/Solver.h';s=h.read_text()
 s=replace_once(s,'    CRef pw_boundary();',
  '    void lt_snapshot(const std::string&);\n    void lt_restart_json(FILE*);\n'
  '    void sc_boundary();\n    void sc_conflict(CRef);\n    void sc_enqueue(Lit,CRef);\n'
  '    void sc_visit(Lit);\n    void sc_bump(Var);\n    void sc_analysis_clause(const Clause&,Lit);\n'
  '    void sc_learned(const vec<Lit>&,int);\n    void sc_decision(Lit);\n    CRef pw_boundary();')
 s='#include <string>\n#include <cstdio>\n'+s
 s=replace_once(s,'        order_heap.decrease(v); }','        order_heap.decrease(v);\n    sc_bump(v); }');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text()
 s=replace_once(s,'#include "'+str(BASE/'pulse.inc')+'"','#include "'+str(BASE/'pulse.inc')+'"\n#include "'+str(BUILD/'local.inc')+'"')
 s=replace_once(s,'        CRef confl = pw_boundary();','        sc_boundary();\n        CRef confl = pw_boundary();')
 s=replace_once(s,'          pw_use(ca[confl],2);','          pw_use(ca[confl],2);\n          sc_conflict(confl);')
 s=replace_once(s,'    pw_enqueue(p,from);','    sc_enqueue(p,from);\n    pw_enqueue(p,from);')
 s=replace_once(s,'        pw_use(c,0);','        sc_analysis_clause(c,p);\n        pw_use(c,0);')
 s=replace_once(s,'            Lit q = c[j];','            Lit q = c[j];\n            sc_visit(q);')
 s=replace_once(s,'            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);',
  '            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);\n            sc_learned(learnt_clause,backtrack_level);')
 s=replace_once(s,'                next = pickBranchLit();','                next = pickBranchLit();\n                sc_decision(next);');cc.write_text(s)
 driver=(BASE/'driver.cc').read_text()
 driver=driver.replace('extern void pw_finish();','extern void pw_finish();\nextern void sc_init(const char*,bool);\nextern void sc_finish();')
 driver=driver.replace('argc != 6','argc != 8').replace('    pw_init(argv[4],argv[5]);','    pw_init(argv[4],argv[5]);\n    sc_init(argv[6],atoi(argv[7])!=0);')
 driver=driver.replace('    pw_finish();','    pw_finish();\n    sc_finish();');(BUILD/'driver.cc').write_text(driver)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'local_build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'local_build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('l2_single_conflict_pulse.inc'),BUILD/'local.inc',BASE/'pulse.inc',cc,h,BUILD/'driver.cc']}})

def run(name,point,gate):
 d=OUT/(name+('_gate' if gate else ''));d.mkdir(exist_ok=False)
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(d/'proof.drup'),'1000000','REMOVE@'+str(point),str(d/'pulse.events.jsonl'),str(d),'1' if gate else '0']
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
 (d/'stdout.txt').write_text(r.stdout+r.stderr)
 if r.returncode not in (0,42):raise RuntimeError(r.stderr)
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')))
 assert stats['status']==('PRE_CONFLICT_GATE' if gate else 'UNSAT'),stats
 verified=False
 if not gate:
  check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(d/'proof.drup')],capture_output=True,text=True,timeout=180)
  (d/'proof_check.txt').write_text(check.stdout+check.stderr)
  verified=check.returncode==0 and 's VERIFIED' in check.stdout;assert verified
  with gzip.open(d/'proof.drup.gz','wb') as f:f.write((d/'proof.drup').read_bytes())
 snapshots={p.name.split('.')[1]:json.loads(p.read_text()) for p in d.glob('local.*.snapshot.json')}
 result={'route':name,'remove_conflict':point,'gate_only':gate,'stats':stats,'proof_verified':verified,'proof_sha256':sha(d/'proof.drup'),'snapshots':snapshots,'events':[json.loads(x) for x in (d/'local.jsonl').read_text().splitlines()]}
 return result

def normalized(s):
 s=json.loads(json.dumps(s));l2id='15289423184524811497'
 s['original_db']=[c for c in s['original_db'] if not c['l2']]
 s['watches']=[[w for w in ws if w[0]!=l2id] for ws in s['watches']]
 for k in ['global','e','clauses_literals','allocator_wasted']:s.pop(k,None)
 return s

def compare(a,b):
 x,y=normalized(a),normalized(b)
 return {'equal':x==y,'different_fields':[k for k in x if x[k]!=y[k]],'hashes':[jhash(x),jhash(y)]}

def main():
 assert not (OUT/'single_conflict_summary.json').exists()
 step1=json.loads((OUT/'remove656_summary.json').read_text());assert step1['stats']['analysis_resolution_steps']==174432
 dump(OUT/'single_conflict_protocol.json',{'key_conflict':656,'SHORT_PULSE_remove':655,'ONE_CONFLICT_LONGER_remove':656,'gate':'Snapshot at entry to C656 conflict handler, after propagation, before queue/analysis mutations; stop both prefixes there and compare before any complete paired runs','comparison_exclusions':['L2 original DB entry and watch entries','clauses_literals (three L2 literals)','allocator_wasted (freed L2)','observer counters'],'scope':[655,656,657],'no_causal_interpretation_if_gate_diverges':True})
 build();a=run('SHORT_PULSE',655,True);b=run('ONE_CONFLICT_LONGER',656,True)
 comparisons={key:compare(a['snapshots'][key],b['snapshots'][key]) for key in a['snapshots'] if key in b['snapshots']}
 gate=comparisons['C656_PRE_ANALYSIS']
 result={'status':'PRE_CONFLICT_STATE_DIVERGED' if not gate['equal'] else 'PRE_CONFLICT_GATE_PASSED','key_conflict':656,'comparisons':comparisons,'paired_full_runs_executed':False,'excluded_fields':json.loads((OUT/'single_conflict_protocol.json').read_text())['comparison_exclusions']}
 if gate['equal']:
  a=run('SHORT_PULSE',655,False);b=run('ONE_CONFLICT_LONGER',656,False)
  expected=[json.loads(Path('results/l2_pulse_window/REMOVE@655.result.json').read_text())['stats'],step1['stats']]
  for r,old in zip([a,b],expected):assert all(r['stats'][k]==v for k,v in old.items() if k!='seconds')
  result.update(status='COMPLETED',paired_full_runs_executed=True,routes=[{k:v for k,v in r.items() if k not in ['snapshots','events']} for r in [a,b]])
 for r in [a,b]:
  for snap in r['snapshots'].values():
   snap['derived_hashes']={k:jhash(snap[k]) for k in ['assignment','trail','activity','heap','learned_layout']}
 dump(OUT/'local_conflict_trace.json',{'scope':[655,656,657],'gate_stopped':not gate['equal'],'routes':[a,b]})
 dump(OUT/'single_conflict_summary.json',result)
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
