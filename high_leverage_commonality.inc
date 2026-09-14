#include <map>
#include <set>
#include <vector>
#include <algorithm>
#include <stdexcept>
typedef unsigned long long HU;
static FILE* hc_out=nullptr;
static int hc_target=0,hc_found=0;
static HU hc_enqueues=0,hc_dequeues=0,hc_ids_next=0;
static bool hc_inside=false,hc_did=false;
static std::map<CRef,HU> hc_ids;
static std::set<std::pair<HU,int>> hc_previous;
struct HCTrack{int id;Lit literal;HU dq0,enq0,xindex,xenq,direct;bool closed,processing;};
static std::vector<HCTrack> hc_tracks;
static int hc_lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static HU hc_hash(const void* p,size_t n,HU h=1469598103934665603ULL){const unsigned char* a=(const unsigned char*)p;for(size_t i=0;i<n;++i)h=(h^a[i])*1099511628211ULL;return h;}
void hc_init(const char* path,int which){hc_target=which;hc_out=fopen(path,"w");if(!hc_out)throw std::runtime_error("log open failed");}
void hc_finish(){fprintf(hc_out,"{\"event\":\"TOTAL\",\"opportunities\":%d,\"interventions\":%d}\n",hc_found,hc_did?1:0);fclose(hc_out);}
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
void Solver::hc_before_enqueue(){
 ++hc_enqueues;for(auto& t:hc_tracks)if(!t.closed&&t.processing)++t.direct;
}
void Solver::hc_dequeue(Lit p){
 ++hc_dequeues;for(auto& t:hc_tracks)if(!t.closed){t.processing=false;if(t.xindex==0&&p==t.literal){t.xindex=hc_dequeues-t.dq0;t.xenq=hc_enqueues;t.processing=true;}}
}
void Solver::hc_conflict(CRef cr){
 for(auto& t:hc_tracks)if(!t.closed){t.closed=true;const Clause& c=ca[cr];
  fprintf(hc_out,"{\"event\":\"NEXT_CONFLICT\",\"opportunity\":%d,\"conflict\":%llu,\"candidate_dequeued\":%s,\"dequeue_index\":%llu,\"propagations_to_conflict\":%llu,\"horizon_after_candidate\":",t.id,(HU)conflicts,t.xindex?"true":"false",t.xindex,hc_dequeues-t.dq0);
  if(t.xindex)fprintf(hc_out,"%llu",hc_dequeues-t.dq0-t.xindex);else fprintf(hc_out,"null");
  fprintf(hc_out,",\"direct_enqueues_during_candidate_processing\":%llu,\"enqueues_after_candidate_dequeue\":",t.direct);
  if(t.xindex)fprintf(hc_out,"%llu",hc_enqueues-t.xenq);else fprintf(hc_out,"null");
  fprintf(hc_out,",\"clause_literals\":[");for(int i=0;i<c.size();++i)fprintf(hc_out,"%s%d",i?",":"",hc_lit(c[i]));fprintf(hc_out,"]}\n");
 }
 fflush(hc_out);
}
void Solver::hc_observe(){
 if(hc_inside||hc_found>=5||hc_did)return;
 struct Candidate{HU id;CRef cr;Lit lit;};std::vector<Candidate> candidates;std::set<std::pair<HU,int>> now;
 auto scan=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){CRef cr=db[i];const Clause& c=ca[cr];if(c.mark()!=0)continue;int unset=0;Lit p=lit_Undef;bool sat=false;for(int j=0;j<c.size();++j){if(value(c[j])==l_Undef){++unset;p=c[j];}else if(value(c[j])==l_True)sat=true;}
  if(sat||unset!=1||!(c.size()==2||(c.size()>2&&c[0]==p)))continue;
  auto key=std::make_pair(hc_ids.at(cr),toInt(p));now.insert(key);if(!hc_previous.count(key))candidates.push_back({key.first,cr,p});}};
 scan(clauses);scan(learnts);hc_previous.swap(now);
 std::sort(candidates.begin(),candidates.end(),[](const Candidate&a,const Candidate&b){return a.id<b.id;});
 for(const auto& cand:candidates){if(hc_found>=5)break;int id=++hc_found;Lit p=cand.lit;const Clause& c=ca[cand.cr];
  unsigned almost=0,fanout=0,implications=0;auto neigh=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){const Clause& d=ca[db[i]];if(d.mark()!=0)continue;bool contains=false,sat=false,negative=false;int unset=0;for(int j=0;j<d.size();++j){contains|=var(d[j])==var(p);negative|=d[j]==~p;sat|=value(d[j])==l_True;unset+=value(d[j])==l_Undef;}if(contains){++fanout;almost+=!sat&&unset==2;}implications+=negative&&d.size()==2;}};neigh(clauses);neigh(learnts);
  int hp=-1;for(int i=0;i<order_heap.size();++i)if(order_heap[i]==var(p))hp=i;
  fprintf(hc_out,"{\"event\":\"OPPORTUNITY\",\"opportunity\":%d,\"global_enqueue\":%llu,\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"trail_length\":%d,\"qhead\":%d,\"pending_queue_length\":%d,\"literal\":%d,\"reason_id\":%llu,\"reason_source\":\"%s\",\"reason_length\":%d,\"reason_literals\":[",id,hc_enqueues,(HU)conflicts,(HU)decisions,decisionLevel(),trail.size(),qhead,trail.size()-qhead,hc_lit(p),cand.id,c.learnt()?"learned":"original",c.size());
  for(int j=0;j<c.size();++j)fprintf(hc_out,"%s%d",j?",":"",hc_lit(c[j]));
  fprintf(hc_out,"],\"antecedent_levels\":[");bool first=true;for(int j=0;j<c.size();++j)if(c[j]!=p){fprintf(hc_out,"%s%d",first?"":",",level(var(c[j])));first=false;}
  fprintf(hc_out,"],\"literal_activity\":\"%a\",\"heap_order_position\":%d,\"almost_unit_neighbors\":%u,\"local_clause_fanout\":%u,\"binary_implication_fanout\":%u,\"state_fingerprint_fnv64\":\"%llu\",\"unit_and_layout_verified\":true}\n",activity[var(p)],hp,almost,fanout,implications,hc_state_hash());fflush(hc_out);
  if(hc_target==0||hc_target==id)hc_tracks.push_back({id,p,hc_dequeues,hc_enqueues,0,0,0,false,false});
  if(hc_target==id){
   // Recheck the entire native unit reason immediately before the sole action.
   if(value(p)!=l_Undef||(c.size()>2&&c[0]!=p))throw std::runtime_error("INVALID_PRE_ACTION");
   for(int j=0;j<c.size();++j)if(c[j]!=p&&value(c[j])!=l_False)throw std::runtime_error("INVALID_PRE_ACTION");
   hc_inside=true;hc_did=true;uncheckedEnqueue(p,cand.cr);hc_inside=false;return;
  }
 }
}
