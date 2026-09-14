"""Frozen C600 L2 pulse grid, using the existing injection/removal operations."""
import csv
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/l2_pulse_window').resolve()
BASE=Path('/private/tmp/satfinding-native-cdcl')
BUILD=Path('/private/tmp/satfinding-l2-pulse-window')
POINTS=[601,605,610,620,630,640,645,650,655,657,660]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 # Retain the prior injection body verbatim except trace output and names.
 old=Path('l2_delayed_amplification.inc').read_text()
 start=old.index('int olddl=decisionLevel();')
 end=old.index('\nLit Solver::da_pick()')
 fn='CRef Solver::pw_inject(){\n '+old[start:end]
 lo=fn.index(' ++lt_global;gzprintf(');hi=fn.index('\n if(assertunit)',lo)
 fn=fn[:lo]+''' fprintf(pw_log,"{\\"event\\":\\"INJECT\\",\\"conflict\\":%llu,\\"decision\\":%llu,\\"nonfalse_before\\":%d,\\"dl_before\\":%d,\\"dl_after\\":%d,\\"unit_assert\\":%d,\\"conflict_trigger\\":%d,\\"watch_order\\":[%d,%d,%d]}\\n",(unsigned long long)conflicts,(unsigned long long)decisions,nf,olddl,decisionLevel(),assertunit,nf==0,pw_int(ls[0]),pw_int(ls[1]),pw_int(ls[2]));'''+fn[hi:]
 fn=fn.replace(' lt_snapshot("injection_after");','').replace('exit(31);','throw std::runtime_error("ABORT_INJECTION_UNIT");')
 (BUILD/'pulse.inc').write_text(Path('l2_pulse_window.inc').read_text()+'\n'+fn)
 h=root/'core/Solver.h';s=h.read_text()
 s=replace_once(s,'    void     uncheckedEnqueue',
  '    CRef pw_boundary();\n    CRef pw_inject();\n    void pw_delete();\n'
  '    void pw_enqueue(Lit,CRef);\n    void pw_use(const Clause&,int);\n    void     uncheckedEnqueue')
 h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text()
 s=replace_once(s,'using namespace Glucose;','using namespace Glucose;\n#include "'+str(BUILD/'pulse.inc')+'"')
 s=replace_once(s,'        CRef confl = propagate();','        CRef confl = pw_boundary();\n        if(confl==CRef_Undef)confl=propagate();')
 s=replace_once(s,'    assigns[var(p)] = lbool(!sign(p));','    pw_enqueue(p,from);\n    assigns[var(p)] = lbool(!sign(p));')
 s=replace_once(s,'        if (p != lit_Undef) SF_COUNT(sf_analysis);','        pw_use(c,0);\n        if (p != lit_Undef) SF_COUNT(sf_analysis);')
 s=s.replace('        SF_COUNT(sf_redundancy);','        pw_use(c,1);\n        SF_COUNT(sf_redundancy);')
 s=replace_once(s,'\t  conflicts++; conflictC++;conflictsRestarts++;','\t  conflicts++; conflictC++;conflictsRestarts++;\n          pw_use(ca[confl],2);')
 cc.write_text(s)
 s=Path('native_cdcl.cc').read_text().replace('int main(int argc, char **argv) {',
  '#include <stdexcept>\n#include <string>\nextern void pw_init(const char*,const char*);\nextern void pw_finish();\nint main(int argc, char **argv) {')
 s=s.replace('argc != 4','argc != 6').replace('    auto start =','    pw_init(argv[4],argv[5]);\n    auto start =')
 s=s.replace('    Glucose::lbool result = solver.solveLimited(assumptions);',
  '    Glucose::lbool result;\n    std::string failure;\n    try { result=solver.solveLimited(assumptions); }\n    catch(const std::runtime_error& e) { failure=e.what(); }')
 s=s.replace('    printf("{','    if(!failure.empty()) status=failure.c_str();\n    printf("{')
 s=s.replace('    return 0;','    pw_finish();\n    return failure.empty()?0:42;')
 (BUILD/'driver.cc').write_text(s)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 p=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(p.stdout+p.stderr);p.check_returncode()
 patches=[]
 for rel in ['core/Solver.cc','core/Solver.h']:
  patches+=list(difflib.unified_diff((BASE/'glucose-3.0'/rel).read_text().splitlines(True),(root/rel).read_text().splitlines(True),fromfile='baseline/'+rel,tofile='pulse/'+rel))
 (OUT/'solver.patch').write_text(''.join(patches))
 shutil.copy2(BUILD/'pulse.inc',OUT/'compiled_pulse.inc')
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('l2_pulse_window.inc'),Path('l2_delayed_amplification.inc'),Path('decision828_l2_remove.py'),BUILD/'pulse.inc',cc,h,BUILD/'driver.cc']},'input_sha256':sha(OUT/'A.cnf'),'base_build':json.loads((BASE/'build.json').read_text())})

