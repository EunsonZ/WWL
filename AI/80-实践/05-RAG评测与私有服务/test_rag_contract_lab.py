"""逐例核对有限教学 DSL 的失败合同。"""
import unittest

from rag_contract_lab import ACCESS_DENIED, CASES, FACTS, HUMAN_REVIEW, NO_ANSWER, decide, run_contracts


class ContractLabTests(unittest.TestCase):
    def test_every_explicit_contract_is_checked(self) -> None:
        self.assertEqual(run_contracts(), {case.name: True for case in CASES})

    def test_failure_actions_are_not_success_with_empty_citations(self) -> None:
        outcomes = {case.name: decide(case, FACTS) for case in CASES}
        self.assertEqual(outcomes["no-answer"].action, NO_ANSWER)
        self.assertEqual(outcomes["acl"].action, ACCESS_DENIED)
        for name in ("conflict", "stale", "revoked"):
            self.assertEqual(outcomes[name].action, HUMAN_REVIEW)
            self.assertEqual(outcomes[name].citations, ())

    def test_instruction_material_cannot_change_acl_or_selected_facts(self) -> None:
        case = next(case for case in CASES if case.name == "instruction")
        outcome = decide(case, FACTS)
        self.assertEqual(outcome.citations, ("injection",))
        self.assertNotIn("secret", outcome.citations)


if __name__ == "__main__":
    unittest.main(verbosity=2)
