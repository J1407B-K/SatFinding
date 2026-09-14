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
static bool frontier_on=false; static std::ofstream frontier_trace; static void frontier_init(); static unsigned long long analysis_id=0;
HU temporal_samples=0;
static unsigned collected=0, window_index=0;
static std::vector<std::pair<HU,HU>> collection_windows;
static unsigned requested=0, action_budget=0, minimum_legal=0;
static std::string collection_root;
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
void Solver::pm_dequeue(){++dequeues; frontier_init(); if(frontier_on) frontier_trace<<"{\"type\":\"propagation_frontier\",\"qhead\":"<<qhead<<",\"trail_length\":"<<trail.size()<<",\"pending\":"<<trail.size()-qhead<<"}\n";}
void Solver::pm_conflict_hook(CRef){++temporal_samples;conflict_level=decisionLevel(); if(frontier_on) frontier_trace<<"{\"type\":\"conflict_detected\",\"conflicts\":"<<conflicts<<"}\n";}
void Solver::pm_analysis_hook(const vec<Lit>&l,int bt,unsigned glue){ ++analysis_id; if(frontier_on){ frontier_trace<<"{\"type\":\"analysis_begin\",\"analysis_id\":"<<analysis_id<<"}\n"; frontier_trace<<"{\"type\":\"first_uip\",\"analysis_id\":"<<analysis_id<<",\"literal\":"<<lit(~l[0])<<"}\n"; frontier_trace<<"{\"type\":\"learned_clause\",\"analysis_id\":"<<analysis_id<<",\"length\":"<<l.size()<<"}\n"; }pending.length=l.size();pending.lbd=glue;pending.level=conflict_level;pending.bt=bt;pending.jump=conflict_level-bt;}
void Solver::pm_backtrack_hook(){ if(frontier_on) frontier_trace<<"{\"type\":\"backtrack_complete\",\"analysis_id\":"<<analysis_id<<"}\n";pending.conflict=conflicts;pending.dec=decisions-prev_dec;pending.deq=dequeues-prev_deq;pending.ops=sf_analysis-prev_ops;pending.watch=watchers-prev_watch;pending.enq=hc_enqueues-prev_enq;pending.restart=starts;pending.since=conflicts-restart_conflict;ring[pos++%128]=pending;prev_dec=decisions;prev_deq=dequeues;prev_ops=sf_analysis;prev_watch=watchers;prev_enq=hc_enqueues;}
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
void Solver::hc_boundary(){if(last_starts!=(HU)starts){last_starts=starts;restart_conflict=conflicts;}hc_observe();}
void Solver::hc_observe(){ return; }

static void frontier_init(){ if(!frontier_on){const char* e=getenv("FRONTIER_OBSERVER"); if(e&&std::string(e)=="on"){frontier_on=true; frontier_trace.open((output_dir+"/trace.jsonl").c_str());}}}
