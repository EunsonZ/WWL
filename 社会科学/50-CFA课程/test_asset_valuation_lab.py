"""Independent identities, finite differences, exhaustive fee regions, invalid inputs."""
import unittest
from fractions import Fraction as Q
from math import exp
import asset_valuation_lab as lab


class AssetTests(unittest.TestCase):
    def test_bond_independent_rational(self):
        price,d,c=lab.bond_metrics([1,2],[5,105],.05)
        exact=Q(5)/Q('1.05')+Q(105)/Q('1.05')**2
        self.assertAlmostEqual(price,float(exact),places=12)
        # Derivative from independent centered repricing, not the analytic summation.
        for h in [1e-3,1e-4]:
            up=lab.bond_metrics([1,2],[5,105],.05+h)[0]
            down=lab.bond_metrics([1,2],[5,105],.05-h)[0]
            self.assertAlmostEqual((down-up)/(2*h*price),d,delta=1e-5)
            self.assertAlmostEqual((up+down-2*price)/(h*h*price),c,delta=2e-5)
        for shock in [-.02,-.01,.01,.02]:
            exact=lab.bond_metrics([1,2],[5,105],.05+shock)[0]
            first=price*(1-d*shock)
            second=first+.5*price*c*shock**2
            self.assertGreater(exact,first)
            self.assertLess(abs(exact-second),abs(exact-first))

    def test_zero_bond_closed_form(self):
        p,d,c=lab.bond_metrics([5],[100],.03)
        self.assertAlmostEqual(d,5/1.03)
        self.assertAlmostEqual(c,30/1.03**2)
        self.assertGreater(p,0)

    def test_curve_interpolation_krd(self):
        nodes=[1,1.5,2];z=[.03,.04,.05];ts=[1,1.25,2];cs=[5,4,105]
        p,k=lab.curve_price_and_krd(ts,cs,nodes,z)
        expected=5*exp(-.03)+4*exp(-.035*1.25)+105*exp(-.05*2)
        self.assertAlmostEqual(p,expected)
        h=1e-5
        for j in range(3):
            up=z.copy();down=z.copy();up[j]+=h;down[j]-=h
            pu=lab.curve_price_and_krd(ts,cs,nodes,up)[0]
            pd=lab.curve_price_and_krd(ts,cs,nodes,down)[0]
            self.assertAlmostEqual((pd-pu)/(2*h*p),k[j],delta=1e-9)
        pu=lab.curve_price_and_krd(ts,cs,nodes,[v+h for v in z])[0]
        pd=lab.curve_price_and_krd(ts,cs,nodes,[v-h for v in z])[0]
        self.assertAlmostEqual(sum(k),(pd-pu)/(2*h*p),delta=1e-9)

    def test_twist_duration_failure(self):
        data=lab.demo()['curve']
        self.assertAlmostEqual(data['krd'][1],0)
        self.assertGreater(data['twist_price'],data['price'])
        self.assertLess(abs(data['twist_linear']-data['twist_price']),.03)

    def test_forward_offset_and_terminal(self):
        fair,long=lab.forward_value(110,105,.04,.5,100)
        _,short=lab.forward_value(110,105,.04,.5,-100)
        self.assertEqual(long,-short)
        self.assertAlmostEqual(long,(fair-105)/(1.04**.5)*100)
        self.assertEqual(lab.forward_value(110,105,.04,0)[1],5)
        self.assertAlmostEqual(lab.forward_value(100,105,.05,1)[1],0)

    def test_futures_telescoping(self):
        for path in [[105,108,103,110],[105,103,108,110],[0,-5,3]]:
            vs=lab.futures_variation(path,10,2)
            self.assertEqual(sum(vs),20*(path[-1]-path[0]))
            self.assertEqual(vs,[-x for x in lab.futures_variation(path,10,-2)])
        self.assertEqual(lab.futures_variation([105,108,103,110],10,2),[60,-100,140])

    def test_option_convexity_and_profit(self):
        self.assertEqual([lab.call_payoff(s,100) for s in [80,100,110,120]],[0,0,10,20])
        # Jensen inequality across payoff kink: average payoff exceeds payoff at average.
        self.assertGreater((lab.call_payoff(80,100)+lab.call_payoff(120,100))/2,
                           lab.call_payoff(100,100))

    def test_waterfall_independent_regions(self):
        # Exact enumeration across capital loss, insufficient hurdle, and residual regions.
        for proceeds in range(0,201):
            w=lab.waterfall(100,proceeds)
            self.assertEqual(w['lp']+w['gp'],proceeds)
            expected_gp=Q(1,5)*max(Q(proceeds)-Q('116.64'),Q(0))
            self.assertEqual(w['gp'],expected_gp)
            self.assertGreaterEqual(w['lp'],0)
            u=lab.waterfall(100,proceeds,catch_up=True)
            self.assertEqual(u['lp']+u['gp'],proceeds)
            profit=Q(proceeds)-100
            expected_catch_gp=min(max(Q(proceeds)-Q('116.64'),Q(0)),max(profit/Q(5),Q(0)))
            self.assertEqual(u['gp'],expected_catch_gp)
        hard=lab.waterfall(100,150)
        self.assertEqual(hard['lp'],Q('143.328'))
        self.assertEqual(hard['gp'],Q('6.672'))
        self.assertEqual(lab.waterfall(100,150,catch_up=True)['gp'],10)

    def test_irr_cashflow_identity(self):
        r=lab.two_year_irr(100,2.4,141.328)
        self.assertAlmostEqual(-100-2.4/(1+r)+141.328/(1+r)**2,0,places=11)
        self.assertAlmostEqual(lab.two_year_irr(100,0,121),.1)
        self.assertAlmostEqual(lab.two_year_irr(100,0,64),-.2)

    def test_invalid_inputs(self):
        bad=[lambda:lab.bond_metrics([],[],.05),
             lambda:lab.bond_metrics([1],[5,105],.05),
             lambda:lab.bond_metrics([1,1],[5,105],.05),
             lambda:lab.bond_metrics([1],[-1],.05),
             lambda:lab.bond_metrics([1],[1],-1),
             lambda:lab.bond_metrics([1],[1],float('nan')),
             lambda:lab.curve_price_and_krd([3],[100],[1,2],[.03,.04]),
             lambda:lab.curve_price_and_krd([1],[100],[1,1],[.03,.04]),
             lambda:lab.forward_value(100,105,.05,-.1),
             lambda:lab.forward_value(100,105,float('inf'),1),
             lambda:lab.futures_variation([1,2],10,.5),
             lambda:lab.futures_variation([1],10,1),
             lambda:lab.call_payoff(-1,100),
             lambda:lab.waterfall(100,150,years=2.5),
             lambda:lab.waterfall(100,150,carry=1),
             lambda:lab.waterfall(100,150,hurdle=-.1),
             lambda:lab.waterfall(True,150),
             lambda:lab.two_year_irr(100,2,-1),
             lambda:lab.two_year_irr(1e308,0,1e-308),
             lambda:lab.curve_price_and_krd([1,2],[1e308,1e308],[1,2],[0,0])]

        for f in bad:
            with self.assertRaises(ValueError):f()


if __name__=='__main__':
    unittest.main()
