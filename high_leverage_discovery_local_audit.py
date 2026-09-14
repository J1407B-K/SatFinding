"""Local-only trace audit of the existing 84 frozen events. No new actions."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import high_leverage_discovery as original
from build_native_cdcl import replace_once
OUT=Path('results/high_leverage_discovery_local_audit').resolve()
OLD=Path('results/high_leverage_discovery').resolve()
BUILD=Path('/private/tmp/satfinding-high-leverage-local-audit')
dump=original.dump;sha=original.sha;chash=original.chash

def build():
 prior=Path('/private/tmp/satfinding-high-leverage-discovery');root=BUILD/'glucose-3.0'
 shutil.copytree(prior/'glucose-3.0',root,dirs_exist_ok=True)
 h=root/'core/Solver.h';s=h.read_text();s=replace_once(s,'    void hc_boundary();','    void hc_boundary();\n    void hd_dequeue(Lit);\n    void hd_conflict(CRef);\n    void hd_learned(const vec<Lit>&);\n    void hd_decision(Lit);');h.write_text(s)
 cc=root/'core/Solver.cc';s=cc.read_text().replace(str(Path('high_leverage_discovery.inc').resolve()),str(Path('high_leverage_discovery_local_audit.inc').resolve()))
 anchor="        Lit            p   = trail[qhead++];     // 'p' is enqueued fact to propagate."
 s=replace_once(s,anchor,anchor+'\n        hd_dequeue(p);')
 anchor='\t  conflicts++; conflictC++;conflictsRestarts++;';s=replace_once(s,anchor,anchor+'\n          hd_conflict(confl);')
 anchor='            analyze(confl, learnt_clause, selectors,backtrack_level,nblevels,szWoutSelectors);';s=replace_once(s,anchor,anchor+'\n            hd_learned(learnt_clause);')
 anchor="            // Increase decision level and enqueue 'next'";s=replace_once(s,anchor,'            hd_decision(next);\n'+anchor);cc.write_text(s)
 shutil.copy2(prior/'driver.cc',BUILD/'driver.cc')
 cmd=['c++','-O3','-DNDEBUG','-std=c++11','-Wno-deprecated','-I'+str(root),str(BUILD/'driver.cc'),str(cc),str(root/'utils/Options.cc'),str(root/'utils/System.cc'),'-lz','-o',str(BUILD/'run')]
 r=subprocess.run(cmd,capture_output=True,text=True);(OUT/'build.log').write_text(r.stdout+r.stderr);r.check_returncode()
 dump(OUT/'build.json',{'command':cmd,'binary_sha256':sha(BUILD/'run'),'prior_build':json.loads((OLD/'build.json').read_text()),'sources':{str(p):sha(p) for p in [Path(__file__),Path('high_leverage_discovery_local_audit.inc'),cc,h,BUILD/'driver.cc']}})

def execute(t,bucket):
 r=original.run(t,bucket);old=json.loads((OLD/t/(r['route']+'.result.json')).read_text())
 r['final_counters_match_original']=all(r['stats'].get(k)==v for k,v in old['stats'].items() if k!='seconds')
 r['same_proof_hash_as_original']=r['proof_sha256']==old['proof_sha256']
 for e in r['events']:
  if e['event']=='LOCAL_TRACE':
   e['conflict_clause_canonical_sha256']=chash(e['conflict_clause_literals']) if e['conflict_index'] else None
   e['learned_clause_canonical_sha256']=chash(e['learned_clause_literals']) if e['learned_seen'] else None
 dump(OUT/t/(r['route']+'.result.json'),r)
 assert r['final_counters_match_original'] and r['proof_validation']=='VERIFIED' and not r['failure'],(t,bucket,'COUNTER_OR_PROOF_FAILURE')
 return r

def main():
 OUT.mkdir(exist_ok=False)
 original.OUT=OUT;original.BUILD=BUILD
 prior=json.loads((OLD/'discovery_summary.json').read_text())
 dump(OUT/'audit_protocol.json',{'source_summary_sha256':sha(OLD/'discovery_summary.json'),'source_sampling_protocol_sha256':sha(OLD/'protocol.json'),'sample_count':84,'selection':'Exactly the existing84 samples. No additional or replacement events.','window':'Begin immediately before original early enqueue (baseline at same observed event); record dequeues until first subsequent conflict detection, its conflict clause and analyzed learned clause; retain only first branch decision literal after that conflict, across extra conflicts/restarts if necessary. No intermediate trace after first conflict.','propagation_diverged':'Ordered dequeue literal sequence differs. This measures processing order, not merely earlier enqueue call timing.','conflict_diverged':'Stable clause ID OR canonical literal hash differs.','learned_diverged':'Canonical learned clause hash differs (or analysis availability differs).','decision_diverged':'First actual decision literal after first conflict differs; termination is an explicit null.','classification':'Deepest true flag in propagation,conflict,learned,decision order; retain all flags.','gate':'All non-time final counters must match corresponding old route; independent drat-trim must verify before comparing traces.'})
 build();rows=[]
 for t in ['T8','T10','T13']:
  d=OUT/t;d.mkdir();shutil.copy2(OLD/t/'input.cnf',d/'input.cnf');b=execute(t,0)
  bt={e['bucket']:e for e in b['events'] if e['event']=='LOCAL_TRACE'}
  bo={e['bucket']:e for e in b['events'] if e['event']=='OPPORTUNITY'}
  for oldrow in prior['targets'][t]['rows']:
   i=oldrow['sample_conflict_bucket'];r=execute(t,i)
   events=[e for e in r['events'] if e['event']=='LOCAL_TRACE'];assert len(events)==1
   y=events[0];x=bt[i];o=next(e for e in r['events'] if e['event']=='OPPORTUNITY');assert o==bo[i]
   frozen=next(e for e in json.loads((OLD/t/'BASELINE.result.json').read_text())['events'] if e['event']=='OPPORTUNITY' and e['bucket']==i);assert o==frozen
   assert next(e for e in r['events'] if e['event']=='TOTAL')['interventions']==1
   assert x['conflict_index'] and y['conflict_index']
   flags={'propagation_diverged':x['dequeue_literals']!=y['dequeue_literals'],'conflict_diverged':any(x[k]!=y[k] for k in ['conflict_clause_id','conflict_clause_canonical_sha256']),'learned_diverged':any(x[k]!=y[k] for k in ['learned_seen','learned_clause_canonical_sha256']),'decision_diverged':x['next_decision_literal']!=y['next_decision_literal']}
   cls='L0_NO_LOCAL_DIVERGENCE'
   for key,name in zip(flags,['L1_PROPAGATION_ONLY','L2_CONFLICT_DIVERGED','L3_LEARNED_DIVERGED','L4_DECISION_DIVERGED']):
    if flags[key]:cls=name
   row={'target':t,'bucket':i,**flags,'classification':cls,'baseline_ops':oldrow['baseline_ops'],'intervention_ops':oldrow['intervention_ops'],'relative_ops_delta_percent':oldrow['relative_ops_delta_percent'],'baseline_dequeue_count':len(x['dequeue_literals']),'intervention_dequeue_count':len(y['dequeue_literals']),'baseline_conflict_id':x['conflict_clause_id'],'intervention_conflict_id':y['conflict_clause_id'],'baseline_conflict_hash':x['conflict_clause_canonical_sha256'],'intervention_conflict_hash':y['conflict_clause_canonical_sha256'],'baseline_learned_hash':x['learned_clause_canonical_sha256'],'intervention_learned_hash':y['learned_clause_canonical_sha256'],'baseline_next_decision':x['next_decision_literal'],'intervention_next_decision':y['next_decision_literal'],'final_counters_match_original':True,'proof_validation':'VERIFIED'}
   rows.append(row);dump(d/f'C{i}.local_comparison.json',{'row':row,'baseline':x,'intervention':y})
  dump(OUT/'partial_rows.json',rows)
 assert len(rows)==84
 with (OUT/'all_84_local_divergence.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 def stats(rr):
  div=[r for r in rr if any(r[k] for k in flags)]
  from collections import Counter
  return {'count':len(rr),'flag_counts':{k:sum(r[k] for r in rr) for k in flags},'classification_counts':dict(Counter(r['classification'] for r in rr)),'local_diverged_count':len(div),'local_diverged_ops_delta_percent_distribution':dict(Counter(str(r['relative_ops_delta_percent']) for r in div)),'zero_final_ops_local_diverged_count':sum(r['relative_ops_delta_percent']==0 for r in div)}
 dump(OUT/'summary.json',{'aggregate':stats(rows),'per_target':{t:stats([r for r in rows if r['target']==t]) for t in ['T8','T10','T13']},'verified_proof_count':87,'all_final_counters_match_original':True,'rows':rows})

if __name__=='__main__':main()
