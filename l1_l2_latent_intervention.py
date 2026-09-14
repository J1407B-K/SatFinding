"""One legally equivalent reason substitution reset, after natural evidence."""
import gzip
import json
from pathlib import Path
import subprocess
from l1_l2_latent import OUT,BUILD
from unseen_selector import dump
from evaluation_oracle_run import sha

def main():
    assert not (OUT/'intervention_result.json').exists(),'Only one intervention'
    observed=json.loads((OUT/'first_divergences.json').read_text())
    assert observed['reason']['B']['e']==28916 and observed['activity_bump']['B']['c']==199
    supplemental=OUT/'supplemental';supplemental.mkdir(exist_ok=True)
    req=OUT/'extra_requests.txt';req.write_text((OUT/'requests.txt').read_text()+'U_199_7\n')
    # Freeze the one mediator and exact trigger before running it.
    dump(OUT/'intervention_protocol.json',dict(trigger=dict(completed_conflicts=198,decision=271,enqueue=28916,literal=565),
        allowed='Only vardata[variable565].reason: L2 clause -> existing original(565,566,567).',
        legality='Both other literals false; clause already allocated; literal565 already at slot0. Abort rather than alter watches or clause order.',
        evidence=observed['reason'],natural_sha256={n:sha(OUT/(n+'.events.jsonl.gz')) for n in ('A','B')},
        source_sha256=sha(__file__),no_further_interventions=True))
    # Natural replay adds the exact first-bump snapshots, with identical ledgers.
    original=json.loads((OUT/'natural_runs.json').read_text())
    for name in ('A','B'):
        p=subprocess.run([str(BUILD/'latent'),str(BUILD/(name+'.cnf')),'/dev/null','1000000',name,str(supplemental.resolve()),str(req)],capture_output=True,text=True,check=True,timeout=180)
        stats=json.loads(next(l for l in reversed(p.stdout.splitlines()) if l.startswith('{')))
        assert {k:v for k,v in stats.items() if k!='seconds'}=={k:v for k,v in original[name].items() if k!='seconds'}
        path=supplemental/(name+'.events.jsonl.gz')
        assert gzip.decompress(path.read_bytes())==gzip.decompress((OUT/(name+'.events.jsonl.gz')).read_bytes())
        path.unlink() # exact duplicate, no additional evidence
    name='B_REASON_RESET'
    p=subprocess.run([str(BUILD/'latent'),str(BUILD/'B.cnf'),str(BUILD/(name+'.drup')),'1000000',name,str(OUT.resolve()),str(req)],capture_output=True,text=True,timeout=180)
    if p.returncode:
        dump(OUT/'intervention_result.json',dict(status='ABORTED_LEGALITY_OR_EXECUTION',returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));print('Intervention aborted; do not rescue');return
    stats=json.loads(next(l for l in reversed(p.stdout.splitlines()) if l.startswith('{')));assert stats['status']=='UNSAT'
    before=json.loads((OUT/(name+'.first_reason_after.snapshot.json')).read_text())
    after=json.loads((OUT/(name+'.reason_reset_after.snapshot.json')).read_text())
    assert [k for k in before if before[k]!=after[k]]==['reasons']
    assert [i for i,(a,b) in enumerate(zip(before['reasons'],after['reasons'])) if a!=b]==[564]
    a=json.loads((OUT/'A.first_reason_after.snapshot.json').read_text())
    assert after['reasons'][564]==a['reasons'][564]
    proofchecks={}
    for n in ('A','B',name):
        cnf=BUILD/('A.cnf' if n=='A' else 'B.cnf');proof=BUILD/(n+'.drup')
        p=subprocess.run(['/private/tmp/satfinding-drat-trim',str(cnf),str(proof)],capture_output=True,text=True,timeout=60)
        assert p.returncode==0 and 'VERIFIED' in p.stdout
        (OUT/(n+'.proof_check.txt')).write_text(p.stdout+p.stderr)
        with gzip.open(OUT/(n+'.drup.gz'),'wb') as f:f.write(proof.read_bytes())
        proofchecks[n]=dict(status='VERIFIED',sha256=sha(proof))
    dump(OUT/'intervention_result.json',dict(status='PASS',stats=stats,only_reason565_changed=True,
        snapshots_sha256={tag:sha(OUT/(name+'.'+tag+'.snapshot.json')) for tag in ('first_reason_after','reason_reset_after')},
        proof_checks=proofchecks,trace_sha256=sha(OUT/(name+'.events.jsonl.gz'))))
    print(stats,flush=True)

if __name__=='__main__':main()
