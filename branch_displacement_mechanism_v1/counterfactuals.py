import sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from historical_run import *
def events(path):return list(map(json.loads,Path(path).read_text().splitlines()))
def decisions(path):return [e for e in events(path) if e['type']=='decision'][:8]
def main():
 plans=[]
 cases=[('T10',1),('T10',2),('T10',5),('T8',4)]
 for target,rank in cases:
  sid='HIST_T10_FIXED' if target=='T10' else 'HIST_T8_S5'
  d=OUT/'historical_runs'/f'{sid}_R{rank}'
  b=decisions(d/'BASELINE/events.jsonl');h=decisions(d/f'ACTION_{rank}/events.jsonl')
  pair=next(((i+1,x,y) for i,(x,y) in enumerate(zip(b,h)) if x['literal']!=y['literal']),None)
  plans.append({'target':target,'rank':rank,'state_id':sid,'first_displaced_branch':pair,'interpretation':'downstream branch mediation test; distinct from direct displacement of the early implied variable'})
 dump(OUT/'counterfactual_plan.json',plans)
 for target in ['T10','T8']:build_historical(target)
 for p in plans:
  if p['first_displaced_branch']:
   ordinal,b,h=p['first_displaced_branch']
   for mode in ['restore','suppress']:run_historical(p['target'],p['rank'],mode,ordinal,b['literal'],'_'+mode)
 run('HIGH_RESTORE1',2,'restore',8,27)
 run('SUPPRESS_BRANCH1',0,'suppress',8,27)
if __name__=='__main__':main()
