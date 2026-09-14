import sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from counterfactuals import *
def main():
 # Final source/binary binding: all reported routes use these three retained builds.
 build()
 for t in ['T10','T8']:build_historical(t)
 for tag,rank,var in [('BASELINE',0,27),('HIGH',2,27),('CONTROL_BASELINE',0,430),('CONTROL',1,430)]:run(tag,rank,var=var)
 for target,ranks in [('T10',[1,2,3,5]),('T8',[1,4])]:
  for rank in ranks:run_historical(target,rank)
 plans=load(OUT/'counterfactual_plan.json')
 for p in plans:
  if p['first_displaced_branch']:
   ordinal,b,h=p['first_displaced_branch']
   for mode in ['restore','suppress']:run_historical(p['target'],p['rank'],mode,ordinal,b['literal'],'_'+mode)
 run('HIGH_RESTORE1',2,'restore',8,27)
 run('SUPPRESS_BRANCH1',0,'suppress',8,27)
if __name__=='__main__':main()
