// Read-only event observer, plus two explicit legal decision interventions.
static HU bm_index=0,bm_d0=0,bm_c0=0,bm_q0=0,bm_decision_ordinal=0;
static bool bm_active=false,bm_injection=false,bm_changed=false;
static int bm_var=0,bm_target_ordinal=0,bm_target_lit=0;
static std::string bm_mode;
static std::ofstream bm_log;
void Solver::bm_event(const char* type, Lit p, CRef cr, const vec<Lit>* clause){
 if(!bm_active || bm_index>=10000)return;
 std::vector<int> cs;
 if(clause){for(int j=0;j<clause->size();j++)cs.push_back(lit((*clause)[j]));}
 else if(cr!=CRef_Undef){const Clause& c=ca[cr];for(int j=0;j<c.size();j++)cs.push_back(lit(c[j]));}
 std::sort(cs.begin(),cs.end());
 int v=bm_var-1,greater=0,equal=0,rank=0,top=0;auto heap=order_heap.semantic_order();
 for(int j=0;j<nVars();j++){greater+=activity[j]>activity[v];equal+=activity[j]==activity[v];}
 for(size_t j=0;j<heap.size();j++){int u=heap[j]-1;if(u==v)rank=j+1;if(!top&&value(u)==l_Undef&&decision[u])top=u+1;}
 bm_log<<"{\"index\":"<<bm_index++<<",\"type\":\""<<type<<"\",\"literal\":"<<(p==lit_Undef?0:lit(p))<<",\"clause\":";array(bm_log,cs);
 bm_log<<",\"injection\":"<<(bm_injection?"true":"false")<<",\"decisions\":"<<decisions-bm_d0<<",\"decision_ordinal\":"<<bm_decision_ordinal<<",\"dequeues\":"<<dequeues-bm_q0<<",\"conflicts\":"<<conflicts-bm_c0<<",\"level\":"<<decisionLevel()<<",\"activity\":"<<std::setprecision(17)<<activity[v]<<",\"activity_rank\":"<<(greater+(equal+1)/2.0)<<",\"heap_rank\":"<<rank<<",\"heap_member\":"<<(order_heap.inHeap(v)?"true":"false")<<",\"top_candidate\":"<<top<<",\"value\":"<<toInt(value(v));
 if(std::string(type)=="heap_activity"||std::string(type)=="checkpoint"){
  bm_log<<",\"heap_order\":";array(bm_log,heap);bm_log<<",\"activity_vector\":[";
  for(int j=0;j<nVars();j++)bm_log<<(j?",":"")<<activity[j];bm_log<<']';
 }
 bm_log<<"}\n";
}
void Solver::bm_start(){
 std::ifstream f(output_dir+"/mechanism_request.txt");f>>bm_var>>bm_mode>>bm_target_ordinal>>bm_target_lit;
 if(!f||bm_var<1||bm_var>nVars())throw std::runtime_error("MECHANISM_REQUEST");
 bm_log.open(output_dir+"/events.jsonl");bm_active=true;bm_d0=decisions;bm_c0=conflicts;bm_q0=dequeues;
 bm_event("checkpoint",lit_Undef,CRef_Undef,nullptr);
}
Lit Solver::bm_pick(){
 if(!bm_active)return pickBranchLit();
 ++bm_decision_ordinal;
 if(!bm_changed && (int)bm_decision_ordinal==bm_target_ordinal && bm_mode=="restore"){
  Lit p=mkLit(abs(bm_target_lit)-1,bm_target_lit<0);
  if(value(p)==l_Undef&&decision[var(p)]){
   if(random_var_freq!=0||rnd_pol)throw std::runtime_error("CF_REQUIRES_DETERMINISTIC_BRANCHING");
   // Native pickBranchLit consumes exactly one RNG draw even at random_var_freq=0.
   (void)drand(random_seed);
   bm_changed=true;bm_event("restoration",p,CRef_Undef,nullptr);
   // Retain ordinary lazy removal semantics by removing this selected variable.
   // Native forced choice may leave it in the heap; assigned entries are skipped normally.
   return p;
  }
  bm_event("restoration_unavailable",p,CRef_Undef,nullptr);
 }
 Lit p=pickBranchLit();
 if(!bm_changed && (int)bm_decision_ordinal==bm_target_ordinal && bm_mode=="suppress" && p!=lit_Undef && var(p)==abs(bm_target_lit)-1){
  if(random_var_freq!=0||rnd_pol)throw std::runtime_error("CF_REQUIRES_DETERMINISTIC_BRANCHING");
  // Continue the same native heap scan without a second random draw.
  Var av=var_Undef;
  while(!order_heap.empty()){Var u=order_heap.removeMin();if(value(u)==l_Undef&&decision[u]){av=u;break;}}
  Lit alternative=av==var_Undef?lit_Undef:mkLit(av,polarity[av]);
  if(alternative!=lit_Undef){insertVarOrder(var(p));bm_changed=true;bm_event("suppression",p,CRef_Undef,nullptr);return alternative;}
  bm_event("suppression_unavailable",p,CRef_Undef,nullptr);
 }
 return p;
}
