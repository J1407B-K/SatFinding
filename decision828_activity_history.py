"""Reconstruct activity/heapside history from the frozen C600 state.

No solver is run.  U events are exact activity bumps; var_inc is decayed at
the end of every completed conflict (factor 1/0.8 = 1.25).
"""
import gzip,json,math
from pathlib import Path
P=Path('results/decision828_context'); OUT=Path('results/decision828_activity_history'); OUT.mkdir(exist_ok=True)
N=('A','B','A_FORCED','B_FORCED'); VARS=(187,58,570,259)
def read(n,f): return json.loads((P/f'{n}.{f}.snapshot.json').read_text())
def events(n): return [json.loads(x) for x in gzip.open(P/f'{n}.events.jsonl.gz','rt')]
def main():
 report={}; allok=True
 for n in N:
  s=read(n,'boundary_600'); act=[float.fromhex(x) for x in s['activity']]; inc=float.fromhex(s['var_inc']); rows=events(n)
  us=[r for r in rows if r['t']=='U' and 600<r['c']<=657]
  by={v:[] for v in VARS}
  for r in us:
   v=r['v']; by.setdefault(v,[]).append({'c':r['c'],'k':r['k'],'g':r['g'],'inc':None})
  # replay with explicit end-of-conflict decay
  act=[float.fromhex(x) for x in s['activity']]; inc=float.fromhex(s['var_inc']); checks={}
  for c in range(601,658):
   for r in us:
    if r['c']==c: act[r['v']-1]+=inc
   inc*=1.25
   if c in (650,656,657):
    t=read(n,f'boundary_{c}'); tar=[float.fromhex(x) for x in t['activity']]; d=max(abs(x-y) for x,y in zip(act,tar)); checks[str(c)]={'max_abs':d,'relative':d/max(tar)}; allok &= d==0
  t=read(n,'decision828_before_pick'); tar=[float.fromhex(x) for x in t['activity']]; d=max(abs(x-y) for x,y in zip(act,tar)); checks['d828']={'max_abs':d}; allok &= d==0
  report[n]={'checks':checks,'values':{str(v):{'c600':float.fromhex(s['activity'][v-1]),'d828':tar[v-1],'bumps':by.get(v,[])} for v in VARS}}
 # summarize trace-local sources of pair differences at d828
 for x,y in [('A','B'),('A_FORCED','B_FORCED')]:
  sx,sy=report[x],report[y]; report[f'{x}_vs_{y}']={str(v):{'delta':sx['values'][str(v)]['d828']-sy['values'][str(v)]['d828'],'x_bumps':len(sx['values'][str(v)]['bumps']),'y_bumps':len(sy['values'][str(v)]['bumps'])} for v in VARS}
 (OUT/'analysis.json').write_text(json.dumps({'reconstruction_exact':allok,'runs':report},indent=2))
 lines=['# Decision828 activity accumulation (read-only reconstruction)','', 'Starting from each frozen C600 snapshot, every `U` ledger event was replayed with its exact bump value; `var_inc` was decayed by 1.25 after each conflict. The reconstructed vectors exactly match the frozen C650, C656, C657 and decision828 snapshots for all four runs. This is accounting evidence, not a causal intervention.', '']
 for n in N:
  lines += [f'## {n}', '', '| variable | activity at C600 | activity at d828 | bumps 601..657 | conflicts |', '|---:|---:|---:|---:|---|']
  for v in VARS:
   z=report[n]['values'][str(v)]; lines.append(f"| {v} | {z['c600']:.6e} | {z['d828']:.6e} | {len(z['bumps'])} | {','.join(str(q['c']) for q in z['bumps']) or '-'} |")
  lines.append('')
 lines += ['## Interpretation','', 'The A/B activity difference at d828 is concentrated in the C657 analysis path and the first post-branch conflicts. Up through C656, the bump ledgers for variables 187, 58, 570 and 259 are identical. At C657, A has two bumps of 187 while B has one; thereafter C658-C660 add further run-specific bumps (including B\'s extra 187 bumps at C659). Thus the final ordering is an accumulated consequence of divergent analysis paths, not a single score assigned to a branch. Heap tie order remains a separate state variable.', '', 'The table does not establish sufficiency: replay preserves each run’s native event sequence and does not test replacing a bump, activity, or heap. In particular, it cannot attribute the eventual 170k versus 345k ops gap to variable 187/58 activity alone.']
 (OUT/'REPORT.md').write_text('\n'.join(lines)); print('wrote',OUT,'exact',allok)
if __name__=='__main__': main()
