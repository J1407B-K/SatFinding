"""Manifest-only dynamic route generator and executor."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from harness_v3.common import *
from harness_v3.runner import verify,run

def derive(o):
 o=Path(o);cohort=frozen(o/'cohort_manifest.json');rows=[]
 for e in cohort['packages']:
  p=o/e['path'];assert sha(p/'package_manifest.json')==e['package_manifest_sha256'];_,st,acts=verify(p)
  for action in [None]+acts['selected']:
   rank=None if action is None else action['rank'];rid=route_id(p,action)
   rows.append({'package':e['path'],'route':'baseline' if action is None else 'action','rank':rank,'route_id':rid,'output':'route_results/'+rid})
 assert len({r['route_id'] for r in rows})==len(rows)
 return rows

def freeze_routes(o):
 o=Path(o);assert not (o/'route_results').exists();rows=derive(o);freeze(o/'expected_routes.json',rows);return rows

def execute(o):
 from harness_v3.audit import pre_audit
 o=Path(o);expected=frozen(o/'expected_routes.json');assert expected==derive(o)
 pre=frozen(o/'pre_ground_truth_audit.json');assert pre['PRE_GROUND_TRUTH_AUDIT']=='PASSED'
 assert pre['input_hashes']==input_hashes(o),'FROZEN_INPUT_MUTATION'
 for e in expected:
  row=run(o/e['package'],e['route'],e['rank'],o/e['output']);print(row['target'],row['package_id'],row['action_rank'],'REPLAY_STATE_VERIFIED / VERIFIED',flush=True)
 assert pre['input_hashes']==input_hashes(o),'FROZEN_INPUT_MUTATION'

def input_hashes(o):
 o=Path(o);paths=[o/'cohort_manifest.json',o/'cohort_manifest.json.sha256',o/'expected_routes.json',o/'expected_routes.json.sha256']
 paths+=list((o/'packages').rglob('*'))
 return {str(p.relative_to(o)):sha(p) for p in paths if p.is_file()}
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--cohort',required=True);ap.add_argument('phase',choices=['freeze','run']);a=ap.parse_args();(freeze_routes if a.phase=='freeze' else execute)(a.cohort)
