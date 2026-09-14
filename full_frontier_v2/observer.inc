// Observer-owned state only. No solver-owned container is modified here.
#include <zlib.h>
#include <CommonCrypto/CommonDigest.h>
#include <sstream>
#include <fstream>
#include <vector>
#include <algorithm>
#include <stdexcept>
#include <iomanip>
static gzFile ff_file=nullptr;
static bool ff_enabled=false, ff_started=false;
static unsigned long long ff_ordinal=0,ff_step=0,ff_conflict=0;
static int ff_before_q=0,ff_before_size=0;
static Lit ff_processed=lit_Undef;
static CC_SHA256_CTX ff_dec_hash,ff_enq_hash;
static unsigned long long ff_dec_count=0,ff_enq_count=0;
static int ff_lit(Lit p){return (var(p)+1)*(sign(p)?-1:1);}
static std::string ff_sha(const std::string&s){unsigned char h[32];CC_SHA256(s.data(),s.size(),h);std::ostringstream o;for(auto c:h)o<<std::hex<<std::setw(2)<<std::setfill('0')<<(int)c;return o.str();}
static std::string ff_finish_hash(CC_SHA256_CTX c){unsigned char h[32];CC_SHA256_Final(h,&c);std::ostringstream o;for(auto v:h)o<<std::hex<<std::setw(2)<<std::setfill('0')<<(int)v;return o.str();}
static void ff_hash(CC_SHA256_CTX&c,int p){std::string s=std::to_string(p)+"\n";CC_SHA256_Update(&c,s.data(),s.size());}
static void ff_open(const std::string&p,bool enabled){ff_enabled=enabled;ff_started=true;ff_ordinal=ff_step=ff_conflict=0;ff_dec_count=ff_enq_count=0;CC_SHA256_Init(&ff_dec_hash);CC_SHA256_Init(&ff_enq_hash);if(enabled){ff_file=gzopen(p.c_str(),"wb1");if(!ff_file)throw std::runtime_error("TRACE_OPEN");gzbuffer(ff_file,1<<20);}}
static void ff_close(){if(ff_file){if(gzclose(ff_file)!=Z_OK)throw std::runtime_error("TRACE_CLOSE");ff_file=nullptr;}ff_enabled=false;}
static std::string ff_sequence_summary(){return "{\"decision_sha256\":\""+ff_finish_hash(ff_dec_hash)+"\",\"enqueue_sha256\":\""+ff_finish_hash(ff_enq_hash)+"\",\"decision_count\":"+std::to_string(ff_dec_count)+",\"enqueue_count\":"+std::to_string(ff_enq_count)+"}";}
template<class V>static void ff_array(std::ostream&o,const V&v){o<<'[';bool first=true;for(auto x:v){if(!first)o<<',';first=false;o<<x;}o<<']';}
std::string Solver::ff_clause(CRef cr){std::ostringstream o;std::vector<int> v;if(cr!=CRef_Undef){const Clause&c=ca[cr];for(int i=0;i<c.size();i++)v.push_back(ff_lit(c[i]));std::sort(v.begin(),v.end());}ff_array(o,v);return o.str();}
void Solver::ff_snapshot(std::ostream&o,bool reasons){o<<"\"qhead\":"<<qhead<<",\"level\":"<<decisionLevel()<<",\"trail\":[";for(int i=0;i<trail.size();i++)o<<(i?",":"")<<ff_lit(trail[i]);o<<"],\"pending_ordered\":[";for(int i=qhead;i<trail.size();i++)o<<(i>qhead?",":"")<<ff_lit(trail[i]);o<<"],\"trail_length\":"<<trail.size();if(reasons){o<<",\"assigned\":[";for(int i=0;i<trail.size();i++){int v=var(trail[i]);std::string c=ff_clause(reason(v));o<<(i?",":"")<<"{\"literal\":"<<ff_lit(trail[i])<<",\"var\":"<<v+1<<",\"sign\":"<<(sign(trail[i])?"true":"false")<<",\"level\":"<<level(v)<<",\"trail_position\":"<<i<<",\"reason\":"<<c<<",\"reason_id\":\""<<(reason(v)==CRef_Undef?(level(v)==0?"ROOT":"DECISION"):ff_sha(c))<<"\"}";}o<<']';}}
void Solver::ff_event(const char* kind,Lit p,CRef cr,const vec<Lit>*ls,int a,int b){
 if(!ff_started)return;
 std::string k(kind);
 if(k=="decision"){ff_hash(ff_dec_hash,ff_lit(p));++ff_dec_count;}
 if(k=="enqueue"){ff_hash(ff_enq_hash,ff_lit(p));++ff_enq_count;}
 if(!ff_enabled)return;
 if(k=="frontier"){++ff_step;ff_before_q=qhead;ff_before_size=trail.size();ff_processed=trail[qhead];}
 if(k=="conflict_detected")++ff_conflict;
 std::ostringstream o;o<<"{\"event\":"<<ff_ordinal++<<",\"type\":\""<<k<<"\",\"step\":"<<ff_step<<",\"analysis_id\":"<<ff_conflict<<",\"conflicts\":"<<conflicts<<",\"decisions\":"<<decisions<<",\"propagations\":"<<propagations<<",\"analysis_ops\":"<<sf_analysis<<",\"decision_level\":"<<decisionLevel();
 if(k=="frontier"||k=="step_end"||k=="conflict_detected"||k=="checkpoint"||k=="backtrack"||k=="analysis_backtrack_complete"){o<<',';ff_snapshot(o,k=="checkpoint");}
 if(k=="frontier")o<<",\"native_next_literal\":"<<ff_lit(ff_processed)<<",\"qhead_before\":"<<qhead;
 if(k=="step_end"){o<<",\"processed_literal\":"<<ff_lit(ff_processed)<<",\"native_next_literal\":"<<ff_lit(ff_processed)<<",\"qhead_before\":"<<ff_before_q<<",\"qhead_after\":"<<qhead<<",\"newly_enqueued\":[";for(int i=ff_before_size;i<trail.size();i++)o<<(i>ff_before_size?",":"")<<ff_lit(trail[i]);o<<"],"<<"\"conflict_clause\":"<<ff_clause(cr);}
 if(p!=lit_Undef)o<<",\"literal\":"<<ff_lit(p)<<",\"var\":"<<var(p)+1;
 if(k=="enqueue"){std::string c=ff_clause(cr);o<<",\"reason\":"<<c<<",\"reason_id\":\""<<(cr==CRef_Undef?(decisionLevel()==0?"ROOT":"DECISION"):ff_sha(c))<<"\",\"trail_position\":"<<trail.size()<<",\"qhead\":"<<qhead;}
 if(k=="conflict_detected"||k=="analysis_begin"||k=="analysis_step")o<<",\"clause\":"<<ff_clause(cr);
 if(k=="analysis_step"){o<<",\"path_count\":"<<a;}
 if(k=="first_uip")o<<",\"first_uip_trail_literal\":"<<ff_lit(p)<<",\"asserting_literal\":"<<ff_lit(~p)<<",\"trail_position\":"<<a<<",\"path_count\":"<<b;
 if(ls){std::vector<int> c;for(int i=0;i<ls->size();i++)c.push_back(ff_lit((*ls)[i]));o<<",\"native_literals\":";ff_array(o,c);std::sort(c.begin(),c.end());o<<",\"canonical_literals\":";ff_array(o,c);o<<",\"length\":"<<ls->size()<<",\"asserting_literal\":"<<ff_lit((*ls)[0])<<",\"backtrack_level\":"<<a<<",\"lbd\":"<<b;}
 if(k=="backtrack"||k=="analysis_backtrack_complete"||k=="backtrack_begin")o<<",\"target_level\":"<<a;
 o<<"}\n";std::string line=o.str();if(gzwrite(ff_file,line.data(),line.size())!=(int)line.size())throw std::runtime_error("TRACE_WRITE");
}
