import unittest

from bytecode_vm import BytecodeVM, Instruction, VerificationError, add_program, verify


class VerifierTests(unittest.TestCase):
    def test_valid_branch_has_consistent_stack_depth(self) -> None:
        code = [
            Instruction("LOAD_ARG", 0),
            Instruction("JUMP_IF_FALSE", 4),
            Instruction("LOAD_CONST", 0),
            Instruction("JUMP", 5),
            Instruction("LOAD_CONST", 1),
            Instruction("RETURN"),
        ]
        depths = verify(code, (10, 20), argument_count=1)
        self.assertEqual(depths[5], 1)

    def test_rejects_bad_operand_underflow_and_join(self) -> None:
        with self.assertRaises(VerificationError):
            verify([Instruction("LOAD_CONST", 1), Instruction("RETURN")], (0,), 0)
        with self.assertRaises(VerificationError):
            verify([Instruction("ADD_GENERIC"), Instruction("RETURN")], (), 0)
        inconsistent = [
            Instruction("LOAD_ARG", 0),
            Instruction("JUMP_IF_FALSE", 4),
            Instruction("LOAD_CONST", 0),
            Instruction("JUMP", 4),
            Instruction("RETURN"),
        ]
        with self.assertRaises(VerificationError):
            verify(inconsistent, (1,), 1)

    def test_rejects_reachable_fallthrough(self) -> None:
        with self.assertRaises(VerificationError):
            verify([Instruction("LOAD_CONST", 0)], (1,), 0)


class VMTests(unittest.TestCase):
    def test_hot_exact_int_site_specializes(self) -> None:
        vm = BytecodeVM(add_program(), argument_count=2, specialization_threshold=2)
        self.assertEqual(vm.run((20, 22)), 42)
        self.assertEqual(vm.run((40, 2)), 42)
        self.assertEqual(vm.code[2].op, "ADD_INT")
        self.assertIn("specialize", [event.kind for event in vm.trace])
        self.assertEqual(vm.run((1, 2)), 3)
        self.assertIn("guard_hit", [event.kind for event in vm.trace])

    def test_guard_failure_uses_generic_path(self) -> None:
        vm = BytecodeVM(add_program(), argument_count=2, specialization_threshold=1)
        self.assertEqual(vm.run((1, 2)), 3)
        self.assertEqual(vm.run(("byte", "code")), "bytecode")
        kinds = [event.kind for event in vm.trace]
        self.assertIn("guard_fail", kinds)
        self.assertIn("generic_fallback", kinds)
        self.assertEqual(vm.code[2].op, "ADD_INT")

    def test_step_limit_contains_infinite_loop(self) -> None:
        vm = BytecodeVM(
            [
                Instruction("LOAD_ARG", 0),
                Instruction("JUMP_IF_FALSE", 0),
                Instruction("LOAD_CONST", 0),
                Instruction("RETURN"),
            ],
            (1,),
            argument_count=1,
            specialization_threshold=1,
        )
        with self.assertRaises(RuntimeError):
            vm.run((False,), step_limit=5)


if __name__ == "__main__":
    unittest.main()
