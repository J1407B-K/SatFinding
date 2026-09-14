// Bounded to previous/key/following conflict; no full-run event trace.
static FILE* sc_log=nullptr;
static bool sc_gate=true;
static std::set<unsigned long long> sc_boundaries;
void sc_init(const char* dir,bool gate){lt_dir=dir;lt_run="local";sc_gate=gate;sc_log=fopen((lt_dir+"/local.jsonl").c_str(),"w");if(!sc_log)throw std::runtime_error("local log open failed");}
void sc_finish(){fclose(sc_log);}
void Solver::sc_boundary(){
 if(conflicts>=655 && conflicts<=657 && !sc_boundaries.count(conflicts)){
  sc_boundaries.insert(conflicts);lt_snapshot("C"+std::to_string(conflicts)+"_COMPLETED_BEFORE_REMOVE");
 }
}
void Solver::sc_conflict(CRef cr){
 if(conflicts<655 || conflicts>657)return;
 fprintf(sc_log,"{\"event\":\"CONFLICT_ENTRY\",\"conflict\":%llu,\"clause\":[",(LU)conflicts);
 const Clause& c=ca[cr];for(int i=0;i<c.size();++i)fprintf(sc_log,"%s%d",i?",":"",lt_int(c[i]));fprintf(sc_log,"]}\n");
 lt_snapshot("C"+std::to_string(conflicts)+"_PRE_ANALYSIS");
 if(conflicts==656 && sc_gate)throw std::runtime_error("PRE_CONFLICT_GATE");
}
void Solver::sc_enqueue(Lit p,CRef from){
 if(conflicts<654 || conflicts>656)return;
 fprintf(sc_log,"{\"event\":\"ENQUEUE_PRE\",\"completed_conflicts\":%llu,\"decision\":%llu,\"level\":%d,\"literal\":%d,\"l2_reason\":%s,\"reason\":[",(LU)conflicts,(LU)decisions,decisionLevel(),lt_int(p),from!=CRef_Undef&&lt_l2(ca[from])?"true":"false");
 if(from!=CRef_Undef){const Clause& c=ca[from];for(int i=0;i<c.size();++i)fprintf(sc_log,"%s%d",i?",":"",lt_int(c[i]));}fprintf(sc_log,"]}\n");
}
void Solver::sc_analysis_clause(const Clause& c,Lit pivot){
 if(conflicts<655 || conflicts>657)return;
 fprintf(sc_log,"{\"event\":\"ANALYSIS_CLAUSE\",\"conflict\":%llu,\"pivot\":%d,\"l2\":%s,\"literals\":[",(LU)conflicts,pivot==lit_Undef?0:lt_int(pivot),lt_l2(c)?"true":"false");for(int i=0;i<c.size();++i)fprintf(sc_log,"%s%d",i?",":"",lt_int(c[i]));fprintf(sc_log,"]}\n");
}
void Solver::sc_visit(Lit p){if(conflicts>=655&&conflicts<=657)fprintf(sc_log,"{\"event\":\"VISIT\",\"conflict\":%llu,\"literal\":%d,\"variable\":%d}\n",(LU)conflicts,lt_int(p),var(p)+1);}
void Solver::sc_bump(Var v){if(conflicts>=655&&conflicts<=657)fprintf(sc_log,"{\"event\":\"BUMP\",\"conflict\":%llu,\"variable\":%d,\"activity_after\":\"%a\"}\n",(LU)conflicts,v+1,activity[v]);}
void Solver::sc_learned(const vec<Lit>& c,int bt){
 if(conflicts<655 || conflicts>657)return;
 fprintf(sc_log,"{\"event\":\"LEARNED\",\"conflict\":%llu,\"backtrack_level\":%d,\"literals\":[",(LU)conflicts,bt);for(int i=0;i<c.size();++i)fprintf(sc_log,"%s%d",i?",":"",lt_int(c[i]));fprintf(sc_log,"]}\n");
 lt_snapshot("C"+std::to_string(conflicts)+"_AFTER_ANALYSIS");
}
void Solver::sc_decision(Lit p){if(conflicts>=655&&conflicts<=657){fprintf(sc_log,"{\"event\":\"NEXT_DECISION\",\"completed_conflicts\":%llu,\"literal\":%d}\n",(LU)conflicts,p==lit_Undef?0:lt_int(p));lt_snapshot("C"+std::to_string(conflicts)+"_AFTER_PICK");}}
