// Only fixed ghost/injection/decision interventions. No solver tuning.
int da_point=-1,da_last_ghost=-1;bool da_ready=false,da_done=false,da_forced=false;
std::set<int> da_checkpoints={100,150,180,190,198,200,220,250,300,400,600};
std::set<int> da_saved;
void da_setup(){da_ready=true;if(lt_run.size()>1&&lt_run[0]=='I')da_point=atoi(lt_run.c_str()+1);}
void Solver::da_ghost(const char* where){
 if(!da_ready || (lt_run!="A"&&lt_run!="A_FORCED"))return;
 Lit ls[3]={mkLit(506,true),mkLit(564,false),mkLit(565,false)};
 int undef=0,sat=0,u=0;for(auto l:ls){if(value(l)==l_True)sat++;if(value(l)==l_Undef){undef++;u=lt_int(l);}}
 int state=sat?0:undef==0?3:undef==1?2:1;
 if(state!=da_last_ghost){++lt_global;gzprintf(lt_out,"{\"t\":\"GHOST\",\"g\":%llu,\"c\":%llu,\"d\":%llu,\"e\":%llu,\"where\":\"%s\",\"state\":%d,\"unit\":%d,\"values\":[%d,%d,%d]}\n",lt_global,(LU)conflicts,(LU)decisions,lt_e,where,state,state==2?u:0,toInt(value(ls[0])),toInt(value(ls[1])),toInt(value(ls[2])));da_last_ghost=state;}
}
CRef Solver::da_inject(){
 if(lt_run=="A" && da_checkpoints.count(conflicts)&&!da_saved.count(conflicts)){da_saved.insert(conflicts);lt_snapshot("boundary_"+std::to_string(conflicts));}
 if(da_point<0 || da_done || conflicts!=(LU)da_point)return CRef_Undef;
 da_done=true;lt_snapshot("injection_before");int olddl=decisionLevel();
 std::vector<Lit> ls={mkLit(506,true),mkLit(564,false),mkLit(565,false)};
 int nf=0;for(auto l:ls)if(value(l)!=l_False)nf++;
 // Keep canonical order within nonfalse literals; greatest false antecedent
 // level supplies the second watch for unit/conflict safety on backtracking.
 std::stable_sort(ls.begin(),ls.end(),[&](Lit a,Lit b){bool af=value(a)==l_False,bf=value(b)==l_False;if(af!=bf)return !af;if(af&&bf)return level(var(a))>level(var(b));return false;});
 bool assertunit=false;
 if(nf==0){int lev=level(var(ls[0]));cancelUntil(lev);}
 else if(nf==1){int lev=level(var(ls[1]));if(value(ls[0])==l_Undef || level(var(ls[0]))>lev){cancelUntil(lev);assertunit=true;}}
 vec<Lit> c;for(auto l:ls)c.push(l);
 if(certifiedUNSAT)fprintf(certifiedOutput,"-507 565 566 0\n");
 CRef cr=ca.alloc(c,false);clauses.push(cr);attachClause(cr);
 ++lt_global;gzprintf(lt_out,"{\"t\":\"INJECT\",\"g\":%llu,\"c\":%llu,\"d\":%llu,\"e\":%llu,\"nonfalse_before\":%d,\"dl_before\":%d,\"dl_after\":%d,\"unit_assert\":%d,\"conflict\":%d,\"watch_order\":[%d,%d,%d]}\n",lt_global,(LU)conflicts,(LU)decisions,lt_e,nf,olddl,decisionLevel(),assertunit,nf==0,lt_int(ls[0]),lt_int(ls[1]),lt_int(ls[2]));
 if(assertunit){if(value(ls[0])!=l_Undef)exit(31);uncheckedEnqueue(ls[0],cr);}
 lt_snapshot("injection_after");
 return nf==0?cr:CRef_Undef;
}
Lit Solver::da_pick(){
 bool checkpoint=decisions==828;
 if(checkpoint)lt_snapshot("decision828_before_pick");
 Lit next=pickBranchLit();
 if(checkpoint)lt_snapshot("decision828_after_native_pick");
 if(checkpoint && (lt_run=="A_FORCED"||lt_run=="B_FORCED")){
  Lit forced=mkLit(lt_run=="A_FORCED"?569:186,true);
  if(value(forced)!=l_Undef || !decision[var(forced)] || next==lit_Undef || qhead!=trail.size())exit(32);
  if(lt_int(next)!=(lt_run=="A_FORCED"?-187:-570))exit(33);
  int natural=lt_int(next);next=forced;da_forced=true;
  lt_snapshot("decision828_after_override");
  gzprintf(lt_out,"{\"t\":\"FORCED\",\"c\":%llu,\"d\":%llu,\"e\":%llu,\"natural\":%d,\"forced\":%d,\"legal\":true}\n",(LU)conflicts,(LU)decisions,lt_e,natural,lt_int(forced));
 }
 return next;
}
