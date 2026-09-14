#include <map>
#include <set>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <fstream>
#include <sstream>
#include <string>
#include <unistd.h>
#include <sys/wait.h>
typedef unsigned long long HU;
static FILE* hc_out=nullptr;
static HU hc_enqueues=0,hc_ids_next=0;
static std::map<CRef,HU> hc_ids;
static std::set<std::pair<HU,int>> cf_previous;
static int cf_index=0,cf_role=0,cf_full_at=0;
static bool cf_child=false,cf_full=false,cf_conflicted=false,cf_learned=false,cf_decided=false;
static std::string cf_dir,fs_tag;
static std::vector<int> cf_dequeues,cf_clause,cf_learnt;
static HU cf_conflict_id=0,cf_conflict_index=0;
static int hc_lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static HU hc_hash(const void* p,size_t n,HU h=1469598103934665603ULL){const unsigned char* a=(const unsigned char*)p;for(size_t i=0;i<n;++i)h=(h^a[i])*1099511628211ULL;return h;}
static void cf_array(FILE* f,const std::vector<int>& a){fprintf(f,"[");for(size_t i=0;i<a.size();++i)fprintf(f,"%s%d",i?",":"",a[i]);fprintf(f,"]");}
static std::string cf_path(int,int,const char* suffix){return cf_dir+"/"+fs_tag+suffix;}
static std::string cf_canonical(std::vector<int> a){std::sort(a.begin(),a.end());std::string s;for(int x:a)s+=std::to_string(x)+" ";return s+"0";}
void hc_init(const char* path,int which){cf_dir=path;cf_full_at=which;hc_out=fopen((cf_dir+"/opportunities.jsonl").c_str(),"w");if(!hc_out)throw std::runtime_error("LOG_OPEN");}
static void cf_stop(const char* status){fprintf(hc_out,"{\"event\":\"STOP\",\"status\":\"%s\",\"opportunity\":%d}\n",status,cf_index);fflush(hc_out);_exit(0);}
void hc_finish(){if(cf_child&&!cf_full){fprintf(hc_out,"{\"event\":\"NO_NEXT_CONFLICT\"}\n");fflush(hc_out);_exit(44);}fprintf(hc_out,"{\"event\":\"FINISH\",\"interventions\":%d}\n",cf_child?cf_role:0);fclose(hc_out);}
void Solver::hc_register(CRef cr){hc_ids[cr]=++hc_ids_next;}
void Solver::hc_gc(){std::map<CRef,HU> next;for(const auto& e:hc_ids){if(!ca[e.first].reloced())throw std::runtime_error("ID_RELOCATION");next[ca[e.first].relocation()]=e.second;}hc_ids.swap(next);}
HU Solver::hc_state_hash(){
 HU h=1469598103934665603ULL;auto add=[&](const void* p,size_t n){h=hc_hash(p,n,h);};
 for(int v=0;v<nVars();++v){int a=toInt(assigns[v]),l=level(v);CRef r=value(v)==l_Undef?CRef_Undef:reason(v);add(&a,sizeof(a));add(&l,sizeof(l));add(&r,sizeof(r));add(&activity[v],sizeof(double));add(&polarity[v],sizeof(char));}
 for(int i=0;i<trail.size();++i){int l=toInt(trail[i]);add(&l,sizeof(l));}for(int i=0;i<trail_lim.size();++i)add(&trail_lim[i],sizeof(int));
 add(&qhead,sizeof(qhead));add(&var_inc,sizeof(var_inc));add(&cla_inc,sizeof(cla_inc));add(&random_seed,sizeof(random_seed));
 HU heaps=order_heap.lt_hash_state(),lq=lbdQueue.lt_hash_state(),tq=trailQueue.lt_hash_state();add(&heaps,sizeof(heaps));add(&lq,sizeof(lq));add(&tq,sizeof(tq));add(&conflicts,sizeof(conflicts));add(&decisions,sizeof(decisions));add(&propagations,sizeof(propagations));add(&starts,sizeof(starts));add(&sumLBD,sizeof(sumLBD));add(&simpDB_props,sizeof(simpDB_props));
 auto db=[&](const vec<CRef>& refs){for(int i=0;i<refs.size();++i){CRef cr=refs[i];Clause& c=ca[cr];add(&cr,sizeof(cr));int n=c.size();add(&n,sizeof(n));for(int j=0;j<n;++j){int l=toInt(c[j]);add(&l,sizeof(l));}if(c.learnt()){float a=c.activity();unsigned l=c.lbd();add(&a,sizeof(a));add(&l,sizeof(l));}}};db(clauses);db(learnts);
 for(int l=0;l<2*nVars();++l){auto ws=[&](const vec<Watcher>& w){int n=w.size();add(&n,sizeof(n));for(int i=0;i<n;++i){add(&w[i].cref,sizeof(CRef));int b=toInt(w[i].blocker);add(&b,sizeof(b));}};ws(watches[toLit(l)]);ws(watchesBin[toLit(l)]);}
 return h;
}

