import time,json,concurrent.futures
from pathlib import Path
import analyze_trajectory_audit as a

def work(c):
 d=a.R/'routes'/c['case']/f'rank{c["rank"]}'/'comparison.json'
 return json.loads(d.read_text()) if d.exists() else a.compare(c)
if __name__=='__main__':
 pending=list(a.P['cohort']);futures={};done=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
  while pending or futures:
   for c in pending[:]:
    d=a.R/'routes'/c['case']/f'rank{c["rank"]}'
    if len(futures)<3 and (d/'action/execution.json').exists():
     futures[pool.submit(work,c)]=c;pending.remove(c)
   for f in list(futures):
    if f.done():
     c=futures.pop(f);r=f.result();done.append(r);print(len(done),r['case'],r['rank'],r['persistence_class'],r['delta_percent'],flush=True)
   if pending or futures:time.sleep(1)
 rows=sorted(done,key=lambda r:next(i for i,c in enumerate(a.P['cohort']) if c['case']==r['case'] and c['rank']==r['rank']))
 (a.R/'ROUTE_COMPARISONS.json').write_text(json.dumps(rows,indent=2));a.summary(rows)
 print('ANALYSIS COMPLETE',flush=True)
