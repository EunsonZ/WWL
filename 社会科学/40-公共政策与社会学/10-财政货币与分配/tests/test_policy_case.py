import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "code" / "policy_case.py"
SPEC = importlib.util.spec_from_file_location("policy_case", MODULE_PATH)
policy_case = importlib.util.module_from_spec(SPEC)
sys.modules["policy_case"] = policy_case
assert SPEC.loader is not None
SPEC.loader.exec_module(policy_case)


class PolicyCaseTest(unittest.TestCase):
    def test_all_instruments_and_intermediary_balance_sheets_close(self):
        self.assertEqual(policy_case.validate(), [])

    def test_every_intermediate_state_closes_without_undeclared_negative_balance(self):
        state = policy_case.apply_entries(entries=())
        for entry in policy_case.ENTRIES:
            state = policy_case.apply_entries(state, (entry,))
            self.assertTrue(all(gap == 0 for gap in policy_case.instrument_gaps(state).values()), entry.name)
            self.assertTrue(all(value >= 0 for positions in state.values() for value in positions.values()), entry.name)

    def test_new_loan_creates_equal_deposit_without_net_wealth(self):
        entry = next(e for e in policy_case.ENTRIES if e.name == "银行向低资产家庭新增贷款")
        before = policy_case.apply_entries(entries=())
        after = policy_case.apply_entries(entries=(entry,))
        self.assertEqual(policy_case.net_financial_worth(after, "低资产家庭"), policy_case.net_financial_worth(before, "低资产家庭"))
        self.assertEqual(after["银行"]["贷款资产"] - before["银行"]["贷款资产"], 10)
        self.assertEqual(after["银行"]["存款负债"] - before["银行"]["存款负债"], 10)

    def test_financing_and_transfer_do_not_enter_gdp(self):
        excluded = {"高资产家庭认购新国债", "向低资产家庭转移"}
        self.assertTrue(all(e.gdp == 0 for e in policy_case.ENTRIES if e.name in excluded))
        self.assertEqual(sum(e.gdp for e in policy_case.ENTRIES), 80)

    def test_consolidation_removes_internal_coupon_and_remittance(self):
        internal = {"政府向央行付息", "央行向政府上缴利润"}
        self.assertTrue(all(e.kind == "合并后抵销" for e in policy_case.ENTRIES if e.name in internal))
        end = policy_case.apply_entries()
        self.assertEqual(policy_case.private_nfw(end), 130)
        self.assertEqual(policy_case.analytical_g_c_nfw(end), -130)

    def test_rate_change_redistributes_but_sums_to_zero(self):
        for timing in ("调息前", "调息后"):
            self.assertAlmostEqual(sum(v[timing] for v in policy_case.RATE_CASHFLOW.values()), 0.0)
        self.assertLess(policy_case.RATE_CASHFLOW["低资产家庭"]["调息后"], policy_case.RATE_CASHFLOW["低资产家庭"]["调息前"])
        self.assertGreater(policy_case.RATE_CASHFLOW["高资产家庭"]["调息后"], policy_case.RATE_CASHFLOW["高资产家庭"]["调息前"])


if __name__ == "__main__":
    unittest.main()
