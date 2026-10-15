import math
import unittest
import numpy as np
from quant_portfolio_lab import twr,npv,irr_bracket,regression,portfolio,constrained_minimum,example

class QuantLabTests(unittest.TestCase):
    def test_cash_ledger_unitization(self):
        units,nav=100.,1.
        nav*=1.09; units+=100/nav
        nav*=187/209; units-=30/nav
        nav*=179/157
        self.assertAlmostEqual(units*nav,179,places=10)
        self.assertAlmostEqual(example()['net_twr'],nav-1,places=12)
        self.assertAlmostEqual(example()['gross_twr'],1.1*.9*1.15-1)
    def test_irregular_root_and_multiple(self):
        r=example()['mwr']
        self.assertAlmostEqual(npv(r,(0,.5,1,2),(-100,-100,30,179)),0,places=8)
        for lo,hi,want in ((.05,.15,.1),(.15,.25,.2)):
            self.assertAlmostEqual(irr_bracket((0,1,2),(-100,230,-132),lo,hi),want,places=10)
        with self.assertRaises(ValueError): irr_bracket((0,1,2),(-100,230,-132),0,.3)
        with self.assertRaises(ValueError): irr_bracket((0,1,2),(-100,100,-100),-.9,10)
    def test_regression_independent_matrix(self):
        x=np.array([-2,-1,0,1,2,3.]); y=np.array([-1,0,0,2,3,3.]); X=np.column_stack((np.ones(6),x))
        coef=np.linalg.lstsq(X,y,rcond=None)[0]; out=regression(x,y)
        np.testing.assert_allclose(coef,[out['intercept'],out['slope']],atol=1e-12)
        np.testing.assert_allclose(X.T@(y-X@coef),[0,0],atol=1e-12)
        self.assertAlmostEqual(out['sse']+out['ssr'],out['sst'])
        self.assertAlmostEqual(out['f'],out['t']**2)
    def test_portfolio_finite_states(self):
        states=[(.1+.2*u,.06+.02*u+math.sqrt(.0096)*v) for u in (-1,1) for v in (-1,1)]
        for w in (0,1/7,.5,1):
            rs=[w*a+(1-w)*b for a,b in states]; mean=sum(rs)/4
            self.assertAlmostEqual(portfolio(w)[0],mean)
            self.assertAlmostEqual(portfolio(w)[1],math.sqrt(sum((r-mean)**2 for r in rs)/4))
    def test_constraint_enumeration(self):
        for target in (.06,.065,.07,.08,.084):
            out=constrained_minimum(target)
            feasible=[portfolio(i/10000)[1] for i in range(6001) if portfolio(i/10000)[0]>=target-1e-14]
            self.assertLessEqual(out['sigma'],min(feasible)+1e-12)
            self.assertLessEqual(min(feasible)-out['sigma'],1e-5)
        with self.assertRaises(ValueError): constrained_minimum(.085)
    def test_tangency_and_tiny_covariance(self):
        cov=np.array([[.04,.004],[.004,.01]])
        direction=np.linalg.solve(cov,np.array([.08,.04]))
        self.assertAlmostEqual((direction/direction.sum())[0],1/3)
        mt,st=portfolio(1/3)
        best=max((portfolio(i/10000)[0]-.02)/portfolio(i/10000)[1] for i in range(10001))
        self.assertLessEqual(best,(mt-.02)/st+1e-12)
        self.assertAlmostEqual(portfolio(.5,cov=((1e-24,0),(0,1e-24)))[1],math.sqrt(5e-25))
        with self.assertRaises(ValueError): portfolio(.5,cov=((1e-24,2e-24),(2e-24,1e-24)))
    def test_invalid_and_termination(self):
        calls=(lambda:twr([],[]),lambda:twr([0],[1]),lambda:twr([1],[float('nan')]),lambda:npv(-1,[0,1],[-1,2]),lambda:npv(.1,[0,0],[-1,2]),lambda:regression([1,1,1],[1,2,3]),lambda:regression([1,2,3],[2,4,6]),lambda:portfolio(float('inf')),lambda:portfolio(.5,cov=((1,2),(2,1))),lambda:irr_bracket([0,1],[-1,2],0,2,tol=0))
        for call in calls:
            with self.assertRaises(ValueError): call()
        with self.assertRaises(RuntimeError): irr_bracket([0,1],[-1,2],0,3,iterations=1)

if __name__=='__main__': unittest.main()
