"""Fail-closed evidence manifest verifier; no truth inferred from report filenames."""
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(manifest):
 errors=[]
 def require(v,msg):
  if not v:raise ValueError(msg)
 def artifact(a):
  require(set(['path','sha256','size'])<=set(a),'artifact fields missing');p=pathlib.Path(a['path']);p=p if p.is_absolute() else ROOT/p
  require(p.is_file(),f'missing {p}');require(p.stat().st_size==a['size'],f'size {p}');require(sha(p)==a['sha256'],f'hash {p}');return p
 def read(a):return json.loads(artifact(a).read_text())
 try:
  m=json.loads(pathlib.Path(manifest).read_text());require(m['schema']=='native-execution-v2','unsupported schema')
  revision=m['source_revision'];require(subprocess.check_output(['git','rev-parse',revision+'^{commit}'],cwd=ROOT,text=True).strip()==revision,'source revision')
  require(len(m['sources'])>0,'sources empty')
  for a in m['sources']:artifact(a)
  for a in m['artifacts']:artifact(a)
  inputs={}
  for a in m['inputs']:
   p=artifact(a);require(a['source_type'] in ['ARCHIVED_FILE','GENERATED'],'input type');require(a['historical_exact_replay'] is False,'qualification scope');inputs[a['sha256']]=str(p)
   if a['source_type']=='ARCHIVED_FILE':require(sha(artifact(a['source']))==a['sha256'],'source/input mismatch')
   else:
    artifact(a['generator']);require(a['command'] and 'seed' in a and 'parameters' in a,'generator provenance')
  require(len(inputs)>=2,'qualification inputs missing')
  b=read(m['build']);require(b['exit_code']==0 and b['source_commit']==revision,'build failed/revision');binary=artifact(m['binary']);require(b['binary_sha256']==m['binary']['sha256'],'build binary');require(b['command'][-1]==str(binary),'build output binding')
  for path,digest in b['source_hashes'].items():require(sha(ROOT/path)==digest,'build source '+path)
  require(len(m['runs'])==6,'expected six native runs');labels=set()
  for row in m['runs']:
   i=read(row['invocation']);s=read(row['summary']);pc=read(row['proof_check']);labels.add((row['case'],row['mode']))
   require(i['exit_code']==0 and i['binary_sha256']==m['binary']['sha256'],'invocation failed/binary');require(i['input_sha256'] in inputs,'unknown input')
   require(i['command'][0]==str(binary) and i['command'][1]==inputs[i['input_sha256']],'invocation binding');require(s['status']=='UNSAT','status');require(not s['replay_controller_initialized'] and s['checkpoint_requests_seen']==s['actions_applied']==0,'replay participated')
   raw=artifact(row['stdout']).read_text();require(json.loads(raw.splitlines()[-1])==s,'summary vs raw stdout');artifact(row['stderr'])
   proof=artifact(row['proof']);checker=artifact(m['checker']);require(pc['command']==[str(checker),inputs[i['input_sha256']],str(proof)],'checker binding');require(pc['exit_code']==0 and pc['proof_sha256']==row['proof']['sha256'],'proof execution failed')
   require('s VERIFIED' in artifact(row['checker_stdout']).read_text(),'checker did not verify');artifact(row['checker_stderr'])
   if row['mode']!='OFF':require(artifact(row['trace']).stat().st_size>0,'empty ON trace')
  require(labels=={(t,r) for t in ['T8','T10'] for r in ['OFF','ON1','ON2']},'missing/duplicate runs')
  audits=read(m['self_consistency']);require(len(audits)==4,'audits missing')
  for a in audits.values():require(a['checks_total']>0 and a['checks_fail']==0 and a['complete_chains']>0,'audit failed')
  np=read(m['nonperturbation']);st=read(m['stability']);require(set(np)==set(st)=={'T8','T10'},'comparison targets')
  for t in np:require(all(np[t].values()) and st[t]['PASS'] and len(set(st[t]['canonical_sha256']))==1,'comparison failed')
 except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as e:errors.append(str(e))
 return {'EVIDENCE_VERIFIED':not errors,'errors':errors,'manifest_sha256':sha(pathlib.Path(manifest))}
if __name__=='__main__':
 r=verify(sys.argv[1]);print(json.dumps(r,indent=2));sys.exit(0 if r['EVIDENCE_VERIFIED'] else 1)
