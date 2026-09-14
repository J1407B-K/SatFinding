// Read-only counters/summaries. Early collection stops only after checkpoint1000.
#include <map>
#include <vector>
#include <algorithm>
#include <fstream>
#include <cmath>
#include <string>
namespace Glucose {
unsigned long long gb_heap_insert=0,gb_heap_pop=0,gb_heap_decrease=0,gb_heap_moves=0;
}
FILE* gb_out=nullptr;
bool gb_prefix=false,gb_bcp=false;
unsigned long long gb_enqueues=0,gb_dequeues=0,gb_reason[4]={},gb_analysis[4]={},gb_minimize[4]={},gb_conflict[4]={};
double gb_width_sum=0,gb_lbd_sum=0,gb_dl_sum=0,gb_jump_sum=0;
std::map<std::vector<int>,std::pair<int,int>> gb_inputs;
std::map<int,unsigned long long> gb_decision_hist;
std::vector<unsigned long long> gb_restarts;
struct GBUse {unsigned long long reason=0,bcp=0,analysis=0,minimize=0,conflict=0;};
std::map<int,GBUse> gb_usage;
std::vector<int> gb_literals(const Clause& c) {std::vector<int> v;for(int i=0;i<c.size();++i)v.push_back((var(c[i])+1)*(sign(c[i])?-1:1));std::sort(v.begin(),v.end());return v;}
std::pair<int,int> gb_origin(const Clause& c) {
    if(c.learnt())return {3,-1};auto p=gb_inputs.find(gb_literals(c));return p==gb_inputs.end()?std::make_pair(0,-1):p->second;
}
void gb_init(const char* mapping,const char* output,const char* mode) {
    gb_prefix=std::string(mode)=="prefix";gb_out=fopen(output,"w");if(!gb_out)exit(5);
    std::ifstream f(mapping);int kind,id,p;
    while(f>>kind>>id){std::vector<int> c;while(f>>p && p)c.push_back(p);std::sort(c.begin(),c.end());gb_inputs[c]={kind,id};if(kind==2)gb_usage[id];}
}
void gb_enqueue(CRef from,ClauseAllocator& ca) {
    ++gb_enqueues;if(from==CRef_Undef)return;auto o=gb_origin(ca[from]);++gb_reason[o.first];
    if(o.first==2){++gb_usage[o.second].reason;if(gb_bcp)++gb_usage[o.second].bcp;}
}
void gb_visit(const Clause& c,int mode) {
    auto o=gb_origin(c);
    if(mode==0)++gb_analysis[o.first];else if(mode==1)++gb_minimize[o.first];else ++gb_conflict[o.first];
    if(o.first==2){auto& u=gb_usage[o.second];if(mode==0)++u.analysis;else if(mode==1)++u.minimize;else ++u.conflict;}
}
void gb_array(unsigned long long* a) {fprintf(gb_out,"[%llu,%llu,%llu,%llu]",a[0],a[1],a[2],a[3]);}
void gb_pick(Lit p) {if(p!=lit_Undef)++gb_decision_hist[var(p)+1];}
void Solver::gb_snapshot(int width,unsigned lbd,int bt) {
    if(conflicts>1000)return;
    gb_width_sum+=width;gb_lbd_sum+=lbd;gb_dl_sum+=decisionLevel();gb_jump_sum+=decisionLevel()-bt;
    fprintf(gb_out,"{\"t\":\"C\",\"n\":%llu,\"ops\":%llu,\"native_props\":%llu,\"dequeues\":%llu,\"enqueues\":%llu,\"decisions\":%llu,\"dl\":%d,\"width\":%d,\"lbd\":%u,\"jump\":%d}\n",(unsigned long long)conflicts,sf_analysis,(unsigned long long)propagations,gb_dequeues,gb_enqueues,(unsigned long long)decisions,decisionLevel(),width,lbd,decisionLevel()-bt);
    if(conflicts!=50 && conflicts!=100 && conflicts!=200 && conflicts!=500 && conflicts!=1000)return;
    fprintf(gb_out,"{\"t\":\"S\",\"n\":%llu,\"ops\":%llu,\"native_props\":%llu,\"dequeues\":%llu,\"enqueues\":%llu,\"decisions\":%llu,\"mean_dl\":%.17g,\"mean_width\":%.17g,\"mean_lbd\":%.17g,\"mean_jump\":%.17g",(unsigned long long)conflicts,sf_analysis,(unsigned long long)propagations,gb_dequeues,gb_enqueues,(unsigned long long)decisions,gb_dl_sum/conflicts,gb_width_sum/conflicts,gb_lbd_sum/conflicts,gb_jump_sum/conflicts);
    std::vector<int> vv;double sum=0,sq=0,ent=0;for(int v=0;v<nVars();++v){vv.push_back(v);double x=activity[v]/var_inc;sum+=x;sq+=x*x;}
    std::sort(vv.begin(),vv.end(),[&](int a,int b){return activity[a]!=activity[b]?activity[a]>activity[b]:a<b;});
    double top=0;for(int i=0;i<std::min(10,nVars());++i)top+=activity[vv[i]]/var_inc;
    if(sum)for(int v=0;v<nVars();++v){double p=activity[v]/var_inc/sum;if(p>0)ent-=p*log(p);}
    fprintf(gb_out,",\"activity_top10_mass\":%.17g,\"activity_entropy\":%.17g,\"activity_spread\":%.17g,\"activity_top10\":[",sum?top/sum:0,ent/log((double)nVars()),sqrt(std::max(0.0,sq/nVars()-sum*sum/nVars()/nVars())));
    for(int i=0;i<std::min(10,nVars());++i)fprintf(gb_out,"%s[%d,%.17g]",i?",":"",vv[i]+1,activity[vv[i]]/var_inc);
    fprintf(gb_out,"],\"heap_insert\":%llu,\"heap_pop\":%llu,\"heap_decrease\":%llu,\"heap_moves\":%llu,\"heap_size\":%d,\"restart_count\":%zu,\"restart_blocks\":%llu,\"restart_indices\":[",gb_heap_insert,gb_heap_pop,gb_heap_decrease,gb_heap_moves,order_heap.size(),gb_restarts.size(),(unsigned long long)nbstopsrestarts);
    for(size_t i=0;i<gb_restarts.size();++i)fprintf(gb_out,"%s%llu",i?",":"",gb_restarts[i]);
    fprintf(gb_out,"],\"decision_hist\":{");bool first=true;for(auto x:gb_decision_hist){fprintf(gb_out,"%s\"%d\":%llu",first?"":",",x.first,x.second);first=false;}
    fprintf(gb_out,"},\"reason_sources\":");gb_array(gb_reason);fprintf(gb_out,",\"analysis_sources\":");gb_array(gb_analysis);fprintf(gb_out,",\"minimization_sources\":");gb_array(gb_minimize);fprintf(gb_out,",\"conflict_sources\":");gb_array(gb_conflict);
    fprintf(gb_out,",\"injected_usage\":{");first=true;for(auto x:gb_usage){auto u=x.second;fprintf(gb_out,"%s\"%d\":[%llu,%llu,%llu,%llu,%llu]",first?"":",",x.first,u.reason,u.bcp,u.analysis,u.minimize,u.conflict);first=false;}fprintf(gb_out,"}}\n");
}
void gb_finish(){fclose(gb_out);}
