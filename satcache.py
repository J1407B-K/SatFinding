"""Small proof-carrying semantic SAT cache. No third-party dependencies."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import permutations, product
import json
from math import sqrt
from pathlib import Path

Clause = tuple[int, ...]
CNF = tuple[Clause, ...]


def normalize(clauses) -> CNF:
    result = set()
    for clause in clauses:
        clause = tuple(clause)
        if any(type(x) is not int or x == 0 for x in clause):
            raise ValueError("Literals must be nonzero integers")
        result.add(tuple(sorted(set(clause))))
    return tuple(sorted(result))


def variables(formula: CNF) -> list[int]:
    return sorted({abs(x) for c in formula for x in c})


def satisfied(formula: CNF, assignment: dict[int, bool]) -> bool:
    return all(v in assignment and type(assignment[v]) is bool
               for v in variables(formula)) and all(
        any(assignment[abs(x)] == (x > 0) for x in c) for c in formula)


def residual(formula: CNF, assumptions: dict[int, bool]) -> CNF:
    if any(type(v) is not int or v <= 0 or type(b) is not bool
           for v, b in assumptions.items()):
        raise ValueError("Invalid assumptions")
    return normalize([
        [x for x in c if abs(x) not in assumptions]
        for c in formula
        if not any(abs(x) in assumptions and assumptions[abs(x)] == (x > 0)
                   for x in c)
    ])


@dataclass
class Step:
    left: int
    right: int
    pivot: int
    clause: Clause


@dataclass
class Certificate:
    kind: str
    assignment: dict[int, bool] | None = None
    premises: CNF = ()
    steps: tuple[Step, ...] = ()


def check(formula: CNF, cert: Certificate) -> bool:
    """Trusted acceptance boundary; checks the CURRENT residual, never similarity."""
    try:
        if not valid_cnf(formula) or type(cert) is not Certificate:
            return False
        if cert.kind == "SAT":
            if type(cert.assignment) is not dict or any(
                type(v) is not int or v <= 0 or type(b) is not bool
                for v, b in cert.assignment.items()
            ):
                return False
            return satisfied(formula, cert.assignment or {})
        if cert.kind != "UNSAT":
            return False
        if not valid_cnf(cert.premises) or type(cert.steps) is not tuple:
            return False
        available = set(formula)
        if any(c not in available for c in cert.premises):
            return False
        derived = list(cert.premises)
        for step in cert.steps:
            if (type(step) is not Step or not valid_clause(step.clause)
                    or type(step.left) is not int or type(step.right) is not int
                    or not 0 <= step.left < len(derived)
                    or not 0 <= step.right < len(derived)
                    or type(step.pivot) is not int or step.pivot == 0):
                return False
            a, b = set(derived[step.left]), set(derived[step.right])
            if step.pivot not in a or -step.pivot not in b:
                return False
            expected = tuple(sorted((a - {step.pivot}) | (b - {-step.pivot})))
            if step.clause != expected:
                return False
            derived.append(step.clause)
        return () in derived
    except (TypeError, ValueError, KeyError, AttributeError):
        return False


def valid_clause(clause) -> bool:
    return (type(clause) is tuple
            and all(type(x) is int and x != 0 for x in clause)
            and all(a < b for a, b in zip(clause, clause[1:])))


def valid_cnf(formula) -> bool:
    # Proof premises are ordered; do not reorder/deduplicate proof indices.
    return type(formula) is tuple and all(valid_clause(c) for c in formula)


def solve(formula: CNF, max_assignments=65536, max_resolution_attempts=100000):
    """Reference producer, intentionally bounded and suited only to small CNFs."""
    vs = variables(formula)
    for count, bits in enumerate(product((False, True), repeat=len(vs))):
        if count >= max_assignments:
            return None
        assignment = dict(zip(vs, bits))
        if satisfied(formula, assignment):
            return Certificate("SAT", assignment=assignment)
    derived, seen, steps = list(formula), set(formula), []
    if () in seen:
        return Certificate("UNSAT", premises=formula)
    right, attempts = 0, 0
    while right < len(derived):
        for left in range(right):
            for pivot in derived[left]:
                attempts += 1
                if attempts > max_resolution_attempts:
                    return None
                if -pivot not in derived[right]:
                    continue
                c = tuple(sorted((set(derived[left]) - {pivot}) |
                                 (set(derived[right]) - {-pivot})))
                if c in seen or any(-x in c for x in c):
                    continue
                steps.append(Step(left, right, pivot, c))
                derived.append(c)
                seen.add(c)
                if not c:
                    return Certificate("UNSAT", premises=formula, steps=tuple(steps))
        right += 1
    return None


def embedding(formula: CNF) -> Counter:
    """Permutation/sign-invariant structural baseline, NOT a learned embedding."""
    features = Counter({"clauses": len(formula), "variables": len(variables(formula))})
    degree = Counter(abs(x) for c in formula for x in c)
    for c in formula:
        features[f"width:{len(c)}"] += 1
    for d in degree.values():
        features[f"degree:{d}"] += 1
    return features


def similarity(a: Counter, b: Counter) -> float:
    denom = sqrt(sum(x*x for x in a.values()) * sum(x*x for x in b.values()))
    return sum(x*b[k] for k, x in a.items()) / denom if denom else 0.0


def mappings(source: CNF, target: CNF, budget: int):
    """Bounded injective variable maps, including independent polarity flips."""
    src, dst = variables(source), variables(target)
    count = 0
    for selected in permutations(dst, len(src)):
        for signs in product((1, -1), repeat=len(src)):
            if count >= budget:
                return
            count += 1
            yield {v: w*s for v, w, s in zip(src, selected, signs)}


def transfer(cert: Certificate, mapping: dict[int, int]) -> Certificate:
    def lit(x):
        return mapping[abs(x)] * (1 if x > 0 else -1)
    def clause(c):
        return tuple(sorted(lit(x) for x in c))
    if cert.kind == "SAT":
        return Certificate("SAT", assignment={abs(mapping[v]): b if mapping[v] > 0 else not b
                           for v, b in (cert.assignment or {}).items()})
    return Certificate(cert.kind, premises=tuple(clause(c) for c in cert.premises),
                       steps=tuple(Step(s.left, s.right, lit(s.pivot), clause(s.clause))
                                   for s in cert.steps))


class Cache:
    def __init__(self):
        self.entries: list[tuple[CNF, Certificate]] = []

    def add(self, formula: CNF, cert: Certificate):
        if not check(formula, cert):
            raise ValueError("Certificate rejected")
        self.entries.append((formula, cert))

    def lookup(self, formula: CNF, top_k=8, mapping_budget=256):
        query = embedding(formula)
        ranked = sorted(self.entries,
                        key=lambda e: similarity(query, embedding(e[0])), reverse=True)
        for source, cert in ranked[:top_k]:
            for mapping in mappings(source, formula, mapping_budget):
                try:
                    candidate = transfer(cert, mapping)
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
                if check(formula, candidate):
                    return candidate
        return None

    def save(self, path):
        Path(path).write_text(json.dumps({"version": 1, "entries": [
            {"formula": f, "certificate": asdict(c)} for f, c in self.entries
        ]}, indent=2) + "\n")

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        if data["version"] != 1:
            raise ValueError("Unsupported cache version")
        cache = cls()
        for entry in data["entries"]:
            raw = entry["certificate"]
            cert = Certificate(raw["kind"],
                None if raw["assignment"] is None else
                {int(k): v for k, v in raw["assignment"].items()},
                tuple(tuple(c) for c in raw["premises"]),
                tuple(Step(s["left"], s["right"], s["pivot"], tuple(s["clause"]))
                      for s in raw["steps"]))
            cache.add(normalize(entry["formula"]), cert)
        return cache


def run(formula: CNF, cache: Cache, assumptions=None):
    """Status is scoped to F|assumptions. Branch UNSAT is never global UNSAT."""
    formula = normalize(formula)
    scope = dict(assumptions or {})
    current = residual(formula, scope)
    cert = cache.lookup(current)
    hit = cert is not None
    if cert is None:
        cert = solve(current)
    if cert is None:
        return {"status": "UNKNOWN", "assumptions": scope, "cache_hit": False}
    if not check(current, cert):
        raise ValueError("Producer returned invalid certificate")
    if not hit:
        cache.add(current, cert)
    result = {"status": cert.kind, "assumptions": scope, "cache_hit": hit}
    if cert.kind == "SAT":
        assignment = {v: False for v in variables(formula)}
        assignment.update(cert.assignment or {})
        assignment.update(scope)
        if not satisfied(formula, assignment):
            raise ValueError("Invalid reconstructed model")
        result["assignment"] = assignment
    return result
