"""Try archived exact native builds without relaxing their checkpoint guards."""
import os,sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from run import *
def main():
 rows=[]
 candidates=load(ROOT/'results/intervention_opportunity_discovery_v1/historical_positive_audit.json')['candidates']
 for sid,target,old,buildpath,index in [
  ('HIST_T10_FIXED','T10',ROOT/'results/fixed_state_action_surface',Path('/private/tmp/satfinding-fixed-state-action-surface'),226),
  ('HIST_T8_S5','T8',ROOT/'results/multi_state_action_surface/S5',Path('/private/tmp/satfinding-multi-state-action-surface'),0)]:
  cand=next(c for c in candidates if c['state_id']==sid)
  manifest=load((old if target=='T10' else old.parent)/'build.json')
  row={'state_id':sid,'target':target,'expected_identity':cand['state_identity'],'canonical_snapshot_available':False,'sources':{},'binary_sha256':sha(buildpath/'run'),'expected_binary_sha256':manifest['binary_sha256']}
  for p,h in manifest['sources'].items():row['sources'][p]={'expected':h,'actual':sha(p) if Path(p).is_file() else None}
  assert row['binary_sha256']==row['expected_binary_sha256']
  if target=='T8':
   # Frozen episode index is retained by the original state selection evidence.
   index=int(load(old/'runs/command.json')['command'][-1])
  d=OUT/'historical_replay_attempts'/sid;d.mkdir(parents=True,exist_ok=False)
  cmd=[str(buildpath/'run'),str(ROOT/f'results/high_leverage_discovery/{target}/input.cnf'),str(d/'prefix.drup'),'1000000',str(d),str(index)]
  env=dict(os.environ,MS_STATE_HASH=cand['state_identity'])
  p=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=240)
  (d/'stdout.txt').write_text(p.stdout);(d/'stderr.txt').write_text(p.stderr)
  row.update(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
  row['exact_replay_passed']=p.returncode==0 and 'ACTION_SURFACE_COMPLETED' in (d/'opportunities.jsonl').read_text()
  dump(d/'audit.json',row);rows.append(row);print(json.dumps(row),flush=True)
 dump(OUT/'historical_replay_audit.json',rows)
if __name__=='__main__':main()
