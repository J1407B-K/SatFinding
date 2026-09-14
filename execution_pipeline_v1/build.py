"""Build an isolated native engine; never modifies the historical harness."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
D=ROOT/'execution_pipeline_v1'; B=D/'native_v2'; S=B/'glucose-3.0'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(p,a,b):
 t=p.read_text();assert t.count(a)==1,(p,a);p.write_text(t.replace(a,b))
def build():
 if S.exists():raise RuntimeError('Build directory already exists; do not overwrite sealed binaries')
 shutil.copytree(ROOT/'harness_v3/glucose-3.0',S)
 shutil.copy(ROOT/'harness_v3/observer.inc',B/'observer.inc')
 shutil.copy(D/'transplant.inc',B/'transplant.inc')
 # Independent source, no historic artifact/schema dependency.
 replace(S/'core/Solver.cc','/Users/kqs-mac/Go/GoProjects/SatFinding/harness_v3/observer.inc',str(B/'observer.inc'))
 replace(S/'core/Solver.h','    void hc_boundary();','    void hc_boundary();\n    void ep_hook();\n    void ep_dump(const std::string&);\n    void ep_bytes(const std::string&);')
 replace(B/'observer.inc','HU temporal_samples=0;','HU temporal_samples=0;\nstatic HU ep_cp=0;\nextern void ep_checkpoint_marker();')
 replace(B/'observer.inc','void Solver::hc_boundary(){','void Solver::hc_boundary(){\n#ifdef REPLAY\n ep_hook();\n#endif\n')
 replace(B/'observer.inc',' reached=true;',' reached=true;ep_cp=conflicts;ep_dump(output_dir+"/state");ep_bytes(output_dir+"/state.protected.bin");')
 with (B/'observer.inc').open('a') as f:f.write('\n#include "'+str(B/'transplant.inc')+'"\n')
 h=S/'mtl/Heap.h'
 replace(h,'    Heap(const Comp& c) : lt(c) { }','''    Heap(const Comp& c) : lt(c) { }
    bool ep_valid() const {for(int i=0;i<heap.size();++i){int v=heap[i];if(v<0||v>=indices.size()||indices[v]!=i)return false;if(i&&lt(v,heap[(i-1)/2]))return false;}return true;}
    void ep_build(vec<int>& v){for(int i=0;i<v.size();i++)indices.growTo(v[i]+1,-1);build(v);}
''')
 replace(S/'core/SolverTypes.h','    OccLists(const Deleted& d) : deleted(d) {}','''
 void ep_audit(FILE*f) const {int n=occs.size();fwrite(&n,sizeof(n),1,f);for(int i=0;i<n;++i){int m=occs[i].size();fwrite(&m,sizeof(m),1,f);if(m)fwrite(&occs[i][0],sizeof(Watcher),m,f);}n=dirty.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&dirty[0],sizeof(char),n,f);n=dirties.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&dirties[0],sizeof(Idx),n,f);}
    OccLists(const Deleted& d) : deleted(d) {}
'''.replace('sizeof(Watcher)','sizeof(Vec::value_type)'))
 # Vec has no value_type; use element expression size instead.
 q=S/'core/SolverTypes.h';q.write_text(q.read_text().replace('sizeof(Vec::value_type)','sizeof(occs[i][0])'))
 replace(S/'core/BoundedQueue.h','public:','''public:
 void ep_audit(FILE*f)const{int n=elems.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&elems[0],sizeof(T),n,f);}
''')
 driver=(ROOT/'harness_v3/driver.cc').read_text().replace('if(argc!=5)return 2;','if(argc!=5 && argc!=7)return 2;\n if(argc==7){ep_k=atoi(argv[5]);ep_donor=argv[6];}')
 driver=driver.replace('extern std::string output_dir, request_path;','extern std::string output_dir, request_path,ep_donor;\nextern int ep_k;\nextern bool ep_done;')
 driver=driver.replace(' return reached&&r==Glucose::lbool((uint8_t)1)?0:61;',' if(argc==7&&!ep_done)return 62;\n return reached&&r==Glucose::lbool((uint8_t)1)?0:61;')
 (B/'driver.cc').write_text(driver)
 commands=[]
 for mode,name in [('COLLECTOR','collect'),('REPLAY','replay')]:
  cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-D'+mode,'-I'+str(S),str(B/'driver.cc'),str(S/'core/Solver.cc'),str(S/'utils/Options.cc'),str(S/'utils/System.cc'),'-lz','-o',str(B/name)]
  r=subprocess.run(cmd,capture_output=True,text=True);(B/(name+'.build.log')).write_text(r.stdout+r.stderr);r.check_returncode();commands.append(cmd)
 shutil.copy('/private/tmp/satfinding-drat-trim',B/'proof-checker')
 files={str(p.relative_to(D)):sha(p) for p in D.rglob('*') if p.is_file() and p.name!='build.json'}
 (B/'build.json').write_text(json.dumps({'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':commands,'files':files},indent=2))
if __name__=='__main__':build()
