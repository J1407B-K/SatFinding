"""Parameterized protocol wrapper for existing audited native instrumentation.

This wrapper never invents lemmas: treatment requires an external checked DRUP
certificate and DIMACS clause set. Unsupported/illegal requests become JSON
ABORT records. The existing L1/L2 native driver remains the implementation
backend; no solver is copied here.
"""
import argparse,json,subprocess,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--run-name',required=True);p.add_argument('--binary',default='/private/tmp/satfinding-decision828-context/run');p.add_argument('--certificate');p.add_argument('--lemma-set');p.add_argument('--checkpoint',default='conflict_end_before_decision');p.add_argument('--budget',type=int,default=1000000);a=p.parse_args();o=Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)
 row=dict(run=a.run_name,input=str(Path(a.input).resolve()),checkpoint=a.checkpoint,certificate=a.certificate,lemma_set=a.lemma_set,status='ABORT')
 if a.run_name!='CONTROL': row.update(reason='No checked lemma set/certificate supplied; smoke driver refuses semantic UNSAT inference');(o/(a.run_name+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));return
 proof=o/(a.run_name+'.drup'); t=time.time();r=subprocess.run([a.binary,a.input,str(proof),str(a.budget),a.run_name,str(o),str(o/'requests.txt')],capture_output=True,text=True,timeout=240);row['wall_seconds']=time.time()-t;row['returncode']=r.returncode;row['stderr']=r.stderr
 if r.returncode:row['status']='FAILED';(o/(a.run_name+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));return
 stats=json.loads(next(x for x in reversed(r.stdout.splitlines()) if x.startswith('{')));row.update(status=stats['status'],stats=stats,proof=str(proof));(o/(a.run_name+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
if __name__=='__main__':main()
