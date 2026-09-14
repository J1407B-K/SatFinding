// Fixed three-variable context; bounded DAG and one-conflict future only.
static bool cx_taken=false,cx_active=false;
static unsigned long long cx_epoch_start=0,cx_future_dequeues=0,cx_future_enqueues=0;
static FILE* cx_future=nullptr;
static int cx_pos(const vec<Lit>& t,int v){for(int i=0;i<t.size();++i)if(var(t[i])==v)return i;return -1;}
static const char* cx_value(lbool x){return x==l_Undef?"UNASSIGNED":x==l_True?"TRUE":"FALSE";}
void Solver::cx_clause(FILE* f,CRef cr){
 if(cr==CRef_Undef){fprintf(f,"null");return;}
 const Clause& c=ca[cr];fprintf(f,"{\"id\":\"CRef:%u\",\"cref\":%u,\"source\":\"%s\",\"literals\":[",cr,cr,c.learnt()?"learned":"original");
 for(int i=0;i<c.size();++i)fprintf(f,"%s%d",i?",":"",lt_int(c[i]));fprintf(f,"]}");
}
void Solver::cx_snapshot(const std::string& name){
 if(name!=CX_TARGET || cx_taken)return;
 cx_taken=true;
 FILE* f=fopen((lt_dir+"/context.raw.json").c_str(),"w");if(!f)throw std::runtime_error("snapshot open failed");
 fprintf(f,"{\"global\":{\"completed_conflicts\":%llu,\"decision\":%llu,\"level\":%d,\"trail_length\":%d,\"qhead\":%d,\"pending_propagations\":%d,\"current_inflight_literal\":%d,\"next_queued_literal\":",(LU)conflicts,(LU)decisions,decisionLevel(),trail.size(),qhead,trail.size()-qhead,qhead?lt_int(trail[qhead-1]):0);
 if(qhead<trail.size())fprintf(f,"%d",lt_int(trail[qhead]));else fprintf(f,"null");
 fprintf(f,",\"next_native_propagation_literal\":\"UNAVAILABLE: current watch scan can conflict before next dequeue\",\"restart_epoch\":%llu,\"conflicts_since_epoch_start\":%llu,\"raw_conflictsRestarts\":%llu},\"variables\":[",(LU)starts,(LU)conflicts-cx_epoch_start,(LU)conflictsRestarts);
 for(int v=564;v<=566;++v){
  int pos=cx_pos(trail,v),hp=-1;for(int i=0;i<order_heap.size();++i)if(order_heap[i]==v)hp=i;
  CRef r=value(v)==l_Undef?CRef_Undef:reason(v);
  fprintf(f,"%s{\"variable\":%d,\"assignment\":\"%s\",\"level\":%d,\"trail_position\":%d,\"activity\":\"%a\",\"heap_order_position\":%d,\"phase_sign\":%d,\"preferred_literal\":%d,\"decision_eligible\":%s,\"assignment_kind\":\"%s\",\"reason\":",v==564?"":",",v+1,cx_value(value(v)),value(v)==l_Undef?-1:level(v),pos,activity[v],hp,(int)polarity[v],polarity[v]?-(v+1):v+1,decision[v]?"true":"false",value(v)==l_Undef?"unassigned":r!=CRef_Undef?"propagated":level(v)>0?"decision":"root_without_reason");
  cx_clause(f,r);fprintf(f,"}");
 }
 CRef target=CRef_Undef;
 for(int i=0;i<clauses.size();++i){const Clause& c=ca[clauses[i]];if(c.size()!=3)continue;std::vector<int>a;for(int j=0;j<3;++j)a.push_back(lt_int(c[j]));std::sort(a.begin(),a.end());if(a==std::vector<int>({565,566,567}))target=clauses[i];}
 if(target==CRef_Undef)throw std::runtime_error("missing original2589");
 const Clause& tc=ca[target];
 fprintf(f,"],\"clause2589\":{\"clause\":");cx_clause(f,target);
 fprintf(f,",\"values_in_layout_order\":[");for(int i=0;i<3;++i)fprintf(f,"%s\"%s\"",i?",":"",cx_value(value(tc[i])));
 fprintf(f,"],\"why_unit\":\"566 unassigned;565 and567 false\",\"native_access_time\":\"UNAVAILABLE: no counterfactual BCP/watch simulation\",\"watches\":[");
 for(int j=0;j<2;++j){Lit trigger=~tc[j];const vec<Watcher>& ws=watches[trigger];int slot=-1,blocker=0;for(int k=0;k<ws.size();++k)if(ws[k].cref==target){slot=k;blocker=lt_int(ws[k].blocker);}
  int tp=cx_pos(trail,var(trigger));bool pending=tp>=qhead&&trail[tp]==trigger;
  fprintf(f,"%s{\"clause_index\":%d,\"watched_literal\":%d,\"trigger_literal\":%d,\"watch_vector_slot\":%d,\"blocker\":%d,\"trigger_trail_position\":%d,\"trigger_pending\":%s,\"queued_entries_ahead\":%d}",j?",":"",j,lt_int(tc[j]),lt_int(trigger),slot,blocker,tp,pending?"true":"false",pending?tp-qhead:-1);
 }
 fprintf(f,"]},\"local_reason_dag\":[");
 std::map<int,int> depths;std::vector<int> todo={564,566};depths[564]=0;depths[566]=0;
 for(size_t i=0;i<todo.size();++i){int v=todo[i],depth=depths[v];CRef r=value(v)==l_Undef?CRef_Undef:reason(v);
  fprintf(f,"%s{\"variable\":%d,\"depth\":%d,\"level\":%d,\"assignment\":\"%s\",\"reason\":",i?",":"",v+1,depth,value(v)==l_Undef?-1:level(v),cx_value(value(v)));
  if(depth<2)cx_clause(f,r);else fprintf(f,"null");
  fprintf(f,",\"depth_limited\":%s,\"parents\":[",depth==2?"true":"false");
  bool first=true;if(r!=CRef_Undef&&depth<2){const Clause& c=ca[r];for(int j=0;j<c.size();++j){int par=var(c[j]);if(par==v)continue;fprintf(f,"%s%d",first?"":",",par+1);first=false;if(!depths.count(par)){depths[par]=depth+1;todo.push_back(par);}}}
  fprintf(f,"]}");
 }
 fprintf(f,"],\"neighborhood\":[");
 for(int v=564;v<=566;++v){unsigned occurrences=0,nclauses=0,bin=0,tri=0,longc=0,orig=0,learn=0,unit=0,almost=0;
  auto scan=[&](const vec<CRef>& db){for(int i=0;i<db.size();++i){const Clause& c=ca[db[i]];if(c.mark()!=0)continue;unsigned occ=0,undef=0;bool satisfied=false;for(int j=0;j<c.size();++j){occ+=var(c[j])==v;undef+=value(c[j])==l_Undef;satisfied|=value(c[j])==l_True;}if(!occ)continue;occurrences+=occ;++nclauses;bin+=c.size()==2;tri+=c.size()==3;longc+=c.size()>3;orig+=!c.learnt();learn+=c.learnt();unit+=!satisfied&&undef==1;almost+=!satisfied&&undef==2;}};
  scan(clauses);scan(learnts);
  fprintf(f,"%s{\"variable\":%d,\"occurrences\":%u,\"clause_count\":%u,\"binary\":%u,\"ternary\":%u,\"long\":%u,\"original\":%u,\"learned\":%u,\"unit\":%u,\"almost_unit\":%u}",v==564?"":",",v+1,occurrences,nclauses,bin,tri,longc,orig,learn,unit,almost);
 }
 fprintf(f,"]}\n");fclose(f);
 cx_future=fopen((lt_dir+"/future.jsonl").c_str(),"w");if(!cx_future)throw std::runtime_error("future open failed");cx_active=true;
}
void Solver::cx_enqueue(Lit p,CRef from){
 if(!cx_active)return;++cx_future_enqueues;
 fprintf(cx_future,"{\"event\":\"ENQUEUE\",\"literal\":%d,\"reason_cref\":%u}\n",lt_int(p),from);
}
void Solver::cx_dequeue(Lit p){if(cx_active){++cx_future_dequeues;fprintf(cx_future,"{\"event\":\"PROPAGATE\",\"literal\":%d}\n",lt_int(p));}}
void Solver::cx_conflict(CRef cr){
 if(!cx_active)return;cx_active=false;
 fprintf(cx_future,"{\"event\":\"FIRST_CONFLICT\",\"conflict\":%llu,\"clause\":",(LU)conflicts);cx_clause(cx_future,cr);
 fprintf(cx_future,",\"propagation_dequeues_to_conflict\":%llu,\"enqueues_to_conflict\":%llu}\n",cx_future_dequeues,cx_future_enqueues);fclose(cx_future);
}
