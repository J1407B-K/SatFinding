"""Add observational hooks to byte-audited archived native sources, retain guards."""
import os,sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from run import *
def build_historical(target):
 stem='fixed-state-action-surface' if target=='T10' else 'multi-state-action-surface'
 inc='fixed_state_action_surface.inc' if target=='T10' else 'multi_state_action_surface.inc'
 old=Path('/private/tmp/satfinding-'+stem);dest=OUT/('build_'+target);tree=dest/'glucose-3.0'
 shutil.copytree(old/'glucose-3.0',tree,dirs_exist_ok=True);shutil.copy2(old/'driver.cc',dest/'driver.cc')
 heap=tree/'mtl/Heap.h';s=heap.read_text();method='    std::vector<int> semantic_order() const { Heap copy(lt); heap.copyTo(copy.heap); indices.copyTo(copy.indices); std::vector<int> out; while(!copy.empty()) out.push_back(copy.removeMin()+1); return out; }\n'
 s=replace(s,'    Heap(const Comp& c)',method+'    Heap(const Comp& c)');heap.write_text('#include <vector>\n'+s)
 hp=tree/'core/Solver.h';s=hp.read_text();s=replace(s,'    void hc_boundary();','    void bm_start();\n    void bm_event(const char*,Lit,CRef,const vec<Lit>*);\n    Lit bm_pick();\n    void hc_boundary();');hp.write_text(s)
 obs=(ROOT/inc).read_text();adapter='''
#include <iomanip>
#include <sys/stat.h>
static HU dequeues=0;
static std::string output_dir;
static int lit(Lit p){return hc_lit(p);}
template<class T> static void array(std::ostream&o,const T&v){o<<'[';bool first=true;for(auto x:v){if(!first)o<<',';first=false;o<<x;}o<<']';}
'''
 bm=(HERE/'observer.inc').read_text()
 bm=replace(bm,' std::ifstream f(output_dir+"/mechanism_request.txt");f>>bm_var>>bm_mode>>bm_target_ordinal>>bm_target_lit;\n if(!f||bm_var<1||bm_var>nVars())throw std::runtime_error("MECHANISM_REQUEST");',
 ''' bm_var=atoi(getenv("BM_VAR"));bm_mode=getenv("BM_MODE");bm_target_ordinal=atoi(getenv("BM_ORDINAL"));bm_target_lit=atoi(getenv("BM_LITERAL"));
 if(bm_var<1||bm_var>nVars())throw std::runtime_error("MECHANISM_REQUEST");''')
 obs=replace(obs,'void Solver::hc_register(CRef cr)',adapter+bm+'\nvoid Solver::hc_register(CRef cr)')
 obs=replace(obs,' for(int i=-1;i<take;++i){',' for(int i=-1;i<take;++i){\n  if(i>=0&&i+1!=atoi(getenv("BM_ACTION")))continue;')
 obs=replace(obs,'   if(i>=0){const auto& a=actions[i];','   output_dir=cf_dir+"/"+fs_tag;mkdir(output_dir.c_str(),0755);bm_start();\n   if((i<0&&bm_mode=="restore")||(i>=0&&bm_mode=="suppress"))bm_mode="observe";\n   if(i>=0){const auto& a=actions[i];')
 obs=replace(obs,'    uncheckedEnqueue(a.p,a.cr);','    bm_injection=true;uncheckedEnqueue(a.p,a.cr);bm_injection=false;')
 (dest/'observer.inc').write_text(obs)
 cc=tree/'core/Solver.cc';s=cc.read_text();s=replace(s,str(ROOT/inc),str(dest/'observer.inc'))
 s=replace(s,'    trail.push_(p);','    trail.push_(p);\n    bm_event(from==CRef_Undef?"enqueue":"propagated_assignment",p,from,nullptr);')
 s=replace(s,'        cf_dequeue(p);','        cf_dequeue(p);\n        ++dequeues;bm_event("dequeue",p,CRef_Undef,nullptr);')
 s=replace(s,'          cf_conflict(confl);','          cf_conflict(confl);\n          bm_event("conflict_clause",lit_Undef,confl,nullptr);')
 s=replace(s,'            cf_analysis(learnt_clause);','            cf_analysis(learnt_clause);\n            bm_event("conflict_analysis",lit_Undef,CRef_Undef,&learnt_clause);')
 s=replace(s,'            cancelUntil(backtrack_level);','            cancelUntil(backtrack_level);\n            bm_event("backtrack",lit_Undef,CRef_Undef,nullptr);\n            bm_event("learned_clause",lit_Undef,CRef_Undef,&learnt_clause);\n            bm_event("heap_activity",lit_Undef,CRef_Undef,nullptr);')
 s=replace(s,'                next = pickBranchLit();','                next = bm_pick();')
 s=replace(s,"            // Increase decision level and enqueue 'next'",'            bm_event("decision",next,CRef_Undef,nullptr);\n'+"            // Increase decision level and enqueue 'next'")
 s=replace(s,'    starts++;','    starts++;\n    bm_event("restart",lit_Undef,CRef_Undef,nullptr);');cc.write_text(s)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(tree),str(dest/'driver.cc'),str(cc),str(tree/'utils/Options.cc'),str(tree/'utils/System.cc'),'-lz','-o',str(dest/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(dest/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(dest/'manifest.json',{'command':cmd,'files':{str(p.relative_to(ROOT)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name!='manifest.json'}})
 return dest
def run_historical(target,rank,mode='observe',ordinal=0,literal=0,suffix=''):
 old=ROOT/('results/fixed_state_action_surface' if target=='T10' else 'results/multi_state_action_surface/S5')
 sid='HIST_T10_FIXED' if target=='T10' else 'HIST_T8_S5'
 acts=[e for e in map(json.loads,(old/'runs/opportunities.jsonl').read_text().splitlines()) if e['event']=='LEGAL_ACTION'];act=acts[rank-1]
 d=OUT/'historical_runs'/f'{sid}_R{rank}{suffix}';d.mkdir(parents=True,exist_ok=False)
 state=load(old/'frozen_state.json');index=int(load(old/'runs/command.json')['command'][-1])
 env=dict(os.environ,MS_STATE_HASH=state['pre_state_hash'],BM_VAR=str(abs(act['implied_literal'])),BM_ACTION=str(rank),BM_MODE=mode,BM_ORDINAL=str(ordinal),BM_LITERAL=str(literal))
 cnf=ROOT/f'results/high_leverage_discovery/{target}/input.cnf'
 cmd=[str(OUT/('build_'+target)/'run'),str(cnf),str(d/'prefix.drup'),'1000000',str(d),str(index)]
 p=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=240);(d/'stdout.txt').write_text(p.stdout);(d/'stderr.txt').write_text(p.stderr);dump(d/'command.json',{'command':cmd,'mechanism_env':{k:v for k,v in env.items() if k.startswith('BM_') or k=='MS_STATE_HASH'}});p.check_returncode()
 events=list(map(json.loads,(d/'opportunities.jsonl').read_text().splitlines()));snap=next(e for e in events if e['event']=='FROZEN_STATE')
 assert snap['pre_state_hash']==state['pre_state_hash'] and snap['heap_including_inverse_hash']==state['heap_including_inverse_hash']
 assert [e for e in events if e['event']=='LEGAL_ACTION']==acts
 assert all(e['wait_status']==0 for e in events if e['event']=='CHILD_EXIT')
 results=[]
 checker=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['checker'];assert sha(checker['path'])==checker['sha256']
 for tag in ['BASELINE',f'ACTION_{rank}']:
  stats=next(json.loads(x) for x in reversed((d/(tag+'.stdout.txt')).read_text().splitlines()) if x.startswith('{'))
  original=load(old/'runs'/f'{tag}.result.json');assert stats['status']=='UNSAT'
  proof=d/f'{tag}.drup';c=subprocess.run([checker['path'],str(cnf),str(proof)],capture_output=True,text=True,timeout=240);(d/f'{tag}.proof.log').write_text(c.stdout+c.stderr);assert c.returncode==0 and 's VERIFIED' in c.stdout
  equivalence=all(stats[k]==v for k,v in original['stats'].items() if k!='seconds') and sha(proof)==original['proof_sha256']
  if mode=='observe' or (mode=='restore' and tag=='BASELINE') or (mode=='suppress' and tag!='BASELINE'):assert equivalence,(target,tag,stats,original['stats'])
  meta={'state_id':sid,'tag':tag,'action':act,'mode':mode,'binary_sha256':sha(OUT/('build_'+target)/'run'),'build_manifest_sha256':sha(OUT/('build_'+target)/'manifest.json'),'original_route_equivalent':equivalence,'operational_checkpoint_verified':True,'historical_canonical_snapshot_available':False,'identity_evidence':'archived binary replay + unmodified checkpoint guard + native heap/inverse guard + unchanged frozen legal actions + complete counters and proof bytes reproduced; source patch is observational outside explicit CF hook','proof':'VERIFIED','proof_sha256':sha(proof),'native_result':stats,'remaining_ops':stats['analysis_resolution_steps']-state['analysis_ops_at_snapshot']}
  dump(d/tag/'result.json',meta);results.append(meta)
 dump(d/'equivalence.json',results);print(target,rank,mode,[r['original_route_equivalent'] for r in results],flush=True)
if __name__=='__main__':
 for target,ranks in [('T10',[1,2,3,5]),('T8',[1,4])]:
  build_historical(target)
  for rank in ranks:run_historical(target,rank)
