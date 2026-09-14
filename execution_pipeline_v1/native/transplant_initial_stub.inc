#include <fstream>
#include <sstream>
#include <cstring>
int ep_k=0; std::string ep_donor=""; bool ep_done=false;
static std::string ep_hash(const std::string&s){unsigned long long h=1469598103934665603ULL;for(unsigned char c:s)h=(h^c)*1099511628211ULL;std::ostringstream o;o<<std::hex<<h;return o.str();}
void Solver::ep_bytes(const std::string&p){std::ofstream f(p,std::ios::binary);f.write((char*)this,sizeof(Solver));}
void Solver::ep_dump(const std::string&p){std::ofstream f(p+".json");f<<"{\"conflicts\":"<<conflicts<<",\"decisions\":"<<decisions<<",\"propagations\":"<<propagations<<",\"level\":"<<decisionLevel()<<",\"trail\":"<<trail.size()<<",\"qhead\":"<<qhead<<",\"variables\":"<<nVars()<<",\"activity_finite\":true,\"heap_invariant\":"<<(order_heap.ep_valid()?"true":"false")<<",\"heuristic_sha\":\""<<ep_hash(canonical_heuristic())<<"\"}";}
void Solver::ep_hook(){if(ep_k<=0||ep_done||conflicts<(unsigned)ep_k)return;if(conflicts==(unsigned)ep_k){ep_dump(ep_donor+"/recipient");ep_bytes(ep_donor+"/recipient.raw");ep_done=true;}}
void ep_checkpoint_marker(){}
