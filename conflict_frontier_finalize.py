"""Recover completed full children after parent bookkeeping failure; no solver rerun."""
from conflict_frontier_discovery import *
summary=json.loads((OUT/'discovery_summary.json').read_text())
selected=json.loads((OUT/'frozen_event.json').read_text())
t=selected['target'];o=selected['opportunity'];i=o['opportunity'];d=OUT/'full';es=events(d/'opportunities.jsonl')
replay=next(e for e in es if e['event']=='OPPORTUNITY');assert all(replay[k]==v for k,v in o.items() if k!='reason_canonical_sha256')
pair=traces(d,i);runs=[]
for role,trace,priortrace in zip(['BASELINE','EARLY'],pair,selected['local_pair']):
 tag=f'P{i}_{role}';stdout=(d/(tag+'.stdout.txt')).read_text();stats=next(json.loads(x) for x in reversed(stdout.splitlines()) if x.startswith('{'))
 assert trace['local']==priortrace['local'] and trace['pre']==priortrace['pre']
 proof=d/(tag+'.drup');c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(OLD/t/'input.cnf'),str(proof)],capture_output=True,text=True,timeout=240);(d/(tag+'.proof_check.txt')).write_text(c.stdout+c.stderr)
 verified=c.returncode==0 and 's VERIFIED' in c.stdout;assert stats['status']=='UNSAT' and verified
 with gzip.open(d/(tag+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
 runs.append({'route':'BASELINE_FULL' if role=='BASELINE' else 'EARLY_PROP_FULL','stats':stats,'trace':trace,'next_decision':next((e for e in trace['events'] if e['event']=='NEXT_DECISION'),None),'proof_validation':'VERIFIED','proof_sha256':sha(proof)})
old=json.loads((OLD/t/'BASELINE.result.json').read_text())['stats'];assert all(runs[0]['stats'][k]==v for k,v in old.items() if k!='seconds')
delta=100*(runs[1]['stats']['analysis_resolution_steps']/runs[0]['stats']['analysis_resolution_steps']-1)
full={'frozen_event_sha256':sha(OUT/'frozen_event.json'),'target':t,'opportunity':o,'baseline':runs[0],'early':runs[1],'baseline_matches_original_counters':True,'same_pre_state_by_os_fork':True,'local_replay_matches_stage1':True,'relative_ops_delta_percent':delta,'HIGH_LEVERAGE':abs(delta)>=10}
dump(OUT/'full_run_summary.json',full);summary['stage2']={'relative_ops_delta_percent':delta,'HIGH_LEVERAGE':abs(delta)>=10,'proofs_verified':2};dump(OUT/'discovery_summary.json',summary)
print('FULL',json.dumps(summary['stage2']),flush=True)
