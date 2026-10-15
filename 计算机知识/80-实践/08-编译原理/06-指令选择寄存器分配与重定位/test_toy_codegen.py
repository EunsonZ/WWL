import unittest

from toy_codegen import (
    IRInstruction,
    Label,
    MachineInstruction,
    Spill,
    apply_relocations,
    assemble,
    demo_ir,
    execute,
    linear_scan_allocate,
    lower_with_spills,
    select_instructions,
)


class SelectionAndAllocationTests(unittest.TestCase):
    def test_instruction_selection_rejects_non_ssa_or_undefined_use(self) -> None:
        with self.assertRaises(ValueError):
            select_instructions([IRInstruction("add", "x", ("missing", "missing"))])
        with self.assertRaises(ValueError):
            select_instructions(
                [IRInstruction("const", "x", immediate=1), IRInstruction("const", "x", immediate=2)]
            )

    def test_linear_scan_spills_and_lowering_reloads(self) -> None:
        virtual = select_instructions(demo_ir())
        allocation = linear_scan_allocate(virtual, ("R0",))
        self.assertTrue(any(isinstance(location, Spill) for location in allocation.values()))
        machine = lower_with_spills(virtual, allocation)
        operations = [instruction.op for instruction in machine]
        self.assertIn("STORE", operations)
        self.assertIn("LOAD", operations)
        self.assertEqual(execute(machine), 17)

    def test_two_register_allocation_preserves_result(self) -> None:
        virtual = select_instructions(demo_ir())
        allocation = linear_scan_allocate(virtual, ("R0", "R1"))
        self.assertEqual(execute(lower_with_spills(virtual, allocation)), 17)


class RelocationTests(unittest.TestCase):
    def test_local_pc_relative_call_is_relocated(self) -> None:
        obj = assemble(
            [
                MachineInstruction("CALL", ("helper",)),
                MachineInstruction("NOP"),
                Label("helper"),
                MachineInstruction("RET", ("R0",)),
            ]
        )
        words = apply_relocations(obj)
        self.assertEqual(words[0], 0x7001)
        self.assertEqual(len(obj.relocations), 1)

    def test_external_symbol_and_errors_are_explicit(self) -> None:
        obj = assemble([MachineInstruction("CALL", ("external",)), MachineInstruction("RET", ("R0",))])
        self.assertEqual(apply_relocations(obj, {"external": 2})[0], 0x7001)
        with self.assertRaisesRegex(ValueError, "undefined symbol"):
            apply_relocations(obj)
        with self.assertRaisesRegex(ValueError, "out of range"):
            apply_relocations(obj, {"external": 200})

    def test_encoding_range_checks(self) -> None:
        with self.assertRaisesRegex(ValueError, "LI immediate out of range"):
            assemble([MachineInstruction("LI", ("R0", 128))])
        with self.assertRaisesRegex(ValueError, "STORE slot out of range"):
            assemble([MachineInstruction("STORE", ("R0", 256))])
        with self.assertRaisesRegex(ValueError, "unknown Toy ISA register"):
            assemble([MachineInstruction("RET", ("R9",))])


if __name__ == "__main__":
    unittest.main()
