import math
import tempfile
import unittest
from pathlib import Path

from level3_core_lab import (appraisal_metrics, brinson_allocation_selection_interaction,
    currency_overlay, futures_contracts, generate_figures, portfolio_stats, surplus_risk)


class Level3CoreLabTests(unittest.TestCase):
    def test_two_asset_stats_hand_oracle(self):
        mean, vol = portfolio_stats([.6,.4],[.03,.065],[[.0025,.0015],[.0015,.0225]])
        self.assertAlmostEqual(mean, .044)
        self.assertAlmostEqual(vol * vol, .00522)

    def test_liability_duration_direction(self):
        self.assertAlmostEqual(surplus_risk(105,100,5,8,.01), 2.75)
        self.assertAlmostEqual(surplus_risk(105,100,5,8,-.01), -2.75)

    def test_overlay_numbers_and_sign(self):
        self.assertAlmostEqual(futures_contracts(50_000_000,.60,.45,2500,50), -60)
        foreign, cash = currency_overlay(20_000_000,7.20,.75,7.24)
        self.assertAlmostEqual(foreign, 2_083_333.3333333333)
        self.assertAlmostEqual(cash, 15_083_333.333333334)

    def test_brinson_reconciles_active_return(self):
        a,s,i,active=brinson_allocation_selection_interaction([.5,.3,.2],[.4,.4,.2],[.10,.03,.05],[.08,.04,.04])
        self.assertAlmostEqual(sum(a), .004)
        self.assertAlmostEqual(sum(s), .006)
        self.assertAlmostEqual(sum(i), .003)
        self.assertAlmostEqual(sum(a)+sum(s)+sum(i), active)
        self.assertAlmostEqual(active, .013)

    def test_drawdown_path_and_metrics(self):
        m=appraisal_metrics([.03,-.02,.04,-.01,.02,.01],[.02,-.03,.03,-.005,.015,.012])
        self.assertAlmostEqual(m["max_drawdown"], -.02)
        self.assertEqual(m["drawdown_duration"], 1)
        self.assertTrue(math.isfinite(m["sortino"]) and math.isfinite(m["appraisal_ratio"]))

    def test_appraisal_regression_known_alpha_beta_residual(self):
        b=[-.02,-.01,.01,.02]
        r=[.005,0,.01,.025]
        m=appraisal_metrics(r,b,mar=.01)
        self.assertAlmostEqual(m["alpha"], .01)
        self.assertAlmostEqual(m["beta"], .5)
        self.assertAlmostEqual(m["residual_risk"], math.sqrt(2)*.005)
        self.assertAlmostEqual(m["appraisal_ratio"], math.sqrt(2))

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): portfolio_stats([.4,.4],[.1,.2],[[1,0],[0,1]])
        with self.assertRaises(ValueError): currency_overlay(10,7,1.1,7.1)
        with self.assertRaises(ValueError): appraisal_metrics([.1],[.1])
        with self.assertRaises(ValueError): appraisal_metrics([.01,.02,.03],[.01,.01,.01])
        with self.assertRaises(ValueError): appraisal_metrics([.01,.02,.03],[.01,.02,.03])
        with self.assertRaises(ValueError): appraisal_metrics([.01,.02,.03],[.01,.02,.03],mar=-1)

    def test_figures_are_generated_and_labeled(self):
        with tempfile.TemporaryDirectory() as d:
            generate_figures(d)
            names={p.name for p in Path(d).glob('*.svg')}
            self.assertEqual(names, {'l3-decision-chain.svg','l3-allocation-robustness.svg','l3-attribution-bridge.svg'})
            self.assertIn('归因', (Path(d)/'l3-attribution-bridge.svg').read_text(encoding='utf-8'))
            allocation=(Path(d)/'l3-allocation-robustness.svg').read_text(encoding='utf-8')
            self.assertIn('cx="212.9" cy="232.0"', allocation)
            self.assertIn('data-weights="0.6,0.4"', allocation)
            self.assertIn('σ 7.225% / E[R] 4.40%', allocation)
            self.assertIn('完整两资产可行轨迹（含非有效段）', allocation)


if __name__ == '__main__': unittest.main()
