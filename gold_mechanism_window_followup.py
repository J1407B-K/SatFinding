"""Two single-conflict snapshots to inspect the observed pair's later forks."""
import json
from pathlib import Path
import subprocess
from gold_mechanism_build import BUILD
from gold_mechanism_run import OUT,run_config
from unseen_selector import dump
from evaluation_oracle_run import sha

def main():
    assert not (OUT/'followup_runs.json').exists()
    dump(OUT/'followup_protocol.json',dict(conflicts=[291,656],configs=['L1','L1_L2'],
        reason='Already observed first differing conflict and first differing learned clause. No new subset or solver setting.',
        source_sha256=sha(__file__)))
    source=BUILD/'glucose-3.0/core/Solver.cc';s=source.read_text()
    assert s.count('conflicts>=196 && conflicts<=206')==1
    s=s.replace('conflicts>=196 && conflicts<=206','conflicts==291 || conflicts==656')
    inc=BUILD/'followup.inc'
    inc.write_text(Path('gold_mechanism_trace.inc').read_text().replace('if(cc<=gm_early && !minimize)',
        'if((cc<=gm_early || cc==291 || cc==656) && !minimize)'))
    s=s.replace(str(Path('gold_mechanism_trace.inc').resolve()),str(inc));source.write_text(s)
    cmd=json.loads((OUT/'window_build.json').read_text())['base_build']['command']
    subprocess.run(cmd,check=True,capture_output=True)
    dump(OUT/'followup_build.json',dict(source_sha256=sha(source),observer_sha256=sha(inc),binary_sha256=sha(BUILD/'trace')))
    inp=json.loads((OUT/'inputs.json').read_text());gold={int(k):v for k,v in inp['gold'].items()}
    runs=[]
    for name,ids in [('FOLLOWUP_L1',[24458]),('FOLLOWUP_L1_L2',[24458,30149])]:
        runs.append(run_config(name,ids,inp['cnf'],inp['templates'],gold,BUILD/'mapping.txt'))
    dump(OUT/'followup_runs.json',runs)

if __name__=='__main__':main()
