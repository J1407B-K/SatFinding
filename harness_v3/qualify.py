"""Infrastructure coverage orchestration. No temporal scientific interpretation."""
import sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.collect import collect
from harness_v3.routes import freeze_routes,execute
from harness_v3.audit import pre_audit,post_audit
from harness_v3.finalize import finalize

def old_lock_check():
 q=ROOT/'results/harness_qualification_v2';lock=load(q/'HARNESS_LOCK.json');assert sha(q/'HARNESS_LOCK.json')==(q/'HARNESS_LOCK.sha256').read_text().strip()
 assert sha(q/'build_freeze.json')==lock['build_freeze_sha256'];b=load(q/'build_freeze.json')
 for name,h in b['source_hashes'].items():assert sha(ROOT/name)==h
 for name,h in b['binaries'].items():assert sha(ROOT/name)==h
 for name,h in lock['evidence'].items():assert sha(q/name)==h
 return sha(q/'HARNESS_LOCK.json')

def main(attempt):
 out=ROOT/'results/harness_qualification_v3';d=out/attempt;d.mkdir(parents=True,exist_ok=False)
 previous=old_lock_check()
 # Preserve the full function bytes, not merely a signature or a hash-format label.
 old=(ROOT/'harness_v2/observer.inc').read_text();new=(HERE/'observer.inc').read_text()
 identity=lambda s:s[s.index('std::string Solver::canonical_logical()'):s.index('void Solver::hc_boundary()')]
 assert identity(old)==identity(new)
 for relative in ['mtl/Heap.h','core/BoundedQueue.h']:
  assert (ROOT/'harness_v2/glucose-3.0'/relative).read_bytes()==(HERE/'glucose-3.0'/relative).read_bytes()
 # Same semantic action block is compiled into the replay version.
 action=lambda s:s[s.index(' if(aid){'):s.index('\n#endif',s.index(' if(aid){'))]
 assert action(old)==action(new)
 old_features=(ROOT/'harness_v2/qualify.py').read_text().split('def features(raw):',1)[1].split('\ndef main():',1)[0]
 assert (HERE/'features.py').read_text().split('def features(raw):',1)[1]==old_features

 native=(HERE/'frozen_replay_native').read_bytes()
 for forbidden in [b'COLLECTION_COMPLETE',b'eligible_ids',b'/actions.json',b'/temporal_raw.json',b'COLLECTION_PLAN']:assert forbidden not in native
 files=[p for p in HERE.rglob('*') if p.is_file() and p.suffix in ['.py','.cc','.h','.inc','.md']]
 files+=[HERE/'canonical_collector_native',HERE/'frozen_replay_native',ROOT/'prospective_temporal_schema.py',ROOT/'temporal_reference.py',PROTOCOL]
 checker=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['checker'];assert sha(checker['path'])==checker['sha256']
 freeze(d/'build_manifest.json',{'time':stamp(),'components':{str(p.relative_to(ROOT)):sha(p) for p in files},'checker':checker,'previous_lock_sha256':previous,'identity_semantics_unchanged':True,'early_enqueue_semantics_unchanged':True})
 inputs=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['inputs']
 plan={'purpose':'V3_CAPABILITY_QUALIFICATION_ONLY','collections':[{'target':target,'input':inputs[target]['path'],'input_sha256':inputs[target]['sha256'],'requested_state_count':2,'K':6,'checkpoint_rule':{'kind':'first_eligible_per_window','windows':[[200,299],[400,499]],'minimum_legal_count':6}} for target in ['T8','T10']]}
 freeze(d/'collection_plan.json',plan)
 o=collect(d/'collection_plan.json',d/'cohort',d/'build_manifest.json')
 expected=freeze_routes(o);pre=pre_audit(o)
 assert len(pre['states'])==4 and all(sum(s['target']==t for s in pre['states'])>=2 for t in ['T8','T10'])
 assert any(s['selected_count']==6 for s in pre['states'])
 execute(o)
 audit,rows=post_audit(o);freeze(o/'route_identity_audit.json',audit)
 actions,states=finalize(o,d/'label_dry_run')
 assert any(r['action_rank']==6 and r['action_verified'] for r in rows)
 assert all(len({r['package_id'] for r in rows if r['target']==t})>=2 for t in ['T8','T10'])
 assert actions==audit['action_routes'] and states==len(pre['states'])
 assert old_lock_check()==previous
 summary={'HARNESS_V3_CAPABILITY_QUALIFIED':True,'packages':states,'targets':dict(collections.Counter(s['target'] for s in pre['states'])),'frozen_actions':actions,'rank_6_passed':sum(r['action_rank']==6 for r in rows),'manifest_driven_routes':True,'generic_auditor_finalizer':True,'generic_label_dry_run':True,'qualification_labels_excluded_from_science':True,'audit':audit}
 dump(d/'CAPABILITY_QUALIFICATION.json',summary)
 lock={'HARNESS_V3_CAPABILITY_QUALIFIED':True,'time':stamp(),'successful_attempt':attempt,'scientific_temporal_cohort_run':False,'summary':{k:v for k,v in summary.items() if k!='audit'},'components':frozen(d/'build_manifest.json')['components'],'checker':checker,'canonical_identity_semantics':'unchanged-v2','canonical_schema_sha256':__import__('prospective_temporal_schema').feature_schema_sha256(),'evidence':{str(p.relative_to(out)):sha(p) for p in d.rglob('*') if p.is_file()},'previous_lock_sha256':previous}
 dump(out/'HARNESS_LOCK_V3.json',lock);(out/'HARNESS_LOCK_V3.sha256').write_text(sha(out/'HARNESS_LOCK_V3.json')+'\n')
 print(__import__('json').dumps({k:v for k,v in summary.items() if k!='audit'}),flush=True)
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--attempt',default='attempt_001');a=ap.parse_args();main(a.attempt)
