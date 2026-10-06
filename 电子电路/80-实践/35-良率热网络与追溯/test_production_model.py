"""Finite author regressions: different oracles, not independent acceptance."""
import math
import unittest
from production_model import (poisson_yield, accepted_bad, zero_failure_upper,
    mismatch_mc, thermal_rhs, thermal_trace, thermal_grid, arrhenius_factor,
    affected_serials, real)


class ModelTests(unittest.TestCase):
    def test_yield_and_zero_limits(self):
        self.assertAlmostEqual(poisson_yield(1e-4,1000), .9048374180359595, places=14)
        self.assertEqual(poisson_yield(0,1e12),1)
        self.assertLess(poisson_yield(2e-4,1000),poisson_yield(1e-4,1000))
        self.assertAlmostEqual(poisson_yield(2e-4,1000),poisson_yield(1e-4,1000)**2)

    def test_bayes_by_100000_item_count(self):
        # 98000 good: 97020 passed. 2000 bad: 200 passed.
        self.assertAlmostEqual(accepted_bad(.02,.9,.01),200/97220)
        self.assertEqual(accepted_bad(0,.5,.1),0)
        self.assertEqual(accepted_bad(1,.5,.1),1)
        with self.assertRaises(ValueError): accepted_bad(.5,1,1)

    def test_zero_failure_inversion(self):
        upper=zero_failure_upper(100)
        self.assertAlmostEqual((1-upper)**100,.05,places=13)
        self.assertGreater(upper,.001)
        self.assertLess(zero_failure_upper(1000),upper)

    def test_mc_moments_and_shared_component(self):
        a=mismatch_mc(50000,2403,.03,.01,.02)
        b=mismatch_mc(50000,2403,.06,.01,.02)
        self.assertEqual(a['variance_difference'],b['variance_difference'])
        self.assertEqual(a['passed'],b['passed'])
        self.assertAlmostEqual(a['variance_difference'],.0002,delta=.000006)
        self.assertAlmostEqual(a['variance_average'],.00095,delta=.00003)
        self.assertAlmostEqual(a['fraction'],math.erf(1),delta=.012)
        self.assertEqual(mismatch_mc(20,5,.03,0,0)['fraction'],1)

    def test_thermal_energy_identity(self):
        for j,b,g in [(0,0,0),(4,3.2,0),(8,3,.002),(-2,1,0)]:
            dj,db=thermal_rhs(j,b,.2,g)
            self.assertAlmostEqual(2*dj+8*db,.2+g*j-j/100-b/20,places=14)
        self.assertAlmostEqual(thermal_rhs(4,3.2)[0],0,places=14)
        self.assertAlmostEqual(thermal_rhs(4,3.2)[1],0,places=14)

    def test_rk4_against_two_exponentials(self):
        # Analytic characteristic roots; no stepping or reuse of RHS.
        for g in (0,.002,.04):
            aa,bb,cc,dd=-.105+g/2,.1,.025,-.03125
            gap=math.sqrt((aa-dd)**2+4*bb*cc)
            l1,l2=(aa+dd+gap)/2,(aa+dd-gap)/2
            js=.2/(.05-g); bs=.8*js
            for end in (.1,5,100):
                actual=thermal_trace(end,.1,.2,g)[-1]
                expected=[]
                for steady,velocity in ((js,.1),(bs,0)):
                    a=(velocity+l2*steady)/(l1-l2)
                    b=-steady-a
                    expected.append(steady+a*math.exp(l1*end)+b*math.exp(l2*end))
                for got,want in zip(actual[1:],expected):
                    self.assertAlmostEqual(got,want,delta=2e-9)
        self.assertEqual(thermal_trace(0),[(0.,0.,0.)])
        tiny=thermal_trace(1e-12)[-1]
        self.assertGreater(tiny[1],0); self.assertGreater(tiny[2],0)
        self.assertAlmostEqual(tiny[1]/1e-12,.1,delta=1e-13)
        self.assertEqual(thermal_trace(2,power_W=0)[-1][1:],(0.,0.))

    def test_grid_against_discrete_sine_inverse(self):
        r=thermal_grid()
        for x,y in ((4,4),(1,1),(2,6),(7,4)):
            value=0.
            for m in range(1,8):
                for n in range(1,8):
                    wave=math.sin(x*m*math.pi/8)*math.sin(y*n*math.pi/8)
                    source=math.sin(4*m*math.pi/8)*math.sin(4*n*math.pi/8)
                    lam=4-2*math.cos(m*math.pi/8)-2*math.cos(n*math.pi/8)
                    value += 4/64*.2/.1*wave*source/lam
            self.assertAlmostEqual(r['theta_K'][y][x],value,delta=2e-8)
        self.assertAlmostEqual(r['boundary_flux_W'],.2,delta=6e-9)
        self.assertLessEqual(r['max_residual_W'],1e-10)
        self.assertEqual(thermal_grid(0)['boundary_flux_W'],0)

    def test_arrhenius_reciprocal_and_no_absolute_life(self):
        af=arrhenius_factor(.5,300,350)
        self.assertAlmostEqual(math.log(af),.5/(8.617333262e-5)*50/(300*350))
        self.assertAlmostEqual(af*arrhenius_factor(.5,350,300),1)
        self.assertEqual(arrhenius_factor(0,300,350),1)
        with self.assertRaises(ValueError): arrhenius_factor(5,1,5000)

    def test_trace_by_original_installed_lot(self):
        rows=[{'serial':'U002','bom':'A','lot':'Y'},
              {'serial':'U001','bom':'A','lot':'X'},
              {'serial':'U003','bom':'B','lot':'Z'}]
        snapshot=[r.copy() for r in rows]
        self.assertEqual(affected_serials(rows,'X'),['U001'])
        self.assertEqual(rows,snapshot)
        self.assertEqual(affected_serials(rows,'missing'),[])
        with self.assertRaises(ValueError): affected_serials(rows+[rows[0]],'X')

    def test_scalar_and_budget_rejections(self):
        for x in (True,1j,float('nan'),float('inf'),10**10000,[],None):
            with self.subTest(x=type(x).__name__):
                with self.assertRaises(ValueError): real('x',x,0,1)
        for fn in (lambda: mismatch_mc(True),lambda: mismatch_mc(100001),
                   lambda: mismatch_mc(20,True),lambda: poisson_yield(-1,5),
                   lambda: accepted_bad(.2,1.01,.2),lambda: zero_failure_upper(0),
                   lambda: thermal_trace(201),lambda: thermal_trace(200,1e-5),
                   lambda: thermal_trace(2,.2),lambda: thermal_rhs(0,0,.2,.05),
                   lambda: thermal_grid(.2,1e-20)):
            with self.assertRaises(ValueError): fn()


if __name__=='__main__':
    unittest.main()
