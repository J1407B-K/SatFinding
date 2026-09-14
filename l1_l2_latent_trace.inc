// Bounded event-level observation. Clause identities are content-based.
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <algorithm>
#include <cstring>
#include <zlib.h>
typedef unsigned long long LU;
gzFile lt_out;
std::string lt_dir,lt_run;
LU lt_global=0,lt_e=0,lt_c=0,lt_d=0;
std::map<std::pair<std::string,LU>,LU> lt_ord;
std::set<std::string> lt_requests;
std::map<LU,std::vector<int>> lt_catalog;
bool lt_intervene=false,lt_did=false;
LU lt_hash(const void* p,size_t n,LU h=1469598103934665603ULL){auto a=(const unsigned char*)p;for(size_t i=0;i<n;++i)h=(h^a[i])*1099511628211ULL;return h;}
template<class T> LU lt_vec(const vec<T>& a){int n=a.size();LU h=lt_hash(&n,sizeof(n));return n?lt_hash(&a[0],sizeof(T)*n,h):h;}
int lt_int(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
bool lt_l2(const Clause& c){if(c.learnt()||c.size()!=3)return false;bool a=false,b=false,d=false;for(int i=0;i<3;++i){int l=lt_int(c[i]);a|=l==-507;b|=l==565;d|=l==566;}return a&&b&&d;}
LU lt_clause(const Clause& c){std::vector<int> v;for(int i=0;i<c.size();++i)v.push_back(lt_int(c[i]));std::sort(v.begin(),v.end());LU h=lt_hash(v.data(),v.size()*sizeof(int));
    auto it=lt_catalog.find(h);if(it!=lt_catalog.end() && it->second!=v)exit(10);lt_catalog[h]=v;return h;}
LU lt_learnt(const vec<Lit>& c){std::vector<int> v;for(int i=0;i<c.size();++i)v.push_back(lt_int(c[i]));std::sort(v.begin(),v.end());LU h=lt_hash(v.data(),v.size()*sizeof(int));lt_catalog[h]=v;return h;}
void lt_init(const char* run,const char* dir,const char* requests){lt_run=run;lt_dir=dir;lt_out=gzopen((lt_dir+"/"+lt_run+".events.jsonl.gz").c_str(),"wb");std::ifstream f(requests);std::string k;while(f>>k)lt_requests.insert(k);lt_intervene=run==std::string("B_REASON_RESET");}
void lt_intvec(FILE* f,const vec<int>& a){fprintf(f,"[");for(int i=0;i<a.size();++i)fprintf(f,"%s%d",i?",":"",a[i]);fprintf(f,"]");}
void Solver::lt_snapshot(const std::string& name){
    FILE* f=fopen((lt_dir+"/"+lt_run+"."+name+".snapshot.json").c_str(),"w");if(!f)exit(9);
    fprintf(f,"{\"c\":%llu,\"d\":%llu,\"e\":%llu,\"global\":%llu,\"dl\":%d,\"qhead\":%d,\"var_inc\":\"%a\",\"assignment\":[",(LU)conflicts,(LU)decisions,lt_e,lt_global,decisionLevel(),qhead,var_inc);
    for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",toInt(assigns[v]));fprintf(f,"],\"activity\":[");
    for(int v=0;v<nVars();++v)fprintf(f,"%s\"%a\"",v?",":"",activity[v]);fprintf(f,"],\"phase\":[");
    for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",(int)polarity[v]);fprintf(f,"],\"eligible\":[");
    for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",(int)decision[v]);fprintf(f,"],\"trail\":[");
    for(int i=0;i<trail.size();++i)fprintf(f,"%s%d",i?",":"",lt_int(trail[i]));fprintf(f,"],\"trail_lim\":");lt_intvec(f,trail_lim);
    fprintf(f,",\"reasons\":[");for(int v=0;v<nVars();++v){LU h=value(v)==l_Undef||reason(v)==CRef_Undef?0:lt_clause(ca[reason(v)]);fprintf(f,"%s\"%llu\"",v?",":"",h);}fprintf(f,"],\"levels\":[");
    for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",value(v)==l_Undef?-1:level(v));fprintf(f,"],\"heap\":");order_heap.lt_dump(f);
    fprintf(f,",\"learned\":[");for(int i=0;i<learnts.size();++i){Clause& c=ca[learnts[i]];fprintf(f,"%s[\"%llu\",%u,\"%a\"]",i?",":"",lt_clause(c),c.lbd(),(double)c.activity());}fprintf(f,"],\"restart\":");lt_restart_json(f);
    fprintf(f,",\"watches\":[");for(int l=0;l<2*nVars();++l){auto& w=watches[toLit(l)];auto& b=watchesBin[toLit(l)];fprintf(f,"%s[",l?",":"");bool first=true;for(int i=0;i<b.size();++i){fprintf(f,"%s[\"%llu\",%d]",first?"":",",lt_clause(ca[b[i].cref]),lt_int(b[i].blocker));first=false;}for(int i=0;i<w.size();++i){fprintf(f,"%s[\"%llu\",%d]",first?"":",",lt_clause(ca[w[i].cref]),lt_int(w[i].blocker));first=false;}fprintf(f,"]");}fprintf(f,"],\"simpDB_props\":%lld,\"clauses_literals\":%llu}\n",(long long)simpDB_props,(LU)clauses_literals);fclose(f);
}
void Solver::lt_restart_json(FILE* f){fprintf(f,"{\"starts\":%llu,\"conflictsRestarts\":%llu,\"blocks\":%llu,\"same\":%llu,\"lastblock\":%llu,\"sumLBD\":\"%a\",\"lbdQueue\":",(LU)starts,(LU)conflictsRestarts,(LU)nbstopsrestarts,(LU)nbstopsrestartssame,(LU)lastblockatrestart,(double)sumLBD);lbdQueue.lt_dump(f);fprintf(f,",\"trailQueue\":");trailQueue.lt_dump(f);fprintf(f,"}");}
LU Solver::lt_restart_hash(){LU vals[]={(LU)starts,(LU)conflictsRestarts,(LU)nbstopsrestarts,(LU)nbstopsrestartssame,(LU)lastblockatrestart};LU h=lt_hash(vals,sizeof(vals));h=lt_hash(&sumLBD,sizeof(sumLBD),h);LU a=lbdQueue.lt_hash_state(),b=trailQueue.lt_hash_state();h=lt_hash(&a,sizeof(a),h);return lt_hash(&b,sizeof(b),h);}
void Solver::lt_event(const char* kind,int value,LU reasonhash,bool special){
    lt_c=conflicts;lt_d=decisions;++lt_global;LU k=++lt_ord[{kind,conflicts}];
    if(conflicts<=900||special){
      LU ah=lt_vec(activity),hh=order_heap.lt_hash_state(),th=lt_vec(trail),rh=lt_restart_hash();
      gzprintf(lt_out,"{\"t\":\"%s\",\"g\":%llu,\"c\":%llu,\"d\":%llu,\"e\":%llu,\"k\":%llu,\"dl\":%d,\"v\":%d,\"r\":\"%llu\",\"a\":\"%llu\",\"h\":\"%llu\",\"trail\":\"%llu\",\"restart\":\"%llu\",\"l2\":%d,\"ops\":%llu}\n",kind,lt_global,(LU)conflicts,(LU)decisions,lt_e,k,decisionLevel(),value,reasonhash,ah,hh,th,rh,special,sf_analysis);
    }
    std::string key=std::string(kind)+"_"+std::to_string(conflicts)+"_"+std::to_string(k);
    if(lt_requests.count(key))lt_snapshot(key);
}
void Solver::lt_pre_enqueue(Lit p,CRef from){
    if(lt_e+1==28916)lt_snapshot("first_reason_before");
}
void Solver::lt_post_enqueue(Lit p,CRef from){
    ++lt_e;lt_event("E",lt_int(p),from==CRef_Undef?0:lt_clause(ca[from]),from!=CRef_Undef && lt_l2(ca[from]));
    if(lt_e==28916){lt_snapshot("first_reason_after");
      if(lt_intervene){
        if(!lt_l2(ca[from])||lt_int(p)!=565||conflicts!=198)exit(11);
        CRef replacement=CRef_Undef;
        for(int i=0;i<clauses.size();++i){Clause& c=ca[clauses[i]];if(c.size()!=3)continue;bool a=false,b=false,d=false;for(int j=0;j<3;++j){a|=lt_int(c[j])==565;b|=lt_int(c[j])==566;d|=lt_int(c[j])==567;}if(a&&b&&d){replacement=clauses[i];break;}}
        if(replacement==CRef_Undef)exit(12);Clause& c=ca[replacement];
        for(int j=0;j<c.size();++j)if(var(c[j])!=var(p) && value(c[j])!=l_False)exit(13);
        if(c[0]!=p)exit(14); // first-UIP's reason convention must already hold
        vardata[var(p)].reason=replacement;lt_did=true;lt_snapshot("reason_reset_after");
      }
    }
}
void Solver::lt_analysis(const Clause& c,Lit pivot,int mode){lt_event(mode==0?"A":"M",pivot==lit_Undef?0:lt_int(pivot),lt_clause(c),lt_l2(c));}
void Solver::lt_bump(Var v){lt_event("U",v+1,0,false);}
void Solver::lt_watch(const Clause& c,Lit trigger,int stage){if(lt_l2(c)){lt_event(stage==0?"W":"W_AFTER",lt_int(trigger),lt_clause(c),true);}}
void lt_finish(){for(auto x:lt_catalog){gzprintf(lt_out,"{\"t\":\"Q\",\"id\":\"%llu\",\"clause\":[",x.first);for(size_t i=0;i<x.second.size();++i)gzprintf(lt_out,"%s%d",i?",":"",x.second[i]);gzprintf(lt_out,"]}\n");}gzclose(lt_out);if(lt_intervene&&!lt_did)exit(15);}
