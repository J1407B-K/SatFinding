#include <fstream>
#include <string>
#include <cstdlib>
bool fr_enabled=false, fr_triggered=false, fr_verified=false; unsigned long long fr_expected_conf=0,fr_expected_dec=0,fr_expected_state=0; int fr_expected_level=0,fr_expected_trail=0,fr_expected_qhead=0; std::string fr_fail;
void fr_config(unsigned long long c,unsigned long long d,unsigned long long h,int l,int t,int q){fr_enabled=true;fr_expected_conf=c;fr_expected_dec=d;fr_expected_state=h;fr_expected_level=l;fr_expected_trail=t;fr_expected_qhead=q;}
void fr_checkpoint(unsigned long long c,unsigned long long d,unsigned long long h,int l,int t,int q){if(!fr_enabled||fr_triggered)return; if(c<fr_expected_conf)return; if(c>fr_expected_conf){fr_fail="REPLAY_CHECKPOINT_MISSED";fr_enabled=false;return;} fr_triggered=true; if(d!=fr_expected_dec||h!=fr_expected_state||l!=fr_expected_level||t!=fr_expected_trail||q!=fr_expected_qhead){fr_fail="REPLAY_STATE_MISMATCH";return;} fr_verified=true;}
