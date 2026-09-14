"""Bounded follow-up at the first L2 activation in the fixed nonadditive pair."""
import json
from pathlib import Path
import subprocess
from gold_mechanism_build import BUILD,build
from gold_mechanism_run import OUT,run_config
from unseen_selector import dump
from evaluation_oracle_run import sha
from build_native_cdcl import replace_once

def main():
    assert not (OUT/'window_runs.json').exists()
    # Chosen because existing pair's first L2 reason enqueue is at completed
    # conflict198; no subset/score selection or search over windows.
    dump(OUT/'window_protocol.json',dict(conflict_window=[196,206],
        rationale='First L2 successful enqueue in already frozen L1+L2 occurs after conflict198.',
        configs=['L1','L1_L2'],counterfactual='Same configurations, bounded observation only',
        no_new_subset=True,source_sha256=sha(__file__)))
    meta=build();source=BUILD/'glucose-3.0/core/Solver.cc';s=source.read_text()
    anchor='          gm_conflict(ca[confl],decisionLevel(),conflicts,propagations,decisions,sf_analysis,trail.size());'
    extra=r'''
          if(conflicts>=196 && conflicts<=206) {
            fprintf(gm_out,"{\"t\":\"S\",\"c\":%llu,\"nodes\":[",(unsigned long long)conflicts);
            for(int z=0;z<trail.size();++z) {
              Lit x=trail[z]; CRef rr=reason(var(x)); int id=rr==CRef_Undef?-1:gm_clause(ca[rr]);
              fprintf(gm_out,"%s{\"e\":%llu,\"lit\":%d,\"dl\":%d,\"r\":%d,\"deps\":",z?",":"",gm_last[var(x)],gm_lit(x),level(var(x)),id);
              std::vector<unsigned long long> deps;
              if(rr!=CRef_Undef)for(int j=0;j<ca[rr].size();++j)if(var(ca[rr][j])!=var(x))deps.push_back(gm_last[var(ca[rr][j])]);
              gm_ids(deps);fprintf(gm_out,"}");
            }
            fprintf(gm_out,"]}\n");
          }
'''
    source.write_text(replace_once(s,anchor,anchor+extra))
    subprocess.run(meta['command'],capture_output=True,check=True)
    dump(OUT/'window_build.json',dict(base_build=meta,window_source_sha256=sha(source),binary_sha256=sha(BUILD/'trace')))
    inp=json.loads((OUT/'inputs.json').read_text());gold={int(k):v for k,v in inp['gold'].items()}
    runs=[]
    for name,ids in [('WINDOW_L1',[24458]),('WINDOW_L1_L2',[24458,30149])]:
        runs.append(run_config(name,ids,inp['cnf'],inp['templates'],gold,BUILD/'mapping.txt'))
    dump(OUT/'window_runs.json',runs)

if __name__=='__main__':main()
