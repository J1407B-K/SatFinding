"""One fixed early propagation before any nonbinary watcher at the key trigger."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/original_clause_early_prop').resolve()
BASE=Path('/private/tmp/satfinding-l2-key-reason-pair')
BUILD=Path('/private/tmp/satfinding-original-early-prop')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def jhash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 for name in ['pulse.inc','snapshot.inc','checker.inc']:
  shutil.copy2(BASE/name,BUILD/name)
 # BEFORE_PROP uses the earlier explicit safe-removal path, which must also
 # retire its observer ID before native GC; no solver state is changed here.
 p=BUILD/'pulse.inc';s=p.read_text();s=replace_once(s,'clauses.pop();c.mark(1);','clauses.pop();kp_forget(target);c.mark(1);');p.write_text(s)
 p=BUILD/'checker.inc';p.write_text(p.read_text()+'\nvoid Solver::kp_forget(CRef cr){kp_ids.erase(cr);}\n')
 sp=(BASE/'sp.inc').read_text()
 sp='static bool ep_original=false,ep_armed=false,ep_done=false;\n'+sp
 sp=replace_once(sp,' sp_one=std::string(route)=="ONE_PROP";',
  ' ep_original=std::string(route)=="ORIGINAL_EARLY_PROP";\n sp_one=ep_original || std::string(route)=="ONE_PROP";')
 sp=replace_once(sp,' if(!sp_one || conflicts!=655 || !l2 || pw_int(p)!=566)return;',
  ' if(!sp_one || conflicts!=655 || !(l2 || ep_armed) || pw_int(p)!=566)return;')
 sp=sp.replace('ALT_ALLOC_2589','ORIGINAL_ALLOC_2589');(BUILD/'sp.inc').write_text(sp)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    bool sp_skip(CRef);','    void kp_forget(CRef);\n    void ep_before_watch(Lit);\n    bool sp_skip(CRef);');h.write_text(s)
 ep=r'''
// Execute at a fixed propagation frontier, before reading any nonbinary watcher.
// Scheduling predicate does not read L2, its watcher, or its unit condition.
void Solver::ep_before_watch(Lit trigger){
 if(!ep_original || ep_done || conflicts!=655 || decisions!=827 ||
    sp_enqueues!=97810 || qhead!=239 || pw_int(trigger)!=507)return;
 CRef original=CRef_Undef;
 for(int i=0;i<clauses.size();++i)if(kp_ids.at(clauses[i])==2589)original=clauses[i];
 if(original==CRef_Undef)throw std::runtime_error("UNSUPPORTED_EARLY_PROP_INTERVENTION");
 const Clause& c=ca[original];Lit unit=mkLit(565,false);
 if(c.learnt() || c.mark()!=0 || c.reloced() || c.size()!=3 ||
    pw_int(c[0])!=566 || pw_int(c[1])!=567 || pw_int(c[2])!=565 ||
    value(unit)!=l_Undef || value(c[1])!=l_False || value(c[2])!=l_False)
  throw std::runtime_error("UNSUPPORTED_EARLY_PROP_INTERVENTION");
 fprintf(kp_out,"{\"event\":\"ORIGINAL_UNIT_AUDIT\",\"hook\":\"AFTER_BINARY_BEFORE_ANY_NONBINARY_WATCH\",\"completed_conflicts\":%llu,\"decision\":%llu,\"level\":%d,\"trigger\":507,\"qhead\":%d,\"prior_global_enqueue\":%llu,\"clause_id\":2589,\"cref\":%u,\"literals\":[566,567,565],\"values\":[\"UNASSIGNED\",\"FALSE\",\"FALSE\"],\"unit_verified\":true,\"l2_watcher_evaluated_for_this_trigger\":false}\n",(unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),qhead,sp_enqueues,original);fflush(kp_out);
 ep_done=true;ep_armed=true;
 uncheckedEnqueue(unit,original);
 ep_armed=false;
}
'''
 (BUILD/'early.inc').write_text(ep)
 cc=root/'core/Solver.cc';s=cc.read_text()
 for name in ['pulse.inc','snapshot.inc','sp.inc','checker.inc']:s=s.replace(str(BASE/name),str(BUILD/name))
 anchor='#include "'+str(BUILD/'checker.inc')+'"';s=replace_once(s,anchor,anchor+'\n#include "'+str(BUILD/'early.inc')+'"')
 anchor='        for (i = j = (Watcher*)ws, end = i + ws.size();  i != end;){'
 s=replace_once(s,anchor,'        ep_before_watch(p);\n'+anchor)
 s=replace_once(s,'    from = kp_check(p,from);',
  '    if(ep_armed){\n        lt_snapshot("TARGET_PRE");\n        if(ks_gate)throw std::runtime_error("PRE_ENQUEUE_GATE");\n        ks_live=true;\n    }else from = kp_check(p,from);')
 cc.write_text(s)
 shutil.copy2(BASE/'driver.cc',BUILD/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),cc,h,BUILD/'pulse.inc',BUILD/'snapshot.inc',BUILD/'checker.inc',BUILD/'sp.inc',BUILD/'early.inc',BUILD/'driver.cc']}})

def run(name,tag,gate=False):
 d=OUT/name;d.mkdir(exist_ok=False)
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(d/'proof.drup'),'1000000',tag,str(d/'pulse.jsonl'),str(d/'events.jsonl'),str(d/'audit.jsonl'),'0',str(d),'1' if gate else '0']
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(d/'stdout.txt').write_text(r.stdout+r.stderr)
 assert r.returncode==(42 if gate else 0),r.stderr
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')))
 assert stats['status']==('PRE_ENQUEUE_GATE' if gate else 'UNSAT')
 verified=False
 if not gate:
  check=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(d/'proof.drup')],capture_output=True,text=True,timeout=180)
  (d/'proof_check.txt').write_text(check.stdout+check.stderr)
  assert check.returncode==0 and 's VERIFIED' in check.stdout;verified=True
  with gzip.open(d/'proof.drup.gz','wb') as f:f.write((d/'proof.drup').read_bytes())
 events=[json.loads(x) for x in (d/'events.jsonl').read_text().splitlines()]
 audit=[json.loads(x) for x in (d/'audit.jsonl').read_text().splitlines()]
 result={'route':name,'stats':stats,'proof_validation':'VERIFIED' if verified else 'GATE_PREFIX_ONLY','proof_sha256':sha(d/'proof.drup'),'usage':events[-1],'command':cmd}
 dump(d/'result.json',result);print(name,json.dumps(stats),flush=True)
 snap=d/'local.TARGET_PRE.snapshot.json'
 return result,{'events':events,'audit':audit,'pre_state':json.loads(snap.read_text()) if snap.exists() else None}

def main():
 OUT.mkdir(exist_ok=False);shutil.copy2('results/l2_single_propagation_pulse/A.cnf',OUT/'A.cnf')
 dump(OUT/'protocol.json',{'routes':['BEFORE_PROP_BASELINE','L2_ONE_PROP','ORIGINAL_EARLY_PROP'],'source':'fixed case, unchanged C600 L2 injection and previous five propagations','early_hook':'After binary propagation of trigger507, before the entire nonbinary watcher loop; fixed c655/d827/qhead239/global enqueue97810 frontier. No L2 clause/watcher evaluation is consulted to schedule the event.','unit_source':'only original allocation ID2589; exact existing layout [566,567,565] and values verified','enqueue':'native uncheckedEnqueue(566,#2589); no reason replacement from L2','disable':'same immediate future-disabled flag; same untouched clause/watch objects','gate':'exact equality of every exported pre-state field vs L2_ONE_PROP; if mismatch stop as UNSUPPORTED_EARLY_PROP_INTERVENTION, never adjust watches/qhead/order','interpretation':{'near174k':'supports timing/order trigger conditional on existing fixed-case prefix','near345k':'L2 execution details remain unisolated','intermediate':'partial mediation','unsupported':'stop without attribution'}})
 build();before,ba=run('BEFORE_PROP_BASELINE','REMOVE@655')
 old=json.loads(Path('results/l2_single_propagation_pulse/BEFORE_PROP.result.json').read_text())['stats'];assert all(before['stats'][k]==v for k,v in old.items() if k!='seconds')
 baseline,la=run('L2_ONE_PROP','ONE_PROP')
 old=json.loads(Path('results/l2_single_propagation_pulse/ONE_PROP.result.json').read_text())['stats'];assert all(baseline['stats'][k]==v for k,v in old.items() if k!='seconds')
 gate,ga=run('ORIGINAL_PRE_STATE_GATE','ORIGINAL_EARLY_PROP',True)
 diffs=[k for k in la['pre_state'] if la['pre_state'][k]!=ga['pre_state'][k]]
 summary={'routes':[before,baseline],'controls_exact_match':True,'pre_state_gate':{'equal':not diffs,'different_fields':diffs,'baseline_sha256':jhash(la['pre_state']),'original_sha256':jhash(ga['pre_state'])},'gate_prefix':gate}
 audits={'BEFORE_PROP_BASELINE':ba,'L2_ONE_PROP':la,'ORIGINAL_PRE_STATE_GATE':ga}
 if diffs:
  summary['status']='UNSUPPORTED_EARLY_PROP_INTERVENTION'
 else:
  original,oa=run('ORIGINAL_EARLY_PROP','ORIGINAL_EARLY_PROP');assert oa['pre_state']==la['pre_state']
  for r in [baseline,original]:assert all(r['usage'][k]==0 for k in ['post_disable_new_reason','post_disable_new_propagation','post_disable_new_conflict'])
  assert original['usage']['target_count']==1 and original['usage']['disabled']
  a,b=la['events'][:3],oa['events'][:3]
  assert [e['global_event'] for e in a]==[e['global_event'] for e in b]
  assert [e['trail'] for e in a]==[e['trail'] for e in b]
  assert b[0]['reason_clause_id']=='ORIGINAL_ALLOC_2589'
  summary.update(status='COMPLETED',routes=[before,baseline,original],same_literal_and_event_timing=True)
  audits['ORIGINAL_EARLY_PROP']=oa
 dump(OUT/'summary.json',summary);dump(OUT/'event_audit.json',audits)
 print(json.dumps(summary['pre_state_gate']),summary['status'])

if __name__=='__main__':main()
