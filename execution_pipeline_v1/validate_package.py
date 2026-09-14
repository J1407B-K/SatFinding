import json,sys
from pathlib import Path
p=Path(sys.argv[1]);m=json.load(open(p/'manifest.json')); req=['input/input.cnf','checkpoint/state.json','action/action.json','baseline/summary.json','treatment/summary.json']
assert all((p/x).exists() for x in req)
assert m.get('package_complete') is True
for d in ('baseline','action'): assert m['routes'][d].get('VERIFIED') is True
print('PACKAGE_COMPLETE=true')
