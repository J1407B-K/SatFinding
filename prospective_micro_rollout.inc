#include <map>
#include <set>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <fstream>
#include <string>
#include <chrono>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <signal.h>
#include <sys/stat.h>
typedef unsigned long long HU;
static FILE* hc_out=nullptr;
static HU hc_enqueues=0,hc_ids_next=0;
static std::map<CRef,HU> hc_ids;
static int pm_role=0,pm_bucket=0,pm_last_bucket=-1,pm_full_at=0;
static int pm_start=100,pm_end=700;
static std::string pm_dir,pm_mode,pm_tag;
static bool pm_conflicted=false,pm_done=false;
static HU pm_watchers=0,pm_dequeues=0,pm_enum=0,pm_potential_work=0;
static HU pm_a0=0,pm_r0=0,pm_b0=0,pm_w0=0,pm_d0=0,pm_dec0=0;
static int pm_conflict_level=0,pm_bt=0,pm_lbd=0,pm_jump=0;
static HU pm_conflict_id=0;
static std::vector<int> pm_conflict,pm_learned;
static std::set<int> pm_visited;
static double pm_birth=0;
static int hc_lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static HU hc_hash(const void* p,size_t n,HU h=1469598103934665603ULL){const unsigned char* a=(const unsigned char*)p;for(size_t i=0;i<n;++i)h=(h^a[i])*1099511628211ULL;return h;}
static double pm_now(){return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();}
static double pm_cpu(){struct rusage u;getrusage(RUSAGE_SELF,&u);return u.ru_utime.tv_sec+u.ru_utime.tv_usec*1e-6+u.ru_stime.tv_sec+u.ru_stime.tv_usec*1e-6;}
static void pm_array(FILE*f,const std::vector<int>&a){fprintf(f,"[");for(size_t i=0;i<a.size();++i)fprintf(f,"%s%d",i?",":"",a[i]);fprintf(f,"]");}
static std::string pm_path(const char*s){return pm_dir+"/"+pm_tag+s;}
static HU pm_ticks(){return sf_analysis-pm_a0+sf_redundancy-pm_r0+sf_binary-pm_b0+pm_watchers-pm_w0+pm_dequeues-pm_d0;}
static void pm_budget(){if(pm_role==1&&pm_ticks()>100000){fprintf(hc_out,"{\"event\":\"BUDGET\",\"status\":\"UNKNOWN_WORK_LIMIT\",\"work_ticks\":%llu}\n",pm_ticks());fflush(hc_out);_exit(0);}}
static void pm_watch(){++pm_watchers;pm_budget();}
static void pm_visit(int v){if(pm_role&&!pm_done)pm_visited.insert(v+1);pm_budget();}
void hc_init(const char*path,int which){
 pm_dir=path;pm_full_at=which;pm_mode=getenv("PM_MODE")?getenv("PM_MODE"):"shadow";
 if(getenv("PM_START"))pm_start=atoi(getenv("PM_START"));
 if(getenv("PM_END"))pm_end=atoi(getenv("PM_END"));
 hc_out=fopen((pm_dir+"/states.jsonl").c_str(),"w");if(!hc_out)throw std::runtime_error("LOG_OPEN");
}
static void pm_stop(const char*s){fprintf(hc_out,"{\"event\":\"STOP\",\"status\":\"%s\"}\n",s);fflush(hc_out);_exit(0);}
void pm_finish(const char*status){
 fprintf(hc_out,"{\"event\":\"FINISH\",\"status\":\"%s\",\"role\":%d,\"analysis_ops\":%llu,\"redundancy\":%llu,\"binary\":%llu,\"watchers\":%llu,\"dequeues\":%llu,\"enumeration_literal_visits\":%llu,\"potential_literal_visits\":%llu,\"cpu_seconds\":%.9f,\"suffix_wall_seconds\":%.9f}\n",status,pm_role,sf_analysis,sf_redundancy,sf_binary,pm_watchers,pm_dequeues,pm_enum,pm_potential_work,pm_cpu(),pm_birth?pm_now()-pm_birth:0);fflush(hc_out);
}
#include "prospective_micro_rollout_state.inc"
void Solver::hc_before_enqueue(){++hc_enqueues;}
void Solver::hc_boundary(){
 if(pm_role==1 && decisions-pm_dec0>256){fprintf(hc_out,"{\"event\":\"BUDGET\",\"status\":\"UNKNOWN_DECISION_LIMIT\"}\n");fflush(hc_out);_exit(0);}
 hc_observe();
}
void Solver::pm_dequeue(){++pm_dequeues;pm_budget();}
void Solver::pm_conflict_hook(CRef cr){
 if(!pm_role||pm_done||pm_conflicted)return;
 pm_conflicted=true;pm_conflict_level=decisionLevel();pm_conflict_id=hc_ids.at(cr);
 const Clause& c=ca[cr];for(int j=0;j<c.size();++j)pm_conflict.push_back(hc_lit(c[j]));
}
void Solver::pm_analysis_hook(const vec<Lit>&l,int bt,unsigned glue){
 if(!pm_role||pm_done)return;
 if(!pm_conflicted)throw std::runtime_error("ANALYSIS_WITHOUT_CONFLICT");
 pm_bt=bt;pm_lbd=glue;pm_jump=pm_conflict_level-bt;
 std::set<int> levels;for(int i=0;i<l.size();++i){pm_learned.push_back(hc_lit(l[i]));levels.insert(level(var(l[i])));}
 if((int)levels.size()!=pm_lbd)throw std::runtime_error("LBD_MISMATCH");
 pm_budget();
}
void Solver::pm_backtrack_hook(){
 if(!pm_role||pm_done||!pm_conflicted)return;
 if(decisionLevel()!=pm_bt)throw std::runtime_error("BACKTRACK_MISMATCH");
 std::vector<int> retained,pending;for(int i=0;i<trail.size();++i){retained.push_back(hc_lit(trail[i]));if(i>=qhead)pending.push_back(hc_lit(trail[i]));}std::sort(retained.begin(),retained.end());
 std::set<int> units;
 auto scan=[&](const vec<CRef>&db){for(int i=0;i<db.size();++i){const Clause&c=ca[db[i]];if(c.mark())continue;int n=0;bool sat=false;Lit p=lit_Undef;for(int j=0;j<c.size();++j){++pm_potential_work;sat|=value(c[j])==l_True;if(value(c[j])==l_Undef){++n;p=c[j];}}if(!sat&&n==1)units.insert(hc_lit(p));}};
 scan(clauses);scan(learnts);
 int n=0,u=0;bool sat=false;for(int x:pm_learned){++pm_potential_work;Lit p=mkLit(abs(x)-1,x<0);sat|=value(p)==l_True;if(value(p)==l_Undef){++n;u=x;}}if(!sat&&n==1)units.insert(u);
 fprintf(hc_out,"{\"event\":\"HORIZON\",\"status\":\"COMPLETE\",\"conflict_index\":%llu,\"conflict_id\":%llu,\"conflict_level\":%d,\"conflict_clause\":",(HU)conflicts,pm_conflict_id,pm_conflict_level);pm_array(hc_out,pm_conflict);
 fprintf(hc_out,",\"learned_clause\":");pm_array(hc_out,pm_learned);
 fprintf(hc_out,",\"learned_length\":%zu,\"lbd\":%d,\"backtrack_level\":%d,\"backjump\":%d,\"analysis_visited\":%zu,\"retained_assignments\":",pm_learned.size(),pm_lbd,pm_bt,pm_jump,pm_visited.size());pm_array(hc_out,retained);
 fprintf(hc_out,",\"pending_literals\":");pm_array(hc_out,pending);
 fprintf(hc_out,",\"qhead\":%d,\"trail_length\":%d,\"immediate_potential\":%zu,\"analysis_ops\":%llu,\"redundancy_ops\":%llu,\"binary_ops\":%llu,\"watcher_visits\":%llu,\"dequeues\":%llu,\"decisions_to_horizon\":%llu,\"work_ticks\":%llu,\"potential_literal_visits\":%llu,\"cpu_seconds\":%.9f,\"wall_seconds\":%.9f}\n",qhead,trail.size(),units.size(),sf_analysis-pm_a0,sf_redundancy-pm_r0,sf_binary-pm_b0,pm_watchers-pm_w0,pm_dequeues-pm_d0,(HU)decisions-pm_dec0,pm_ticks(),pm_potential_work,pm_cpu(),pm_now()-pm_birth);
 fflush(hc_out);pm_done=true;
 if(pm_role==1)_exit(0);
}

