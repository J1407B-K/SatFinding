import json,sys,pathlib,subprocess
from build import ROOT,OUT,sha,dump
sys.path.insert(0,str(ROOT))
from verify_experiment_evidence import verify

def art(p):
 p=pathlib.Path(p).resolve();return {'path':str(p),'sha256':sha(p),'size':p.stat().st_size}
def main():
 b=json.loads((OUT/'BUILD_MANIFEST.json').read_text());m={'schema':'native-execution-v2','source_revision':b['source_commit'],'sources':[art(ROOT/p) for p in b['source_hashes']],'inputs':[],'build':art(OUT/'BUILD_MANIFEST.json'),'binary':art(b['binary']),'checker':art('/private/tmp/satfinding-drat-trim'),'artifacts':[],'runs':[]}
 for t,pkg in [('T8','T8_S1_B448899'),('T10','T10_S1_B457201')]:
  inp=ROOT/f'results/full_propagation_frontier_observer_v2/inputs/{t}_qualification.cnf';a=art(inp);a.update(source_type='ARCHIVED_FILE',historical_exact_replay=False,qualification_case_label=t,source=art(ROOT/f'results/prospective_temporal_state_cohort_v3/packages/{pkg}/input.cnf'));m['inputs'].append(a)
  for mode in ['OFF','ON1','ON2']:
   d=OUT/'runs'/t/mode;r={'case':t,'mode':mode}
   for k,n in {'invocation':'invocation.json','summary':'summary.json','proof_check':'proof_check.json','stdout':'stdout.txt','stderr':'stderr.txt','proof':'proof.drup','checker_stdout':'checker.stdout.txt','checker_stderr':'checker.stderr.txt'}.items():r[k]=art(d/n)
   if mode!='OFF':r['trace']=art(d/'trace.jsonl.gz.gz')
   m['runs'].append(r)
 for k,n in [('self_consistency','OBSERVER_SELF_CONSISTENCY.json'),('nonperturbation','OBSERVER_NONPERTURBATION.json'),('stability','OBSERVER_CROSS_RUN_STABILITY.json')]:m[k]=art(OUT/n)
 for p in [OUT/'build/stdout.txt',OUT/'build/stderr.txt',* [ROOT/'full_frontier_v2'/n for n in ['build.py','run_qualification.py','audit.py','finalize.py']],ROOT/'verify_experiment_evidence.py']:m['artifacts'].append(art(p))
 dump(OUT/'EVIDENCE_MANIFEST.json',m)
 cmd=[sys.executable,str(ROOT/'verify_experiment_evidence.py'),str(OUT/'EVIDENCE_MANIFEST.json')];r=subprocess.run(cmd,capture_output=True,text=True);dump(OUT/'EVIDENCE_VERIFICATION_INVOCATION.json',{'command':cmd,'exit_code':r.returncode,'stderr':r.stderr});v=json.loads(r.stdout);dump(OUT/'EVIDENCE_VERIFICATION.json',v);r.check_returncode()
 result={'FULL_FRONTIER_OBSERVER_V2_QUALIFIED':v['EVIDENCE_VERIFIED'],'evidence_manifest_sha256':sha(OUT/'EVIDENCE_MANIFEST.json'),'evidence_verification_sha256':sha(OUT/'EVIDENCE_VERIFICATION.json'),'scope':'fresh root-solve T8/T10; historical exact replay not qualified by these runs','native_runs':6,'proof_checks':6,'self_consistency':json.loads((OUT/'OBSERVER_SELF_CONSISTENCY.json').read_text()),'nonperturbation':json.loads((OUT/'OBSERVER_NONPERTURBATION.json').read_text())};dump(OUT/'OBSERVER_QUALIFICATION.json',result)
 (OUT/'OBSERVER_QUALIFICATION.md').write_text('Qualification derived by full_frontier_v2/finalize.py from six actual runs, six fresh checker invocations, streaming trace audits and fail-closed manifest verification.\n\nFULL_FRONTIER_OBSERVER_V2_QUALIFIED = '+str(result['FULL_FRONTIER_OBSERVER_V2_QUALIFIED'])+'\n')
 print(json.dumps(v))
if __name__=='__main__':main()
