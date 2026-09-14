// One exact-state read-only scan; stable IDs are observer-only metadata.
#include <map>
static std::map<CRef,unsigned long long> kp_ids;
static unsigned long long kp_next=0;
static FILE* kp_out=nullptr;
void kp_init(const char* path){kp_out=fopen(path,"w");if(!kp_out)throw std::runtime_error("check open failed");}
void kp_finish(){fclose(kp_out);}
void Solver::kp_register(CRef cr){kp_ids[cr]=++kp_next;}
void Solver::kp_relocated(){
 std::map<CRef,unsigned long long> ids;
 for(const auto& e:kp_ids){const Clause& c=ca[e.first];if(!c.reloced())throw std::runtime_error("ID_RELOCATION_FAILED");ids[c.relocation()]=e.second;}
 kp_ids.swap(ids);
}
void Solver::kp_check(Lit p,CRef from){
 if(!sp_pending)return;
 if(pw_int(p)!=566 || value(p)!=l_Undef || !pw_l2(ca[from]))throw std::runtime_error("WRONG_KEY_STATE");
 unsigned scanned=0,logical=0,compatible=0;CRef best=CRef_Undef;unsigned long long bestid=~0ULL;
 fprintf(kp_out,"{\"event\":\"ALTERNATE_CHECK\",\"completed_conflicts\":%llu,\"decision\":%llu,\"level\":%d,\"global_event\":%llu,\"global_enqueue\":%llu,\"literal\":566,\"pre_unassigned\":true,\"l2_id\":%llu,\"candidates\":[",(unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),sp_event,sp_enqueues,kp_ids.at(from));
 auto scan=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){
  CRef cr=db[i];const Clause& c=ca[cr];if(cr==from || c.mark()!=0)continue;++scanned;
  int unset=0;bool valid=true;for(int j=0;j<c.size();++j){if(value(c[j])==l_Undef){++unset;if(c[j]!=p)valid=false;}else if(value(c[j])!=l_False)valid=false;}
  if(!valid || unset!=1)continue;
  bool layout=c.size()==2 || (c.size()>2 && c[0]==p);
  fprintf(kp_out,"%s{\"id\":%llu,\"cref\":%u,\"source\":\"%s\",\"logical_valid\":true,\"layout_compatible\":%s,\"literals\":[",logical?",":"",kp_ids.at(cr),cr,c.learnt()?"learned":"original",layout?"true":"false");
  for(int j=0;j<c.size();++j)fprintf(kp_out,"%s%d",j?",":"",pw_int(c[j]));fprintf(kp_out,"],\"values\":[");
  for(int j=0;j<c.size();++j)fprintf(kp_out,"%s\"%s\"",j?",":"",value(c[j])==l_Undef?"UNASSIGNED":"FALSE");fprintf(kp_out,"]}");
  ++logical;if(layout){++compatible;if(kp_ids.at(cr)<bestid){bestid=kp_ids.at(cr);best=cr;}}
 }};
 scan(clauses);scan(learnts);
 fprintf(kp_out,"],\"candidate_count\":%u,\"logical_valid_count\":%u,\"layout_compatible_count\":%u,\"selected_id\":",scanned,logical,compatible);
 if(best==CRef_Undef)fprintf(kp_out,"null");else fprintf(kp_out,"%llu",bestid);
 fprintf(kp_out,",\"status\":\"%s\"}\n",best==CRef_Undef?"NO_COMPATIBLE_ALT_REASON":"COMPATIBLE_ALT_REASON_FOUND");fflush(kp_out);
}
void Solver::kp_read(const Clause& c,Lit pivot){
 if(!sp_disabled || !pw_l2(c))return;
 fprintf(kp_out,"{\"event\":\"EXISTING_L2_ANALYSIS_READ\",\"conflict\":%llu,\"decision\":%llu,\"pivot\":%d}\n",(unsigned long long)conflicts,(unsigned long long)decisions,pivot==lit_Undef?0:pw_int(pivot));fflush(kp_out);
}
