"""Only BEFORE_PROP and ONE_PROP; no full trace or follow-up experiments."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import difflib
from build_native_cdcl import replace_once

OUT=Path('results/l2_single_propagation_pulse').resolve()
BASE=Path('/private/tmp/satfinding-l2-pulse-window')
BUILD=Path('/private/tmp/satfinding-l2-single-propagation')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 shutil.copy2(BASE/'pulse.inc',BUILD/'pulse.inc')
 h=root/'core/Solver.h';s=h.read_text()
 s=replace_once(s,'    CRef pw_boundary();',
  '    bool sp_skip(CRef);\n    void sp_use(const Clause&,int);\n'
  '    void sp_pre(Lit,CRef);\n    void sp_post(Lit,CRef);\n'
  '    void sp_record(const char*,Lit,CRef);\n    CRef pw_boundary();')
 h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text()
 s=replace_once(s,'#include "'+str(BASE/'pulse.inc')+'"',
  '#include "'+str(BUILD/'pulse.inc')+'"\n#include "'+str(Path('l2_single_propagation_pulse.inc').resolve())+'"')
 # Guard BEFORE blocker/false-literal/representation access and before every
 # binary trigger too. Copy the skipped watcher unchanged in native order.
 s=replace_once(s,'            Lit blocker = i->blocker;',
  '            if(sp_skip(i->cref)){ *j++ = *i++; continue; }\n            Lit blocker = i->blocker;')
 s=replace_once(s,'\t  Lit imp = wbin[k].blocker;',
  '\t  if(sp_skip(wbin[k].cref))continue;\n\t  Lit imp = wbin[k].blocker;')
 s=replace_once(s,'    pw_enqueue(p,from);','    sp_pre(p,from);\n    pw_enqueue(p,from);')
 s=replace_once(s,'    trail.push_(p);','    trail.push_(p);\n    sp_post(p,from);')
 for kind in [0,1]:s=s.replace(f'pw_use(c,{kind});',f'sp_use(c,{kind});\n        pw_use(c,{kind});')
 s=replace_once(s,'          pw_use(ca[confl],2);','          sp_use(ca[confl],2);\n          pw_use(ca[confl],2);')
 cc.write_text(s)
 driver=(BASE/'driver.cc').read_text().replace('extern void pw_finish();',
  'extern void pw_finish();\nextern void sp_init(const char*,const char*);\nextern void sp_finish();')
 driver=driver.replace('argc != 6','argc != 7').replace('    pw_init(argv[4],argv[5]);',
  '    pw_init(argv[4],argv[5]);\n    sp_init(argv[4],argv[6]);')
 driver=driver.replace('    pw_finish();','    pw_finish();\n    sp_finish();')
 (BUILD/'driver.cc').write_text(driver)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 changes=[]
 for rel in ['core/Solver.cc','core/Solver.h']:
  changes+=list(difflib.unified_diff((BASE/'glucose-3.0'/rel).read_text().splitlines(True),(root/rel).read_text().splitlines(True),fromfile='pulse/'+rel,tofile='single_prop/'+rel))
 (OUT/'solver.patch').write_text(''.join(changes))
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),Path('l2_single_propagation_pulse.inc'),BUILD/'pulse.inc',cc,h,BUILD/'driver.cc']}})

def run(name):
 tag='REMOVE@655' if name=='BEFORE_PROP' else name
 proof=OUT/(name+'.drup')
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(proof),'1000000',tag,str(OUT/(name+'.pulse.jsonl')),str(OUT/(name+'.events.jsonl'))]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
 (OUT/(name+'.stdout.txt')).write_text(r.stdout+r.stderr)
 if r.returncode not in (0,42):raise RuntimeError(r.stderr)
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')))
 events=[json.loads(x) for x in (OUT/(name+'.events.jsonl')).read_text().splitlines()]
 for e in events:
  if 'trail' in e:
   e['trail_sha256']=hashlib.sha256((' '.join(map(str,e['trail']))+'\n').encode()).hexdigest()
   e['reason_clause_sha256']=hashlib.sha256((' '.join(map(str,sorted(e['reason_literals'])))+' 0\n').encode()).hexdigest()
 result={'route':name,'stats':stats,'usage':events[-1],'proof_validation':'INCOMPLETE','command':cmd}
 if stats['status']=='UNSAT':
  check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(proof)],capture_output=True,text=True,timeout=180)
  (OUT/(name+'.proof_check.txt')).write_text(check.stdout+check.stderr)
  assert check.returncode==0 and 's VERIFIED' in check.stdout
  result.update(proof_validation='VERIFIED',proof_sha256=sha(proof),input_sha256=sha(OUT/'A.cnf'))
 with gzip.open(OUT/(name+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
 dump(OUT/(name+'.result.json'),result)
 print(name,json.dumps(result),flush=True)
 return result,events

def main():
 OUT.mkdir(exist_ok=False)
 shutil.copy2('results/l2_pulse_window/A.cnf',OUT/'A.cnf')
 dump(OUT/'protocol.json',{'routes':['BEFORE_PROP','ONE_PROP'],'injection':'identical existing C600 pulse injection','before_prop':'identical REMOVE@655 strict safe removal','target':{'completed_conflicts':655,'next_conflict':656,'decision':827,'level':12,'literal':566,'reason':[-507,565,566],'ordinal_in_window':1},'disable':'Immediately after completed uncheckedEnqueue, set future-disabled flag; skip both binary/nonbinary L2 watcher triggers before evaluation; retain clause, watch entries, order and existing reasons. No detach/free or proof deletion at disable.','global_event_definition':'Monotonic counter of every pre-enqueue, post-enqueue, and disable transition; other operations do not advance this task-local clock.','identity':'L2_INJECT_C600 logical clause identity; source ID 30149; CRef recorded at event; content-based guard survives native GC','interpretation':{'near_174k':'One target propagation with its existing reason permitted to be read is sufficient in this fixed case','near_345k':'First visible divergence is not sufficient; later interaction remains necessary','intermediate':'partial mediation','unsafe':'UNSUPPORTED_SAFE_DISABLE; no conclusion'},'validation':'BEFORE_PROP exact frozen non-time counters; ONE_PROP target exactly once, post-disable new reason/propagation/conflict zero, both independent proofs VERIFIED','no_other_experiments':True})
 build();before,be=run('BEFORE_PROP')
 old=json.loads(Path('results/l2_pulse_window/REMOVE@655.result.json').read_text())['stats']
 assert all(before['stats'][k]==v for k,v in old.items() if k!='seconds')
 one,oe=run('ONE_PROP')
 if one['stats']['status']=='UNSAT':
  assert one['usage']['target_count']==1 and one['usage']['disabled']
  assert all(one['usage'][k]==0 for k in ['post_disable_new_reason','post_disable_new_propagation','post_disable_new_conflict'])
  pre,post,disable=oe[:3]
  assert [e['event'] for e in oe[:3]]==['TARGET_ENQUEUE_PRE','TARGET_ENQUEUE_POST','FUTURE_DISABLED']
  assert pre['trail']+[566]==post['trail']==disable['trail']
  assert post['reason_pointer_matches'] and disable['reason_pointer_matches']
  assert pre['global_event']+1==post['global_event'] and post['global_event']+1==disable['global_event']
 dump(OUT/'event_ledger.json',{'BEFORE_PROP':be,'ONE_PROP':oe,'hash_encoding':{'trail_sha256':'signed DIMACS trail joined by spaces plus newline','reason_clause_sha256':'sorted signed DIMACS literals joined by spaces plus " 0\\n"'}})
 dump(OUT/'summary.json',{'routes':[before,one],'before_prop_exact_baseline_match':True,'checker_sha256':sha('/private/tmp/satfinding-drat-trim'),'protocol':'protocol.json'})

if __name__=='__main__':main()
