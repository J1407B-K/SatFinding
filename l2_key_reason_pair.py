"""Fixed selected alternate 2589; exact target snapshots and native reason split."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from build_native_cdcl import replace_once

OUT=Path('results/l2_key_propagation_reason_split').resolve()
BASE=Path('/private/tmp/satfinding-l2-key-reason-split')
BUILD=Path('/private/tmp/satfinding-l2-key-reason-pair')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def jhash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build():
 root=BUILD/'glucose-3.0';shutil.copytree(BASE/'glucose-3.0',root,dirs_exist_ok=True)
 shutil.copy2(BASE/'pulse.inc',BUILD/'pulse.inc')
 # Reuse only the exact-state dump methods already used for the local gate.
 local=Path('/private/tmp/satfinding-l2-single-conflict/local.inc').read_text()
 local=local[:local.index('// Bounded to previous/key/following')]
 local+='''\nstatic bool ks_alt=false,ks_gate=false,ks_live=false;
 static unsigned long long ks_reads=0;
 void ks_init(const char* dir,bool alt,bool gate){lt_dir=dir;lt_run="local";ks_alt=alt;ks_gate=gate;}
 '''
 (BUILD/'snapshot.inc').write_text(local)
 for rel in ['mtl/Heap.h','core/BoundedQueue.h']:
  shutil.copy2(Path('/private/tmp/satfinding-l2-single-conflict/glucose-3.0')/rel,root/rel)
 h=root/'core/Solver.h';s=h.read_text().replace('void kp_check(Lit,CRef);','CRef kp_check(Lit,CRef);')
 s='#include <string>\n#include <cstdio>\n'+s
 s=replace_once(s,'    void kp_register(CRef);','    void lt_snapshot(const std::string&);\n    void lt_restart_json(FILE*);\n    void kp_register(CRef);');h.write_text(s)
 checker=Path('l2_key_propagation_reason_split.inc').read_text()
 checker=checker.replace('void Solver::kp_check(Lit p,CRef from){','CRef Solver::kp_check(Lit p,CRef from){')
 checker=replace_once(checker,' if(!sp_pending)return;',
  ' if(pw_int(p)==566 && !sp_pending)ks_live=false;\n if(!sp_pending)return from;\n'
  ' lt_snapshot("TARGET_PRE");\n if(ks_gate)throw std::runtime_error("PRE_ENQUEUE_GATE");')
 anchor='fflush(kp_out);\n}\nvoid Solver::kp_read'
 checker=replace_once(checker,anchor,
  'fflush(kp_out);\n if(ks_alt && (best==CRef_Undef || bestid!=2589))throw std::runtime_error("ALT_SELECTION_CHANGED");\n'
  ' ks_live=true;\n return ks_alt?best:from;\n}\nvoid Solver::kp_read')
 checker=replace_once(checker,' if(!sp_disabled || !pw_l2(c))return;',r'''
 if(ks_live && pivot!=lit_Undef && pw_int(pivot)==566){
  ++ks_reads;
  fprintf(kp_out,"{\"event\":\"TARGET_REASON_ANALYSIS_READ\",\"conflict\":%llu,\"pivot\":566,\"l2\":%s,\"read_count\":%llu}\n",(unsigned long long)conflicts,pw_l2(c)?"true":"false",ks_reads);
 }
 if(!sp_disabled || !pw_l2(c))return;''')
 (BUILD/'checker.inc').write_text(checker)
 sp=Path('l2_single_propagation_pulse.inc').read_text()
 # Correct the existing small event ledger's reason labels for the alternate.
 sp=sp.replace('\\"L2_INJECT_C600\\"','\\"%s\\"').replace(',\\"reason_source_id\\":30149','')
 sp=sp.replace('pw_int(p),from);','pw_int(p),pw_l2(ca[from])?"L2_INJECT_C600":"ALT_ALLOC_2589",from);')
 sp=replace_once(sp,' sp_record("FUTURE_DISABLED",p,from);',' sp_record("FUTURE_DISABLED",p,from);\n lt_snapshot("TARGET_POST_DISABLED");')
 (BUILD/'sp.inc').write_text(sp)
 cc=root/'core/Solver.cc';s=cc.read_text()
 s=s.replace(str(BASE/'pulse.inc'),str(BUILD/'pulse.inc'))
 s=s.replace('#include "'+str(Path('l2_single_propagation_pulse.inc').resolve())+'"',
  '#include "'+str(BUILD/'snapshot.inc')+'"\n#include "'+str(BUILD/'sp.inc')+'"')
 s=s.replace(str(Path('l2_key_propagation_reason_split.inc').resolve()),str(BUILD/'checker.inc'))
 s=replace_once(s,'    kp_check(p,from);','    from = kp_check(p,from);');cc.write_text(s)
 driver=(BASE/'driver.cc').read_text().replace('extern void kp_finish();','extern void kp_finish();\nextern void ks_init(const char*,bool,bool);')
 driver=driver.replace('argc != 8','argc != 11').replace('    kp_init(argv[7]);','    kp_init(argv[7]);\n    ks_init(argv[9],atoi(argv[8])!=0,atoi(argv[10])!=0);')
 (BUILD/'driver.cc').write_text(driver)
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'pair_build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'pair_build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'sources':{str(p):sha(p) for p in [Path(__file__),cc,h,BUILD/'sp.inc',BUILD/'checker.inc',BUILD/'snapshot.inc',BUILD/'pulse.inc',BUILD/'driver.cc']}})

def run(name,alt,gate=False):
 d=OUT/name;d.mkdir(exist_ok=False)
 cmd=[str(BUILD/'run'),str(OUT/'A.cnf'),str(d/'proof.drup'),'1000000','ONE_PROP',str(d/'pulse.jsonl'),str(d/'events.jsonl'),str(d/'check.jsonl'),'1' if alt else '0',str(d),'1' if gate else '0']
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(d/'stdout.txt').write_text(r.stdout+r.stderr)
 assert r.returncode==(42 if gate else 0),r.stderr
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')))
 assert stats['status']==('PRE_ENQUEUE_GATE' if gate else 'UNSAT')
 verified=False
 if not gate:
  c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OUT/'A.cnf'),str(d/'proof.drup')],capture_output=True,text=True,timeout=180)
  (d/'proof_check.txt').write_text(c.stdout+c.stderr);assert c.returncode==0 and 's VERIFIED' in c.stdout;verified=True
  with gzip.open(d/'proof.drup.gz','wb') as f:f.write((d/'proof.drup').read_bytes())
 events=[json.loads(x) for x in (d/'events.jsonl').read_text().splitlines()]
 checks=[json.loads(x) for x in (d/'check.jsonl').read_text().splitlines()]
 reads=[e for e in checks if e['event']=='TARGET_REASON_ANALYSIS_READ']
 result={'route':name,'stats':stats,'proof_validation':'VERIFIED' if verified else 'GATE_PREFIX_ONLY','proof_sha256':sha(d/'proof.drup'),'usage':events[-1],'target_reason_analysis_read_count':len(reads),'target_reason_reads':reads,'events':events,'alternate_check':next((c for c in checks if c['event']=='ALTERNATE_CHECK'),None),'command':cmd}
 if not gate:assert all(result['usage'][k]==0 for k in ['post_disable_new_reason','post_disable_new_propagation','post_disable_new_conflict'])
 dump(d/'result.json',result);print(name,json.dumps(stats),flush=True)
 return result,json.loads((d/'local.TARGET_PRE.snapshot.json').read_text())

def main():
 check=json.loads((OUT/'alternate_reason_check.json').read_text());assert check['selected_id']==2589 and check['layout_compatible_count']==1
 dump(OUT/'pair_protocol.json',{'selected_id':2589,'selected_literals':[566,567,565],'selection_frozen_before_pair_outcomes':True,'gate':'Exact equality of all exported pre-enqueue state fields, no exclusions; ALT gate prefix halts before substitution.','sole_solver_change':'from replaced with pre-validated selected CRef before normal enqueue; same immediate future-disable','target_reason_read_tracking':'Only the target 566 assignment lifetime; expires at any later enqueue of 566; count analyze visits with pivot566','no_fallback':True})
 build();base,pre=run('PAIR_ONE_PROP_L2_REASON',False)
 old=json.loads((OUT/'ONE_PROP_L2_REASON.result.json').read_text())
 assert all(base['stats'][k]==v for k,v in old['stats'].items() if k!='seconds')
 gate,gpre=run('ALT_PRE_ENQUEUE_GATE',True,True)
 diffs=[k for k in pre if pre[k]!=gpre[k]]
 assert not diffs,('PRE_ENQUEUE_STATE_DIVERGED',diffs)
 alt,apre=run('ONE_PROP_ALT_REASON',True)
 assert pre==apre
 posts=[json.loads((OUT/name/'local.TARGET_POST_DISABLED.snapshot.json').read_text()) for name in ['PAIR_ONE_PROP_L2_REASON','ONE_PROP_ALT_REASON']]
 postdiff=[k for k in posts[0] if posts[0][k]!=posts[1][k]]
 assert postdiff==['reasons'],postdiff
 changed=[i+1 for i,(a,b) in enumerate(zip(posts[0]['reasons'],posts[1]['reasons'])) if a!=b];assert changed==[566]
 assert base['events'][0]==alt['events'][0]
 for r in [base,alt]:
  pree,post,disabled=r['events'][:3]
  assert pree['trail']+[566]==post['trail']==disabled['trail']
  assert disabled['global_event']==post['global_event']+1==pree['global_event']+2
 s=json.loads((OUT/'summary.json').read_text());s.update(stage2_status='COMPLETED',alternate_route_executed=True,fallback_pending=False,routes=[base,alt],state_validation={'all_exported_pre_fields_exact_equal':True,'pre_sha256':jhash(pre),'post_different_fields':postdiff,'post_different_reason_variables':changed,'enqueue_literal_and_event_timing_equal':True,'same_future_disable':True},checker_sha256=sha('/private/tmp/satfinding-drat-trim'))
 dump(OUT/'summary.json',s)

if __name__=='__main__':main()
