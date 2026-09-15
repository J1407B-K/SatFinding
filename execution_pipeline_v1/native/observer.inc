#include <sys/stat.h>
#include <map>
#include <vector>
#include <algorithm>
#include <sstream>
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <CommonCrypto/CommonDigest.h>
using HU=unsigned long long;
std::string output_dir,request_path;
bool reached=false,action_verified=false;
static std::map<CRef,HU> hc_ids;
static HU hc_ids_next=0,hc_enqueues=0,watchers=0,dequeues=0,boundary=0;
HU temporal_samples=0;
static HU ep_cp=0;
extern void ep_checkpoint_marker();
static unsigned collected=0, window_index=0;
static std::vector<std::pair<HU,HU>> collection_windows;
static unsigned requested=0, action_budget=0, minimum_legal=0;
static std::string collection_root;
static bool checkpoint_captured=false;
#ifdef OBSERVE_FULL_RUN
static std::vector<int> observe_literals; static FILE* observe_file=nullptr; static HU observe_deq=0;
#endif
static void collection_finish(const char* reason){printf("{\"status\":\"COLLECTION_COMPLETE\",\"reason\":\"%s\",\"collected\":%u}\n",reason,collected);fflush(NULL);std::_Exit(0);}
std::string scientific_counters(){std::ostringstream o;o<<"{\"analysis_resolution_steps\":"<<sf_analysis<<",\"redundancy\":"<<sf_redundancy<<",\"binary\":"<<sf_binary<<",\"watchers\":"<<watchers<<",\"dequeues\":"<<dequeues<<",\"enqueues\":"<<hc_enqueues<<"}";return o.str();}
static HU restart_conflict=0,last_starts=0;
static int conflict_level=0;
struct Sample{HU conflict,dec,deq,ops,watch,enq,restart,since;unsigned length,lbd;int level,bt,jump;};
static Sample ring[128],pending{};static HU pos=0,prev_dec=0,prev_deq=0,prev_ops=0,prev_watch=0,prev_enq=0;
static std::string digest(const std::string&s){unsigned char hash[CC_SHA256_DIGEST_LENGTH];CC_SHA256(s.data(),s.size(),hash);std::ostringstream o;for(auto c:hash)o<<std::hex<<std::setw(2)<<std::setfill('0')<<(int)c;return o.str();}
static std::string read(const std::string&p){std::ifstream f(p);if(!f)throw std::runtime_error("READ "+p);return std::string(std::istreambuf_iterator<char>(f),{});}
static void write(const std::string&p,const std::string&s){std::ofstream f(p);if(!f)throw std::runtime_error("WRITE "+p);f<<s;}
static int lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static std::string hex(double d){char b[100];snprintf(b,sizeof b,"%a",d);return b;}
template<class T> static void array(std::ostream&o,const T&v){o<<'[';bool first=true;for(auto x:v){if(!first)o<<',';first=false;o<<x;}o<<']';}
void Solver::hc_register(CRef cr){hc_ids[cr]=++hc_ids_next;}
void Solver::hc_gc(){std::map<CRef,HU> next;for(auto e:hc_ids)next[ca[e.first].relocation()]=e.second;hc_ids.swap(next);}
void Solver::hc_before_enqueue(){++hc_enqueues;}
static void pm_watch(){++watchers;}
static void pm_visit(int){}
void Solver::pm_dequeue(){++dequeues;
#ifdef OBSERVE_FULL_RUN
 ++observe_deq;
#endif
}
void Solver::pm_conflict_hook(CRef){++temporal_samples;conflict_level=decisionLevel();}
void Solver::pm_analysis_hook(const vec<Lit>&l,int bt,unsigned glue){pending.length=l.size();pending.lbd=glue;pending.level=conflict_level;pending.bt=bt;pending.jump=conflict_level-bt;}
void Solver::pm_backtrack_hook(){pending.conflict=conflicts;pending.dec=decisions-prev_dec;pending.deq=dequeues-prev_deq;pending.ops=sf_analysis-prev_ops;pending.watch=watchers-prev_watch;pending.enq=hc_enqueues-prev_enq;pending.restart=starts;pending.since=conflicts-restart_conflict;ring[pos++%128]=pending;prev_dec=decisions;prev_deq=dequeues;prev_ops=sf_analysis;prev_watch=watchers;prev_enq=hc_enqueues;}
std::string Solver::canonical_logical(){
 std::ostringstream o;o.imbue(std::locale::classic());o<<"logical-v2\n";
 o<<"counters "<<conflicts<<' '<<decisions<<' '<<propagations<<' '<<hc_enqueues<<' '<<decisionLevel()<<' '<<trail.size()<<' '<<qhead<<'\n';
 for(int v=0;v<nVars();++v){o<<"var "<<v+1<<' '<<toInt(value(v))<<' '<<(value(v)==l_Undef?-1:level(v))<<" reason ";std::vector<int> rs;if(value(v)!=l_Undef&&reason(v)!=CRef_Undef){const Clause&c=ca[reason(v)];for(int j=0;j<c.size();j++)rs.push_back(lit(c[j]));std::sort(rs.begin(),rs.end());}array(o,rs);o<<'\n';}
 o<<"trail ";for(int i=0;i<trail.size();i++)o<<lit(trail[i])<<' ';o<<"\nlimits ";for(int i=0;i<trail_lim.size();i++)o<<trail_lim[i]<<' ';o<<'\n';return o.str();
}
std::string Solver::canonical_heuristic(){
 std::ostringstream o;o.imbue(std::locale::classic());o<<"heuristic-v2\n";
 for(int v=0;v<nVars();v++)o<<"var "<<v+1<<' '<<hex(activity[v])<<' '<<(int)polarity[v]<<' '<<(int)decision[v]<<'\n';
 o<<"heap_pop_order ";array(o,order_heap.semantic_order());o<<'\n';
 o<<"increments "<<hex(var_inc)<<' '<<hex(cla_inc)<<" random "<<hex(random_seed)<<' '<<hex(random_var_freq)<<' '<<rnd_pol<<' '<<phase_saving<<'\n';
 o<<"decay "<<hex(var_decay)<<' '<<hex(clause_decay)<<" restart "<<starts<<' '<<conflictsRestarts<<' '<<hex(sumLBD)<<' '<<curRestart<<' '<<nbclausesbeforereduce<<' '<<hex(K)<<' '<<hex(R)<<'\n';
 o<<"simplify "<<simpDB_assigns<<' '<<simpDB_props<<' '<<remove_satisfied<<'\n';
 o<<"lbd_queue "<<lbdQueue.maxSize()<<' '<<lbdQueue.getsum()<<' ';array(o,lbdQueue.semantic_values());o<<"\ntrail_queue "<<trailQueue.maxSize()<<' '<<trailQueue.getsum()<<' ';array(o,trailQueue.semantic_values());o<<'\n';
 // Stable semantic clause identities preserve traversal order and active watched-literal order.
 auto db=[&](const vec<CRef>& refs){for(int i=0;i<refs.size();i++){Clause&c=ca[refs[i]];o<<"clause "<<hc_ids.at(refs[i])<<' '<<c.learnt()<<' '<<c.mark()<<' ';for(int j=0;j<c.size();j++)o<<lit(c[j])<<' ';if(c.learnt())o<<hex(c.activity())<<' '<<c.lbd()<<' '<<c.canBeDel();o<<'\n';}};db(clauses);db(learnts);
 // Watch scheduling uses semantic clause IDs and literals, never allocator references.
 for(int l=0;l<2*nVars();l++){auto ws=[&](const vec<Watcher>& w,const char*kind){o<<kind<<' '<<lit(toLit(l))<<' ';for(int i=0;i<w.size();i++){if(ca[w[i].cref].mark())continue;o<<hc_ids.at(w[i].cref)<<':'<<lit(w[i].blocker)<<' ';}o<<'\n';};ws(watches[toLit(l)],"watch");ws(watchesBin[toLit(l)],"binary_watch");}
 return o.str();
}
void Solver::hc_boundary(){
#ifdef REPLAY
 ep_hook();
#endif
if(last_starts!=(HU)starts){last_starts=starts;restart_conflict=conflicts;}hc_observe();}
void Solver::hc_observe(){
 ++boundary;
#ifdef REPLAY
 if(reached)return;
#endif
#ifdef COLLECTOR
 static bool plan_loaded=false;
 if(!plan_loaded){std::ifstream f(request_path);unsigned n;f>>action_budget>>requested>>minimum_legal>>n;if(!f||action_budget<1||action_budget>6||!requested||!minimum_legal||n<requested)throw std::runtime_error("COLLECTION_PLAN");HU previous=0;for(unsigned i=0;i<n;i++){HU lo,hi;f>>lo>>hi;if(!f||lo>hi||(i&&lo<=previous))throw std::runtime_error("COLLECTION_WINDOWS");collection_windows.push_back({lo,hi});previous=hi;}std::string extra;if(f>>extra)throw std::runtime_error("PLAN_TRAILING_INPUT");collection_root=output_dir;plan_loaded=true;}
 while(window_index<collection_windows.size()&&conflicts>collection_windows[window_index].second)++window_index;
 if(window_index==collection_windows.size() && !checkpoint_captured){
#ifdef OBSERVE_FULL_RUN
 return;
#else
 collection_finish("WINDOWS_EXHAUSTED");
#endif
}
 if(conflicts<collection_windows[window_index].first)return;
 struct Action{HU id;CRef cr;Lit p;};std::vector<Action> actions;
 auto scan=[&](const vec<CRef>&db){for(int i=0;i<db.size();i++){CRef cr=db[i];const Clause&c=ca[cr];if(c.mark())continue;bool sat=false;int n=0;Lit p=lit_Undef;for(int j=0;j<c.size();j++){sat|=value(c[j])==l_True;if(value(c[j])==l_Undef){n++;p=c[j];}}if(!sat&&n==1&&(c.size()==2||(c.size()>2&&c[0]==p)))actions.push_back({hc_ids.at(cr),cr,p});}};scan(clauses);scan(learnts);if(actions.size()<minimum_legal)return;
 std::sort(actions.begin(),actions.end(),[](const Action&a,const Action&b){return a.id<b.id;});
#else
 static bool loaded=false;static HU want=0,wc=0,wd=0;static int wl=0,wt=0,wq=0;static std::string lh,hh;static HU aid=0;static int implied=0,source=0;static std::vector<int> frozen;
 if(!loaded){std::ifstream f(request_path);int n;f>>want>>wc>>wd>>wl>>wt>>wq>>lh>>hh>>aid>>implied>>source>>n;if(!f||n<0)throw std::runtime_error("REQUEST_PARSE");for(int i=0,x;i<n;i++){f>>x;frozen.push_back(x);}if(!f)throw std::runtime_error("CLAUSE_PARSE");loaded=true;}
 if(boundary<want)return;if(boundary!=want||conflicts!=wc||decisions!=wd||decisionLevel()!=wl||trail.size()!=wt||qhead!=wq)throw std::runtime_error("REPLAY_CHECKPOINT_MISMATCH");
#endif
#ifdef COLLECTOR
 output_dir=collection_root+"/S"+std::to_string(collected+1);
 if(!checkpoint_captured && mkdir(output_dir.c_str(),0755)!=0)throw std::runtime_error("CHECKPOINT_DIRECTORY_EXISTS");
 checkpoint_captured=true;
#endif
 std::string logical=canonical_logical(),heuristic=canonical_heuristic();
 write(output_dir+"/logical.txt",logical);write(output_dir+"/heuristic.txt",heuristic);
#ifdef REPLAY
 if(digest(logical)!=lh||digest(heuristic)!=hh)throw std::runtime_error("REPLAY_CANONICAL_MISMATCH");
#endif
#ifdef REPLAY
 reached=true;ep_cp=conflicts;ep_dump(output_dir+"/state");ep_bytes(output_dir+"/state.protected.bin");
#endif
 std::ostringstream st;st<<"{\"boundary\":"<<boundary<<",\"conflicts\":"<<conflicts<<",\"decisions\":"<<decisions<<",\"level\":"<<decisionLevel()<<",\"trail_length\":"<<trail.size()<<",\"qhead\":"<<qhead<<",\"canonical_logical_state_hash\":\""<<digest(logical)<<"\",\"canonical_heuristic_state_hash\":\""<<digest(heuristic)<<"\"}";write(output_dir+"/checkpoint.json",st.str());
 write(output_dir+"/prefix_counters.json",scientific_counters());
#ifdef COLLECTOR
 int take=std::min((unsigned)actions.size(),action_budget);
 std::ostringstream a;a<<"{\"legal_count\":"<<actions.size()<<",\"K\":"<<action_budget<<",\"selected_count\":"<<take<<",\"selected\":[";for(int i=0;i<take;i++){auto act=actions[i];const Clause&c=ca[act.cr];if(i)a<<',';a<<"{\"rank\":"<<i+1<<",\"id\":"<<act.id<<",\"literal\":"<<lit(act.p)<<",\"source\":\""<<(c.learnt()?"learned":"original")<<"\",\"unit_layout_verified\":true,\"unassigned_count\":1,\"true_count\":0,\"clause\":[";for(int j=0;j<c.size();j++)a<<(j?",":"")<<lit(c[j]);a<<"]}";}a<<"],\"all_actions\":[";for(size_t i=0;i<actions.size();i++){auto act=actions[i];const Clause&c=ca[act.cr];if(i)a<<',';a<<"{\"rank\":"<<i+1<<",\"id\":"<<act.id<<",\"literal\":"<<lit(act.p)<<",\"source\":\""<<(c.learnt()?"learned":"original")<<"\",\"unit_layout_verified\":true,\"unassigned_count\":1,\"true_count\":0,\"clause\":[";for(int j=0;j<c.size();j++)a<<(j?",":"")<<lit(c[j]);a<<"]}";}a<<"],\"eligible_ids\":[";for(size_t i=0;i<actions.size();i++)a<<(i?",":"")<<actions[i].id;a<<"]}";write(output_dir+"/actions.json",a.str());
 std::ostringstream t;t<<"{\"logical_samples\":[";HU n=std::min(pos,128ULL);for(HU i=0;i<n;i++){const Sample&s=ring[(pos-n+i)%128];if(i)t<<',';t<<"{\"conflict_index\":"<<s.conflict<<",\"learned_length\":"<<s.length<<",\"lbd\":"<<s.lbd<<",\"backtrack_level\":"<<s.bt<<",\"backjump_depth\":"<<s.jump<<",\"decisions_delta\":"<<s.dec<<",\"dequeues_delta\":"<<s.deq<<",\"analysis_ops_delta\":"<<s.ops<<",\"watcher_visits_delta\":"<<s.watch<<",\"enqueues_delta\":"<<s.enq<<",\"restart_epoch\":"<<s.restart<<",\"conflicts_since_restart\":"<<s.since<<"}";}t<<"]}";write(output_dir+"/temporal_raw.json",t.str());
 #ifdef OBSERVE_FULL_RUN
 for(auto const& act: actions) observe_literals.push_back(lit(act.p));
 observe_file=fopen((output_dir+"/native_timing.jsonl").c_str(),"w");
#else
 ++collected;++window_index;
 if(collected==requested)collection_finish("REQUEST_SATISFIED");
#endif
#else
 if(aid){CRef cr=CRef_Undef;for(auto e:hc_ids)if(e.second==aid){cr=e.first;break;}if(cr==CRef_Undef)throw std::runtime_error("CLAUSE_ID_MISSING");const Clause&c=ca[cr];if(c.mark()||c.learnt()!=source||c.size()!=(int)frozen.size())throw std::runtime_error("CLAUSE_METADATA");std::vector<int> actual;for(int j=0;j<c.size();j++)actual.push_back(lit(c[j]));std::sort(actual.begin(),actual.end());std::sort(frozen.begin(),frozen.end());if(actual!=frozen)throw std::runtime_error("CLAUSE_CONTENT");Lit p=mkLit(abs(implied)-1,implied<0);int n=0;for(int j=0;j<c.size();j++){if(c[j]==p)n++;else if(value(c[j])!=l_False)throw std::runtime_error("NOT_UNIT");}if(n!=1||value(p)!=l_Undef||!(c.size()==2||(c.size()>2&&c[0]==p)))throw std::runtime_error("ILLEGAL_IMPLICATION");uncheckedEnqueue(p,cr);action_verified=true;}
#endif
}

#include "/Users/kqs-mac/Go/GoProjects/SatFinding/execution_pipeline_v1/transplant.inc"
