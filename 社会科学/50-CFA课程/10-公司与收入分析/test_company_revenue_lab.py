import math
import tempfile
import unittest
from pathlib import Path

from company_revenue_lab import (allocate_transaction_price, bundle_contract,
    case_results, generate_figures, over_time_contract, reinvestment_growth,
    revenue_cash_bridge, roic)


class CompanyRevenueLabTests(unittest.TestCase):
    def test_relative_standalone_price_allocation(self):
        allocation = allocate_transaction_price(120, {"system": 120, "monitoring": 30})
        self.assertEqual(allocation, {"system": 96, "monitoring": 24})
        self.assertAlmostEqual(sum(allocation.values()), 120)

    def test_bundle_contract_has_remaining_obligation(self):
        result = bundle_contract()
        self.assertEqual(result["revenue"], 96)
        self.assertEqual(result["contract_liability"], 24)
        self.assertEqual(result["receivable"], 60)
        self.assertEqual(result["gross_profit"], 41)

    def test_over_time_cost_progress_and_contract_asset(self):
        result = over_time_contract(80, 18, 48, 20, 10)
        self.assertEqual(result["progress"], 0.375)
        self.assertEqual(result["revenue"], 30)
        self.assertEqual(result["contract_asset"], 10)
        self.assertEqual(result["receivable"], 10)
        self.assertEqual(result["gross_profit"], 12)

    def test_revenue_cash_bridge_uses_balance_changes(self):
        self.assertEqual(revenue_cash_bridge(70, 70, 10, 24), 126)
        result = case_results()
        self.assertEqual(result["aggregate_revenue"], result["bridge"])

    def test_roic_uses_average_capital_and_units(self):
        self.assertAlmostEqual(roic(30, 140, 160), 0.20)
        self.assertAlmostEqual(roic(24, 54, 60), 24 / 57)
        self.assertNotAlmostEqual(roic(30, 140, 160), 30 / 160)

    def test_reinvestment_growth_identity(self):
        owned = reinvestment_growth(30, 20, 32.5)
        partner = reinvestment_growth(24, 6, 26.4)
        self.assertAlmostEqual(owned["reinvestment_rate"], 2 / 3)
        self.assertAlmostEqual(owned["roiic"], 0.125)
        self.assertAlmostEqual(owned["product"], owned["growth"])
        self.assertAlmostEqual(partner["reinvestment_rate"], 0.25)
        self.assertAlmostEqual(partner["roiic"], 0.40)
        self.assertAlmostEqual(partner["growth"], 0.10)

    def test_high_blended_roic_can_hide_bad_increment(self):
        result = case_results()["bad_increment"]
        self.assertLess(result["roiic"], result["capital_charge"])
        self.assertAlmostEqual(result["incremental_economic_profit"], -0.7)
        next_blended_roic = 31.5 / 160
        self.assertGreater(next_blended_roic, result["capital_charge"])

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            allocate_transaction_price(100, {"bad": 0})
        with self.assertRaises(ValueError):
            over_time_contract(80, 18, 48, 20, 10, customer_controls_asset=False)
        with self.assertRaises(ValueError):
            over_time_contract(80, 50, 48, 20, 10)
        with self.assertRaises(ValueError):
            roic(1, 0, 0)
        with self.assertRaises(ValueError):
            reinvestment_growth(30, 0, 31)
        with self.assertRaises(ValueError):
            revenue_cash_bridge(math.inf, 0, 0, 0)

    def test_figures_are_generated_from_the_same_case(self):
        with tempfile.TemporaryDirectory() as directory:
            generate_figures(directory)
            paths = {path.name for path in Path(directory).glob("*.svg")}
            self.assertEqual(paths, {"org-capital-map.svg",
                                     "roic-reinvestment-bridge.svg",
                                     "revenue-contract-bridge.svg"})
            revenue = (Path(directory) / "revenue-contract-bridge.svg").read_text(encoding="utf-8")
            roic_svg = (Path(directory) / "roic-reinvestment-bridge.svg").read_text(encoding="utf-8")
            org = (Path(directory) / "org-capital-map.svg").read_text(encoding="utf-8")
            self.assertIn("70 + 70 + 10 - 24 = 126", revenue)
            self.assertIn("ROIC 42.11%", roic_svg)
            self.assertIn("PingFang SC", org)
            self.assertIn("公众有限责任公司", org)
            self.assertIn("法律形式不等于已上市", org)
            self.assertIn("上市证券通常更有流动性", org)
            self.assertNotIn("公众 / 上市发行人", org)

    def test_committed_figures_match_generator(self):
        committed = Path(__file__).with_name("assets")
        with tempfile.TemporaryDirectory() as directory:
            generate_figures(directory)
            for name in ("org-capital-map.svg", "roic-reinvestment-bridge.svg",
                         "revenue-contract-bridge.svg"):
                self.assertEqual((Path(directory) / name).read_text(encoding="utf-8"),
                                 (committed / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
