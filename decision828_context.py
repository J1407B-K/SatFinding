import json,shutil,subprocess,gzip
from pathlib import Path
from evaluation_oracle_run import sha
from unseen_selector import dump
from build_native_cdcl import replace_once
P=Path('results/decision828_context');B=Path('/private/tmp/satfinding-decision828-context');OLD=Path('/private/tmp/satfinding-l2-forced-valid')
def build():
 P.mkdir(exist_ok=True);B.mkdir(exist_ok=True);root=B/'glucose-3.0';shutil.copytree(OLD/'glucose-3.0',root,dirs_exist_ok=True)
 s=(OLD/'trace.inc').read_text();start=s.index('void Solver::lt_event(');end=s.index('void Solver::lt_pre_enqueue',start)
 original=Path('l1_l2_latent_trace.inc').read_text();event=original[original.index('void Solver::lt_event('):original.index('void Solver::lt_pre_enqueue')]
 event=event.replace('if(conflicts<=900||special)','if(conflicts>=600 && conflicts<=800)')
 event=event.replace('special,sf_analysis);','special,sf_analysis);')
 # Add cumulative native propagations and exact bumped value without changing actions.
 event=event.replace('\\"ops\\":%llu}', '\\"ops\\":%llu,\\"props\\":%llu,\\"bump_value\\":\\"%a\\"}')
 event=event.replace('special,sf_analysis);','special,sf_analysis,(LU)propagations,std::string(kind)=="U"?activity[value-1]:0.0);')
 s=s[:start]+event+s[end:]
 start=s.index('void Solver::da_ghost(');end=s.index('Lit Solver::da_pick()',start)
 s=s[:start]+r'''
void Solver::da_ghost(const char* where){if(da_ready&&std::string(where)=="backtrack")lt_event("CANCEL",decisionLevel(),0);}
CRef Solver::da_inject(){
 static std::set<int> checkpoints={600,650,656,657,658,662,667,677,700,707,750,800};
 if(checkpoints.count(conflicts)&&!da_saved.count(conflicts)){da_saved.insert(conflicts);lt_snapshot("boundary_"+std::to_string(conflicts));}
 return CRef_Undef;
}
'''+s[end:]
 (B/'trace.inc').write_text(s);source=root/'core/Solver.cc';source.write_text(source.read_text().replace(str(OLD/'trace.inc'),str(B/'trace.inc')))
 shutil.copyfile(OLD/'driver.cc',B/'driver.cc')
 for n in ['A','B']:shutil.copyfile(OLD/f'{n}.cnf',B/f'{n}.cnf')
 (P/'requests.txt').write_text('')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(B/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(B/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stderr
 return dict(binary_sha256=sha(B/'run'),sources={str(p):sha(p) for p in [Path(__file__),Path('docs/decision828-context-protocol.md'),B/'trace.inc',source]},input_sha256={n:sha(B/f'{n}.cnf') for n in ['A','B']})
def main():
 assert not (P/'runs.json').exists();meta=build();dump(P/'protocol.json',meta)
 old=json.loads(Path('results/l2_delayed_amplification/forced_valid/runs.json').read_text());runs={}
 for n in ['A','B','A_FORCED','B_FORCED']:
  proof=B/f'{n}.drup';inp=n.split('_')[0]
  r=subprocess.run([str(B/'run'),str(B/f'{inp}.cnf'),str(proof),'1000000',n,str(P.resolve()),str(P/'requests.txt')],capture_output=True,text=True,timeout=180);assert r.returncode==0,(n,r.returncode,r.stderr)
  stats=json.loads(next(l for l in reversed(r.stdout.splitlines()) if l.startswith('{')))
  assert {k:v for k,v in stats.items() if k!='seconds'}=={k:v for k,v in old[n]['stats'].items() if k!='seconds'}
  assert sha(proof)==old[n]['proof_sha256']
  c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(B/f'{inp}.cnf'),str(proof)],capture_output=True,text=True,timeout=60);assert c.returncode==0 and 'VERIFIED' in c.stdout
  (P/f'{n}.proof_check.txt').write_text(c.stdout+c.stderr)
  with gzip.open(P/f'{n}.drup.gz','wb') as f:f.write(proof.read_bytes())
  runs[n]=dict(stats=stats,proof_verified=True,proof_byte_identical=True,proof_sha256=sha(proof),trace_sha256=sha(P/f'{n}.events.jsonl.gz'))
  dump(P/f'{n}.result.json',runs[n]);print(n,stats,flush=True)
 dump(P/'runs.json',runs)
if __name__=='__main__':main()
