import unittest

from dataflow_opt import (
    Instruction,
    Kind,
    OVERDEFINED,
    UNDEF,
    constant,
    constant_propagation,
    demo_program,
    differential_check,
    interpret,
    join,
    optimize,
)


class LatticeTests(unittest.TestCase):
    def test_join_is_monotone_for_three_point_constant_lattice(self) -> None:
        self.assertEqual(join(UNDEF, constant(4)), constant(4))
        self.assertEqual(join(constant(4), constant(4)), constant(4))
        self.assertEqual(join(constant(4), constant(5)), OVERDEFINED)
        self.assertEqual(join(constant(4), OVERDEFINED), OVERDEFINED)
        self.assertEqual(constant(128), OVERDEFINED)

    def test_work_list_reaches_loop_fixed_point(self) -> None:
        program = [
            Instruction("CONST", "x", (0,)),
            Instruction("LABEL", args=("loop",)),
            Instruction("ADD", "x", ("x", "one")),
            Instruction("CONST", "one", (1,)),
            Instruction("JUMP", args=("loop",)),
        ]
        analysis = constant_propagation(program)
        self.assertGreater(analysis.visits, len(program))
        self.assertEqual(analysis.in_states[2]["x"].kind, Kind.OVERDEFINED)  # type: ignore[index]


class OptimizationTests(unittest.TestCase):
    def test_constant_folding_branch_pruning_and_dce(self) -> None:
        optimized, _ = optimize(demo_program())
        text = [instruction.text() for instruction in optimized]
        self.assertIn("five = const 5", text)
        self.assertIn("jump zero", text)
        self.assertNotIn("out = const 999", text)
        self.assertNotIn("dead = const 77", text)
        self.assertEqual(interpret(optimized, {"x": -7}), -35)

    def test_fixed_seed_finite_differential_check(self) -> None:
        original = demo_program()
        optimized, _ = optimize(original)
        first = differential_check(original, optimized, seed=1234, cases=64)
        second = differential_check(original, optimized, seed=1234, cases=64)
        self.assertEqual(first, second)
        self.assertTrue(all(before == after for _, before, after in first))

    def test_differential_check_exposes_bad_rewrite(self) -> None:
        bad = [Instruction("CONST", "out", (1,)), Instruction("RETURN", args=("out",))]
        with self.assertRaises(AssertionError):
            differential_check(demo_program(), bad, cases=1)


if __name__ == "__main__":
    unittest.main()
