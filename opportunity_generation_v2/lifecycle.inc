enum class ObserverPhase { WAITING_FOR_CHECKPOINT, CAPTURE_ONCE, OBSERVING_FULL_RUN, TERMINATED };
static ObserverPhase ov_phase=ObserverPhase::WAITING_FOR_CHECKPOINT;
static unsigned ov_capture=0,ov_freeze=0,ov_arm=0,ov_finalize=0;
static HU ov_p=0,ov_c=0,ov_i=0;
static FILE* ov_raw=nullptr;
struct FrozenOpportunity {HU id; int literal; std::vector<int> clause; bool found=false; std::string timing;};
static std::vector<FrozenOpportunity> ov_actions;
static bool ov_on(){const char*v=getenv("OPPORTUNITY_TELEMETRY");return !v||std::string(v)!="OFF";}
static std::string ov_bucket(HU p){return p==1?"BUCKET_1":p>=2&&p<=4?"BUCKET_2_4":p>=5&&p<=16?"BUCKET_5_16":p>16?"BUCKET_GT16":"UNCLASSIFIED_ZERO_DELAY";}
static void ov_event(const char* kind,const std::string& value){if(ov_raw)fprintf(ov_raw,"{\"i\":%llu,\"kind\":\"%s\",\"value\":%s}\n",ov_i++,kind,value.c_str());}
static void ov_enqueue(int literal,HU rid,std::vector<int> reason){
 if(ov_phase!=ObserverPhase::OBSERVING_FULL_RUN||!ov_on())return;
 std::sort(reason.begin(),reason.end());std::ostringstream v;v<<"{\"literal\":"<<literal<<",\"reason_id\":"<<rid<<",\"reason\":";array(v,reason);v<<"}";
 HU event=ov_i;ov_event("enqueue",v.str());
 for(auto&a:ov_actions)if(!a.found&&a.literal==literal){a.found=true;std::ostringstream t;t<<"{\"naturally_enqueued\":true,\"event\":"<<event<<",\"dequeue_delay\":"<<ov_p<<",\"conflict_delay\":"<<ov_c<<",\"native_reason_id\":"<<rid<<",\"native_reason\":";array(t,reason);t<<",\"same_source_clause\":"<<(rid==a.id&&reason==a.clause?"true":"false")<<",\"before_first_conflict\":"<<(ov_c==0?"true":"false")<<",\"bucket\":\""<<ov_bucket(ov_p)<<"\"}";a.timing=t.str();}
}
void opportunity_finish(){
 if(ov_phase==ObserverPhase::TERMINATED)throw std::runtime_error("DOUBLE_FINALIZE");
 bool captured=ov_phase==ObserverPhase::OBSERVING_FULL_RUN;
 ov_phase=ObserverPhase::TERMINATED;
 if(captured){++ov_finalize;if(ov_raw){fflush(ov_raw);fclose(ov_raw);ov_raw=nullptr;}
 std::ostringstream o;o<<"[";for(size_t i=0;i<ov_actions.size();i++){if(i)o<<",";auto&a=ov_actions[i];o<<"{\"id\":"<<a.id<<",\"literal\":"<<a.literal<<",\"timing\":"<<(a.found?a.timing:"{\"naturally_enqueued\":false,\"status\":\"NEVER_ENQUEUED\"}")<<"}";}o<<"]";if(ov_on())write(output_dir+"/timing.json",o.str());}
 std::ostringstream l;l<<"{\"phase\":\"TERMINATED\",\"checkpoint_capture_count\":"<<ov_capture<<",\"inventory_freeze_count\":"<<ov_freeze<<",\"observer_arm_count\":"<<ov_arm<<",\"observer_finalize_count\":"<<ov_finalize<<"}";write(output_dir+"/lifecycle.json",l.str());
}
