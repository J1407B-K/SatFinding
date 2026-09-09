"""Checked extended-resolution modules with capture-free instantiation.

Only finite data is accepted; no executable macros or implicit proof expansion.
All definitions are y <-> (left AND right), where inputs are signed literals.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from itertools import permutations, product
import json

from satcache import (CNF, Clause, Step, embedding, normalize, residual,
                      similarity, valid_clause, valid_cnf, variables)


@dataclass(frozen=True)
class ExtensionDefinition:
    variable: int
    left: int
    right: int

    def clauses(self) -> CNF:
        y, a, b = self.variable, self.left, self.right
        # Preserve the three slots, even for degenerate gates; proof indices
        # address this sequence, not a globally normalized clause set.
        return tuple(tuple(sorted(set(c))) for c in ((-y, a), (-y, b), (y, -a, -b)))


@dataclass(frozen=True)
class ProofModule:
    assumptions: Clause
    extension_definitions: tuple[ExtensionDefinition, ...]
    premises: CNF
    conclusion: Clause
    derivation: tuple[Step, ...]


@dataclass(frozen=True)
class CheckedConclusion:
    assumptions: Clause
    conclusion: Clause
    guarded_clause: Clause
    extension_definitions: tuple[ExtensionDefinition, ...]
    # None means the conclusion uses extension vocabulary: retain the context.
    root_clause: Clause | None

    @property
    def proves_unsat(self) -> bool:
        return self.guarded_clause == ()


@dataclass(frozen=True)
class Instantiation:
    module: ProofModule
    base_mapping: dict[int, int]
    extension_mapping: dict[int, int]


def literal(x):
    return type(x) is int and x != 0


def shape(module):
    if type(module) is not ProofModule:
        return False
    if (not valid_clause(module.assumptions) or not valid_cnf(module.premises)
            or not valid_clause(module.conclusion)
            or type(module.extension_definitions) is not tuple
            or type(module.derivation) is not tuple):
        return False
    for d in module.extension_definitions:
        if (type(d) is not ExtensionDefinition or type(d.variable) is not int
                or d.variable <= 0 or not literal(d.left) or not literal(d.right)):
            return False
    for s in module.derivation:
        if (type(s) is not Step or type(s.left) is not int or type(s.right) is not int
                or not literal(s.pivot) or not valid_clause(s.clause)):
            return False
    return True


def base_variables(module):
    if not shape(module):
        raise ValueError('Malformed module')
    used = set(variables(module.premises)) | {abs(x) for x in module.assumptions+module.conclusion}
    for d in module.extension_definitions:
        used.update((abs(d.left), abs(d.right)))
    for s in module.derivation:
        used.update(abs(x) for x in s.clause)
        used.add(abs(s.pivot))
    return used - {d.variable for d in module.extension_definitions}


class ProofContext:
    """Single-threaded proof session. Commit only by rechecking a full module.

    Clauses include definitions and globally guarded lemmas. They are an
    equisatisfiable extension of the root CNF, NOT necessarily root-language clauses.
    """
    def __init__(self, formula: CNF, reserved_variables=()):
        reserved = tuple(reserved_variables)
        if any(type(v) is not int or v <= 0 for v in reserved):
            raise ValueError('Invalid reserved variable')
        self._clauses = normalize(formula)
        self._root_variables = frozenset(set(variables(self._clauses)) | set(reserved))
        self._used = self._root_variables
        self._definitions = ()

    @property
    def clauses(self):
        return self._clauses

    @property
    def used_variables(self):
        return self._used

    @property
    def extension_definitions(self):
        return self._definitions

    def check(self, module: ProofModule) -> CheckedConclusion | None:
        if not shape(module):
            return None
        assumptions = module.assumptions
        if any(-x in assumptions or abs(x) not in self._used for x in assumptions):
            return None
        # Input premises are current facts (possibly simplified under assumptions).
        # Locally introduced extensions cannot serve as unproved input premises.
        if any(abs(x) not in self._used for c in module.premises for x in c):
            return None
        available = set(self._clauses)
        if assumptions:
            available.update(residual(self._clauses, {abs(x): x > 0 for x in assumptions}))
        if any(c not in available for c in module.premises):
            return None
        known, definition_clauses = set(self._used), []
        for d in module.extension_definitions:
            if d.variable in known or abs(d.left) not in known or abs(d.right) not in known:
                return None
            known.add(d.variable)
            definition_clauses.extend(d.clauses())
        if any(abs(x) not in known for x in module.conclusion):
            return None
        # Stable initial indexing: premises, assumption units, then gate clauses.
        derived = list(module.premises) + [(x,) for x in assumptions] + definition_clauses
        for s in module.derivation:
            if not (0 <= s.left < len(derived) and 0 <= s.right < len(derived)):
                return None
            a, b = set(derived[s.left]), set(derived[s.right])
            if s.pivot not in a or -s.pivot not in b:
                return None
            expected = tuple(sorted((a-{s.pivot}) | (b-{-s.pivot})))
            if s.clause != expected:
                return None
            derived.append(s.clause)
        if module.conclusion not in derived:
            return None
        guarded = tuple(sorted(set(module.conclusion) | {-x for x in assumptions}))
        root_clause = guarded if all(abs(x) in self._root_variables for x in guarded) else None
        return CheckedConclusion(assumptions, module.conclusion, guarded,
                                 module.extension_definitions, root_clause)

    def apply(self, module: ProofModule) -> CheckedConclusion:
        # Snapshot finite certificate data; a returned CheckedConclusion itself
        # is never accepted as evidence by this API.
        if not shape(module):
            raise ValueError('Malformed module; context unchanged')
        module = deepcopy(module)
        result = self.check(module)
        if result is None:
            raise ValueError('Module rejected; context unchanged')
        clauses = list(self._clauses)
        for d in module.extension_definitions:
            clauses.extend(d.clauses())
        clauses.append(result.guarded_clause)
        updated = normalize(clauses)
        definitions = self._definitions + module.extension_definitions
        used = self._used | {d.variable for d in module.extension_definitions}
        self._clauses, self._definitions, self._used = updated, definitions, used
        return result


def instantiate(template, mapping, context):
    """Signed injective base mapping + fresh, positive local extension names."""
    base = base_variables(template)
    if (type(mapping) is not dict or set(mapping) != base
            or any(type(k) is not int or not literal(v) for k, v in mapping.items())
            or len({abs(v) for v in mapping.values()}) != len(mapping)
            or any(abs(v) not in context.used_variables for v in mapping.values())):
        raise ValueError('Expected a total injective base mapping into the current vocabulary')
    extension_ids = [d.variable for d in template.extension_definitions]
    if len(set(extension_ids)) != len(extension_ids):
        raise ValueError('Duplicate extension variable')
    next_id = max(context.used_variables, default=0)+1
    extensions = {v: next_id+i for i, v in enumerate(extension_ids)}
    full = dict(mapping) | extensions
    def lit(x):
        return full[abs(x)]*(1 if x > 0 else -1)
    def clause(c):
        return tuple(sorted(lit(x) for x in c))
    module = ProofModule(clause(template.assumptions),
                tuple(ExtensionDefinition(extensions[d.variable], lit(d.left), lit(d.right))
                      for d in template.extension_definitions),
                tuple(clause(c) for c in template.premises), clause(template.conclusion),
                tuple(Step(s.left, s.right, lit(s.pivot), clause(s.clause)) for s in template.derivation))
    return Instantiation(module, dict(mapping), extensions)


class ProofModuleCache:
    """Small bounded structural-retrieval baseline; no efficient-mapping claim."""
    def __init__(self):
        self._modules = []

    def add(self, module):
        # Validate the lemma under its DECLARED premises, not their applicability
        # to a future query. The query context checks applicability again.
        base = base_variables(module)
        abstract = ProofContext(module.premises, reserved_variables=base)
        if abstract.check(module) is None:
            raise ValueError('Invalid proof module')
        self._modules.append(deepcopy(module))

    def lookup(self, context, top_k=8, mapping_budget=256):
        if type(top_k) is not int or type(mapping_budget) is not int or min(top_k, mapping_budget) < 0:
            raise ValueError('Nonnegative integral budgets required')
        query = embedding(context.clauses)
        ranked = sorted(self._modules, key=lambda m: similarity(query, embedding(m.premises)), reverse=True)
        for template in ranked[:top_k]:
            base = sorted(base_variables(template))
            tries = 0
            for chosen in permutations(sorted(context.used_variables), len(base)):
                if tries >= mapping_budget:
                    break
                for signs in product((1, -1), repeat=len(base)):
                    if tries >= mapping_budget:
                        break
                    tries += 1
                    mapping = {v: w*s for v, w, s in zip(base, chosen, signs)}
                    candidate = instantiate(template, mapping, context)
                    if context.check(candidate.module) is not None:
                        return candidate
        return None


def dumps(module):
    if not shape(module):
        raise ValueError('Malformed module')
    return json.dumps({'version': 1, 'module': asdict(module)}, indent=2)+'\n'


def loads(text):
    data = json.loads(text)
    if type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unsupported module version')
    raw = data['module']
    module = ProofModule(tuple(raw['assumptions']),
                 tuple(ExtensionDefinition(d['variable'], d['left'], d['right']) for d in raw['extension_definitions']),
                 tuple(tuple(c) for c in raw['premises']), tuple(raw['conclusion']),
                 tuple(Step(s['left'], s['right'], s['pivot'], tuple(s['clause'])) for s in raw['derivation']))
    if not shape(module):
        raise ValueError('Malformed module')
    return module  # Parsing is not proof verification; add/check/apply recheck it.
