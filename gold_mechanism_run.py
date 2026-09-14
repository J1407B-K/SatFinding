"""Fixed diagnostic interventions; no candidate or subset optimization."""
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import subprocess

from evaluation_oracle_run import sha,dimacs
from gold_mechanism_build import BUILD,BASE,build
from oracle_lemma import prepare,TARGET,HISTORY,TEMPLATE
from unseen_selector import dump,digest

OUT=Path('results/gold_mechanism')

def run_config(name,ids,cnf,templates,clauses,mapping):
    assert ids==sorted(set(ids))
    path=BUILD/(name+'.cnf');trace=BUILD/(name+'.jsonl')
    dimacs(path,list(cnf)+templates+[clauses[i] for i in ids])
    stats=[]
    for binary in (BASE/'counted',BUILD/'trace'):
        cmd=[str(binary),str(path),'/dev/null','1000000']
        if binary.name=='trace':cmd += [str(mapping),str(trace)]
        p=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=60)
        row=json.loads(next(l for l in reversed(p.stdout.splitlines()) if l.startswith('{')))
        assert row['status']=='UNSAT';stats.append(row)
    assert {k:v for k,v in stats[0].items() if k!='seconds'}=={k:v for k,v in stats[1].items() if k!='seconds'},name
    with gzip.open(OUT/(name+'.trace.jsonl.gz'),'wb') as f:f.write(trace.read_bytes())
    trace.unlink();path.unlink() # bounded transient logs only; compressed evidence retained
    row=dict(name=name,ids=ids,stats=stats[0],trace_stats=stats[1],
        input_sha256=digest(list(cnf)+templates+[clauses[i] for i in ids]),
        trace_sha256=sha(OUT/(name+'.trace.jsonl.gz')),counters_match=True)
    dump(OUT/(name+'.result.json'),row)
    print(name,stats[0]['analysis_resolution_steps'],stats[0]['conflicts'],flush=True)
    return row

def main():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'runs.json').exists(),'Do not overwrite measurements'
    data=prepare()
    payload=json.loads(Path('results/oracle_lemma/gold_lemmas.json').read_text())
    gold=payload['sets']['exact_64']['selected_ids'];assert len(gold)==64
    proof,lemmas,validation=data['h'].materialize(data['cnf'],gold)
    clauses=dict(zip(gold,lemmas))
    with gzip.open(OUT/'gold_checked_support.json.gz','wt') as f:json.dump(asdict(proof),f)
    dump(OUT/'inputs.json',dict(cnf=data['cnf'],templates=data['templates'],gold=clauses))
    configs={'CONTROL':[],'TREATMENT':gold,'L1':[24458],'L2':[30149],'L3':[210136],
        'L1_L2':[24458,30149],'L1_L2_L3':[24458,30149,210136]}
    for i in (2772,150191,96687,210136):
        if i!=210136:configs['ONLY_'+str(i)]=[i]
        configs['DROP_'+str(i)]=[j for j in gold if j!=i]
    mapping=BUILD/'mapping.txt'
    buildmeta=build()
    mapping.write_text(''.join(f'O{i} -1 '+ ' '.join(map(str,c))+' 0\n' for i,c in enumerate(data['cnf']))+
        ''.join(f'T{i} -1 '+' '.join(map(str,c))+' 0\n' for i,c in enumerate(data['templates']))+
        ''.join(f'G{i} {i} '+' '.join(map(str,clauses[i]))+' 0\n' for i in gold))
    dump(OUT/'frozen.json',dict(target=str(TARGET),configs=configs,validation=validation,
        build=buildmeta,sources={str(p):sha(p) for p in (TARGET,HISTORY,TEMPLATE,
            Path('docs/gold-mechanism-protocol.md'),Path(__file__),Path('gold_mechanism_trace.inc'),
            Path('gold_mechanism_build.py'),Path('results/oracle_lemma/gold_lemmas.json'))},
        inputs_sha256=sha(OUT/'inputs.json'),mapping_sha256=sha(mapping)))
    runs=[]
    for name,ids in configs.items():runs.append(run_config(name,ids,data['cnf'],data['templates'],clauses,mapping))
    assert runs[0]['stats']['analysis_resolution_steps']==203623
    assert runs[1]['stats']['analysis_resolution_steps']==130718
    dump(OUT/'runs.json',runs)

if __name__=='__main__':main()