def run(route):
 proof=OUT/(route+'.drup');ledger=OUT/(route+'.events.jsonl')
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(proof),'1000000',route,str(ledger)]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
 (OUT/(route+'.stdout.txt')).write_text(p.stdout+p.stderr)
 if p.returncode not in (0,42):raise RuntimeError(p.stderr)
 stats=json.loads(next(x for x in reversed(p.stdout.splitlines()) if x.startswith('{')))
 events=[json.loads(x) for x in ledger.read_text().splitlines()]
 verified=False
 if stats['status']=='UNSAT':
  check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(proof)],capture_output=True,text=True,timeout=180)
  (OUT/(route+'.proof_check.txt')).write_text(check.stdout+check.stderr)
  verified=check.returncode==0 and 's VERIFIED' in check.stdout
  if not verified:raise RuntimeError('Independent proof failed: '+route)
 with gzip.open(OUT/(route+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
 result={'route':route,'stats':stats,'proof_verified':verified,'proof_validation_status':'VERIFIED' if verified else 'INCOMPLETE_NO_UNSAT_PROOF','proof_sha256':sha(proof),'input_sha256':sha(OUT/'A.cnf'),'l2_uses':events[-1],'events':events,'command':cmd}
 dump(OUT/(route+'.result.json'),result)
 print(route,json.dumps(stats),'proof',verified,'uses',json.dumps(events[-1]),flush=True)
 return result

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 assert not (OUT/'protocol.json').exists(),'Frozen experiment already exists'
 data=json.loads(Path('results/gold_mechanism/inputs.json').read_text())
 cnf=data['cnf']+data['templates']+[data['gold']['24458']]
 (OUT/'A.cnf').write_text(f'p cnf {max(abs(x) for c in cnf for x in c)} {len(cnf)}\n'+''.join(' '.join(map(str,c))+' 0\n' for c in cnf))
 dump(OUT/'protocol.json',{'remove_conflicts':POINTS,'controls':['A_NORMAL','B_DELAY600_KEEP'],'injection_conflict':600,'L2':[-507,565,566],'boundary':'First search-loop entry after complete processing of conflict C, before next propagation; same as prior delayed injection','injection':'Prior da_inject state-changing body unchanged','removal':'Prior safe strict detach, stable clause-vector erase, proof deletion, mark/free; no active reason refs allowed; no backtrack, reason rewrite, reset or checkpoint shift','safety':'Abort an unsafe route before deletion; do not move or omit checkpoints. Old all-literals-unassigned checkpoint assertion is recorded as values here; deletion requires the semantic guard of no active reasons/locked clause.','counts':{'reason_use':'successful enqueue with reason=L2 including insertion assertion','propagation':'L2 enqueues from native BCP, excludes insertion assertion','conflict_analysis_use':'visits to L2 in analyze, including initial conflict clause','candidate_identity':'original nonlearned exact L2 content'},'interpretation':{'transition':'Find earliest sampled short route and adjacent A-like/B-like checkpoints; report nonmonotonicity without fitting a continuous trend','all_short':'formation earlier than first C601 removal boundary','all_long':'stop and flag delayed600/removal semantics for review','highly_nonmonotonic':'do not define one formation window'},'no_adaptive_checkpoints':True})
 build();runs=[]
 oldA=json.loads(Path('results/l1_l2_latent/natural_runs.json').read_text())['A']
 oldB=json.loads(Path('results/l2_delayed_amplification/I600.result.json').read_text())['stats']
 for name,expected in [('A_NORMAL',oldA),('B_DELAY600_KEEP',oldB)]:
  r=run(name);runs.append(r)
  assert all(r['stats'][k]==v for k,v in expected.items() if k!='seconds'),name+' baseline mismatch'
 for point in POINTS:
  runs.append(run('REMOVE@'+str(point)))
 summary={'protocol':'protocol.json','controls_exact_match':True,'routes':runs,'checker_sha256':sha('/private/tmp/satfinding-drat-trim'),'A_reference_ops':345592,'B_reference_ops':169858}
 dump(OUT/'pulse_summary.json',summary)
 fields=['route','ops','conflicts','decisions','propagations','status','proof_verified','reason_use_count','conflict_analysis_use_count','propagation_count']
 with (OUT/'routes.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
  for r in runs:
   writer.writerow(dict(route=r['route'],ops=r['stats']['analysis_resolution_steps'],**{k:r['stats'][k] for k in ['conflicts','decisions','propagations','status']},proof_verified=r['proof_verified'],**{k:r['l2_uses'][k] for k in fields[-3:]}))

if __name__=='__main__':main()
