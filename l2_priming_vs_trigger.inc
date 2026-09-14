// Only the one original clause is observed. No L2 is injected in either route.
static CRef ut_clause=CRef_Undef;
static bool ut_treatment=false,ut_first=false,ut_eligible=false,ut_done=false,ut_inside=false;
static bool ut_wait_enqueue=false,ut_wait_propagate=false;
static unsigned long long ut_event=0,ut_enqueues=0,ut_count=0;
static FILE* ut_log=nullptr;
void ut_init(const char* dir,bool treatment){
 lt_dir=dir;lt_run="local";ut_treatment=treatment;ut_log=fopen((lt_dir+"/opportunity.jsonl").c_str(),"w");
 if(!ut_log)throw std::runtime_error("log open failed");
}
void ut_finish(){fprintf(ut_log,"{\"event\":\"TOTAL\",\"first_logical_found\":%s,\"safe_native_opportunity_found\":%s,\"interventions\":%llu,\"global_event\":%llu}\n",ut_first?"true":"false",ut_eligible?"true":"false",ut_count,ut_event);fclose(ut_log);}
void Solver::ut_register(CRef cr){
 const Clause& c=ca[cr];if(c.learnt()||c.size()!=3)return;
 std::vector<int> a;for(int i=0;i<3;++i)a.push_back(lt_int(c[i]));std::sort(a.begin(),a.end());
 if(a==std::vector<int>({565,566,567})){
  if(ut_clause!=CRef_Undef)throw std::runtime_error("DUPLICATE_TARGET_CLAUSE");ut_clause=cr;
 }
}
void Solver::ut_note(const char* event,Lit p){
 fprintf(ut_log,"{\"event\":\"%s\",\"global_event\":%llu,\"global_enqueue\":%llu,\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"qhead\":%d,\"literal\":%d}\n",event,ut_event,ut_enqueues,(LU)conflicts,(LU)decisions,decisionLevel(),qhead,p==lit_Undef?0:lt_int(p));fflush(ut_log);
}
void Solver::ut_pre(Lit p){
 ++ut_event;++ut_enqueues;
 if(ut_wait_enqueue&&!ut_inside){ut_note("DEFAULT_NEXT_ENQUEUE",p);ut_wait_enqueue=false;}
}
void Solver::ut_dequeue(Lit p){
 ++ut_event;if(ut_wait_propagate&&!ut_inside){ut_note("DEFAULT_NEXT_PROPAGATE",p);ut_wait_propagate=false;}
}
void Solver::ut_check(const char* where,bool safe){
 if(ut_inside||ut_eligible||ut_clause==CRef_Undef)return;
 const Clause& c=ca[ut_clause];Lit p=mkLit(565,false);
 if(c.mark()!=0 || value(p)!=l_Undef || value(mkLit(566,false))!=l_False || value(mkLit(564,false))!=l_False)return;
 bool layout=c.size()==3&&c[0]==p;
 if(!ut_first || (layout&&safe)){
  const char* event=!ut_first?"FIRST_LOGICAL_UNIT":"FIRST_SAFE_NATIVE_UNIT";
  fprintf(ut_log,"{\"event\":\"%s\",\"where\":\"%s\",\"global_event\":%llu,\"global_enqueue\":%llu,\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"qhead\":%d,\"clause_id\":2589,\"cref\":%u,\"literals\":[%d,%d,%d],\"values_566_567_565\":[\"UNASSIGNED\",\"FALSE\",\"FALSE\"],\"native_layout\":%s,\"safe_insertion_site\":%s}\n",event,where,ut_event,ut_enqueues,(LU)conflicts,(LU)decisions,decisionLevel(),qhead,ut_clause,lt_int(c[0]),lt_int(c[1]),lt_int(c[2]),layout?"true":"false",safe?"true":"false");fflush(ut_log);
 }
 if(!ut_first){ut_first=true;lt_snapshot("FIRST_LOGICAL_UNIT");}
 if(!layout||!safe)return;
 ut_eligible=true;lt_snapshot("TRIGGER_PRE");
 ut_wait_enqueue=ut_wait_propagate=true;
 if(!ut_treatment)return;
 // This callback is after a completed enqueue or before search propagate.
 // It cannot invalidate an already selected pending uncheckedEnqueue.
 ut_done=true;ut_inside=true;++ut_count;
 ut_note("EARLY_ENQUEUE_BEGIN",p);uncheckedEnqueue(p,ut_clause);
 ut_note("EARLY_ENQUEUE_END",p);lt_snapshot("TRIGGER_POST");ut_inside=false;
 // Counterfactual native next actions come exclusively from the control run.
 ut_wait_enqueue=ut_wait_propagate=false;
}
