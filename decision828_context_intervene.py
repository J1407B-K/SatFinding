"""One trace-selected context ingredient: B C657 clause as A's -259 reason."""
import gzip,json,shutil,subprocess
from pathlib import Path
from evaluation_oracle_run import sha
from unseen_selector import dump
import decision828_context as base
P=base.P/'intervention';B=Path('/private/tmp/satfinding-decision828-ingredient')
def main():
 P.mkdir(exist_ok=True);B.mkdir(exist_ok=True);assert not (P/'protocol.json').exists()
 a=json.loads((base.P/'A_FORCED.decision828_before_pick.snapshot.json').read_text());b=json.loads((base.P/'B.decision828_before_pick.snapshot.json').read_text())
 assert a['assignment']==b['assignment'] and [i for i,(x,y) in enumerate(zip(a['reasons'],b['reasons'])) if x!=y]==[258]
 h=b['reasons'][258];cat={}
 for l in gzip.open(base.P/'B.events.jsonl.gz','rt'):
  r=json.loads(l)
  if r['t']=='Q':cat[r['id']]=r['clause']
 clause=cat[h];assert clause[0]==-259
 idx=next(i for i,r in enumerate(b['learned']) if r[0]==h);assert idx==656
 # Certificate-only B derivation prefix. No auxiliary clause enters solver DB.
 prefix=['-507 565 566 0\n'];found=False
 for l in gzip.open(base.P/'B.drup.gz','rt'):
  if l.startswith('d '):continue
  nums=list(map(int,l.split()));assert nums[-1]==0 and len(nums)>1
  prefix.append(l)
  if sorted(nums[:-1])==clause:found=True;break
 assert found
 (B/'witness.drup').write_text(''.join(prefix))
 root=B/'glucose-3.0';shutil.copytree(base.B/'glucose-3.0',root,dirs_exist_ok=True)
 s=(base.B/'trace.inc').read_text()
 code=r'''
void Solver::ctx_transplant(){
 lt_snapshot("ingredient_before");
 if(conflicts!=657||decisions!=828||value(mkLit(258,true))!=l_True||reason(258)==CRef_Undef)exit(41);
 if(lt_clause(ca[reason(258)])!=5534893583465213536ULL)exit(42);
 std::vector<int> ints={CLAUSE};std::vector<Lit> ps;for(int i:ints)ps.push_back(mkLit(abs(i)-1,i<0));
 if(ps[0]!=mkLit(258,true))exit(43);
 for(size_t i=1;i<ps.size();++i)if(value(ps[i])!=l_False)exit(44);
 std::stable_sort(ps.begin()+1,ps.end(),[&](Lit x,Lit y){return level(var(x))>level(var(y));});
 if(level(var(ps[1]))>level(258))exit(45);
 // Fresh correctly oriented reason, ordinary learned DB ownership/watches.
 // All other literals are false; the already assigned head was implied before
 // its own level. No enqueue, propagation, backjump or heuristic state copy.
 if(certifiedUNSAT){std::ifstream f("WITNESS");std::string l;while(std::getline(f,l))fprintf(certifiedOutput,"%s\n",l.c_str());}
 vec<Lit> c;for(auto p:ps)c.push(p);CRef cr=ca.alloc(c,true);
 ca[cr].setLBD(6);ca[cr].setSizeWithoutSelectors(c.size());ca[cr].activity()=0x1.ed7dd4p+0;
 learnts.push(cr);attachClause(cr);vardata[258].reason=cr;
 lt_snapshot("ingredient_after");
}
'''.replace('CLAUSE',','.join(map(str,clause))).replace('WITNESS',str(B/'witness.drup'))
 # C++11 hex floating literal is an extension supported by current clang; use strtod instead.
 code=code.replace('0x1.ed7dd4p+0','strtod("0x1.ed7dd4p+0",NULL)')
 s=s.replace('Lit Solver::da_pick(){',code+'\nLit Solver::da_pick(){')
 s=s.replace(' if(cp && (lt_run=="A_FORCED" || lt_run=="B_FORCED")){',' if(cp && lt_run=="A_FORCED")ctx_transplant();\n if(cp && (lt_run=="A_FORCED" || lt_run=="B_FORCED")){')
 (B/'trace.inc').write_text(s)
 header=root/'core/Solver.h';header.write_text(header.read_text().replace('    void lt_start();','    void lt_start();\n    void ctx_transplant();'))
 source=root/'core/Solver.cc';source.write_text(source.read_text().replace(str(base.B/'trace.inc'),str(B/'trace.inc')))
 shutil.copyfile(base.B/'driver.cc',B/'driver.cc');shutil.copyfile(base.B/'A.cnf',B/'A.cnf');(P/'requests.txt').write_text('')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(B/'driver.cc'),str(source),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(B/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stderr
 dump(P/'protocol.json',dict(trigger='A-context decision828 pre-pick; existing -259=true reason is A C657',one_ingredient='Add exactly B C657 learned clause and make it current reason(-259). Keep A C657. Then execute existing legal -570 forced branch.',clause=clause,source_B_metadata=b['learned'][idx],allowed=['new learned clause allocation/DB entry/LBD/activity metadata and watches','vardata[258].reason'],untouched=['assignments','trail/levels','variable activity','heap','phase','restart','decision eligibility'],proof='Append B derivation prefix through C657 plus RUP-valid L2 to certificate only, retaining A prefix. No witness clauses injected into solver.',witness_sha256=sha(B/'witness.drup'),sources={str(p):sha(p) for p in [Path(__file__),B/'trace.inc',source]},binary_sha256=sha(B/'run'),no_other_interventions=True))
 proof=B/'A_FORCED.drup';r=subprocess.run([str(B/'run'),str(B/'A.cnf'),str(proof),'1000000','A_FORCED',str(P.resolve()),str(P/'requests.txt')],capture_output=True,text=True,timeout=180)
 if r.returncode:dump(P/'result.json',dict(status='ABORTED',code=r.returncode,stderr=r.stderr));print('Aborted',r.returncode);return
 stats=json.loads(next(l for l in reversed(r.stdout.splitlines()) if l.startswith('{')));assert stats['status']=='UNSAT'
 pre=json.loads((P/'A_FORCED.ingredient_before.snapshot.json').read_text());post=json.loads((P/'A_FORCED.ingredient_after.snapshot.json').read_text())
 assert pre==a
 diff=[k for k in pre if pre[k]!=post[k]];assert set(diff)=={'reasons','learned','watches'},diff
 assert [i for i,(x,y) in enumerate(zip(pre['reasons'],post['reasons'])) if x!=y]==[258]
 assert post['reasons'][258]==h and post['learned'][:-1]==pre['learned']
 c=subprocess.run(['/private/tmp/satfinding-drat-trim',str(B/'A.cnf'),str(proof)],capture_output=True,text=True,timeout=60)
 (P/'proof_check.txt').write_text(c.stdout+c.stderr);verified=c.returncode==0 and 'VERIFIED' in c.stdout
 with gzip.open(P/'A_FORCED.drup.gz','wb') as f:f.write(proof.read_bytes())
 dump(P/'result.json',dict(status='PASS' if verified else 'INVALID_PROOF',stats=stats,proof_verified=verified,proof_sha256=sha(proof),pre_matches_A_forced=True,changed_fields=diff,pre_sha256=sha(P/'A_FORCED.ingredient_before.snapshot.json'),post_sha256=sha(P/'A_FORCED.ingredient_after.snapshot.json')))
 print(stats,'proof',verified,flush=True)
if __name__=='__main__':main()