void Solver::hc_observe(){
 if(pm_role)return;
 int bucket=((int)conflicts/100)*100;
 bool smoke=pm_mode=="smoke_shadow"||pm_mode=="smoke_full";
 if(smoke){if(conflicts!=0||decisions!=18||hc_enqueues!=263||trail.size()!=263||qhead!=252)return;bucket=0;}
 else {if((int)conflicts>=pm_end)pm_stop("CHECKPOINT_SCAN_COMPLETED");if(bucket<pm_start||bucket==pm_last_bucket)return;}
 struct Action{CRef cr;Lit p;HU id;};std::vector<Action>actions;
 double enum_start=pm_now(),enum_cpu=pm_cpu();HU enum0=pm_enum;
 auto scan=[&](const vec<CRef>&db){for(int i=0;i<db.size();++i){CRef cr=db[i];const Clause&c=ca[cr];if(c.mark())continue;int n=0;bool sat=false;Lit p=lit_Undef;for(int j=0;j<c.size();++j){++pm_enum;sat|=value(c[j])==l_True;if(value(c[j])==l_Undef){++n;p=c[j];}}if(!sat&&n==1&&(c.size()==2||(c.size()>2&&c[0]==p)))actions.push_back({cr,p,hc_ids.at(cr)});}};
 scan(clauses);scan(learnts);
 if(actions.size()<2)return;
 std::sort(actions.begin(),actions.end(),[](const Action&a,const Action&b){return a.id<b.id;});
 pm_last_bucket=bucket;
 if((pm_mode=="full"||pm_mode=="smoke_full")&&bucket!=pm_full_at)return;
 pm_bucket=bucket;
 HU state=hc_state_hash(),raw=hc_hash(this,sizeof(Solver)),heap=order_heap.lt_hash_state();
 if(smoke&&state!=422271443557180589ULL)throw std::runtime_error("SMOKE_STATE_MISMATCH");
 int take=std::min(16,(int)actions.size());
 fprintf(hc_out,"{\"event\":\"STATE\",\"bucket\":%d,\"state_hash\":\"%llu\",\"raw_hash\":\"%llu\",\"heap_hash\":\"%llu\",\"conflicts\":%llu,\"decisions\":%llu,\"level\":%d,\"trail_length\":%d,\"qhead\":%d,\"global_enqueue\":%llu,\"prefix_analysis\":%llu,\"prefix_redundancy\":%llu,\"prefix_binary\":%llu,\"prefix_watchers\":%llu,\"prefix_dequeues\":%llu,\"legal_count\":%zu,\"selected_count\":%d,\"enumeration_literal_visits\":%llu,\"enumeration_wall_seconds\":%.9f,\"enumeration_cpu_seconds\":%.9f}\n",bucket,state,raw,heap,(HU)conflicts,(HU)decisions,decisionLevel(),trail.size(),qhead,hc_enqueues,sf_analysis,sf_redundancy,sf_binary,pm_watchers,pm_dequeues,actions.size(),take,pm_enum-enum0,pm_now()-enum_start,pm_cpu()-enum_cpu);
 for(size_t i=0;i<actions.size();++i){const auto&a=actions[i];const Clause&c=ca[a.cr];std::vector<int> ls;for(int j=0;j<c.size();++j)ls.push_back(hc_lit(c[j]));fprintf(hc_out,"{\"event\":\"ACTION\",\"bucket\":%d,\"action_index\":%zu,\"id\":%llu,\"literal\":%d,\"source\":\"%s\",\"selected\":%s,\"unit_layout_verified\":true,\"clause\":",bucket,i+1,a.id,hc_lit(a.p),c.learnt()?"learned":"original",i<(size_t)take?"true":"false");pm_array(hc_out,ls);fprintf(hc_out,"}\n");}
 bool full=pm_mode=="full"||pm_mode=="smoke_full";
 fflush(NULL);double package_start=pm_now(),parent_cpu=pm_cpu();
 for(int i=0;i<=take;++i){
  if(hc_state_hash()!=state||hc_hash(this,sizeof(Solver))!=raw||order_heap.lt_hash_state()!=heap)throw std::runtime_error("PARENT_STATE_MUTATED");
  pm_tag="C"+std::to_string(bucket)+(full?"_FULL_":"_SHADOW_")+std::to_string(i);
  pm_a0=sf_analysis;pm_r0=sf_redundancy;pm_b0=sf_binary;pm_w0=pm_watchers;pm_d0=pm_dequeues;pm_dec0=decisions;
  fflush(NULL);double start=pm_now(),cpu=pm_cpu();pid_t pid=fork();double fork_end=pm_now();
  if(pid<0)throw std::runtime_error("FORK_FAILED");
  if(pid==0){
   pm_birth=start;pm_role=full?2:1;alarm(full?240:5);
   if(hc_state_hash()!=state||hc_hash(this,sizeof(Solver))!=raw||order_heap.lt_hash_state()!=heap)_exit(46);
   fclose(hc_out);hc_out=fopen(pm_path(".trace.jsonl").c_str(),"w");if(!hc_out)_exit(45);
   fprintf(hc_out,"{\"event\":\"PRE_STATE\",\"state_hash\":\"%llu\",\"raw_hash\":\"%llu\",\"heap_hash\":\"%llu\",\"action_index\":%d}\n",state,raw,heap,i);fflush(hc_out);
   long pos=ftell(certifiedOutput);if(pos<0)_exit(47);FILE*dst=fopen(pm_path(".drup").c_str(),"w");if(!dst)_exit(48);
   std::ifstream src(pm_dir+"/prefix.drup",std::ios::binary);for(long k=0;k<pos;++k){int ch=src.get();if(ch==EOF)_exit(49);fputc(ch,dst);}fclose(certifiedOutput);certifiedOutput=dst;
   if(!freopen(pm_path(".stdout.txt").c_str(),"w",stdout))_exit(50);
   if(i){const auto&a=actions[i-1];const Clause&c=ca[a.cr];if(value(a.p)!=l_Undef||!(c.size()==2||(c.size()>2&&c[0]==a.p)))_exit(51);for(int j=0;j<c.size();++j)if(c[j]!=a.p&&value(c[j])!=l_False)_exit(52);uncheckedEnqueue(a.p,a.cr);fprintf(hc_out,"{\"event\":\"EARLY_ENQUEUE\",\"literal\":%d,\"id\":%llu,\"global_enqueue\":%llu}\n",hc_lit(a.p),a.id,hc_enqueues);fflush(hc_out);}
   return;
  }
  double fork_cpu=pm_cpu()-cpu;int status=0;struct rusage usage;if(wait4(pid,&status,0,&usage)!=pid)throw std::runtime_error("WAIT_FAILED");
  double child_cpu=usage.ru_utime.tv_sec+usage.ru_utime.tv_usec*1e-6+usage.ru_stime.tv_sec+usage.ru_stime.tv_usec*1e-6;
  fprintf(hc_out,"{\"event\":\"CHILD_EXIT\",\"bucket\":%d,\"tag\":\"%s\",\"action_index\":%d,\"wait_status\":%d,\"fork_wall_seconds\":%.9f,\"fork_cpu_seconds\":%.9f,\"child_cpu_seconds\":%.9f,\"child_wall_seconds\":%.9f,\"minor_faults\":%ld,\"major_faults\":%ld}\n",bucket,pm_tag.c_str(),i,status,fork_end-start,fork_cpu,child_cpu,pm_now()-start,usage.ru_minflt,usage.ru_majflt);fflush(hc_out);
  if(!(WIFEXITED(status)&&WEXITSTATUS(status)==0)&&!(WIFSIGNALED(status)&&WTERMSIG(status)==SIGALRM))throw std::runtime_error("CHILD_HARD_FAILURE");
 }
 if(hc_state_hash()!=state||hc_hash(this,sizeof(Solver))!=raw)throw std::runtime_error("PARENT_STATE_MUTATED_AFTER_TRIALS");
 fprintf(hc_out,"{\"event\":\"PACKAGE\",\"bucket\":%d,\"parent_cpu_seconds\":%.9f,\"wall_seconds\":%.9f}\n",bucket,pm_cpu()-parent_cpu,pm_now()-package_start);fflush(hc_out);
 if(full||smoke)pm_stop("STATE_COMPLETED");
}
