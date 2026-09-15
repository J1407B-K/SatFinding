// Thin driver for unmodified Glucose 3.0 search plus observational counters.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <zlib.h>
#include "core/Solver.h"
#include "core/Dimacs.h"

extern unsigned long long sf_analysis, sf_redundancy, sf_binary;

#include <stdexcept>
#include <string>
#include <fstream>
#include <iterator>
extern void hc_init(const char*,int);
extern void pm_finish(const char*);
int main(int argc, char **argv) {
    if (argc >= 5 && std::string(argv[1]) == "--replay-frozen-package") {
        std::string pkg=argv[2], route=argv[4]; auto read=[&](const char* n){std::ifstream f(pkg+"/"+n); return std::string((std::istreambuf_iterator<char>(f)),{});};
        std::string st=read("state.json"), ac=read("actions.json"); auto num=[&](std::string x,std::string k){auto p=x.find("\""+k+"\""); if(p==std::string::npos)return std::string("0"); p=x.find(":",p)+1; auto e=x.find_first_of(",}\n",p); return x.substr(p,e-p);};
        setenv("PM_MODE","frozen_replay",1); setenv("PM_REPLAY_BUCKET",num(st,"conflict_index").c_str(),1); setenv("PM_REPLAY_STATE_HASH",num(st,"state_hash").c_str(),1); if(route=="action"){int rank=atoi(argv[5]); std::string key="\"rank\":"+std::to_string(rank); auto q=ac.find(key); auto z=ac.find("\"literal\"",q); auto e=ac.find_first_of(",}",ac.find(":",z)+1); setenv("PM_REPLAY_LITERAL",ac.substr(ac.find(":",z)+1,e-ac.find(":",z)-1).c_str(),1); auto id=num(ac,"id"); setenv("PM_REPLAY_ACTION_ID",id.c_str(),1);} } else if (argc != 6) {
        fprintf(stderr, "usage: native_cdcl input.cnf output.drup conflict_budget\n");
        return 2;
    }
    hc_init(argv[4],atoi(argv[5]));
    auto start = std::chrono::steady_clock::now();
    Glucose::Solver solver;
    solver.verbosity = 0;
    solver.certifiedUNSAT = true;
    solver.certifiedOutput = fopen(argv[2], "w");
    if (!solver.certifiedOutput) return 3;
    gzFile in = gzopen(argv[1], "rb");
    if (!in) return 4;
    Glucose::parse_DIMACS(in, solver);
    gzclose(in);
    solver.setConfBudget(atoll(argv[3]));
    Glucose::vec<Glucose::Lit> assumptions;
    Glucose::lbool result((uint8_t)2);std::string failure;
    try{result=solver.solveLimited(assumptions);}catch(const std::runtime_error& e){failure=e.what();}
    double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    const char *status = result == Glucose::lbool((uint8_t)0) ? "SAT" :
                         result == Glucose::lbool((uint8_t)1) ? "UNSAT" : "UNKNOWN";
    if(!failure.empty())status=failure.c_str();
    printf("{\"status\":\"%s\",\"seconds\":%.9f,\"analysis_resolution_steps\":%llu,"
           "\"minimization_reason_visits\":%llu,\"binary_minimization_candidates\":%llu,"
           "\"conflicts\":%llu,\"decisions\":%llu,\"propagations\":%llu}\n",
           status, seconds, sf_analysis, sf_redundancy, sf_binary,
           (unsigned long long)solver.conflicts, (unsigned long long)solver.decisions,
           (unsigned long long)solver.propagations);
    if (result == Glucose::lbool((uint8_t)0) && failure.empty()) {
        printf("{\"event\":\"MODEL\",\"model\":[");
        for(int v=0;v<solver.nVars();++v) printf("%s%d",v?",":"",(v+1)*(solver.modelValue(v)==Glucose::lbool((uint8_t)0)?1:-1));
        printf("]}\n");
    }
    pm_finish(status);
    return failure.empty()?0:42;
}
