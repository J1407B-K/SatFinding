#include <cstdio>
#include <string>
#include <fstream>
#include <zlib.h>
#include "core/Solver.h"
#include "core/Dimacs.h"
extern std::string scientific_counters();
extern void observer_open(const char*,bool);
extern void observer_close();
extern std::string observer_sequences();
int main(int argc,char**argv){
 if(argc!=5)return 2; // input, proof, trace, off|on
 if(std::string(argv[4])!="on"&&std::string(argv[4])!="off")return 2;
 observer_open(argv[3],std::string(argv[4])=="on");
 Glucose::Solver s;s.verbosity=0;s.certifiedUNSAT=true;s.certifiedOutput=fopen(argv[2],"w");if(!s.certifiedOutput)return 3;
 gzFile in=gzopen(argv[1],"rb");if(!in)return 4;Glucose::parse_DIMACS(in,s);gzclose(in);
 Glucose::vec<Glucose::Lit>a;auto r=s.solveLimited(a);
 observer_close();
 printf("{\"status\":\"%s\",\"conflicts\":%llu,\"decisions\":%llu,\"propagations\":%llu,\"restarts\":%llu,\"replay_controller_initialized\":false,\"checkpoint_requests_seen\":0,\"actions_applied\":0,\"sequences\":%s,\"counters\":%s}\n",r==Glucose::lbool((uint8_t)1)?"UNSAT":"OTHER",(unsigned long long)s.conflicts,(unsigned long long)s.decisions,(unsigned long long)s.propagations,(unsigned long long)s.starts,observer_sequences().c_str(),scientific_counters().c_str());
 return r==Glucose::lbool((uint8_t)1)?0:61;
}
