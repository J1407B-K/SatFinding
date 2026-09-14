"""Isolated exploratory instrumentation; frozen harness and evidence are read only."""
import csv, hashlib, json, subprocess, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'results/branch_displacement_mechanism_v1'
BUILD=OUT/'build'
PKG=ROOT/'results/prospective_temporal_state_cohort_v3/packages/T10_S3_B488045'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def dump(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def build():
 BUILD.mkdir(exist_ok=True)
 source=ROOT/'harness_v3'
 tree=BUILD/'glucose-3.0'
 shutil.copytree(source/'glucose-3.0',tree,dirs_exist_ok=True)
 shutil.copy2(source/'driver.cc',BUILD/'driver.cc')
 obs=(source/'observer.inc').read_text()
 # Forward declarations are class members; the independent implementation goes before replay observer.
 obs=replace(obs,'void Solver::hc_register(CRef cr)',(HERE/'observer.inc').read_text()+'\nvoid Solver::hc_register(CRef cr)')
 obs=replace(obs,' reached=true;',' reached=true;\n bm_start();')
 obs=replace(obs,'uncheckedEnqueue(p,cr);action_verified=true;','bm_injection=true;uncheckedEnqueue(p,cr);bm_injection=false;action_verified=true;')
 (BUILD/'observer.inc').write_text(obs)
 hp=tree/'core/Solver.h';s=hp.read_text();s=replace(s,'    void hc_boundary();','    void bm_start();\n    void bm_event(const char*,Lit,CRef,const vec<Lit>*);\n    Lit bm_pick();\n    void hc_boundary();');hp.write_text(s)
 cc=tree/'core/Solver.cc';s=cc.read_text()
 s=replace(s,str(source/'observer.inc'),str(BUILD/'observer.inc'))
 s=replace(s,'    trail.push_(p);\n    hc_observe();','    trail.push_(p);\n    bm_event(from==CRef_Undef?"enqueue":"propagated_assignment",p,from,nullptr);\n    hc_observe();')
 s=replace(s,'        pm_dequeue();','        pm_dequeue();\n        bm_event("dequeue",p,CRef_Undef,nullptr);')
 s=replace(s,'          pm_conflict_hook(confl);','          pm_conflict_hook(confl);\n          bm_event("conflict_clause",lit_Undef,confl,nullptr);')
 anchor='            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);'
 s=replace(s,anchor,anchor+'\n            bm_event("conflict_analysis",lit_Undef,CRef_Undef,&learnt_clause);')
 s=replace(s,'            cancelUntil(backtrack_level);','            cancelUntil(backtrack_level);\n            bm_event("backtrack",lit_Undef,CRef_Undef,nullptr);\n            bm_event("learned_clause",lit_Undef,CRef_Undef,&learnt_clause);\n            bm_event("heap_activity",lit_Undef,CRef_Undef,nullptr);')
 s=replace(s,'                next = pickBranchLit();','                next = bm_pick();')
 s=replace(s,"            // Increase decision level and enqueue 'next'",'            bm_event("decision",next,CRef_Undef,nullptr);\n'+"            // Increase decision level and enqueue 'next'")
 s=replace(s,'    starts++;','    starts++;\n    bm_event("restart",lit_Undef,CRef_Undef,nullptr);')
 cc.write_text(s)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-DREPLAY','-I'+str(tree),str(BUILD/'driver.cc'),str(cc),str(tree/'utils/Options.cc'),str(tree/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(BUILD/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(BUILD/'manifest.json',{'command':cmd,'files':{str(p.relative_to(ROOT)):sha(p) for p in BUILD.rglob('*') if p.is_file() and p.name!='manifest.json'}})
def run(tag,rank=0,mode='observe',ordinal=0,literal=0,var=27):
 d=OUT/'runs'/tag;d.mkdir(parents=True,exist_ok=False)
 st=load(PKG/'state.json');acts=load(PKG/'actions.json')['selected'];a=acts[rank-1] if rank else None
 request=[st[k] for k in ['boundary','conflicts','decisions','level','trail_length','qhead','canonical_logical_state_hash','canonical_heuristic_state_hash']]
 request+= [a['id'],a['literal'],int(a['source']=='learned'),len(a['clause'])]+a['clause'] if a else [0,0,0,0]
 (d/'request.txt').write_text(' '.join(map(str,request))+'\n')
 (d/'mechanism_request.txt').write_text(f'{var} {mode} {ordinal} {literal}\n')
 cmd=[str(BUILD/'run'),str(PKG/'input.cnf'),str(d/'proof.drup'),str(d),str(d/'request.txt')]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=240);(d/'stdout.txt').write_text(p.stdout);(d/'stderr.txt').write_text(p.stderr);dump(d/'command.json',cmd);p.check_returncode()
 lines=p.stdout.splitlines();result=load(d/'checkpoint.json');assert all(result[k]==st[k] for k in result)
 for n,key in [('logical.txt','canonical_logical_state_hash'),('heuristic.txt','canonical_heuristic_state_hash')]:assert sha(d/n)==st[key]
 assert load(d/'prefix_counters.json')==load(PKG/'prefix_counters.json')
 native=json.loads(lines[-2]);native.update(json.loads(lines[-1])['final_counters']);assert native['status']=='UNSAT'
 checker=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['checker'];assert sha(checker['path'])==checker['sha256']
 c=subprocess.run([checker['path'],str(PKG/'input.cnf'),str(d/'proof.drup')],capture_output=True,text=True,timeout=240);(d/'proof.log').write_text(c.stdout+c.stderr);assert c.returncode==0 and 's VERIFIED' in c.stdout
 meta={'tag':tag,'rank':rank,'mode':mode,'binary_sha256':sha(BUILD/'run'),'build_manifest_sha256':sha(BUILD/'manifest.json'),'canonical_verified':True,'proof':'VERIFIED','proof_sha256':sha(d/'proof.drup'),'native_result':native,'remaining_ops':native['analysis_resolution_steps']-st['prefix_analysis_ops']}
 dump(d/'result.json',meta);print(json.dumps(meta),flush=True);return meta
if __name__=='__main__':
 build()
 for tag,rank,var in [('BASELINE',0,27),('HIGH',2,27),('CONTROL_BASELINE',0,430),('CONTROL',1,430)]:run(tag,rank,var=var)
