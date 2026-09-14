// Observation only: no writes to solver assignments, watches, activity or queues.
#include <map>
#include <vector>
#include <algorithm>
#include <fstream>
#include <string>
#include <cstdint>

FILE* gm_out=nullptr;
const int gm_early=64;
bool gm_bcp=false;
unsigned long long gm_events=0,gm_dequeues=0,gm_cc=0;
std::vector<unsigned long long> gm_last(10000,0),gm_mask(10000,0);
std::map<std::vector<int>,std::string> gm_input;
std::map<std::vector<int>,int> gm_gold;
std::map<int,int> gm_bits;
std::map<std::pair<bool,std::vector<int>>,int> gm_index;
struct GMClause {
    std::vector<int> lits; std::string label; int gold=-1;
    unsigned long long enqueue=0,bcp=0,analysis=0,minimize=0,conflict=0;
    long long first_enqueue=-1,first_bcp=-1,first_analysis=-1,first_conflict=-1;
};
std::vector<GMClause> gm_clauses;
int gm_lit(Lit p) { return (var(p)+1)*(sign(p)?-1:1); }
void gm_ints(const std::vector<int>& v) {
    fprintf(gm_out,"[");for(size_t i=0;i<v.size();++i)fprintf(gm_out,"%s%d",i?",":"",v[i]);fprintf(gm_out,"]");
}
void gm_ids(const std::vector<unsigned long long>& v) {
    fprintf(gm_out,"[");for(size_t i=0;i<v.size();++i)fprintf(gm_out,"%s%llu",i?",":"",v[i]);fprintf(gm_out,"]");
}
int gm_register(std::vector<int> v,bool learned) {
    std::sort(v.begin(),v.end());auto k=std::make_pair(learned,v);
    auto it=gm_index.find(k);if(it!=gm_index.end())return it->second;
    int id=gm_clauses.size();GMClause r;r.lits=v;
    r.label=learned?"L":(gm_input.count(v)?gm_input[v]:"I");
    if(!learned && gm_gold.count(v))r.gold=gm_gold[v];
    gm_index[k]=id;gm_clauses.push_back(r);return id;
}
int gm_clause(const Clause& c) {
    std::vector<int> v;for(int i=0;i<c.size();++i)v.push_back(gm_lit(c[i]));return gm_register(v,c.learnt());
}
int gm_learned(const vec<Lit>& c) {
    std::vector<int> v;for(int i=0;i<c.size();++i)v.push_back(gm_lit(c[i]));return gm_register(v,true);
}
void gm_init(const char* mapping,const char* output) {
    gm_out=fopen(output,"w");if(!gm_out)exit(5);
    std::ifstream f(mapping);std::string label;int gold,p,bit=0;
    while(f>>label>>gold) {std::vector<int> c;while(f>>p && p)c.push_back(p);
      std::sort(c.begin(),c.end());gm_input[c]=label;
      if(gold>=0){gm_gold[c]=gold;gm_bits[gold]=bit++;}
    }
    if(bit>64)exit(6);
}
void gm_enqueue(Lit p,CRef from,ClauseAllocator& ca,int dl,unsigned long long cc) {
    ++gm_events;gm_cc=cc;int id=-1;unsigned long long mask=0;
    std::vector<unsigned long long> deps;
    if(from!=CRef_Undef) {
        id=gm_clause(ca[from]);auto& r=gm_clauses[id];++r.enqueue;
        if(r.first_enqueue<0)r.first_enqueue=cc;
        if(gm_bcp){++r.bcp;if(r.first_bcp<0)r.first_bcp=cc;}
        for(int i=0;i<ca[from].size();++i)if(var(ca[from][i])!=var(p)) {
            int v=var(ca[from][i]);mask|=gm_mask[v];deps.push_back(gm_last[v]);
        }
        if(r.gold>=0)mask|=1ULL<<gm_bits[r.gold];
    }
    gm_last[var(p)]=gm_events;gm_mask[var(p)]=mask;
    if(cc<gm_early) {
        fprintf(gm_out,"{\"t\":\"E\",\"e\":%llu,\"c\":%llu,\"dl\":%d,\"lit\":%d,\"r\":%d,\"bcp\":%d,\"mask\":\"%llu\",\"deps\":",gm_events,cc,dl,gm_lit(p),id,gm_bcp,mask);
        gm_ids(deps);fprintf(gm_out,"}\n");
    }
}
void gm_analysis(const Clause& c,Lit p,unsigned long long cc,bool minimize=false) {
    int id=gm_clause(c);auto& r=gm_clauses[id];
    if(minimize)++r.minimize;else {++r.analysis;if(r.first_analysis<0)r.first_analysis=cc;}
    if(cc<=gm_early && !minimize)fprintf(gm_out,"{\"t\":\"A\",\"c\":%llu,\"r\":%d,\"pivot\":%d}\n",cc,id,p==lit_Undef?0:gm_lit(p));
}
void gm_conflict(const Clause& c,int dl,unsigned long long cc,unsigned long long props,unsigned long long decisions,unsigned long long ops,int trail) {
    gm_cc=cc;int id=gm_clause(c);auto& r=gm_clauses[id];++r.conflict;
    if(r.first_conflict<0)r.first_conflict=cc;
    fprintf(gm_out,"{\"t\":\"C\",\"c\":%llu,\"r\":%d,\"dl\":%d,\"props\":%llu,\"dequeues\":%llu,\"enqueues\":%llu,\"decisions\":%llu,\"ops\":%llu,\"trail\":%d",cc,id,dl,props,gm_dequeues,gm_events,decisions,ops,trail);
    if(cc<=gm_early){std::vector<unsigned long long> deps;for(int i=0;i<c.size();++i)deps.push_back(gm_last[var(c[i])]);fprintf(gm_out,",\"deps\":");gm_ids(deps);}
    fprintf(gm_out,"}\n");
}
void gm_learn(const vec<Lit>& c,int dl,int bt,unsigned lbd,unsigned long long cc,unsigned long long ops,const vec<double>& activity) {
    int id=gm_learned(c);
    fprintf(gm_out,"{\"t\":\"L\",\"c\":%llu,\"r\":%d,\"dl\":%d,\"bt\":%d,\"width\":%d,\"lbd\":%u,\"ops\":%llu",cc,id,dl,bt,c.size(),lbd,ops);
    if(cc<=gm_early || cc%100==0) {
        std::vector<int> vv;for(int i=0;i<activity.size();++i)vv.push_back(i);
        std::partial_sort(vv.begin(),vv.begin()+std::min(10,(int)vv.size()),vv.end(),[&](int a,int b){return activity[a]!=activity[b]?activity[a]>activity[b]:a<b;});
        fprintf(gm_out,",\"top\":[");for(int i=0;i<std::min(10,(int)vv.size());++i)fprintf(gm_out,"%s[%d,%.17g]",i?",":"",vv[i]+1,activity[vv[i]]);fprintf(gm_out,"]");
    }
    fprintf(gm_out,"}\n");
}
void gm_decision(Lit p,int dl,unsigned long long cc,unsigned long long d) {
    if(p!=lit_Undef)fprintf(gm_out,"{\"t\":\"D\",\"c\":%llu,\"d\":%llu,\"dl\":%d,\"lit\":%d,\"e\":%llu}\n",cc,d,dl,gm_lit(p),gm_events);
}
void gm_finish() {
    for(size_t id=0;id<gm_clauses.size();++id) {
        auto& r=gm_clauses[id];
        fprintf(gm_out,"{\"t\":\"Q\",\"id\":%zu,\"label\":\"%s\",\"gold\":%d,\"clause\":",id,r.label.c_str(),r.gold);gm_ints(r.lits);
        fprintf(gm_out,",\"reason\":%llu,\"bcp\":%llu,\"analysis\":%llu,\"minimize\":%llu,\"conflict\":%llu,\"first_reason\":%lld,\"first_bcp\":%lld,\"first_analysis\":%lld,\"first_conflict\":%lld}\n",r.enqueue,r.bcp,r.analysis,r.minimize,r.conflict,r.first_enqueue,r.first_bcp,r.first_analysis,r.first_conflict);
    }
    fprintf(gm_out,"{\"t\":\"END\",\"enqueues\":%llu,\"dequeues\":%llu}\n",gm_events,gm_dequeues);fclose(gm_out);
}
