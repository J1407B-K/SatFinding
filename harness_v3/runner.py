#!/usr/bin/env python3
"""Frozen package replay only. Never invokes a collector or enumerates actions."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import ROOT,HERE,PROTOCOL,sha,load,dump,route_id
from prospective_temporal_schema import feature_schema_sha256
def verify(p):
 m=load(p/'package_manifest.json');assert sha(p/'package_manifest.json')==(p/'package_manifest.sha256').read_text().strip(),'MANIFEST_HASH'
 required={'state.json','actions.json','temporal_raw.json','temporal_features.json','logical.txt','heuristic.txt','input.cnf','protocol.json','feature_schema.json','prefix_counters.json','collection_plan.json'}
 assert set(m['files'])==required,'ARTIFACT_SET'
 assert set(x.name for x in p.iterdir())==required|{'package_manifest.json','package_manifest.sha256'},'PACKAGE_EXTRA'
 for n,h in m['files'].items():assert sha(p/n)==h,('ARTIFACT_HASH',n)
 assert m['identity_version']==2 and m['outcome_blind'] is True
 st=load(p/'state.json');acts=load(p/'actions.json');f=load(p/'temporal_features.json')
 assert sha(p/'logical.txt')==st['canonical_logical_state_hash']
 assert sha(p/'heuristic.txt')==st['canonical_heuristic_state_hash']
 assert sha(p/'protocol.json')==sha(PROTOCOL)==f['protocol_sha256']
 assert f['feature_schema_sha256']==feature_schema_sha256()==sha(p/'feature_schema.json')
 assert f['raw_temporal_sha256']==sha(p/'temporal_raw.json')
 k=load(p/'collection_plan.json')['K'];n=acts['selected_count']
 assert 1<=k<=6 and acts['K']==k and n==min(k,acts['legal_count'])
 assert len(acts['selected'])==n and [x['rank'] for x in acts['selected']]==list(range(1,n+1))
 assert acts['eligible_ids']==sorted(set(acts['eligible_ids'])) and len(acts['eligible_ids'])==acts['legal_count']
 assert [x['id'] for x in acts['selected']]==acts['eligible_ids'][:n]
 assert m['replay_binary_sha256']==sha(HERE/'frozen_replay_native'),'BINARY_HASH'
 assert m['runner_sha256']==sha(__file__),'RUNNER_HASH'
 return m,st,acts
def run(package,route,rank,output):
 p=Path(package).resolve();o=Path(output).resolve();m,st,acts=verify(p)
 assert route in ['baseline','action'];assert (route=='baseline' and rank is None) or (route=='action' and rank in range(1,acts['selected_count']+1))
 action=None if route=='baseline' else acts['selected'][rank-1]
 before={x.name:sha(x) for x in p.iterdir()};o.mkdir(parents=True,exist_ok=False)
 identity=sha(p/'package_manifest.json')+(':BASELINE' if action is None else f':ACTION:{rank}:{action["id"]}')
 rid=hashlib.sha256(identity.encode()).hexdigest()
 request=[st['boundary'],st['conflicts'],st['decisions'],st['level'],st['trail_length'],st['qhead'],st['canonical_logical_state_hash'],st['canonical_heuristic_state_hash']]
 request+= [0,0,0,0] if action is None else [action['id'],action['literal'],int(action['source']=='learned'),len(action['clause'])]+action['clause']
 (o/'request.txt').write_text(' '.join(map(str,request))+'\n')
 cmd=[str(HERE/'frozen_replay_native'),str(p/'input.cnf'),str(o/'proof.drup'),str(o),str(o/'request.txt')]
 t0=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
 (o/'stdout.txt').write_text(r.stdout);(o/'stderr.txt').write_text(r.stderr);dump(o/'command.json',cmd)
 solve_seconds=time.monotonic()-t0
 r.check_returncode();lines=r.stdout.splitlines();result=json.loads(lines[-2]);counters=json.loads(lines[-1])['final_counters'];result.update(counters);result['analysis_resolution_steps']=counters['analysis_resolution_steps'];assert result['status']=='UNSAT' and result['state_verified']
 actual=load(o/'checkpoint.json');assert all(actual[k]==st[k] for k in actual),'CHECKPOINT'
 assert result['action_verified']==(action is not None),'ACTION_VERIFIED'
 assert load(o/'prefix_counters.json')==load(p/'prefix_counters.json'),'PREFIX_COUNTERS'
 assert result['analysis_resolution_steps']>=load(p/'prefix_counters.json')['analysis_resolution_steps']
 assert sha(o/'logical.txt')==st['canonical_logical_state_hash'] and sha(o/'heuristic.txt')==st['canonical_heuristic_state_hash']
 checker=load(ROOT/'results/prospective_micro_rollout/frozen_protocol.json')['checker'];assert sha(checker['path'])==checker['sha256']
 proofcmd=[checker['path'],str(p/'input.cnf'),str(o/'proof.drup')];proof_t0=time.monotonic();c=subprocess.run(proofcmd,capture_output=True,text=True,timeout=240)
 (o/'proof.log').write_text(c.stdout+c.stderr);dump(o/'proof_command.json',proofcmd)
 assert c.returncode==0 and 's VERIFIED' in c.stdout,'PROOF_FAILED'
 assert before=={x.name:sha(x) for x in p.iterdir()},'PACKAGE_MUTATION'
 # All emitted files are route evidence; whitelist audited by qualification.
 meta=dict(route_id=rid,package_id=p.name,package_manifest_sha256=before['package_manifest.json'],target=st['target'],route_type=route.upper(),action_rank=rank,logical_verified=True,heuristic_verified=True,action_verified=result['action_verified'],proof='VERIFIED',proof_sha256=sha(o/'proof.drup'),package_hashes_unchanged=True,native_result=result,proof_path=str(o/'proof.drup'),checker_returncode=c.returncode,prefix_counters=load(p/'prefix_counters.json'),solve_seconds=solve_seconds,proof_seconds=time.monotonic()-proof_t0)
 dump(o/'route_metadata.json',meta);return meta
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--package',required=True);ap.add_argument('--route',choices=['baseline','action'],required=True);ap.add_argument('--action-rank',type=int);ap.add_argument('--output',required=True);a=ap.parse_args();print(json.dumps(run(a.package,a.route,a.action_rank,a.output)))
