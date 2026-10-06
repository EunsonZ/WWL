"""Independent arithmetic and boundary checks for equity_market_lab."""
from fractions import Fraction as Q
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import equity_market_lab as lab


class EquityMarketLabTests(unittest.TestCase):
    def test_market_order_cost_ledger(self):
        x = lab.execution_cost("32.90", "33.10", "33.10", 1000, 20, "32.95")
        self.assertEqual(x["midpoint"], Q(33))
        self.assertEqual(x["quoted_spread"], Q(1, 5))
        self.assertEqual(x["effective_spread_per_share"], Q(1, 5))
        self.assertEqual(x["implicit_midpoint_cost"], 100)
        self.assertEqual(x["total_midpoint_cost"], 120)
        self.assertEqual(x["decision_shortfall"], 170)
        self.assertEqual(x["cash_outflow"], 33120)
        self.assertAlmostEqual(float(x["decision_shortfall_bps"]), 51.59332321699545)

    def test_split_divisor_preserves_index_level(self):
        x = lab.index_case()
        self.assertEqual(x["divisor0"], 1)
        self.assertEqual(x["divisor1"], Q(7, 10))
        self.assertEqual(sum(x["prices0"]) / x["divisor0"], 100)
        self.assertEqual(sum(x["reference_after_split"]) / x["divisor1"], 100)

    def test_weighting_methods_are_independently_recomputed(self):
        x = lab.index_case()
        self.assertEqual(x["price_returns"], (Q(1, 10), Q(-1, 10), Q(1, 10)))
        self.assertEqual(x["price_weight_return"], Q(1, 70))
        self.assertEqual(x["equal_price_return"], Q(1, 30))
        weights = [Q(600, 1700), Q(600, 1700), Q(500, 1700)]
        independent = sum(w * r for w, r in zip(weights, x["price_returns"]))
        self.assertEqual(x["cap_price_return"], independent)
        self.assertEqual(x["cap_price_return"], Q(1, 34))

    def test_price_and_total_return_stay_distinct(self):
        x = lab.index_case()
        self.assertEqual(sum(x["distributions"]), 20)
        self.assertEqual(x["cap_total_return"], Q(7, 170))
        self.assertGreater(x["cap_total_return"], x["cap_price_return"])
        self.assertEqual(x["equal_total_return"], Q(41, 900))

    def test_driver_forecast_and_changed_condition(self):
        x = lab.company_forecast()
        self.assertEqual(x["company_units"], Q(1113, 100))
        self.assertEqual(x["revenue"], Q(114639, 100))
        self.assertEqual(x["ebit"], Q(802473, 10000))
        conservative = lab.company_forecast(industry_units=106, market_share="0.10", price=100)
        self.assertEqual(conservative["revenue"], 1060)
        self.assertLess(conservative["revenue"], x["revenue"])

    def test_fcfe_bridge_and_per_share_units(self):
        x = lab.company_forecast()
        independent = x["net_income"] + 20 - 30 - 8 + 3
        self.assertEqual(x["fcfe"], independent)
        self.assertEqual(x["fcfe"], Q(1207419, 40000))
        self.assertEqual(x["fcfe_per_share"], x["fcfe"] / 20)

    def test_ddm_timing_and_sensitivity(self):
        x = lab.two_stage_ddm("1.50", "1.65", "0.10", "0.04")
        self.assertEqual(x["d3"], Q(429, 250))
        self.assertEqual(x["terminal2"], Q(143, 5))
        independent = Q(3, 2) / Q(11, 10) + (Q(33, 20) + Q(143, 5)) / Q(11, 10) ** 2
        self.assertEqual(x["value0"], independent)
        self.assertEqual(x["value0"], Q(290, 11))
        lower_discount = lab.two_stage_ddm("1.50", "1.65", "0.09", "0.04")
        self.assertGreater(lower_discount["value0"], x["value0"])

    def test_relative_value_normalization_and_preferred(self):
        f = lab.company_forecast()
        x = lab.relative_values(f["eps"], f["revenue"], 20, 14, "0.55", "0.40")
        self.assertEqual(x["normalized_pe_value"], f["eps"] * 14)
        self.assertEqual(x["reported_pe_value"] - x["normalized_pe_value"], Q(28, 5))
        self.assertEqual(x["ps_value"], f["revenue"] / 20 * Q(11, 20))
        self.assertEqual(lab.preferred_value("2.40", "0.08"), 30)

    def test_ps_remains_computable_when_eps_is_negative(self):
        self.assertEqual(lab.ps_value(100, 10, "0.55"), Q(11, 2))
        with self.assertRaises(ValueError):
            lab.pe_values(-1, 14)

    def test_efficiency_result_depends_on_expected_return_model(self):
        self.assertEqual(lab.abnormal_return("0.04", "0.01"), Q(3, 100))
        self.assertEqual(lab.abnormal_return("0.04", "0.015"), Q(1, 40))
        self.assertNotEqual(lab.abnormal_return("0.04", "0.01"),
                            lab.abnormal_return("0.04", "0.015"))

    def test_invalid_inputs_and_committed_figures(self):
        bad = [
            lambda: lab.execution_cost(33.1, 32.9, 33, 100, 0, 33),
            lambda: lab.execution_cost(32.9, 33.1, 33.1, 1.5, 0, 33),
            lambda: lab.company_forecast(market_share="1.1"),
            lambda: lab.company_forecast(shares=0),
            lambda: lab.two_stage_ddm(1, 1, ".04", ".04"),
            lambda: lab.two_stage_ddm(-1, 1, ".10", ".04"),
            lambda: lab.preferred_value(2, 0),
            lambda: lab.relative_values(0, 100, 10, 14, 1),
            lambda: lab.abnormal_return(float("nan"), 0),
        ]
        for case in bad:
            with self.assertRaises(ValueError):
                case()
        root = Path(__file__).resolve().parent
        with TemporaryDirectory() as tmp:
            generated = lab.render_svgs(tmp)
            self.assertEqual(set(generated), {
                "market-order-cost.svg", "index-weighting-bridge.svg",
                "forecast-valuation-bridge.svg",
            })
            for name, expected in generated.items():
                self.assertEqual((root / "assets" / name).read_text(encoding="utf-8"), expected)
            self.assertIn("除数 1 → 0.7", generated["index-weighting-bridge.svg"])
            self.assertIn("DDM 26.36", generated["forecast-valuation-bridge.svg"])


if __name__ == "__main__":
    unittest.main()
