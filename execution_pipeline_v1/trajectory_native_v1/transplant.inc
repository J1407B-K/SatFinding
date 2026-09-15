#include <fstream>
#include <sstream>
#include <cstring>
#include <cmath>
#include <set>
int ep_k=0; std::string ep_donor=""; bool ep_done=false;
static std::set<HU> ep_saved;
template<class T>static void ep_vec(FILE*f,const vec<T>&v){int n=v.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&v[0],sizeof(T),n,f);}
void Solver::ep_bytes(const std::string&p){
 FILE*f=fopen(p.c_str(),"wb");if(!f)throw std::runtime_error("AUDIT_OPEN");
 std::vector<unsigned char>b(sizeof(Solver));memcpy(b.data(),this,b.size());
 auto mask=[&](const void*a,size_t n){size_t k=(const unsigned char*)a-(const unsigned char*)this;std::fill(b.begin()+k,b.begin()+k+n,0);};mask(&activity,sizeof(activity));mask(&order_heap,sizeof(order_heap));fwrite(b.data(),1,b.size(),f);
#define E(x) ep_vec(f,x)
 E(model);E(conflict);E(clauses);E(learnts);E(assigns);E(polarity);E(decision);E(trail);E(nbpos);E(trail_lim);E(vardata);E(assumptions);E(permDiff);E(seen);E(analyze_stack);E(analyze_toclear);E(add_tmp);E(assumptionPositions);E(initialPositions);
#ifdef UPDATEVARACTIVITY
 E(lastDecisionLevel);
#endif
#undef E
 watches.ep_audit(f);watchesBin.ep_audit(f);trailQueue.ep_audit(f);lbdQueue.ep_audit(f);
 uint32_t n=ca.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(ca.RegionAllocator<uint32_t>::lea(0),sizeof(uint32_t),n,f);
 HU counts[]={sf_analysis,sf_redundancy,sf_binary,hc_enqueues,watchers,dequeues,boundary};fwrite(counts,sizeof(counts),1,f);fclose(f);
}
void Solver::ep_dump(const std::string&p){
 std::ostringstream a,order; a<<std::setprecision(17);a<<'[';for(int v=0;v<nVars();++v){if(!std::isfinite(activity[v]))throw std::runtime_error("NONFINITE_ACTIVITY");if(v)a<<',';a<<activity[v];}a<<']';
 auto sem=order_heap.semantic_order();array(order,sem);
 std::vector<int> rank(nVars(),-1),eligible;for(size_t i=0;i<sem.size();++i){int v=sem[i]-1;rank[v]=i;if(decision[v]&&value(v)==l_Undef)eligible.push_back(v+1);}
 std::ostringstream o;o<<"{\"conflicts\":"<<conflicts<<",\"offset\":"<<(reached?conflicts-ep_cp:0)<<",\"decisions\":"<<decisions<<",\"propagations\":"<<propagations<<",\"variables\":"<<nVars()<<",\"decision_level\":"<<decisionLevel()<<",\"qhead\":"<<qhead<<",\"logical_sha256\":\""<<digest(canonical_logical())<<"\",\"activity\":"<<a.str()<<",\"semantic_heap_order\":"<<order.str()<<",\"activity_sha256\":\""<<digest(a.str())<<"\",\"heap_sha256\":\""<<digest(order.str())<<"\",\"heap_rank\":";array(o,rank);
 o<<",\"next_branch_candidate\":"<<(eligible.empty()?0:lit(mkLit(eligible[0]-1,polarity[eligible[0]-1])))<<",\"top8\":";array(o,std::vector<int>(eligible.begin(),eligible.begin()+std::min(size_t(8),eligible.size())));o<<",\"top32\":";array(o,std::vector<int>(eligible.begin(),eligible.begin()+std::min(size_t(32),eligible.size())));
 o<<",\"starts\":"<<starts<<",\"conflicts_since_restart\":"<<conflictsRestarts<<",\"learned_count\":"<<learnts.size()<<",\"reductions\":"<<nbReduceDB<<",\"heap_invariant\":"<<(order_heap.ep_valid()?"true":"false")<<",\"trail\":[";for(int i=0;i<trail.size();++i)o<<(i?",":"")<<lit(trail[i]);o<<"]}";write(p+".json",o.str());
 write(p+".logical.txt",canonical_logical());write(p+".full.txt",canonical_heuristic());
 std::ostringstream data;data<<nVars()<<'\n'<<std::setprecision(17);for(int i=0;i<nVars();++i)data<<activity[i]<<' ';data<<'\n'<<sem.size()<<'\n';for(int v:sem)data<<v<<' ';data<<'\n';write(p+".donor.txt",data.str());
}
void Solver::ep_hook(){
 if(!reached)return;HU k=conflicts-ep_cp;if(k!=1&&k!=4&&k!=16&&k!=64)return;if(!ep_saved.insert(k).second)return;
 std::string stem=output_dir+"/donor_k"+std::to_string(k);ep_dump(stem);
 if(ep_k!=(int)k)return;
 auto logical=canonical_logical();ep_bytes(output_dir+"/protected.before.bin");
 std::ifstream f(ep_donor);int n,m;f>>n;if(!f||n!=nVars())throw std::runtime_error("DONOR_DIMENSION");std::vector<double>a(n);for(double&x:a){f>>x;if(!f||!std::isfinite(x))throw std::runtime_error("DONOR_ACTIVITY");}f>>m;if(!f||m<0||m>n)throw std::runtime_error("DONOR_HEAP_LENGTH");std::vector<int>rank(n,n);for(int i=0;i<m;++i){int v;f>>v;--v;if(!f||v<0||v>=n||rank[v]!=n)throw std::runtime_error("DONOR_HEAP_UNIVERSE");rank[v]=i;}
 std::string extra;if(f>>extra)throw std::runtime_error("DONOR_TRAILING_DATA");
 std::vector<int> free;for(int v=0;v<n;++v)if(decision[v]&&value(v)==l_Undef)free.push_back(v);
 std::sort(free.begin(),free.end(),[&](int x,int y){if(a[x]!=a[y])return a[x]>a[y];if(rank[x]!=rank[y])return rank[x]<rank[y];return x<y;});
 for(int v=0;v<n;++v)activity[v]=a[v];vec<int>hv;for(int v:free)hv.push(v);order_heap.ep_build(hv);
 if(!order_heap.ep_valid())throw std::runtime_error("HEAP_INVARIANT");for(int v=0;v<n;++v)if(decision[v]&&value(v)==l_Undef&&!order_heap.inHeap(v))throw std::runtime_error("HEAP_COVERAGE");
 ep_bytes(output_dir+"/protected.after.bin");if(read(output_dir+"/protected.before.bin")!=read(output_dir+"/protected.after.bin"))throw std::runtime_error("PROTECTED_STATE_CHANGED");if(logical!=canonical_logical())throw std::runtime_error("LOGICAL_CHANGED");
 ep_dump(output_dir+"/transplanted");write(output_dir+"/legality.json","{\"PASS\":true,\"same_universe\":true,\"activity_finite\":true,\"heap_invariant\":true,\"eligible_coverage\":true,\"logical_unchanged\":true,\"protected_object_and_live_buffers_identical\":true}");ep_done=true;
}
void ep_checkpoint_marker(){}
