// Fixed-case pulse only. Injection body is copied from the prior experiment.
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <string>
static FILE* pw_log=nullptr;
static bool pw_enabled=false,pw_injected=false,pw_removed=false,pw_inserting=false;
static int pw_remove=-1;
static unsigned long long pw_reason=0,pw_analysis=0,pw_prop=0,pw_min=0,pw_conflict=0;
static int pw_int(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static bool pw_l2(const Clause& c){
 if(c.learnt() || c.size()!=3)return false;
 bool a=false,b=false,d=false;
 for(int i=0;i<3;++i){int l=pw_int(c[i]);a|=l==-507;b|=l==565;d|=l==566;}
 return a&&b&&d;
}
void pw_init(const char* route,const char* path){
 std::string r(route);pw_enabled=r!="A_NORMAL";
 if(r.find("REMOVE@")==0)pw_remove=std::stoi(r.substr(7));
 pw_log=fopen(path,"w");if(!pw_log)throw std::runtime_error("ledger open failed");
}
void pw_finish(){
 fprintf(pw_log,"{\"event\":\"TOTAL\",\"injected\":%s,\"removed\":%s,\"reason_use_count\":%llu,\"conflict_analysis_use_count\":%llu,\"propagation_count\":%llu,\"minimization_use_count\":%llu,\"conflict_trigger_count\":%llu}\n",pw_injected?"true":"false",pw_removed?"true":"false",pw_reason,pw_analysis,pw_prop,pw_min,pw_conflict);
 fclose(pw_log);
}
void Solver::pw_use(const Clause& c,int kind){
 if(!pw_l2(c))return;
 if(pw_removed)throw std::runtime_error("ABORT_POST_REMOVE_L2_USE");
 if(kind==0)++pw_analysis;
 if(kind==1)++pw_min;
 if(kind==2)++pw_conflict;
}
void Solver::pw_enqueue(Lit p,CRef from){
 if(from==CRef_Undef || !pw_l2(ca[from]))return;
 if(pw_removed || value(p)!=l_Undef)throw std::runtime_error("ABORT_L2_ENQUEUE_INVARIANT");
 ++pw_reason;if(!pw_inserting)++pw_prop;
}
void Solver::pw_delete(){
 CRef target=CRef_Undef;int slot=-1;
 for(int i=0;i<clauses.size();++i)if(pw_l2(ca[clauses[i]])){
  if(target!=CRef_Undef)throw std::runtime_error("ABORT_DUPLICATE_L2");
  target=clauses[i];slot=i;
 }
 if(target==CRef_Undef)throw std::runtime_error("ABORT_L2_NOT_IN_DB");
 Clause& c=ca[target];int active=0,refs=0;
 for(int v=0;v<nVars();++v)if(value(v)!=l_Undef && reason(v)==target)++active;
 // Read the raw vectors: operator[] cleans smudged lists in some versions.
 for(int l=0;l<2*nVars();++l){
  for(int i=0;i<watches[toLit(l)].size();++i)if(watches[toLit(l)][i].cref==target)++refs;
  for(int i=0;i<watchesBin[toLit(l)].size();++i)if(watchesBin[toLit(l)][i].cref==target)++refs;
 }
 fprintf(pw_log,"{\"event\":\"REMOVE_PRE\",\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"active_reasons\":%d,\"watch_refs\":%d,\"literals\":[%d,%d,%d],\"values\":[%d,%d,%d],\"reason_use_count\":%llu,\"conflict_analysis_use_count\":%llu,\"propagation_count\":%llu,\"minimization_use_count\":%llu,\"conflict_trigger_count\":%llu}\n",
 (unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),active,refs,pw_int(c[0]),pw_int(c[1]),pw_int(c[2]),toInt(value(c[0])),toInt(value(c[1])),toInt(value(c[2])),pw_reason,pw_analysis,pw_prop,pw_min,pw_conflict);fflush(pw_log);
 if(c.mark()!=0 || c.reloced() || locked(c) || active || refs!=2)
  throw std::runtime_error("ABORT_UNSAFE_L2_REMOVAL");
 for(int i=0;i<learnts.size();++i)if(learnts[i]==target)throw std::runtime_error("ABORT_L2_LEARNED_ALIAS");
 // Same strict-detach / proof deletion / stable vector erasure / free sequence.
 fprintf(certifiedOutput,"d ");
 for(int i=0;i<c.size();++i)fprintf(certifiedOutput,"%i ",pw_int(c[i]));
 fprintf(certifiedOutput,"0\n");
 detachClause(target,true);
 for(int j=slot;j+1<clauses.size();++j)clauses[j]=clauses[j+1];
 clauses.pop();c.mark(1);ca.free(target);pw_removed=true;
 for(int i=0;i<clauses.size();++i)if(clauses[i]==target)throw std::runtime_error("ABORT_POST_REMOVE_DB_REF");
 for(int l=0;l<2*nVars();++l){
  for(int i=0;i<watches[toLit(l)].size();++i)if(watches[toLit(l)][i].cref==target)throw std::runtime_error("ABORT_POST_REMOVE_WATCH_REF");
  for(int i=0;i<watchesBin[toLit(l)].size();++i)if(watchesBin[toLit(l)][i].cref==target)throw std::runtime_error("ABORT_POST_REMOVE_BINARY_REF");
 }
 fprintf(pw_log,"{\"event\":\"REMOVED\",\"conflict\":%llu,\"active_reasons\":0,\"watch_refs_after\":0}\n",(unsigned long long)conflicts);
}
CRef Solver::pw_boundary(){
 if(!pw_enabled)return CRef_Undef;
 if(pw_injected && !pw_removed && pw_remove>=0 && conflicts==(unsigned long long)pw_remove)pw_delete();
 if(pw_injected || conflicts!=600)return CRef_Undef;
 pw_injected=true;pw_inserting=true;
 CRef cr=pw_inject();pw_inserting=false;return cr;
}
