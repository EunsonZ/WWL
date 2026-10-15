"""Independent exact arithmetic, path cashflow oracles, and domain counterexamples."""
import unittest
from fractions import Fraction as F
from itertools import product
from math import sqrt
import level2_case_lab as lab


class Level2Cases(unittest.TestCase):
    def test_ar_closed_form_and_variance(self):
        a = lab.ar1(.4,.8,3,.3,2)
        self.assertAlmostEqual(a['mean'],2)
        self.assertAlmostEqual(a['unconditional_variance'],float(F(1,4)))
        for h,p in enumerate(a['forecasts'],1):
            self.assertAlmostEqual(p,float(2+F(4,5)**h))
            self.assertAlmostEqual(a['conditional_variances'][h-1],float(F(9,100)*(1-F(16,25)**h)/(1-F(16,25))))
        self.assertEqual(lab.ar1(2,0,5,0,1)['forecasts'],[2])
        self.assertAlmostEqual(lab.ar1(3,-.5,8,.2,1)['forecasts'][0],-1)

    def test_arch_boundary_against_homoskedastic_assumption(self):
        # Independent theoretical counterexample, not an ARCH implementation.
        # Same unconditional innovation variance .09, different conditional state.
        omega, alpha, observed = F('.045'), F('.5'), F('.6')
        unconditional = omega/(1-alpha)
        h1 = omega+alpha*observed**2
        h2 = omega+alpha*h1
        error2 = F('.8')**2*h1+h2
        self.assertEqual(unconditional,F('.09'))
        self.assertEqual(h1,F('.225'))
        self.assertEqual(h2,F('.1575'))
        self.assertEqual(error2,F('.3015'))
        constant_case=lab.ar1(.4,.8,3,.3,2)
        self.assertNotAlmostEqual(constant_case['conditional_variances'][0],float(h1))
        self.assertNotAlmostEqual(constant_case['conditional_variances'][1],float(error2))

    def test_rmse_exact_error_sum(self):
        self.assertAlmostEqual(lab.rmse([2.9,2.3,2.5,2.1],[2.8,2.72,2.24,2.4]),sqrt(float(F(43,500))))
        self.assertAlmostEqual(lab.rmse([2.9,2.3,2.5,2.1],[3,2.9,2.3,2.5]),sqrt(float(F(57,400))))

    def test_df_hand_tabulated_oracle(self):
        # 8 lag values: sum x=97, sum dx=4, sum x^2=1199,
        # sum x*dx=41, sum dx^2=14. No calls to production OLS.
        n=8
        sxx=F(1199)-F(97**2,n)
        sxy=F(41)-F(97*4,n)
        syy=F(14)-F(4**2,n)
        beta=sxy/sxx
        se=sqrt(float((syy-sxy*sxy/sxx)/F(n-2)/sxx))
        result=lab.df_no_lag([10,11,10,12,13,12,14,15,14])
        self.assertAlmostEqual(result['slope'],float(beta))
        self.assertAlmostEqual(result['intercept'],float(F(4,n)-beta*F(97,n)))
        self.assertAlmostEqual(result['statistic'],float(beta)/se)

    def test_spurious_is_single_generated_nonstationary_sample(self):
        x,y=lab.spurious_sample()
        self.assertEqual(len(x),80)
        fit=lab.ols(x,y)
        self.assertGreater(fit['r2'],.8)
        self.assertGreater(fit['statistic'],18)
        # DGP independence is specified in the generator, not certified by this fit.
        self.assertNotEqual([b-a for a,b in zip(x,x[1:])],[b-a for a,b in zip(y,y[1:])])

    def test_fcff_cash_ledger_and_terminal_capital(self):
        self.assertEqual(lab.fcff(110,.25,20,35,15),float(F(105,2)))
        self.assertEqual(lab.fcff(132,.25,24,42,18),63)
        self.assertAlmostEqual(lab.fcff(145.2,.25,26.4,44.4,19.8),71.1)
        capital2=F(600)+F(42-24+18)+F('44.4')-F('26.4')+F('19.8')
        nopat3=F('145.2')*F(3,4)*F(103,100)
        stable_cash=nopat3-F(3,100)*capital2
        self.assertEqual(stable_cash,F('91.953'))
        # Using mere 71.1*(1.03) would retain inconsistent reinvestment.
        self.assertNotEqual(stable_cash,F('71.1')*F('1.03'))
        exact=F(63)/F('1.09')+(F('71.1')+stable_cash/F('.06'))/F('1.09')**2
        self.assertAlmostEqual(lab.dcf([63,71.1],.09,91.953,.03),float(exact))
        self.assertEqual(lab.fcff(110,0,20,35,15),80)
        for growth in (F('.02'),F('.03'),F('.04')):
            stable=F('108.9')*(1+growth)-capital2*growth
            for rate in (F('.08'),F('.09'),F('.1')):
                oracle=F(63)/(1+rate)+(F('71.1')+stable/(rate-growth))/(1+rate)**2
                self.assertAlmostEqual(lab.dcf([63,71.1],float(rate),float(stable),float(growth)),float(oracle))

    def test_equity_bridge_disjoint_cash_and_claims(self):
        self.assertEqual(lab.equity_bridge(1000,80,90,280,40,25,15),810)
        self.assertEqual(1000-(280+40-80)+90-25-15,810)
        self.assertNotEqual(1000+80-(280+40-80)+90-25-15,810)
        self.assertAlmostEqual(lab.dcf([20,25],.12,25.75,.03),float(F(20)/F('1.12')+(F(25)+F('25.75')/F('.09'))/F('1.12')**2))

    def test_straight_pathwise_exact_oracle(self):
        rates=[[F('.05')],[F('.08'),F('.04')],[F('.11'),F('.06'),F('.02')]]
        # Enumerate terminal paths and discounted payments, no backward recursion.
        exact=F(0)
        for path in product((0,1),repeat=3):
            denominator=F(1)
            downs=0
            pv=F(0)
            for t in range(3):
                denominator*=1+rates[t][downs]
                pv+=F(106 if t==2 else 6)/denominator
                downs+=path[t]
            exact+=pv/F(8)
        self.assertAlmostEqual(lab.bond_tree([[.05],[.08,.04],[.11,.06,.02]])['price'],float(exact))

    def test_callable_path_cashflows_and_ordering(self):
        rates=[[F('.05')],[F('.08'),F('.04')],[F('.11'),F('.06'),F('.02')]]
        exact=F(0)
        for path in product((0,1),repeat=3):
            d=F(1); downs=0; pv=F(0)
            for t in range(3):
                d*=1+rates[t][downs]
                # Independently identified optimal policy for this one input:
                # redeem at date1 down branch, date2 non-UU branches (tie redeem).
                next_downs=downs+path[t]
                redeem=(t==0 and next_downs==1) or (t==1 and next_downs>=1)
                pv+=F(106 if redeem or t==2 else 6)/d
                if redeem:
                    break
                downs=next_downs
            exact+=pv/F(8)
        r=[[.05],[.08,.04],[.11,.06,.02]]
        price=lab.bond_tree(r,call={1:100,2:100})['price']
        self.assertAlmostEqual(price,float(exact))
        self.assertLess(price,lab.bond_tree(r)['price'])
        self.assertAlmostEqual(lab.bond_tree(r,call={1:1000,2:1000})['price'],lab.bond_tree(r)['price'])
        self.assertLess(lab.bond_tree(r,call={1:90,2:90})['price'],price)
        self.assertAlmostEqual(lab.bond_tree([[.05]],coupon=0)['price'],100/1.05)

    def test_oas_independent_policy_equation(self):
        r=[[.05],[.08,.04],[.11,.06,.02]]
        s=lab.oas(r,99,{1:100,2:100})
        # For s > 0, middle date2 continuation is below100, lower capped100;
        # date1 down is capped100 and up branch is not capped.
        up=(6+53/(1.11+s)+53/(1.06+s))/(1.08+s)
        oracle=(6+.5*up+.5*100)/(1.05+s)
        self.assertAlmostEqual(oracle,99,places=10)
        self.assertGreater(s,0)
        self.assertLess(s,.001)

    def test_credit_terminal_state_oracle_and_cva(self):
        # Disjoint states: D1=.02, S1D2=.0294, S2=.9506, mass sum1.
        probs=[F('.02'),F('.0294'),F('.9506')]
        self.assertEqual(sum(probs),1)
        exact=probs[0]*40/F('1.05')+(probs[1]*40+probs[2]*100)/F('1.05')**2
        result=lab.credit_zero([.02,.03],[40,40],.05)
        self.assertAlmostEqual(result['price'],float(exact))
        loss1=F('.02')*(100/F('1.05')-40)/F('1.05')
        loss2=F('.0294')*60/F('1.05')**2
        self.assertAlmostEqual(result['cva'],float(loss1+loss2))
        self.assertAlmostEqual(result['price']*(1+result['yield'])**2,100)
        self.assertEqual(lab.credit_zero([0,0],[0,0],.05)['cva'],0)
        self.assertAlmostEqual(lab.credit_zero([1],[40],.05)['price'],40/1.05)
        # Earlier recovery of face may exceed a discounted risk-free price:
        # so generic CVA is not assumed positive for every allowed recovery convention.
        self.assertLess(lab.credit_zero([1,0],[100,0],.05)['cva'],0)

    def test_invalid_inputs(self):
        actions=[lambda:lab.ar1(.4,1,3,.3,2),lambda:lab.ar1(.4,.8,3,-1,2),lambda:lab.ar1(.4,.8,3,.3,True),
            lambda:lab.rmse([],[]),lambda:lab.rmse([1],[1,2]),lambda:lab.rmse([True],[1]),lambda:lab.rmse([float('nan')],[1]),
            lambda:lab.ols([1,1,1],[1,2,3]),lambda:lab.df_no_lag([1,2]),lambda:lab.fcff(1,1.1,1,1,1),
            lambda:lab.dcf([1],.03,1,.03),lambda:lab.equity_bridge(1,1,1,-1,1,1,1),
            lambda:lab.bond_tree([[.05],[.08]]),lambda:lab.bond_tree([[-1]]),lambda:lab.bond_tree([[.05],[.08,.04]],call={2:100}),
            lambda:lab.bond_tree([[.05],[.08,.04]],call={True:100}),lambda:lab.oas([[.05],[.08,.04]],999,{1:100}),
            lambda:lab.credit_zero([1.1],[40],.05),lambda:lab.credit_zero([.02],[101],.05),lambda:lab.credit_zero([.02],[],.05)]
        for action in actions:
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    action()


if __name__=='__main__':
    unittest.main()
