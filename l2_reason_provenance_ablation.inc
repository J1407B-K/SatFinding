// Task-local observer metadata; no writes to solver state in the scan.
#include <map>
#include <vector>
#include <algorithm>
#include <stdexcept>
static std::map<CRef, unsigned long long> rp_ids;
static unsigned long long rp_next = 0, rp_l2 = 0;
static FILE* rp_log = nullptr;
static bool rp_enabled = false;
void rp_init(const char* route, const char* path) {
    rp_enabled = std::string(route) == "B_NO_L2_PROVENANCE_COMPAT";
    rp_log = fopen(path, "w");
    if (!rp_log) throw std::runtime_error("ledger open failed");
}
void rp_finish() { if (rp_log) fclose(rp_log); }
static int rp_lit(Lit p) { return (var(p)+1)*(sign(p)?-1:1); }
static bool rp_is_l2(const Clause& c) {
    if(c.size()!=3) return false;
    std::vector<int> v;
    for(int i=0;i<c.size();++i) v.push_back(rp_lit(c[i]));
    std::sort(v.begin(),v.end());
    return v == std::vector<int>({-507,565,566});
}
void Solver::rp_register(CRef cr) {
    rp_ids[cr] = ++rp_next;
    if(!ca[cr].learnt() && rp_is_l2(ca[cr])) {
        if(rp_l2) throw std::runtime_error("duplicate input L2");
        rp_l2 = rp_next;
    }
}
void Solver::rp_relocated() {
    std::map<CRef,unsigned long long> next;
    for(const auto& entry:rp_ids) {
        const Clause& c=ca[entry.first];
        if(!c.reloced()) throw std::runtime_error("active clause not relocated");
        next[c.relocation()]=entry.second;
    }
    rp_ids.swap(next);
}
bool Solver::rp_unit(CRef cr, Lit p) const {
    const Clause& c=ca[cr];
    if(c.mark()!=0 || value(p)!=l_Undef) return false;
    int unset=0;
    for(int j=0;j<c.size();++j) {
        if(value(c[j])==l_Undef) {
            if(c[j]!=p) return false;
            ++unset;
        } else if(value(c[j])!=l_False) return false;
    }
    return unset==1;
}
CRef Solver::rp_reason(Lit p,CRef from) {
    if(from==CRef_Undef || !rp_l2 || rp_ids.at(from)!=rp_l2) return from;
    // Explicit runtime validation remains active in the -DNDEBUG build.
    if(value(p)!=l_Undef || !rp_unit(from,p))
        throw std::runtime_error("L2 pre-enqueue unit invariant failed");
    CRef best=CRef_Undef;
    unsigned long long best_id=~0ULL;
    unsigned candidates=0, legal=0;
    std::vector<CRef> candidate_refs;
    auto scan=[&](const vec<CRef>& db) {
        for(int i=0;i<db.size();++i) {
            CRef cr=db[i];
            if(cr==from || !rp_unit(cr,p)) continue;
            ++candidates;
            candidate_refs.push_back(cr);
            const Clause& c=ca[cr];
            if(!(c.size()==2 || (c.size()>2 && c[0]==p))) continue;
            ++legal;
            auto id=rp_ids.at(cr);
            if(id<best_id) { best=cr;best_id=id; }
        }
    };
    scan(clauses);scan(learnts);
    bool layout=best!=CRef_Undef && (ca[best].size()==2 ||
                      (ca[best].size()>2 && ca[best][0]==p));
    bool substitute=rp_enabled && best!=CRef_Undef && layout;
    bool abort=false;
    if(best!=CRef_Undef && (!rp_unit(best,p) || !layout))
        throw std::runtime_error("alternate online unit verification failed");
    fprintf(rp_log,"{\"conflict\":%llu,\"decision\":%llu,\"level\":%d,\"literal\":%d,\"l2_id\":%llu,\"pre_enqueue_unassigned\":true,\"unit_candidates\":%u,\"legal_candidates\":%u,\"selected_layout_legal\":%s,\"substituted\":%s,\"abort\":%s,\"alternate\":",
        (unsigned long long)conflicts,(unsigned long long)decisions,decisionLevel(),rp_lit(p),rp_l2,candidates,legal,layout?"true":"false",substitute?"true":"false",abort?"true":"false");
    if(best==CRef_Undef) fprintf(rp_log,"null");
    else {
        const Clause& c=ca[best];
        fprintf(rp_log,"{\"id\":%llu,\"learnt\":%s,\"literals\":[",best_id,c.learnt()?"true":"false");
        for(int j=0;j<c.size();++j) fprintf(rp_log,"%s%d",j?",":"",rp_lit(c[j]));
        fprintf(rp_log,"],\"pre_values\":[");
        for(int j=0;j<c.size();++j) fprintf(rp_log,"%s\"%s\"",j?",":"",value(c[j])==l_Undef?"UNASSIGNED":"FALSE");
        fprintf(rp_log,"],\"online_unit_verified\":true}");
    }
    fprintf(rp_log,",\"l2_clause\":[");
    const Clause& l2=ca[from];
    for(int j=0;j<l2.size();++j) fprintf(rp_log,"%s%d",j?",":"",rp_lit(l2[j]));
    fprintf(rp_log,"],\"candidates\":[");
    for(size_t i=0;i<candidate_refs.size();++i) {
        CRef cr=candidate_refs[i];const Clause& c=ca[cr];
        bool compatible=c.size()==2 || (c.size()>2 && c[0]==p);
        fprintf(rp_log,"%s{\"id\":%llu,\"layout_compatible\":%s,\"status\":\"%s\",\"literals\":[",
            i?",":"",rp_ids.at(cr),compatible?"true":"false",
            compatible?"LOGICALLY_VALID_LAYOUT_COMPATIBLE":"LOGICALLY_VALID_LAYOUT_INCOMPATIBLE");
        for(int j=0;j<c.size();++j) fprintf(rp_log,"%s%d",j?",":"",rp_lit(c[j]));
        fprintf(rp_log,"],\"pre_values\":[");
        for(int j=0;j<c.size();++j) fprintf(rp_log,"%s\"%s\"",j?",":"",value(c[j])==l_Undef?"UNASSIGNED":"FALSE");
        fprintf(rp_log,"]}");
    }
    fprintf(rp_log,"]}\n");fflush(rp_log);
    return substitute?best:from;
}
