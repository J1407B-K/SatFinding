// Single intervention. All search-state writes are confined to activity and
// Heap::ah_restore's heap/indices; the comparator remains bound to Gold activity.
#include <vector>
#include <string>
#include <cstring>
#include <algorithm>
#include <stdexcept>

std::string ah_mode,ah_dir;
FILE* ah_trace=nullptr;
bool ah_done=false;
void ah_init(const char* mode,const char* dir) {
    ah_mode=mode;ah_dir=dir;
    ah_trace=fopen((ah_dir+"/"+ah_mode+".trace.jsonl").c_str(),"w");
    if(!ah_trace)throw std::runtime_error("Cannot open trace");
}
template<class T> void ah_vec(FILE* f,const vec<T>& v) {
    int n=v.size();fwrite(&n,sizeof(n),1,f);if(n)fwrite(&v[0],sizeof(T),n,f);
}
template<class T> std::vector<T> ah_read(FILE* f) {
    int n=-1;if(fread(&n,sizeof(n),1,f)!=1 || n<0 || n>100000)throw std::runtime_error("Invalid snapshot size");
    std::vector<T> a(n);if(n && fread(a.data(),sizeof(T),n,f)!=(size_t)n)throw std::runtime_error("Truncated snapshot");return a;
}
template<class T> void ah_json_ints(FILE* f,const vec<T>& v) {
    fprintf(f,"[");for(int i=0;i<v.size();++i)fprintf(f,"%s%d",i?",":"",(int)v[i]);fprintf(f,"]");
}
void Solver::ah_dump(const char* tag) {
    std::string stem=ah_dir+"/"+ah_mode+"."+tag;
    FILE* f=fopen((stem+".allowed.bin").c_str(),"wb");
    ah_vec(f,activity);order_heap.ah_save(f);fclose(f);
    // Stable within-process byte comparison. Mask ONLY the allowed members in
    // the object representation; explicitly include all live owned buffers.
    f=fopen((stem+".other.bin").c_str(),"wb");
    std::vector<unsigned char> object(sizeof(Solver));memcpy(object.data(),this,sizeof(Solver));
    auto mask=[&](const void* p,size_t n){size_t k=(const unsigned char*)p-(const unsigned char*)this;std::fill(object.begin()+k,object.begin()+k+n,0);};
    mask(&activity,sizeof(activity));mask(&order_heap,sizeof(order_heap));
    fwrite(object.data(),1,object.size(),f);
#define AHV(x) ah_vec(f,x)
    AHV(model);AHV(conflict);AHV(clauses);AHV(learnts);AHV(assigns);AHV(polarity);AHV(decision);
    AHV(trail);AHV(nbpos);AHV(trail_lim);AHV(vardata);AHV(assumptions);AHV(permDiff);
#ifdef UPDATEVARACTIVITY
    AHV(lastDecisionLevel);
#endif
    AHV(seen);AHV(analyze_stack);AHV(analyze_toclear);AHV(add_tmp);AHV(assumptionPositions);AHV(initialPositions);
#undef AHV
    watches.ah_audit(f);watchesBin.ah_audit(f);trailQueue.ah_audit(f);lbdQueue.ah_audit(f);
    uint32_t words=ca.size();fwrite(&words,sizeof(words),1,f);
    if(words)fwrite(ca.RegionAllocator<uint32_t>::lea(0),sizeof(uint32_t),words,f);
    fwrite(&sf_analysis,sizeof(sf_analysis),1,f);fwrite(&sf_redundancy,sizeof(sf_redundancy),1,f);fwrite(&sf_binary,sizeof(sf_binary),1,f);
    fclose(f);
    // Address-independent logical fields for cross-run interpretation.
    f=fopen((stem+".json").c_str(),"w");
    fprintf(f,"{\"conflicts\":%llu,\"decision_call\":%llu,\"dl\":%d,\"qhead\":%d,\"trail_size\":%d,\"var_inc\":\"%a\",\"activity\":[",(unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),qhead,trail.size(),var_inc);
    for(int v=0;v<activity.size();++v)fprintf(f,"%s\"%a\"",v?",":"",activity[v]);
    fprintf(f,"],\"heap\":");order_heap.ah_json(f);
    fprintf(f,",\"assignment\":[");for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",toInt(assigns[v]));
    fprintf(f,"],\"phase\":");ah_json_ints(f,polarity);
    fprintf(f,",\"decision_eligible\":");ah_json_ints(f,decision);
    fprintf(f,",\"trail\":[");for(int i=0;i<trail.size();++i)fprintf(f,"%s%d",i?",":"",(var(trail[i])+1)*(sign(trail[i])?-1:1));
    fprintf(f,"],\"trail_lim\":");ah_json_ints(f,trail_lim);
    fprintf(f,",\"reasons\":[");for(int v=0;v<nVars();++v)fprintf(f,"%s%u",v?",":"",reason(v));
    fprintf(f,"],\"levels\":[");for(int v=0;v<nVars();++v)fprintf(f,"%s%d",v?",":"",level(v));
    // Pop a COPY to inspect exact tie-aware candidate ordering, without touching
    // the actual heap, assignments, random seed, or saved phase.
    vec<int> hh,ii;order_heap.ah_copy(hh,ii);Heap<VarOrderLt> probe((VarOrderLt(activity)));probe.ah_restore(hh,ii);
    fprintf(f,"],\"pop_order\":[");bool first=true;int missing=0;
    for(int v=0;v<nVars();++v)if(value(v)==l_Undef && decision[v] && !order_heap.inHeap(v))++missing;
    while(!probe.empty()){int v=probe.removeMin();fprintf(f,"%s[%d,%d,%d]",first?"":",",v+1,value(v)==l_Undef && decision[v],(int)polarity[v]);first=false;}
    fprintf(f,"],\"missing_eligible\":%d,\"heap_consistent\":%s}\n",missing,order_heap.ah_valid()?"true":"false");fclose(f);
}
void Solver::ah_hook() {
    if(decisions!=22)return;
    if(ah_done || conflicts!=3 || qhead!=trail.size())throw std::runtime_error("Wrong logical intervention time");
    ah_dump("before");
    if(ah_mode=="GOLD_ACTIVITY_RESET") {
        FILE* f=fopen((ah_dir+"/CONTROL.before.allowed.bin").c_str(),"rb");
        if(!f)throw std::runtime_error("Missing CONTROL snapshot");
        auto aa=ah_read<double>(f);auto hh=ah_read<int>(f);auto ii=ah_read<int>(f);
        if(fgetc(f)!=EOF)throw std::runtime_error("Extra snapshot data");fclose(f);
        if(aa.size()!=(size_t)activity.size())throw std::runtime_error("Variable count mismatch");
        vec<int> hv,iv;for(int v:hh)hv.push(v);for(int v:ii)iv.push(v);
        for(int v=0;v<activity.size();++v)activity[v]=aa[v];
        order_heap.ah_restore(hv,iv);
        if(!order_heap.ah_valid())throw std::runtime_error("Invalid restored heap");
        for(int v=0;v<nVars();++v)if(value(v)==l_Undef && decision[v] && !order_heap.inHeap(v))throw std::runtime_error("Gold free variable missing from restored CONTROL heap");
    }
    ah_dump("after");ah_done=true;
}
void ah_decision(Lit p,unsigned long long cc,unsigned long long d,int dl) {
    if(p!=lit_Undef)fprintf(ah_trace,"{\"t\":\"D\",\"c\":%llu,\"d\":%llu,\"dl\":%d,\"lit\":%d}\n",cc,d,dl,(var(p)+1)*(sign(p)?-1:1));
}
void ah_learn(const vec<Lit>& c,unsigned long long cc,unsigned long long ops,unsigned lbd) {
    std::vector<int> vv;for(int i=0;i<c.size();++i)vv.push_back((var(c[i])+1)*(sign(c[i])?-1:1));std::sort(vv.begin(),vv.end());
    fprintf(ah_trace,"{\"t\":\"L\",\"c\":%llu,\"ops\":%llu,\"lbd\":%u,\"clause\":[",cc,ops,lbd);
    for(size_t i=0;i<vv.size();++i)fprintf(ah_trace,"%s%d",i?",":"",vv[i]);fprintf(ah_trace,"]}\n");
}
void ah_finish(){if(!ah_done)throw std::runtime_error("Intervention point not reached");fclose(ah_trace);}
