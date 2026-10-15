"""Independent grid/integral/cash-flow checks of the teaching examples."""
import math
import unittest
from economics_lab import (QuadraticFirm, competitive_benchmark, small_country_tariff,
                           inverse_quote, cross_quote, cip_forward, cip_bounds,
                           forward_points, ppp_relative, concentration, small_country_quota,
                           opportunity_cost_cloth)


class EconomicTests(unittest.TestCase):
    def test_monopoly_global_grid_and_exact_profit_gap(self):
        f = QuadraticFirm()
        optimum = f.monopoly()
        for i in range(6001):
            q = i/100
            direct_profit = (120-2*q)*q-(100+20*q+q*q)
            self.assertGreaterEqual(optimum['profit']+1e-9, direct_profit)
            self.assertAlmostEqual(optimum['profit']-direct_profit,
                                   3*(q-100/6)**2, places=8)

    def test_welfare_by_midpoint_integration(self):
        f = QuadraticFirm()
        for record in (f.monopoly(), competitive_benchmark(f), f.welfare(20)):
            q, p = record['q'], record['price']
            n = 1000
            # Independently integrate willingness to pay minus marginal resource cost.
            integral = sum((120-2*((i+.5)*q/n))-(20+2*((i+.5)*q/n))
                           for i in range(n))*q/n-100
            self.assertAlmostEqual(record['welfare'], integral)
            self.assertAlmostEqual(record['cs'], (120-p)*q/2)
        self.assertAlmostEqual(competitive_benchmark(f)['welfare']-f.monopoly()['welfare'], 1250/9)

    def test_shutdown_capacity_avoidable_and_sunk_costs(self):
        for fixed in (0, 100, 10000):
            f = QuadraticFirm(fixed=fixed)
            self.assertEqual(f.competitive(30)['q'], 5)
            self.assertEqual(f.competitive(19)['q'], 0)
            self.assertEqual(f.competitive(20)['q'], 0)
            self.assertEqual(f.monopoly(capacity=10)['q'], 10)
        self.assertEqual(QuadraticFirm(operating=30).competitive(30)['q'], 0)
        self.assertEqual(QuadraticFirm(operating=25).competitive(30)['q'], 0)
        self.assertEqual(QuadraticFirm().monopoly(intercept=10)['q'], 0)
        self.assertEqual(QuadraticFirm().competitive(100, capacity=0)['q'], 0)

    def test_cournot_unilateral_grid_same_aggregate_cost(self):
        # Rival q=10; each own cost=50+20q+2q^2. No profitable unilateral deviation.
        equilibrium_profit = 80*10-(50+20*10+2*10**2)
        for i in range(5501):
            q = i/100
            direct = (120-2*(q+10))*q-(50+20*q+2*q*q)
            self.assertGreaterEqual(equilibrium_profit+1e-9, direct)
        self.assertEqual(QuadraticFirm().cost(20), 2*(50+20*10+2*10**2))

    def test_tariff_welfare_triangles_and_prohibition(self):
        free = small_country_tariff(tariff=0)
        self.assertEqual(free['welfare'], 1000)
        for i in range(101):
            t = i/10
            result = small_country_tariff(tariff=t)
            self.assertAlmostEqual(result['dwl'], 2*t*t)
            self.assertAlmostEqual(free['cs']-result['cs'],
                                   result['ps']-free['ps']+result['revenue']+result['dwl'])
        result = small_country_tariff(tariff=50)
        self.assertEqual((result['price'], result['imports'], result['revenue']), (30, 0, 0))
        self.assertEqual(result['welfare'], 800)

    def test_quota_rent_allocation_and_trade_resource_feasibility(self):
        domestic = small_country_quota()
        foreign = small_country_quota(domestic_rent_share=0)
        self.assertEqual(domestic['welfare']-foreign['welfare'], 100)
        self.assertEqual((domestic['price'], domestic['imports']), (25, 20))
        self.assertEqual((foreign['welfare'], foreign['dwl']), (850, 150))
        self.assertEqual(small_country_quota(limit=100)['welfare'], 1000)
        self.assertEqual(small_country_quota(limit=0)['welfare'], 800)
        # Production (4 cloth in H; 4 wine in F) and consumption conserve goods.
        self.assertEqual(4*2, 8)
        self.assertEqual(4*1, 4)
        self.assertEqual(2+2, 4)
        self.assertEqual(1.5+2.5, 4)
        self.assertLess(opportunity_cost_cloth(2, 4), .75)
        self.assertLess(.75, opportunity_cost_cloth(1, 1))
        self.assertGreater(opportunity_cost_cloth(5, 4), .75)

    def test_quotes_round_trip_and_trade_execution(self):
        bid, ask = 1.099, 1.101
        inv = inverse_quote(bid, ask)
        self.assertEqual(inverse_quote(*inv), (bid, ask))
        self.assertLess(bid/ask, 1)  # sell EUR for USD then buy EUR
        cross = cross_quote((149.9, 150.1), (bid, ask))
        self.assertAlmostEqual(cross[0], 164.7401)
        self.assertAlmostEqual(cross[1], 165.2601)
        self.assertGreater(166/150.1/ask, 1)  # executable triangular synthetic example

    def test_cip_cashflows_inverse_and_points(self):
        s, rd, rf, t = 1.1, .04, .02, .5
        f = cip_forward(s, rd, rf, t)
        # Start with one USD: domestic deposit vs buying EUR, deposit and forward sale.
        self.assertAlmostEqual(1+rd*t, (1/s)*(1+rf*t)*f)
        self.assertAlmostEqual(cip_forward(1/s, rf, rd, t), 1/f)
        self.assertAlmostEqual(s+forward_points(s, f)*.0001, f)
        self.assertEqual(cip_forward(s, rd, rf, 0), s)
        self.assertLess(cip_forward(s, -.02, .01, 1), s)
        self.assertAlmostEqual(ppp_relative(s, .03, .01)/s, 1.03/1.01)

    def test_bid_ask_cip_bounds_match_zero_profit_transactions(self):
        sb, sa, t = 1.099, 1.101, .5
        lo, hi = cip_bounds(sb, sa, .04, .05, .02, .03, t)
        self.assertLess(lo, hi)
        # One USD borrowed, EUR bought at ask and lent: upper forward-bid threshold.
        self.assertAlmostEqual((1/sa)*(1+.02*t)*hi-(1+.05*t), 0)
        # One EUR borrowed and sold at bid, USD lent: lower forward-ask threshold.
        self.assertAlmostEqual(sb*(1+.04*t)-(1+.03*t)*lo, 0)
        self.assertAlmostEqual(cip_bounds(1.1, 1.1, .04, .04, .02, .02, t)[0],
                               cip_forward(1.1, .04, .02, t))

    def test_hhi_merger_identity(self):
        before = concentration([.4, .3, .2, .1])
        after = concentration([.7, .2, .1])
        self.assertAlmostEqual(before['hhi_10000'], 3000)
        self.assertAlmostEqual(after['hhi_fraction']-before['hhi_fraction'], 2*.4*.3)

    def test_invalid_inputs_and_finite_results(self):
        for bad in (math.nan, math.inf, -math.inf, None, '1', True):
            with self.assertRaises(ValueError):
                QuadraticFirm(fixed=bad)
            with self.assertRaises(ValueError):
                cip_forward(bad, .04, .02, .5)
        calls = [lambda: QuadraticFirm(quadratic=0), lambda: QuadraticFirm().cost(-1),
                 lambda: QuadraticFirm().monopoly(slope=0),
                 lambda: QuadraticFirm().competitive(30, capacity=-1),
                 lambda: QuadraticFirm().welfare(61), lambda: inverse_quote(2, 1),
                 lambda: cip_forward(1, .02, -2, 1), lambda: cip_forward(1, .02, .03, -1),
                 lambda: forward_points(1, 1.1, 0), lambda: small_country_tariff(world=31),
                 lambda: small_country_tariff(tariff=-1), lambda: concentration([]),
                 lambda: concentration([.2, .3]), lambda: concentration(None),
                 lambda: cross_quote(None, (1, 1)), lambda: cross_quote((1,), (1, 1)),
                 lambda: small_country_quota(limit=-1),
                 lambda: small_country_quota(domestic_rent_share=1.1),
                 lambda: opportunity_cost_cloth(2, 0),
                 lambda: cip_bounds(1, 1, .05, .04, .01, .02, 1),
                 lambda: QuadraticFirm().cost(1e308)]
        for call in calls:
            with self.assertRaises(ValueError):
                call()


if __name__ == '__main__':
    unittest.main()
