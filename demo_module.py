"""History -> retrieval -> base mapping -> fresh extensions -> checked lemma."""
from dataclasses import asdict
import json

from proofmodule import (ExtensionDefinition, ProofContext, ProofModule,
                         ProofModuleCache, instantiate)
from satcache import Step, normalize


def example_module():
    # (a OR c), (b OR c) |- (y OR c), with y <-> (a AND b).
    # Premises occupy 0,1; the three definition clauses occupy 2,3,4.
    return ProofModule((), (ExtensionDefinition(4, 1, 2),), ((1, 3), (2, 3)), (3, 4),
                       (Step(0, 4, 1, (-2, 3, 4)), Step(1, 5, 2, (3, 4))))


def main():
    cache = ProofModuleCache()
    cache.add(example_module())
    context = ProofContext(normalize([[11, 23], [17, 23], [4, 100]]))
    candidate = cache.lookup(context)
    if candidate is None:
        raise RuntimeError('No verified module found')
    accepted = context.apply(candidate.module)
    print(json.dumps(dict(base_mapping=candidate.base_mapping,
                          extension_mapping=candidate.extension_mapping,
                          accepted=asdict(accepted)), indent=2))
    # Consume the new clause and a retained extension definition in another module.
    y = candidate.extension_mapping[4]
    a, c = candidate.base_mapping[1], candidate.base_mapping[3]
    consume = ProofModule((), (), ((1, 3), (-1, 2)), (2, 3), (Step(0, 1, 1, (2, 3)),))
    exported = context.apply(instantiate(consume, {1: y, 2: a, 3: c}, context).module)
    print('Composed root-language clause:', exported.root_clause)
    # UNSAT under a branch is a guarded lemma, not a global UNSAT answer.
    branch = ProofModule((-1,), (), ((1,),), (), (Step(0, 1, 1, ()),))
    scoped = ProofContext(((1,),)).apply(branch)
    print('Branch result:', json.dumps(dict(guarded_clause=scoped.guarded_clause,
                                           proves_unsat=scoped.proves_unsat)))


if __name__ == '__main__':
    main()
