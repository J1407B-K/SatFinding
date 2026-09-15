#include <cstdio>
#include <cstdlib>
#include <string>
#include <zlib.h>
#include "core/Solver.h"
#include "core/Dimacs.h"
extern std::string output_dir, request_path,ep_donor;
extern int ep_k;
extern bool ep_done;
extern bool reached,action_verified;
extern std::string scientific_counters();
extern unsigned long long temporal_samples;
#ifdef OBSERVE_FULL_RUN
extern void opportunity_finish();
#endif
int main(int argc,char**argv){
 if(argc!=5 && argc!=7)return 2;
 if(argc==7){ep_k=atoi(argv[5]);ep_donor=argv[6];}
 output_dir=argv[3];request_path=argv[4];
 Glucose::Solver s;s.verbosity=0;s.certifiedUNSAT=true;s.certifiedOutput=fopen(argv[2],"w");if(!s.certifiedOutput)return 3;
 gzFile in=gzopen(argv[1],"rb");if(!in)return 4;Glucose::parse_DIMACS(in,s);gzclose(in);
 Glucose::vec<Glucose::Lit>a;auto r=s.solveLimited(a);
#ifdef OBSERVE_FULL_RUN
 opportunity_finish();
#endif
 printf("{\"status\":\"%s\",\"state_verified\":%s,\"action_verified\":%s,\"conflicts\":%llu,\"decisions\":%llu,\"propagations\":%llu,\"temporal_samples\":%llu}\n",r==Glucose::lbool((uint8_t)1)?"UNSAT":"OTHER",reached?"true":"false",action_verified?"true":"false",(unsigned long long)s.conflicts,(unsigned long long)s.decisions,(unsigned long long)s.propagations,temporal_samples);
 printf("{\"final_counters\":%s}\n",scientific_counters().c_str());
 if(argc==7&&!ep_done)return 62;
 return reached&&r==Glucose::lbool((uint8_t)1)?0:61;
}
