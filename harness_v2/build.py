from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parent
cc=root/'glucose-3.0/core/Solver.cc'
s=cc.read_text();s=s.replace('/Users/kqs-mac/Go/GoProjects/SatFinding/results/prospective_micro_rollout/source/prospective_micro_rollout.inc',str(root/'observer.inc'));cc.write_text(s)
h=root/'glucose-3.0/core/Solver.h';s=h.read_text();s=s.replace('    unsigned long long hc_canonical_state_hash();','    std::string canonical_logical();\n    std::string canonical_heuristic();');s=s.replace('#include "mtl/Vec.h"','#include <string>\n#include "mtl/Vec.h"');h.write_text(s)
h=root/'glucose-3.0/mtl/Heap.h';s=h.read_text();anchor='    Heap(const Comp& c) : lt(c) { }';extra='''    std::vector<int> semantic_order() const { Heap copy(lt); heap.copyTo(copy.heap); indices.copyTo(copy.indices); std::vector<int> out; while(!copy.empty()) out.push_back(copy.removeMin()+1); return out; }
''';s=s.replace(anchor,extra+anchor) if 'semantic_order' not in s else s;s='#include <vector>\n'+s if '#include <vector>' not in s else s;h.write_text(s)
h=root/'glucose-3.0/core/BoundedQueue.h';s=h.read_text();s=s.replace('public:\n','public:\n std::vector<unsigned long long> semantic_values() const {std::vector<unsigned long long> out; for(int i=0;i<queuesize;i++)out.push_back(elems[(last+i)%maxsize]);return out;}\n') if 'semantic_values' not in s else s;s='#include <vector>\n'+s if '#include <vector>' not in s else s;h.write_text(s)
for mode,binary in [('COLLECTOR','canonical_collector_native'),('REPLAY','frozen_replay_native')]:
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-D'+mode,'-I'+str(root/'glucose-3.0'),str(root.parent/'frozen_replay_driver.cc') if mode=='REPLAY' else str(root/'driver.cc'),str(cc),str(root/'glucose-3.0/utils/Options.cc'),str(root/'glucose-3.0/utils/System.cc'),'-lz','-o',str(root.parent/binary)]
 p=subprocess.run(cmd,capture_output=True,text=True);(root/(mode+'.build.log')).write_text(p.stdout+p.stderr);print(mode,p.returncode,p.stderr[-2500:]);p.check_returncode()
