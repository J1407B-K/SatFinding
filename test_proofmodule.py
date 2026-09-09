from dataclasses import replace
from itertools import product
import json
import unittest

from demo_module import example_module
from proofmodule import (ExtensionDefinition, ProofContext, ProofModule, ProofModuleCache,
                         dumps, instantiate, loads)
from satcache import Step, normalize, satisfied


class ProofModuleTests(unittest.TestCase):
    def test_gate_encoding_including_signed_and_degenerate_inputs(self):
        for a, b in product((1, -1, 2, -2), repeat=2):
            d = ExtensionDefinition(3, a, b)
            for bits in product((False, True), repeat=3):
                model = dict(zip((1, 2, 3), bits))
                expected = model[3] == ((model[abs(a)] == (a > 0)) and (model[abs(b)] == (b > 0)))
                self.assertEqual(satisfied(d.clauses(), model), expected)

    def test_retrieval_freshening_and_export_boundary(self):
        cache, context = ProofModuleCache(), ProofContext(normalize([[11, 23], [17, 23], [4, 100]]))
        cache.add(example_module())
        candidate = cache.lookup(context)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.extension_mapping, {4: 101})
        result = context.apply(candidate.module)
        self.assertIsNone(result.root_clause)
        self.assertIn(result.guarded_clause, context.clauses)
        self.assertEqual(len(context.extension_definitions), 1)
        self.assertFalse(result.proves_unsat)

    def test_signed_mapping_and_capture_avoidance(self):
        context = ProofContext(normalize([[-4, 20], [7, 20]]))
        candidate = instantiate(example_module(), {1: -4, 2: 7, 3: 20}, context)
        self.assertEqual(candidate.extension_mapping, {4: 21})
        result = context.apply(candidate.module)
        self.assertEqual(result.conclusion, (20, 21))
        self.assertEqual(context.extension_definitions[0].left, -4)

    def test_composition_keeps_extension_definitions(self):
        context = ProofContext(((1, 3), (2, 3)))
        first = context.apply(instantiate(example_module(), {1: 1, 2: 2, 3: 3}, context).module)
        y = first.extension_definitions[0].variable
        consume = ProofModule((), (), ((1, 3), (-1, 2)), (2, 3), (Step(0, 1, 1, (2, 3)),))
        second = context.apply(instantiate(consume, {1: y, 2: 1, 3: 3}, context).module)
        self.assertEqual(second.root_clause, (1, 3))
        without_definitions = ProofContext((first.conclusion,))
        with self.assertRaises(ValueError):
            without_definitions.apply(instantiate(consume, {1: y, 2: 1, 3: 3},
                                     ProofContext((first.conclusion,), reserved_variables=(1,))).module)

    def test_stale_allocations_are_rejected_atomically(self):
        context = ProofContext(((1, 3), (2, 3)), reserved_variables=(50,))
        a = instantiate(example_module(), {1: 1, 2: 2, 3: 3}, context)
        b = instantiate(example_module(), {1: 1, 2: 2, 3: 3}, context)
        context.apply(a.module)
        before = (context.clauses, context.used_variables, context.extension_definitions)
        with self.assertRaises(ValueError):
            context.apply(b.module)
        self.assertEqual(before, (context.clauses, context.used_variables, context.extension_definitions))
        c = instantiate(example_module(), {1: 1, 2: 2, 3: 3}, context)
        self.assertEqual(c.extension_mapping, {4: 52})

    def test_residual_premise_must_be_guarded(self):
        context = ProofContext(((1, 2),))
        module = ProofModule((-1,), (), ((2,),), (2,), ())
        result = context.apply(module)
        self.assertEqual(result.root_clause, (1, 2))
        self.assertNotIn((2,), context.clauses)
        self.assertTrue(satisfied(context.clauses, {1: True, 2: False}))
        self.assertIsNone(ProofContext(((1, 2),)).check(replace(module, assumptions=())))

    def test_branch_unsat_is_not_global_unsat(self):
        module = ProofModule((-1,), (), ((1,),), (), (Step(0, 1, 1, ()),))
        context = ProofContext(((1,),))
        result = context.apply(module)
        self.assertFalse(result.proves_unsat)
        self.assertEqual(result.root_clause, (1,))
        self.assertTrue(satisfied(context.clauses, {1: True}))

    def test_composed_global_unsat(self):
        context = ProofContext(normalize([[1], [2], [-1, -2]]))
        introduce = ProofModule((), (ExtensionDefinition(3, 1, 2),), ((1,), (2,)), (3,),
                                (Step(0, 4, 1, (-2, 3)), Step(1, 5, 2, (3,))))
        context.apply(introduce)
        refute = ProofModule((), (), ((-2, -1), (-3, 1), (-3, 2), (3,)), (),
                             (Step(1, 0, 1, (-3, -2)), Step(2, 4, 2, (-3,)), Step(3, 5, 3, ())))
        result = context.apply(refute)
        self.assertTrue(result.proves_unsat)
        self.assertEqual(result.root_clause, ())

    def test_bad_definition_graphs_and_missing_premises(self):
        context = ProofContext(((1, 3), (2, 3)))
        template = example_module()
        definitions = [(ExtensionDefinition(1, 2, 3),), (ExtensionDefinition(4, 4, 1),),
                       (ExtensionDefinition(4, 5, 1), ExtensionDefinition(5, 1, 2)),
                       (ExtensionDefinition(4, 1, 2), ExtensionDefinition(4, 1, 2)),
                       (ExtensionDefinition(4, 1, 99),)]
        for ds in definitions:
            self.assertIsNone(context.check(replace(template, extension_definitions=ds)))
        self.assertIsNone(ProofContext(((1, 3),)).check(template))
        self.assertIsNone(context.check(replace(template, assumptions=(4,))))
        self.assertIsNone(context.check(replace(template, assumptions=(-1, 1))))

    def test_forged_derivations_and_conclusions(self):
        context, module = ProofContext(((1, 3), (2, 3))), example_module()
        for step in (Step(-1, 4, 1, (-2, 3, 4)), Step(0, 99, 1, (-2, 3, 4)),
                     Step(0, 4, 2, (-2, 3, 4)), Step(0, 4, 1, (3, 4))):
            self.assertIsNone(context.check(replace(module, derivation=(step, module.derivation[1]))))
        self.assertIsNone(context.check(replace(module, conclusion=())))
        self.assertIsNone(context.check(replace(module, premises=((True, 3), (2, 3)))))

    def test_definitions_preserve_every_root_model(self):
        root = ((1, 3), (2, 3))
        context = ProofContext(root)
        context.apply(example_module())
        for bits in product((False, True), repeat=3):
            model = dict(zip((1, 2, 3), bits))
            if not satisfied(root, model):
                continue
            for d in context.extension_definitions:
                model[d.variable] = (model[abs(d.left)] == (d.left > 0)) and (model[abs(d.right)] == (d.right > 0))
            self.assertTrue(satisfied(context.clauses, model))

    def test_long_nested_definitions_are_not_expanded(self):
        ds = [ExtensionDefinition(3, 1, 2)]
        ds += [ExtensionDefinition(y, y-1, y-1) for y in range(4, 1003)]
        module = ProofModule((), tuple(ds), (), ds[-1].clauses()[0], ())
        context = ProofContext((), reserved_variables=(1, 2))
        self.assertIsNone(context.apply(module).root_clause)
        self.assertEqual(len(context.extension_definitions), 1000)
        self.assertLessEqual(len(context.clauses), 3001)

    def test_json_and_mapping_validation(self):
        module = example_module()
        self.assertEqual(loads(dumps(module)), module)
        raw = json.loads(dumps(module))
        raw['version'] = True
        with self.assertRaises(ValueError):
            loads(json.dumps(raw))
        context = ProofContext(((1, 3), (2, 3)))
        for mapping in ({1: 1}, {1: 1, 2: 1, 3: 3}, {1: 1, 2: 2, 3: 99}, {True: 1, 2: 2, 3: 3}):
            with self.assertRaises(ValueError):
                instantiate(module, mapping, context)
        with self.assertRaises(ValueError):
            ProofModuleCache().add(replace(module, conclusion=()))

    def test_zero_retrieval_budget(self):
        cache = ProofModuleCache()
        cache.add(example_module())
        context = ProofContext(((1, 3), (2, 3)))
        self.assertIsNone(cache.lookup(context, mapping_budget=0))
        self.assertIsNone(cache.lookup(context, top_k=0))


if __name__ == '__main__':
    unittest.main()