void Solver::hc_before_enqueue(){++hc_enqueues;}
void Solver::hc_boundary(){hc_observe();}
void Solver::hc_observe(){
 if(cf_child)return;
 struct Candidate{HU id;CRef cr;Lit p;};std::vector<Candidate> cs;std::set<std::pair<HU,int>> now;
 auto scan=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){CRef cr=db[i];const Clause& c=ca[cr];if(c.mark()!=0)continue;
  int unset=0;bool sat=false;Lit p=lit_Undef;
  for(int j=0;j<c.size();++j){if(value(c[j])==l_True){sat=true;break;}if(value(c[j])==l_Undef){++unset;p=c[j];}}
  if(sat||unset!=1||!(c.size()==2||(c.size()>2&&c[0]==p)))continue;
  auto key=std::make_pair(hc_ids.at(cr),toInt(p));now.insert(key);if(!cf_previous.count(key))cs.push_back({key.first,cr,p});
 }};scan(clauses);scan(learnts);cf_previous.swap(now);
 std::sort(cs.begin(),cs.end(),[](const Candidate&a,const Candidate&b){return a.id<b.id;});
 for(const auto& cnd:cs){++cf_index;
  if(cf_index==226){if(hc_state_hash()!=422271443557180589ULL || conflicts!=0 || decisions!=18 || decisionLevel()!=18 || trail.size()!=263 || qhead!=252 || hc_enqueues!=263)throw std::runtime_error("FROZEN_STATE_MISMATCH");fs_surface();return;}
 }
}

void Solver::cf_dequeue(Lit p){if(cf_child&&!cf_conflicted)cf_dequeues.push_back(hc_lit(p));}
void Solver::cf_conflict(CRef cr){if(cf_child&&!cf_conflicted){cf_conflicted=true;cf_conflict_index=conflicts;cf_conflict_id=hc_ids.at(cr);const Clause& c=ca[cr];for(int i=0;i<c.size();++i)cf_clause.push_back(hc_lit(c[i]));}}
void Solver::cf_analysis(const vec<Lit>& learned){if(!cf_child||cf_learned)return;cf_learned=true;for(int i=0;i<learned.size();++i)cf_learnt.push_back(hc_lit(learned[i]));
 fprintf(hc_out,"{\"event\":\"LOCAL_RESULT\",\"conflict_index\":%llu,\"conflict_clause_id\":%llu,\"dequeue_literals\":",cf_conflict_index,cf_conflict_id);cf_array(hc_out,cf_dequeues);
 fprintf(hc_out,",\"conflict_clause_literals\":");cf_array(hc_out,cf_clause);fprintf(hc_out,",\"learned_clause_literals\":");cf_array(hc_out,cf_learnt);fprintf(hc_out,"}\n");fflush(hc_out);
 if(!cf_full){std::ofstream f(cf_path(cf_index,cf_role,".canonical.txt"));f<<cf_canonical(cf_clause)<<"\n"<<cf_canonical(cf_learnt)<<"\n";f.close();_exit(0);}
}
void Solver::cf_decision(Lit p){if(cf_child&&cf_learned&&!cf_decided){cf_decided=true;fprintf(hc_out,"{\"event\":\"NEXT_DECISION\",\"literal\":%d,\"conflict\":%llu}\n",hc_lit(p),(HU)conflicts);fflush(hc_out);}}

