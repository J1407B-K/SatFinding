// A single future-disable flag. Watch entries and clause objects stay intact.
static bool sp_one=false,sp_disabled=false,sp_pending=false;
static unsigned long long sp_event=0,sp_enqueues=0,sp_targets=0;
static unsigned long long sp_new_reason=0,sp_new_conflict=0,sp_analysis=0,sp_min=0,sp_skipped=0;
static FILE* sp_log=nullptr;
static unsigned long long sp_hash_trail(const vec<Lit>& t){
 unsigned long long h=1469598103934665603ULL;
 for(int i=0;i<t.size();++i){int x=pw_int(t[i]);for(unsigned j=0;j<sizeof(x);++j)h=(h^((const unsigned char*)&x)[j])*1099511628211ULL;}
 return h;
}
void sp_init(const char* route,const char* path){
 sp_one=std::string(route)=="ONE_PROP";sp_log=fopen(path,"w");
 if(!sp_log)throw std::runtime_error("event ledger open failed");
}
void sp_finish(){
 fprintf(sp_log,"{\"event\":\"TOTAL\",\"global_event\":%llu,\"global_enqueue_count\":%llu,\"target_count\":%llu,\"disabled\":%s,\"post_disable_new_reason\":%llu,\"post_disable_new_propagation\":%llu,\"post_disable_new_conflict\":%llu,\"post_disable_existing_reason_analysis\":%llu,\"post_disable_existing_reason_minimization\":%llu,\"suppressed_watch_visits\":%llu}\n",sp_event,sp_enqueues,sp_targets,sp_disabled?"true":"false",sp_new_reason,sp_new_reason,sp_new_conflict,sp_analysis,sp_min,sp_skipped);
 fclose(sp_log);
}
bool Solver::sp_skip(CRef cr){
 if(!sp_disabled || !pw_l2(ca[cr]))return false;
 ++sp_skipped;return true;
}
void Solver::sp_use(const Clause& c,int kind){
 if(!sp_disabled || !pw_l2(c))return;
 if(kind==0)++sp_analysis;
 if(kind==1)++sp_min;
 if(kind==2){++sp_new_conflict;throw std::runtime_error("INTERVENTION_FAILURE_NEW_L2_CONFLICT");}
}
void Solver::sp_pre(Lit p,CRef from){
 ++sp_event;++sp_enqueues;
 bool l2=from!=CRef_Undef && pw_l2(ca[from]);
 if(sp_disabled && l2){++sp_new_reason;throw std::runtime_error("INTERVENTION_FAILURE_NEW_L2_REASON");}
 if(!sp_one || conflicts!=655 || !l2 || pw_int(p)!=566)return;
 ++sp_targets;
 // This flag needs no vector/allocator mutation. Check the frozen event before
 // allowing the enqueue itself; an unsupported state stops before mutation.
 if(sp_targets!=1 || decisions!=827 || decisionLevel()!=12 || value(p)!=l_Undef ||
    ca[from].mark()!=0 || ca[from].reloced() || ca[from][0]!=p || pw_inserting)
  throw std::runtime_error("UNSUPPORTED_SAFE_DISABLE");
 for(int i=1;i<ca[from].size();++i)if(value(ca[from][i])!=l_False)
  throw std::runtime_error("UNSUPPORTED_SAFE_DISABLE");
 sp_pending=true;sp_record("TARGET_ENQUEUE_PRE",p,from);
}
void Solver::sp_record(const char* event,Lit p,CRef from){
 fprintf(sp_log,"{\"event\":\"%s\",\"global_event\":%llu,\"global_enqueue\":%llu,\"completed_conflicts\":%llu,\"decision\":%llu,\"level\":%d,\"literal\":%d,\"reason_clause_id\":\"L2_INJECT_C600\",\"reason_cref\":%u,\"reason_source_id\":30149,\"reason_literals\":[",event,sp_event,sp_enqueues,(unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),pw_int(p),from);
 const Clause& c=ca[from];for(int i=0;i<c.size();++i)fprintf(sp_log,"%s%d",i?",":"",pw_int(c[i]));
 fprintf(sp_log,"],\"trail_hash_fnv64\":\"%llu\",\"trail\":[",sp_hash_trail(trail));
 for(int i=0;i<trail.size();++i)fprintf(sp_log,"%s%d",i?",":"",pw_int(trail[i]));
 fprintf(sp_log,"],\"assigned_value\":%d,\"reason_pointer_matches\":%s,\"disabled\":%s}\n",toInt(value(p)),value(p)!=l_Undef&&reason(var(p))==from?"true":"false",sp_disabled?"true":"false");fflush(sp_log);
}
void Solver::sp_post(Lit p,CRef from){
 ++sp_event;
 if(!sp_pending)return;
 // uncheckedEnqueue has just executed assigns, vardata and trail.push_. No
 // propagation can interleave here. Keep that completed enqueue untouched.
 sp_record("TARGET_ENQUEUE_POST",p,from);
 sp_pending=false;sp_disabled=true;++sp_event;
 sp_record("FUTURE_DISABLED",p,from);
}
