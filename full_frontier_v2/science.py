"""Exact fixed-dataset adapter. Reuses qualified observer; no action search."""
import json,os,pathlib,shutil,subprocess,sys
from build import ROOT,HERE,OUT,sha,dump,replace,instrument
SCI=ROOT/'results/full_frontier_mechanism_anatomy_v2'
OLD=ROOT/'results/branch_displacement_mechanism_v1'
def build_science(kind):
 dest=SCI/'build'/kind;tree=dest/'glucose-3.0';src=OLD/('build' if kind=='v3' else 'build_'+kind)
 shutil.copytree(src/'glucose-3.0',tree,dirs_exist_ok=True)
 # Existing branch observer remains observational (mode=observe); replay guards retained.
 obs=(src/'observer.inc').read_text();obs='#include "'+str(HERE/'observer.inc')+'"\n'+obs
 if kind=='v3':obs=replace(obs,' reached=true;',' reached=true;\n ff_open((output_dir+"/frontier.jsonl.gz").c_str(),true);ff_event("checkpoint");')
 else:obs=replace(obs,'output_dir=cf_dir+"/"+fs_tag;mkdir(output_dir.c_str(),0755);bm_start();','output_dir=cf_dir+"/"+fs_tag;mkdir(output_dir.c_str(),0755);ff_open((output_dir+"/frontier.jsonl.gz").c_str(),true);ff_event("checkpoint");bm_start();')
 (dest/'observer.inc').write_text(obs);instrument(tree,dest/'observer.inc')
 cc=tree/'core/Solver.cc';s=cc.read_text();s=s.replace('ff_event("step_end",lit_Undef,','if(ff_step)ff_event("step_end",lit_Undef,')
 anchor='            ff_event("analysis_backtrack_complete",lit_Undef,CRef_Undef,nullptr,backtrack_level);'
 s=replace(s,anchor,anchor+'\n            if(ff_enabled)ff_close();')
 s=replace(s,'\t  if (decisionLevel() == 0) {','\t  if (decisionLevel() == 0) {\n            if(ff_enabled)ff_close();')
 cc.write_text(s);shutil.copy2(src/'driver.cc',dest/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated']+(['-DREPLAY'] if kind=='v3' else [])+['-I'+str(tree),str(dest/'driver.cc'),str(cc),str(tree/'utils/Options.cc'),str(tree/'utils/System.cc'),'-lz','-o',str(dest/'native')]
 r=subprocess.run(cmd,capture_output=True,text=True);(dest/'stdout.txt').write_text(r.stdout);(dest/'stderr.txt').write_text(r.stderr);r.check_returncode()
 dump(dest/'BUILD_MANIFEST.json',{'command':cmd,'exit_code':r.returncode,'binary_sha256':sha(dest/'native'),'qualified_observer_sha256':sha(HERE/'observer.inc'),'files':{str(p.relative_to(ROOT)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name!='BUILD_MANIFEST.json'}})
 return dest

def run():
 q=json.loads((OUT/'OBSERVER_QUALIFICATION.json').read_text());assert q['FULL_FRONTIER_OBSERVER_V2_QUALIFIED']
 sys.path.insert(0,str(ROOT/'branch_displacement_mechanism_v1'))
 import analyze as oldan
 cases=oldan.cases();rows=[]
 for c in cases:
  meta=json.loads((c['action_dir']/'result.json').read_text());base=json.loads((c['baseline_dir']/'result.json').read_text())
  rows.append({k:v for k,v in c.items() if k not in ['baseline_dir','action_dir','original']}|{'baseline_source':str(c['baseline_dir']),'action_source':str(c['action_dir']),'original_source':str(c['original']),'expected_effect_percent':100*(meta['remaining_ops']/base['remaining_ops']-1),'proof_sha256':meta['proof_sha256'],'observer_dependency':sha(OUT/'OBSERVER_QUALIFICATION.json'),'replayability':'REPLAYABLE'})
 dump(SCI/'FIXED_DATASET.json',rows)
 builds={kind:build_science(kind) for kind in ['v3','T8','T10']}
 checker=json.loads((ROOT/'results/prospective_micro_rollout/frozen_protocol.json').read_text())['checker'];assert sha(checker['path'])==checker['sha256']
 results=[]
 for c,row in zip(cases,rows):
  kind=c['target'] if c['historical'] else 'v3';dest=builds[kind];d=SCI/'runs'/f'{c["state_id"]}_A{c["action_id"]}';d.mkdir(parents=True,exist_ok=False)
  if not c['historical']:
   inp=c['original']/'input.cnf';route_paths=[]
   for tag,old in [('BASELINE',c['baseline_dir']),('ACTION',c['action_dir'])]:
    rd=d/tag;rd.mkdir();shutil.copy2(old/'request.txt',rd/'request.txt');shutil.copy2(old/'mechanism_request.txt',rd/'mechanism_request.txt')
    cmd=[str(dest/'native'),str(inp),str(rd/'proof.drup'),str(rd),str(rd/'request.txt')];r=subprocess.run(cmd,capture_output=True,text=True);(rd/'stdout.txt').write_text(r.stdout);(rd/'stderr.txt').write_text(r.stderr);dump(rd/'invocation.json',{'command':cmd,'exit_code':r.returncode,'binary_sha256':sha(dest/'native'),'input_sha256':sha(inp)});r.check_returncode()
    for n in ['checkpoint.json','logical.txt','heuristic.txt','prefix_counters.json']:assert (rd/n).read_bytes()==(old/n).read_bytes(),n
    native=json.loads(r.stdout.splitlines()[-2]);native.update(json.loads(r.stdout.splitlines()[-1])['final_counters']);route_paths.append((tag,rd,rd/'proof.drup',native,old))
  else:
   inp=ROOT/f'results/high_leverage_discovery/{kind}/input.cnf';old=c['original'];st=json.loads((old/'frozen_state.json').read_text());index=json.loads((old/'runs/command.json').read_text())['command'][-1]
   env=dict(os.environ,MS_STATE_HASH=st['pre_state_hash'],BM_VAR=str(abs(c['literal'])),BM_ACTION=str(c['rank']),BM_MODE='observe',BM_ORDINAL='0',BM_LITERAL='0')
   cmd=[str(dest/'native'),str(inp),str(d/'prefix.drup'),'1000000',str(d),str(index)];r=subprocess.run(cmd,capture_output=True,text=True,env=env);(d/'stdout.txt').write_text(r.stdout);(d/'stderr.txt').write_text(r.stderr);dump(d/'invocation.json',{'command':cmd,'env':{k:v for k,v in env.items() if k.startswith('BM_') or k=='MS_STATE_HASH'},'exit_code':r.returncode,'binary_sha256':sha(dest/'native'),'input_sha256':sha(inp)});r.check_returncode()
   events=list(map(json.loads,(d/'opportunities.jsonl').read_text().splitlines()));snap=next(e for e in events if e['event']=='FROZEN_STATE');assert snap['pre_state_hash']==st['pre_state_hash'];assert snap['heap_including_inverse_hash']==st['heap_including_inverse_hash'];assert all(e['wait_status']==0 for e in events if e['event']=='CHILD_EXIT')
   route_paths=[]
   for tag,oldrd in [('BASELINE',c['baseline_dir']),(f'ACTION_{c["rank"]}',c['action_dir'])]:
    native=next(json.loads(x) for x in reversed((d/f'{tag}.stdout.txt').read_text().splitlines()) if x.startswith('{'));route_paths.append((tag,d/tag,d/f'{tag}.drup',native,oldrd))
  for tag,rd,proof,native,old in route_paths:
   original=json.loads((old/'result.json').read_text());expected=original['native_result'];assert all(native[k]==v for k,v in expected.items() if k!='seconds'),(c['action_id'],tag,native,expected);assert sha(proof)==original['proof_sha256'],('proof bytes',c['action_id'],tag)
   cmd=[checker['path'],str(inp),str(proof)];r=subprocess.run(cmd,capture_output=True,text=True);(rd/'checker.stdout.txt').write_text(r.stdout);(rd/'checker.stderr.txt').write_text(r.stderr);check={'command':cmd,'exit_code':r.returncode,'verified':r.returncode==0 and 's VERIFIED' in r.stdout,'proof_sha256':sha(proof)};dump(rd/'proof_check.json',check);assert check['verified'];assert (rd/'frontier.jsonl.gz').is_file()
   rec={'state_id':c['state_id'],'action_id':c['action_id'],'HIGH':c['HIGH'],'literal':c['literal'],'route':tag,'route_dir':str(rd),'native_result':native,'original_equivalent':True,'proof':check,'trace_sha256':sha(rd/'frontier.jsonl.gz'),'input_sha256':sha(inp),'binary_sha256':sha(dest/'native')};dump(rd/'result.json',rec);results.append(rec)
  dump(SCI/'ROUTE_AUDIT.json',results);print(c['state_id'],c['action_id'],'PAIR VERIFIED',flush=True)
if __name__=='__main__':run()
