"""独立手算结果对应正文的反例；不把数据源核验或理解验收冒充为单测。"""

from fractions import Fraction as F
import unittest

from ai_investment_examples import break_even_revenue, examples, npv, two_year_scenario


class InvestmentExamplesTests(unittest.TestCase):
    def test_terminal_receipt_is_discounted(self):
        self.assertEqual(npv(F(100), (F(0), F(0)), F(121), F(1, 10)), 0)
        self.assertEqual(npv(F(100), (F(0), F(0)), F(110), F(1, 10)), F(-100, 11))

    def test_break_even_uses_fixed_cost_not_total_cost(self):
        case = examples()["break_even"]
        self.assertEqual(case["revenue"], 8)
        self.assertEqual(case["profit"], 0)
        self.assertEqual(case["double_counted_threshold"], F(32, 3))
        self.assertEqual(case["profit_at_wrong_threshold"], 2)
        self.assertEqual(break_even_revenue(F(6), F(2, 5)), 10)
        with self.assertRaises(ValueError):
            break_even_revenue(F(6), F(1))

    def test_unit_conversion_is_arithmetically_correct(self):
        units = examples()["unit_conversion_only"]
        self.assertEqual(units["divided_by_half_billion_usd_per_year"], F("17.028"))
        self.assertEqual(units["same_amount_in_hundred_million_usd_per_year"], F("170.28"))

    def test_overlapping_demand_is_counted_once(self):
        self.assertEqual(examples()["demand"], {
            "terminal_use": 70, "strategic_motive": 50, "intersection": 30, "union": 90,
        })

    def test_payment_boundary_preserves_cash_without_inflating_final_payments(self):
        ledger = examples()["payment_ledger"]
        self.assertEqual(ledger["cash_change"], {"模型商": 40, "云商": 30, "设备商": 30})
        self.assertEqual(sum(ledger["cash_change"].values()), 100)
        self.assertEqual(ledger["outside_customer_cash"], 100)
        self.assertEqual(ledger["layered_sales"], 190)
        self.assertEqual(ledger["rho_cash_over_gross"], F(10, 19))

    def test_same_closure_progress_has_opposite_npv_signs(self):
        cases = examples()["scenarios"]
        expected = {"A": F(700, 121), "B": F(-140, 11),
                    "C": F(-3050, 121), "D": F(-3800, 121)}
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertEqual(cases[name]["closure"], (F(1, 2), F(7, 10)))
                self.assertEqual(cases[name]["npv"], value)
        self.assertEqual(cases["A"]["sold"], (40, 56))
        self.assertEqual(cases["A"]["npv"] - cases["B"]["npv"], F(2240, 121))

    def test_utilization_is_applied_once_and_zero_sales_keep_fixed_costs(self):
        self.assertEqual(two_year_scenario(utilization=F(0))["cash_flows"], (-10, -10))
        self.assertEqual(two_year_scenario(utilization=F(1))["sold"], (50, 70))
        with self.assertRaises(ValueError):
            two_year_scenario(utilization=F(11, 10))


if __name__ == "__main__":
    unittest.main()
