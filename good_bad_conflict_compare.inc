#include <set>
#include <vector>
#include <algorithm>
static int gb_start=atoi(getenv("GB_START")?getenv("GB_START"):"0");
static FILE* gb_out=nullptr;
static unsigned long long gb_dq=0,gb_enq=0,gb_prev_dq=0,gb_prev_dec=0,gb_key_enq=0,gb_prefix=1469598103934665603ULL,gb_seq=1469598103934665603ULL,gb_ops0=0;
static bool gb_analyzing=false,gb_immediate_done=false;
static int gb_trail_before=0;
static std::set<int> gb_visited_vars,gb_bumped_vars;
static unsigned long long gb_hash(const void* ptr,size_t n,unsigned long long h=1469598103934665603ULL){const unsigned char* p=(const unsigned char*)ptr;for(size_t i=0;i<n;++i)h=(h^p[i])*1099511628211ULL;return h;}
static int gb_lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static void gb_open(){if(gb_out)return;std::string path=getenv("GB_OUT");
#ifdef GB_FORK
 path+=cf_role?".EARLY.jsonl":".BASELINE.jsonl";
#endif
 gb_out=fopen(path.c_str(),"w");if(!gb_out)throw std::runtime_error("GB_LOG_OPEN");}
void Solver::gb_enqueue(){++gb_enq;}
void Solver::gb_dequeue(){++gb_dq;}
void Solver::gb_visit(Var v){if(gb_analyzing){int x=v+1;gb_seq=gb_hash(&x,sizeof(x),gb_seq);gb_visited_vars.insert(x);}}
void Solver::gb_bump(Var v){if(gb_analyzing)gb_bumped_vars.insert(v+1);}
void Solver::gb_heuristic(const char* label){unsigned long long h=1469598103934665603ULL;for(int v=0;v<nVars();++v)h=gb_hash(&activity[v],sizeof(double),h);
 unsigned long long hh=1469598103934665603ULL;for(int i=0;i<order_heap.size();++i){int v=order_heap[i];hh=gb_hash(&v,sizeof(v),hh);}
 fprintf(gb_out,"{\"event\":\"%s\",\"activity_hash_fnv64\":\"%llu\",\"heap_hash_fnv64\":\"%llu\",\"top10_heap_array_variables\":[",label,h,hh);for(int i=0;i<10&&i<order_heap.size();++i)fprintf(gb_out,"%s%d",i?",":"",order_heap[i]+1);fprintf(gb_out,"]}\n");fflush(gb_out);}
void Solver::gb_before(CRef cr){
 const Clause& c=ca[cr];
 if(conflicts<(unsigned long long)gb_start){std::vector<int> lits;for(int i=0;i<c.size();++i)lits.push_back(gb_lit(c[i]));std::sort(lits.begin(),lits.end());int n=lits.size();gb_prefix=gb_hash(&n,sizeof(n),gb_prefix);for(int x:lits)gb_prefix=gb_hash(&x,sizeof(x),gb_prefix);return;}
 if(conflicts>(unsigned long long)gb_start+10)return;
 gb_open();
 if(conflicts==(unsigned long long)gb_start){
  gb_ops0=sf_analysis;gb_analyzing=true;gb_trail_before=trail.size();
  fprintf(gb_out,"{\"event\":\"CONFLICT_BEFORE\",\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"trail_length\":%d,\"prior_conflict_count\":%d,\"prior_canonical_conflict_sequence_hash_fnv64\":\"%llu\",\"conflict_clause_literals\":[",(unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),trail.size(),gb_start-1,gb_prefix);
  for(int i=0;i<c.size();++i)fprintf(gb_out,"%s%d",i?",":"",gb_lit(c[i]));fprintf(gb_out,"]}\n");gb_heuristic("HEURISTIC_BEFORE");
 }else{
  fprintf(gb_out,"{\"event\":\"WINDOW_COUNTS\",\"conflict\":%llu,\"propagation_count\":%llu,\"decision_count\":%llu}\n",(unsigned long long)conflicts,gb_dq-gb_prev_dq,(unsigned long long)decisions-gb_prev_dec);fflush(gb_out);
 }
}
void Solver::gb_analysis(const vec<Lit>& learnt,int bt,unsigned lbd){
 if(conflicts<(unsigned long long)gb_start||conflicts>(unsigned long long)gb_start+10)return;
 if(conflicts==(unsigned long long)gb_start){gb_analyzing=false;
  fprintf(gb_out,"{\"event\":\"ANALYSIS\",\"visited_variable_count\":%zu,\"visited_sequence_hash_fnv64\":\"%llu\",\"resolution_steps\":%llu,\"bumped_variable_count\":%zu,\"bumped_variable_set\":[",gb_visited_vars.size(),gb_seq,sf_analysis-gb_ops0,gb_bumped_vars.size());bool first=true;for(int v:gb_bumped_vars){fprintf(gb_out,"%s%d",first?"":",",v);first=false;}
  fprintf(gb_out,"],\"learned_literals\":[");for(int i=0;i<learnt.size();++i)fprintf(gb_out,"%s%d",i?",":"",gb_lit(learnt[i]));
  fprintf(gb_out,"],\"lbd\":%u,\"asserting_literal\":%d,\"backtrack_level\":%d,\"backjump_levels\":%d,\"subsume_or_strengthen_existing\":\"UNAVAILABLE\"}\n",lbd,gb_lit(learnt[0]),bt,decisionLevel()-bt);
 }else fprintf(gb_out,"{\"event\":\"WINDOW_LEARNED\",\"conflict\":%llu,\"learned_length\":%d,\"lbd\":%u,\"backtrack_level\":%d}\n",(unsigned long long)conflicts,learnt.size(),lbd,bt);
 fflush(gb_out);
}
void Solver::gb_backtrack(const vec<Lit>& learnt){if(conflicts!=(unsigned long long)gb_start)return;
 bool unit=value(learnt[0])==l_Undef;for(int i=1;i<learnt.size();++i)unit&=value(learnt[i])==l_False;
 fprintf(gb_out,"{\"event\":\"BACKTRACK\",\"trail_length\":%d,\"removed_assignments\":%d,\"learned_immediately_unit\":%s}\n",trail.size(),gb_trail_before-trail.size(),unit?"true":"false");fflush(gb_out);
}
void Solver::gb_end(){if(conflicts<(unsigned long long)gb_start||conflicts>(unsigned long long)gb_start+10)return;
 if(conflicts==(unsigned long long)gb_start){gb_key_enq=gb_enq;gb_heuristic("HEURISTIC_AFTER");}
 gb_prev_dq=gb_dq;gb_prev_dec=decisions;
}
void Solver::gb_decision(Lit p){if(!gb_out||gb_immediate_done||conflicts<(unsigned long long)gb_start)return;gb_immediate_done=true;
 fprintf(gb_out,"{\"event\":\"IMMEDIATE\",\"new_propagations_before_next_decision\":%llu,\"conflict_before_next_decision\":%s,\"next_decision_literal\":%d,\"next_decision_after_conflict\":%llu}\n",gb_enq-gb_key_enq,conflicts>(unsigned long long)gb_start?"true":"false",gb_lit(p),(unsigned long long)conflicts);fflush(gb_out);
}