void Solver::fs_surface(){
 struct Action{CRef cr;Lit p;HU id;};std::vector<Action> actions;
 auto scan=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){CRef cr=db[i];const Clause& c=ca[cr];if(c.mark()!=0)continue;int n=0;bool sat=false;Lit p=lit_Undef;
  for(int j=0;j<c.size();++j){sat|=value(c[j])==l_True;if(value(c[j])==l_Undef){++n;p=c[j];}}
  if(!sat&&n==1&&(c.size()==2||(c.size()>2&&c[0]==p)))actions.push_back({cr,p,hc_ids.at(cr)});
 }};scan(clauses);scan(learnts);std::sort(actions.begin(),actions.end(),[](const Action&a,const Action&b){return a.id<b.id;});
 HU state=hc_state_hash(),raw=hc_hash(this,sizeof(Solver));int take=std::min(32,(int)actions.size());
 fprintf(hc_out,"{\"event\":\"FROZEN_STATE\",\"pre_state_hash\":\"%llu\",\"raw_solver_object_hash\":\"%llu\",\"heap_including_inverse_hash\":\"%llu\",\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"trail_length\":%d,\"qhead\":%d,\"global_enqueue\":%llu,\"analysis_ops_at_snapshot\":%llu,\"restart_epoch\":%llu,\"conflicts_since_restart\":%llu,\"random_seed_hex\":\"%a\",\"legal_action_count\":%zu,\"selected_action_count\":%d}\n",state,raw,order_heap.lt_hash_state(),(HU)conflicts,(HU)decisions,decisionLevel(),trail.size(),qhead,hc_enqueues,sf_analysis,(HU)starts,(HU)conflictsRestarts,random_seed,actions.size(),take);
 for(size_t i=0;i<actions.size();++i){const auto& a=actions[i];const Clause& c=ca[a.cr];
  fprintf(hc_out,"{\"event\":\"LEGAL_ACTION\",\"action_index\":%zu,\"stable_clause_id\":%llu,\"implied_literal\":%d,\"clause_length\":%d,\"source\":\"%s\",\"clause_literals\":[",i+1,a.id,hc_lit(a.p),c.size(),c.learnt()?"learned":"original");
  for(int j=0;j<c.size();++j)fprintf(hc_out,"%s%d",j?",":"",hc_lit(c[j]));fprintf(hc_out,"],\"literal_values\":[");for(int j=0;j<c.size();++j)fprintf(hc_out,"%s\"%s\"",j?",":"",value(c[j])==l_Undef?"UNASSIGNED":"FALSE");
  fprintf(hc_out,"],\"unit_verified\":true,\"native_reason_layout_compatible\":true,\"selected\":%s}\n",(int)i<take?"true":"false");
 }
 // All selection records are durable before any branch starts.
 fflush(NULL);
 for(int i=-1;i<take;++i){
  if(hc_state_hash()!=state || hc_hash(this,sizeof(Solver))!=raw)throw std::runtime_error("PARENT_STATE_MUTATED");
  fs_tag=i<0?"BASELINE":"ACTION_"+std::to_string(i+1);
  fflush(NULL);pid_t pid=fork();if(pid<0)throw std::runtime_error("FORK_FAILED");
  if(pid==0){cf_child=true;cf_full=true;cf_role=i<0?0:1;
   HU inherited=hc_state_hash(),inherited_raw=hc_hash(this,sizeof(Solver));
   if(inherited!=state||inherited_raw!=raw)_exit(46);
   fclose(hc_out);hc_out=fopen(cf_path(0,0,".trace.jsonl").c_str(),"w");if(!hc_out)_exit(45);
   fprintf(hc_out,"{\"event\":\"PRE_STATE\",\"hash\":\"%llu\",\"raw_solver_object_hash\":\"%llu\",\"heap_including_inverse_hash\":\"%llu\",\"same_parent_snapshot\":true}\n",inherited,inherited_raw,order_heap.lt_hash_state());fflush(hc_out);
   long pos=ftell(certifiedOutput);if(pos<0)_exit(47);FILE* dst=fopen(cf_path(0,0,".drup").c_str(),"w");if(!dst)_exit(48);
   std::ifstream src(cf_dir+"/prefix.drup",std::ios::binary);for(long k=0;k<pos;++k){int ch=src.get();if(ch==EOF)_exit(49);fputc(ch,dst);}certifiedOutput=dst;
   if(!freopen(cf_path(0,0,".stdout.txt").c_str(),"w",stdout))_exit(50);
   if(i>=0){const auto& a=actions[i];const Clause& c=ca[a.cr];if(value(a.p)!=l_Undef || !(c.size()==2||(c.size()>2&&c[0]==a.p)))_exit(51);for(int j=0;j<c.size();++j)if(c[j]!=a.p&&value(c[j])!=l_False)_exit(52);
    uncheckedEnqueue(a.p,a.cr);fprintf(hc_out,"{\"event\":\"EARLY_ENQUEUE\",\"literal\":%d,\"reason_id\":%llu,\"global_enqueue\":%llu}\n",hc_lit(a.p),a.id,hc_enqueues);fflush(hc_out);
   }
   return;
  }
  int status=0;if(waitpid(pid,&status,0)!=pid)throw std::runtime_error("WAIT_FAILED");
  fprintf(hc_out,"{\"event\":\"CHILD_EXIT\",\"route\":\"%s\",\"wait_status\":%d}\n",fs_tag.c_str(),status);fflush(hc_out);
 }
 cf_stop("ACTION_SURFACE_COMPLETED");
}
