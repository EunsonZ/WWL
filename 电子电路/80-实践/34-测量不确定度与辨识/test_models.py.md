---
stage: 1
aliases: []
sources: []
prerequisites: []
---
# test_models.py 源码镜像

源码为真源，此页只镜像，不运行。

<!-- code-sync: 电子电路/80-实践/34-测量不确定度与辨识/test_models.py -->
```python
import math
import random
import unittest
import models as m

class MeasurementTests(unittest.TestCase):
    def test_same_tau_different_current(self):
        for t in [0,.00025,.001,.002]:
            self.assertAlmostEqual(m.step(1000,1e-6,t),m.step(2000,.5e-6,t),places=14)
            self.assertAlmostEqual(m.current(1000,1e-6,t),2*m.current(2000,.5e-6,t),places=14)
        for w in [0,100,1000,10000]:
            self.assertEqual(m.frequency(1000,1e-6,w),m.frequency(2000,.5e-6,w))
    def test_kcl_finite_difference(self):
        for r,c,v0 in [(1000,1e-6,0),(2000,.5e-6,.4)]:
            t=.00025; h=1e-8
            derivative=(m.step(r,c,t+h,v0=v0)-m.step(r,c,t-h,v0=v0))/(2*h)
            self.assertAlmostEqual(c*derivative,m.current(r,c,t,v0=v0),delta=1e-12)
    def test_initial_and_final(self):
        self.assertEqual(m.step(1000,1e-6,0,u=100,v0=-.4),-.4)
        self.assertAlmostEqual(m.step(1000,1e-6,1),1)
        self.assertAlmostEqual(m.step(1000,1e-6,.001,v0=.4),.7792723352971346)
    def test_small_t_retains_initial(self):
        self.assertEqual(m.step(1000,1e-6,1e-30,u=100,v0=.4),.4)
    def test_extra_observation_identifies(self):
        for r,c in [(1000,1e-6),(2000,.5e-6)]:
            rr,cc=m.identify_current(r*c,m.current(r,c,r*c))
            self.assertAlmostEqual(rr,r); self.assertAlmostEqual(cc,c)
            rr,cc=m.identify_impedance(m.input_impedance(r,c,1000),1000)
            self.assertAlmostEqual(rr,r); self.assertAlmostEqual(cc,c)
    def test_jacobian_log_coordinates(self):
        eps=1e-5;r=1000;c=1e-6;t=.0007
        exact=m.sensitivity(r,c,t)
        for k in [0,1]:
            rp,cp=(r*math.exp(eps),c) if k==0 else (r,c*math.exp(eps))
            rm,cm=(r*math.exp(-eps),c) if k==0 else (r,c*math.exp(-eps))
            for row,fn in enumerate([m.step,m.current]):
                numeric=(fn(rp,cp,t)-fn(rm,cm,t))/(2*eps)
                self.assertAlmostEqual(numeric,exact[row][k],delta=1e-10)
    def test_fisher_rank(self):
        f=m.fisher(1000,1e-6,.001)
        self.assertEqual(f[0][0]*f[1][1]-f[0][1]**2,0)
        f=m.fisher(1000,1e-6,.001,include_current=True)
        self.assertGreater(f[0][0]*f[1][1]-f[0][1]**2,0)
    def test_loading(self):
        v,k,tau=m.loaded_step(1000,1e-6,.001,10000)
        self.assertAlmostEqual(k,10/11);self.assertAlmostEqual(tau,1/1100)
        self.assertAlmostEqual(v,(10/11)*(1-math.exp(-1.1)))
        v0,k,tau=m.loaded_step(1000,1e-6,0,10000,v0=.4)
        self.assertEqual(v0,.4)
    def test_tau_derivatives(self):
        t=.001;v=1-1/math.e;u=1
        for k,h in enumerate([1e-8,1e-6,1e-6]):
            p=[t,v,u];n=[t,v,u];p[k]+=h;n[k]-=h
            d=(m.tau_from_crossing(*p)-m.tau_from_crossing(*n))/(2*h)
            self.assertAlmostEqual(d,m.tau_sensitivity(t,v,u)[k],delta=1e-8)
    def test_budget_correlation(self):
        args=(.001,1-1/math.e,1,2e-6,.001,.001)
        a=m.tau_budget(*args,rho=.6);b=m.tau_budget(*args,rho=0)
        self.assertLess(a['uc_s'],b['uc_s'])
        self.assertAlmostEqual(a['uc_s']**2,sum(a['diagonal_s2'])+a['cross_s2'],places=24)
        for rho in [-1,1]: self.assertGreaterEqual(m.tau_budget(*args,rho=rho)['uc_s'],0)
    def test_type_a_mean(self):
        mean,u,df=m.mean_uncertainty([.630,.631,.633,.634])
        self.assertAlmostEqual(mean,.632);self.assertAlmostEqual(u,math.sqrt(10e-6/3)/2);self.assertEqual(df,3)
    def test_mc_reproducible_local_state(self):
        state=random.getstate();args=(.001,1-1/math.e,1,2e-6,.001,.001)
        a=m.mc_tau(*args,rho=.6,samples=2000,seed=23)
        self.assertEqual(a,m.mc_tau(*args,rho=.6,samples=2000,seed=23));self.assertEqual(state,random.getstate())
        self.assertLess(a['q025_s'],.001);self.assertGreater(a['q975_s'],.001)
        self.assertAlmostEqual(a['std_s'],m.tau_budget(*args,rho=.6)['uc_s'],delta=.15e-6)
    def test_mc_failure_restores_global_state(self):
        state=random.getstate()
        with self.assertRaises(ValueError):m.mc_tau(.001,.6,1,100,10,10,samples=100)
        self.assertEqual(state,random.getstate())
    def test_loss_nonunique(self):
        times=[.00025,.0005,.001,.002];ys=[m.step(1000,1e-6,t) for t in times]
        self.assertEqual(m.voltage_loss(1000,1e-6,times,ys),0)
        self.assertEqual(m.voltage_loss(2000,.5e-6,times,ys),0)
    def test_invalid_real_preconversion(self):
        class Coerce:
            def __float__(self):raise AssertionError('must not coerce')
        class FloatSubclass(float):pass
        for bad in [True,1j,float('nan'),float('inf'),Coerce(),FloatSubclass(1000),10**1000]:
            with self.assertRaises(ValueError):m.step(bad,1e-6,.001)
        with self.assertRaises(ValueError):m.tau_budget(.001,.6,1,1e-6,.001,.001,rho=1.1)
        for v in [0,1,2]:
            with self.assertRaises(ValueError):m.tau_from_crossing(.001,v,1)
        with self.assertRaises(ValueError):m.identify_impedance(1000+1000j,1000)
    def test_ill_conditioned_crossing_fails_explicitly(self):
        for v in [5e-324,1e-310]:
            with self.assertRaises(ValueError):m.tau_from_crossing(1e4,v,100)
        with self.assertRaises(ValueError):m.tau_sensitivity(.001,1e-200,1)
        with self.assertRaises(ValueError):m.tau_budget(.001,1e-100,1,100,10,10)
    def test_finite_budgets(self):
        for bad in [99,20001,100.,True]:
            with self.assertRaises(ValueError):m.mc_tau(.001,.6,1,0,0,0,samples=bad)
        with self.assertRaises(ValueError):m.voltage_loss(1000,1e-6,[0]*257,[0]*257)
        with self.assertRaises(ValueError):m.voltage_loss(1000,1e-6,[0],[0,1])

if __name__=='__main__':unittest.main()
```
