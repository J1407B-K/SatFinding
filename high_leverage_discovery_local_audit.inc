#include <map>
#include <vector>
#include <stdexcept>
typedef unsigned long long HU;
static FILE* hc_out=nullptr;
static int hc_target=0,hc_next_bucket=250,hc_found=0;
static HU hc_enqueues=0,hc_ids_next=0;
static bool hc_inside=false,hc_did=false;
static std::map<CRef,HU> hc_ids;
static std::vector<int> hc_pending;
static int hc_lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static HU hc_hash(const void* p,size_t n,HU h=1469598103934665603ULL){const unsigned char* a=(const unsigned char*)p;for(size_t i=0;i<n;++i)h=(h^a[i])*1099511628211ULL;return h;}
void hc_init(const char* path,int which){hc_target=which;hc_out=fopen(path,"w");if(!hc_out)throw std::runtime_error("log open failed");}
static void hd_finish();
void hc_finish(){hd_finish();fprintf(hc_out,"{\"event\":\"TOTAL\",\"opportunities\":%d,\"interventions\":%d}\n",hc_found,hc_did?1:0);fclose(hc_out);}
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
void Solver::hc_boundary(){
 if(hc_did)return;
 while((HU)hc_next_bucket <= (HU)conflicts){
  if(hc_target==0||hc_target==hc_next_bucket)hc_pending.push_back(hc_next_bucket);
  hc_next_bucket+=250;
 }
 hc_observe();
}
struct HDTrace{int bucket;std::vector<int> dequeue,learned,clause;HU conflict=0,clause_id=0,decision_conflict=0;int next_decision=0;bool learned_seen=false,done=false;};
static std::vector<HDTrace> hd_traces;
static void hd_start(int bucket){HDTrace t;t.bucket=bucket;hd_traces.push_back(t);}
void Solver::hc_observe(){
 if(hc_inside||hc_did||hc_pending.empty())return;
 CRef selected=CRef_Undef;HU selected_id=~HU(0);Lit p=lit_Undef;
 auto scan=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){CRef cr=db[i];const Clause& c=ca[cr];if(c.mark()!=0)continue;
  int unset=0;Lit unit=lit_Undef;bool sat=false;
  for(int j=0;j<c.size();++j){if(value(c[j])==l_Undef){++unset;unit=c[j];}else if(value(c[j])==l_True){sat=true;break;}}
  if(sat||unset!=1||!(c.size()==2||(c.size()>2&&c[0]==unit)))continue;
  HU id=hc_ids.at(cr);if(id<selected_id){selected=cr;selected_id=id;p=unit;}
 }};
 scan(clauses);scan(learnts);if(selected==CRef_Undef)return;
 const Clause& c=ca[selected];HU state=hc_state_hash();
 for(int bucket:hc_pending){++hc_found;hd_start(bucket);
  fprintf(hc_out,"{\"event\":\"OPPORTUNITY\",\"bucket\":%d,\"global_enqueue\":%llu,\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"literal\":%d,\"reason_id\":%llu,\"reason_source\":\"%s\",\"reason_literals\":[",bucket,hc_enqueues,(HU)conflicts,(HU)decisions,decisionLevel(),hc_lit(p),selected_id,c.learnt()?"learned":"original");
  for(int j=0;j<c.size();++j)fprintf(hc_out,"%s%d",j?",":"",hc_lit(c[j]));
  fprintf(hc_out,"],\"state_fingerprint_fnv64\":\"%llu\",\"unit_and_layout_verified\":true}\n",state);fflush(hc_out);
 }
 hc_pending.clear();
 if(hc_target){
  if(value(p)!=l_Undef||(c.size()>2&&c[0]!=p))throw std::runtime_error("INVALID_PRE_ACTION");
  for(int j=0;j<c.size();++j)if(c[j]!=p&&value(c[j])!=l_False)throw std::runtime_error("INVALID_PRE_ACTION");
  hc_inside=true;hc_did=true;uncheckedEnqueue(p,selected);hc_inside=false;
  fprintf(hc_out,"{\"event\":\"EARLY_ENQUEUE\",\"global_enqueue\":%llu,\"literal\":%d,\"reason_id\":%llu}\n",hc_enqueues,hc_lit(p),selected_id);fflush(hc_out);
 }
}

void Solver::hd_dequeue(Lit p){for(auto& t:hd_traces)if(!t.conflict)t.dequeue.push_back(hc_lit(p));}
void Solver::hd_conflict(CRef cr){for(auto& t:hd_traces)if(!t.conflict){t.conflict=conflicts;t.clause_id=hc_ids.at(cr);const Clause& c=ca[cr];for(int i=0;i<c.size();++i)t.clause.push_back(hc_lit(c[i]));}}
void Solver::hd_learned(const vec<Lit>& learnt){for(auto& t:hd_traces)if(t.conflict==(HU)conflicts&&!t.learned_seen){t.learned_seen=true;for(int i=0;i<learnt.size();++i)t.learned.push_back(hc_lit(learnt[i]));}}
void Solver::hd_decision(Lit p){for(auto& t:hd_traces)if(t.conflict&&!t.done){t.done=true;t.next_decision=hc_lit(p);t.decision_conflict=conflicts;}}
static void hd_array(const std::vector<int>& v){fprintf(hc_out,"[");for(size_t i=0;i<v.size();++i)fprintf(hc_out,"%s%d",i?",":"",v[i]);fprintf(hc_out,"]");}
static void hd_finish(){for(const auto& t:hd_traces){
 fprintf(hc_out,"{\"event\":\"LOCAL_TRACE\",\"bucket\":%d,\"dequeue_literals\":",t.bucket);hd_array(t.dequeue);
 fprintf(hc_out,",\"conflict_index\":%llu,\"conflict_clause_id\":%llu,\"conflict_clause_literals\":",t.conflict,t.clause_id);hd_array(t.clause);
 fprintf(hc_out,",\"learned_seen\":%s,\"learned_clause_literals\":",t.learned_seen?"true":"false");hd_array(t.learned);
 fprintf(hc_out,",\"next_decision_literal\":");if(t.done)fprintf(hc_out,"%d",t.next_decision);else fprintf(hc_out,"null");
 fprintf(hc_out,",\"next_decision_conflict_index\":%llu,\"next_decision_status\":\"%s\"}\n",t.decision_conflict,t.done?"OBSERVED":"TERMINATED_BEFORE_NEXT_DECISION");
}}
