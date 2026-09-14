"""CNF parity recognition and explicitly checked GF(2) derivation DAGs.

This is a separate algebraic proof format, not a resolution ProofModule.
Discovery sees only CNF, never a graph, charges, or an oracle certificate.
"""
from collections import defaultdict
from itertools import product


def parity_clauses(scope, rhs):
    return [tuple(-v if bit else v for v, bit in zip(scope, bits))
            for bits in product((0, 1), repeat=len(scope))
            if sum(bits) % 2 != rhs]


def extract(formula, max_width=8):
    groups = defaultdict(set)
    for clause in formula:
        if not clause or len(clause) > max_width:
            continue
        if any(type(v) is not int or v == 0 for v in clause):
            raise ValueError('Invalid literal')
        scope = tuple(sorted(abs(v) for v in clause))
        if len(set(scope)) != len(scope):
            continue
        groups[scope].add(tuple(sorted(clause)))
    equations = []
    for scope, clauses in sorted(groups.items()):
        for rhs in (0, 1):
            needed = {tuple(sorted(c)) for c in parity_clauses(scope, rhs)}
            if needed <= clauses:
                equations.append((scope, rhs))
    return equations


def discover(formula):
    equations = extract(formula)
    cert = {'equations': equations, 'steps': [], 'conclusion': None}
    basis = {}
    for i, (scope, rhs) in enumerate(equations):
        mask = sum(1 << (v-1) for v in scope)
        node = i
        while mask:
            pivot = mask.bit_length()-1
            if pivot not in basis:
                basis[pivot] = (mask, rhs, node)
                break
            other, bit, parent = basis[pivot]
            cert['steps'].append((node, parent))
            node = len(equations)+len(cert['steps'])-1
            mask ^= other
            rhs ^= bit
        if mask == 0 and rhs == 1:
            cert['conclusion'] = node
            break
    return cert


def oracle(equations):
    cert = {'equations': equations, 'steps': [], 'conclusion': 0}
    for i in range(1, len(equations)):
        cert['steps'].append((cert['conclusion'], i))
        cert['conclusion'] = len(equations)+len(cert['steps'])-1
    return cert


def check(formula, cert):
    """Revalidate each parity premise against CNF; replay every XOR step."""
    try:
        clauses = {tuple(sorted(c)) for c in formula}
        nodes = []
        for scope, rhs in cert['equations']:
            if type(rhs) is not int or rhs not in (0, 1):
                return False
            if not 1 <= len(scope) <= 8 or len(set(scope)) != len(scope):
                return False
            if any(type(v) is not int or v <= 0 for v in scope):
                return False
            # Independent premise check: each forbidden assignment must have
            # its exact blocking clause present in the input formula.
            for bits in product((0, 1), repeat=len(scope)):
                if sum(bits) % 2 == rhs:
                    continue
                blocking = tuple(sorted(-v if b else v for v, b in zip(scope, bits)))
                if blocking not in clauses:
                    return False
            nodes.append((set(scope), rhs))
        for left, right in cert['steps']:
            if any(type(i) is not int or not 0 <= i < len(nodes) for i in (left, right)):
                return False
            a, x = nodes[left]
            b, y = nodes[right]
            nodes.append((a ^ b, x ^ y))
        end = cert['conclusion']
        return type(end) is int and 0 <= end < len(nodes) and nodes[end] == (set(), 1)
    except (KeyError, TypeError, ValueError):
        return False


def trace_stats(cert):
    nodes = [(set(scope), {i}) for i, (scope, _) in enumerate(cert['equations'])]
    max_width = max((len(scope) for scope, _ in nodes), default=0)
    max_regions = 1 if nodes else 0
    for a, b in cert['steps']:
        scope = nodes[a][0] ^ nodes[b][0]
        regions = nodes[a][1] ^ nodes[b][1]
        nodes.append((scope, regions))
        max_width = max(max_width, len(scope))
        max_regions = max(max_regions, len(regions))
    return dict(xor_steps=len(cert['steps']), max_equation_width=max_width,
                max_combined_regions=max_regions)
