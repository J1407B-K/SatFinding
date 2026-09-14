"""Projection-preserving splitting; private ground truth stays in the harness."""
from collections import Counter
import random

from derived_parity import clause
from global_xor_experiment import instance


def split(cnf, depth):
    if type(depth) is not int or depth < 0:
        raise ValueError('Invalid depth')
    current = [clause(c) for c in cnf]
    fresh = max((abs(x) for c in current for x in c), default=0)
    witness = []
    for _ in range(depth):
        following = []
        for c in current:
            fresh += 1
            left, right = clause(c+(fresh,)), clause(c+(-fresh,))
            witness.append(dict(parent=c, pivot=fresh, left=left, right=right))
            following.extend((left,right))
        current = following
    return current, witness


def check_projection(original, hidden, witness):
    try:
        active = Counter(clause(c) for c in original)
        used = {abs(x) for c in active for x in c}
        for s in witness:
            c,p,l,r = clause(s['parent']),s['pivot'],clause(s['left']),clause(s['right'])
            if type(p) is not int or p <= 0 or p in used or active[c] <= 0:
                return False
            if set(l) != set(c)|{p} or set(r) != set(c)|{-p}:
                return False
            active[c] -= 1
            active[l] += 1
            active[r] += 1
            used.add(p)
        return +active == Counter(clause(c) for c in hidden)
    except (ValueError, TypeError, KeyError):
        return False


def make(n, seed, depth, kind):
    unsat, equations, sat, assignment = instance(n, seed)
    original = unsat if kind == 'UNSAT' else sat
    if kind == 'SAT':
        equations = [(s, sum(assignment[x] for x in s)%2) for s,_ in equations]
    hidden, witness = split(original, depth)
    assert check_projection(original, hidden, witness)
    total = max(abs(x) for c in hidden for x in c)
    rng = random.Random(300000+seed+1000*depth)
    names = list(range(1,total+1))
    rng.shuffle(names)
    mapping = {i+1:v * rng.choice((-1,1)) for i,v in enumerate(names)}
    def transform(c):
        return clause(tuple(mapping[abs(x)] * (1 if x>0 else -1) for x in c))
    cnf = [transform(c) for c in hidden]
    rng.shuffle(cnf)
    eq = [(tuple(sorted(abs(mapping[x]) for x in scope)),
           rhs ^ (sum(mapping[x]<0 for x in scope)%2)) for scope,rhs in equations]
    model = {abs(mapping[x]):bool(assignment.get(x,0)) ^ (mapping[x]<0) for x in mapping}
    return cnf, eq, [transform(c) for c in original], model


def dimacs(cnf):
    nv = max((abs(x) for c in cnf for x in c), default=0)
    return (f'p cnf {nv} {len(cnf)}\n'+''.join(' '.join(map(str,c))+' 0\n' for c in cnf)).encode()
