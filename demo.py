import json
from satcache import Cache, normalize, run

cache = Cache()
examples = [
    ("learn SAT", [[1], [-1, 2]]),
    ("transfer SAT", [[-7], [7, 9]]),
    ("learn UNSAT", [[1], [-1]]),
    ("transfer UNSAT into larger formula", [[7], [-7], [8, 9]]),
]
for label, clauses in examples:
    print(label, json.dumps(run(normalize(clauses), cache), sort_keys=True))
