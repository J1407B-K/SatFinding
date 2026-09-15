static bool au_enabled=false,au_active=false;
static HU au_conflicts=0,au_dequeues=0,au_events=0;
static FILE* au_file=nullptr;
static std::string au_clause(const Clause& c){std::vector<int>v;for(int i=0;i<c.size();++i)v.push_back(lit(c[i]));std::sort(v.begin(),v.end());std::ostringstream o;array(o,v);return o.str();}
std::string Solver::au_state(){
 std::ostringstream o;
 for(int v=0;v<nVars();++v){o<<toInt(value(v))<<':';if(value(v)!=l_Undef){o<<level(v)<<':';if(reason(v)!=CRef_Undef)o<<au_clause(ca[reason(v)]);}o<<';';}
 o<<"trail:";for(int i=0;i<trail.size();i++)o<<lit(trail[i])<<',';
 o<<"limits:";for(int i=0;i<trail_lim.size();i++)o<<trail_lim[i]<<',';
 o<<"qhead:"<<qhead;return digest(o.str());
}
std::string Solver::au_frontier(){std::ostringstream o;for(int i=qhead;i<trail.size();i++)o<<lit(trail[i])<<',';return digest(o.str());}
void Solver::au_emit(const char* kind,const std::string& payload){
 if(!au_active)return;
 fprintf(au_file,"{\"i\":%llu,\"c\":%llu,\"p\":%llu,\"kind\":\"%s\",\"value\":%s",au_events++,au_conflicts,au_dequeues,kind,payload.c_str());
 if(au_conflicts==0)fprintf(au_file,",\"state\":\"%s\",\"frontier\":\"%s\"",au_state().c_str(),au_frontier().c_str());
 fprintf(au_file,"}\n");
}
void Solver::au_start(){
 au_enabled=getenv("TRAJECTORY_AUDIT_ON")!=nullptr;if(!au_enabled)return;
 au_file=fopen((output_dir+"/telemetry.jsonl").c_str(),"w");if(!au_file)throw std::runtime_error("AUDIT_FILE");setvbuf(au_file,nullptr,_IOFBF,1<<20);au_active=true;au_emit("prestate","null");
}
void Solver::au_enqueue(Lit p,CRef from){if(!au_active)return;std::string c=from==CRef_Undef?"null":au_clause(ca[from]);au_emit("enqueue","{\"literal\":"+std::to_string(lit(p))+",\"reason\":"+c+"}");}
void Solver::au_conflict(CRef cr){
 if(!au_active)return;++au_conflicts;
 au_emit("conflict",au_clause(ca[cr]));
 if(au_conflicts==1||au_conflicts==2||au_conflicts==4||au_conflicts==8||au_conflicts==16){
 std::vector<std::string>ls;for(int i=0;i<learnts.size();i++)if(!ca[learnts[i]].mark())ls.push_back(au_clause(ca[learnts[i]]));std::sort(ls.begin(),ls.end());std::string all;for(auto&s:ls)all+=s+"\n";
 au_emit("milestone","{\"k\":"+std::to_string(au_conflicts)+",\"logical\":\""+au_state()+"\",\"learned\":\""+digest(all)+"\",\"frontier\":\""+au_frontier()+"\"}");
 }
}
void Solver::au_learned(const vec<Lit>&l){if(!au_active)return;std::vector<int>v;for(int i=0;i<l.size();i++)v.push_back(lit(l[i]));std::sort(v.begin(),v.end());std::ostringstream o;array(o,v);au_emit("learned",o.str());}
void trajectory_finish(){if(au_file){fflush(au_file);fclose(au_file);au_file=nullptr;}}
