from pathlib import Path
import shutil,subprocess,json,hashlib
root=Path.cwd(); b=root/'execution_pipeline_v1/trajectory_native_v1'; src=root/'execution_pipeline_v1/native'
assert not b.exists()
shutil.copytree(src,b)
s=b/'glucose-3.0'
def edit(p,a,c):
 t=p.read_text();assert t.count(a)==1,(p,a,t.count(a));p.write_text(t.replace(a,c))
edit(s/'core/Solver.cc',str(src/'observer.inc'),str(b/'observer.inc'))
edit(s/'core/Solver.h','    void ep_hook();','    void au_start();\n    void au_emit(const char*,const std::string&);\n    void au_enqueue(Lit,CRef);\n    void au_conflict(CRef);\n    void au_learned(const vec<Lit>&);\n    std::string au_state();\n    std::string au_frontier();\n    void ep_hook();')
obs=b/'observer.inc'
edit(obs,'void Solver::hc_register(CRef cr)', '#include "'+str(root/'execution_pipeline_v1/trajectory_observer.inc')+'"\nvoid Solver::hc_register(CRef cr)')
edit(obs,'void Solver::pm_dequeue(){++dequeues;}','void Solver::pm_dequeue(){++dequeues;if(au_active){++au_dequeues;au_emit("dequeue",std::to_string(lit(trail[qhead-1])));}}')
edit(obs,'void Solver::pm_conflict_hook(CRef){','void Solver::pm_conflict_hook(CRef cr){au_conflict(cr);')
edit(obs,'pending.length=l.size();','au_learned(l);pending.length=l.size();')
edit(obs,' if(aid){CRef cr=', ' au_start();\n if(aid){CRef cr=')
cc=s/'core/Solver.cc'
edit(cc,'    trail.push_(p);','    trail.push_(p);\n    au_enqueue(p,from);')
edit(cc,'    starts++;','    starts++;\n    au_emit("restart","null");')
edit(cc,'    if (decisionLevel() > level){','    if (decisionLevel() > level){\n        au_emit("backtrack",std::to_string(level));')
edit(cc,'            newDecisionLevel();\n            uncheckedEnqueue(next);','            au_emit("decision",std::to_string(lit(next)));\n            newDecisionLevel();\n            uncheckedEnqueue(next);')
# Seal used observer and transplant include locally; no transplant invocation accepted by runner.
shutil.copy(root/'execution_pipeline_v1/trajectory_observer.inc',b/'trajectory_observer.inc')
edit(obs,str(root/'execution_pipeline_v1/trajectory_observer.inc'),str(b/'trajectory_observer.inc'))
shutil.copy(root/'execution_pipeline_v1/transplant.inc',b/'transplant.inc')
edit(obs,str(root/'execution_pipeline_v1/transplant.inc'),str(b/'transplant.inc'))
d=b/'driver.cc';edit(d,'extern bool ep_done;','extern bool ep_done;\nextern void trajectory_finish();');edit(d,'auto r=s.solveLimited(a);','auto r=s.solveLimited(a);trajectory_finish();')
cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-DREPLAY','-I'+str(s),str(d),str(cc),str(s/'utils/Options.cc'),str(s/'utils/System.cc'),'-lz','-o',str(b/'audit-replay')]
p=subprocess.run(cmd,capture_output=True,text=True);(b/'audit-build.log').write_text(p.stdout+p.stderr);p.check_returncode()
(b/'audit-build.json').write_text(json.dumps({'command':cmd,'files':{str(p.relative_to(b)):hashlib.sha256(p.read_bytes()).hexdigest() for p in b.rglob('*') if p.is_file()}},indent=2))
print(b/'audit-replay')
