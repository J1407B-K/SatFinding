from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parent
for mode,binary in [('COLLECTOR','canonical_collector_native'),('REPLAY','frozen_replay_native')]:
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-D'+mode,'-I'+str(root/'glucose-3.0'),str(root/'driver.cc'),str(root/'glucose-3.0/core/Solver.cc'),str(root/'glucose-3.0/utils/Options.cc'),str(root/'glucose-3.0/utils/System.cc'),'-lz','-o',str(root/binary)]
 p=subprocess.run(cmd,capture_output=True,text=True);(root/(mode+'.build.log')).write_text(p.stdout+p.stderr);print(mode,p.returncode,p.stderr[-2000:],flush=True);p.check_returncode()
