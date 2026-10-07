"""固定菱形 CFG 的结构、支配和 SSA 验证测试。"""

from __future__ import annotations

import unittest

from minilang_ir import Block, CFG, Instruction, Terminator, dominators, lower_diamond_to_tac, to_ssa, verify_ssa


class IRTests(unittest.TestCase):
    def test_tac_blocks_and_edges_have_terminators(self) -> None:
        cfg = lower_diamond_to_tac()
        self.assertEqual(cfg.successors("entry"), ("neg", "nonneg"))
        self.assertEqual(cfg.predecessors("join"), ("neg", "nonneg"))
        self.assertTrue(all(block.terminator is not None for block in cfg.blocks.values()))

    def test_dominators_for_diamond(self) -> None:
        dom = dominators(lower_diamond_to_tac())
        self.assertEqual(dom["entry"], {"entry"})
        self.assertEqual(dom["neg"], {"entry", "neg"})
        self.assertEqual(dom["join"], {"entry", "join"})

    def test_ssa_has_phi_and_verifies(self) -> None:
        ssa = to_ssa(lower_diamond_to_tac())
        phi = ssa.blocks["join"].instructions[0]
        self.assertEqual((phi.op, phi.dest, phi.args), ("phi", "x.3", (("neg", "x.1"), ("nonneg", "x.2"))))
        self.assertEqual(verify_ssa(ssa), [])

    def test_verifier_rejects_missing_phi_predecessor_and_definition(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("jump", ("join",))), "join": Block("join", [Instruction("phi", "x.1", (("entry", "x.0"),))], Terminator("return", ("x.1",)))})
        self.assertEqual(verify_ssa(cfg), ["undefined value x.0"])

    def test_verifier_rejects_nonexistent_phi_edge_without_crashing(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [Instruction("param", "x.0")], Terminator("jump", ("join",))),
            "join": Block("join", [Instruction("phi", "x.1", (("missing", "x.0"),))], Terminator("return", ("x.1",))),
        })
        self.assertEqual(verify_ssa(cfg), ["join: phi predecessors do not match CFG"])

    def test_invalid_phi_edge_does_not_hide_valid_edge_diagnostic(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [Instruction("param", "x.0")], Terminator("jump", ("join",))),
            "join": Block("join", [Instruction("phi", "x.1", (("missing", "x.0"), ("entry", "unknown.0")))], Terminator("return", ("x.1",))),
        })
        self.assertEqual(verify_ssa(cfg), ["join: phi predecessors do not match CFG", "undefined value unknown.0"])

    def test_verifier_rejects_same_block_use_before_definition(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [
                Instruction("add", "y.0", ("x.0", 1)),
                Instruction("param", "x.0"),
            ], Terminator("return", ("y.0",))),
        })
        self.assertEqual(verify_ssa(cfg), ["x.0 used before definition in entry"])

    def test_verifier_rejects_undefined_branch_condition(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [], Terminator("branch", ("c.0", "yes", "no"))),
            "yes": Block("yes", [], Terminator("return", ("1",))),
            "no": Block("no", [], Terminator("return", ("0",))),
        })
        self.assertEqual(verify_ssa(cfg), ["undefined value c.0"])

    def test_verifier_rejects_unknown_terminator(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("halt", ()))})
        self.assertEqual(verify_ssa(cfg), ["entry: unknown terminator halt"])

    def test_verifier_rejects_wrong_terminator_arity(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("jump", ()))})
        self.assertEqual(verify_ssa(cfg), ["entry: jump expects exactly 1 target"])

    def test_verifier_rejects_missing_target_block(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("jump", ("missing",)))})
        self.assertEqual(verify_ssa(cfg), ["entry: target block missing does not exist"])

    def test_verifier_rejects_unreachable_block_under_its_contract(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [], Terminator("return", ("0",))),
            "dead": Block("dead", [], Terminator("return", ("0",))),
        })
        self.assertEqual(verify_ssa(cfg), ["dead: unreachable block; verifier requires every block to be reachable from entry"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
