#include <cstdio>
#include <cstdlib>
#include <string>
#include <zlib.h>
#include "core/Solver.h"
#include "core/Dimacs.h"
extern std::string output_dir, request_path;
extern bool reached,action_verified;
extern std::string scientific_counters();
extern unsigned long long temporal_samples;
int main(int argc,char**argv){
 if(argc<5)return 2;
 output_dir=argv[3];request_path="";
 Glucose::Solver s;s.verbosity=0;s.certifiedUNSAT=true;s.certifiedOutput=fopen(argv[2],"w");if(!s.certifiedOutput)return 3;
 gzFile in=gzopen(argv[1],"rb");if(!in)return 4;Glucose::parse_DIMACS(in,s);gzclose(in);
 Glucose::vec<Glucose::Lit>a;auto r=s.solveLimited(a);
 printf("{\"status\":\"%s\",\"state_verified\":%s,\"action_verified\":%s,\"conflicts\":%llu,\"decisions\":%llu,\"propagations\":%llu,\"temporal_samples\":%llu}\n",r==Glucose::lbool((uint8_t)1)?"UNSAT":"OTHER",reached?"true":"false",action_verified?"true":"false",(unsigned long long)s.conflicts,(unsigned long long)s.decisions,(unsigned long long)s.propagations,temporal_samples);
 printf("{\"final_counters\":%s}\n",scientific_counters().c_str());
 return r==Glucose::lbool((uint8_t)1)?0:61;
}
