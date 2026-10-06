import unittest, math, importlib.util, pathlib, subprocess, sys, tempfile
from models import *
class Models(unittest.TestCase):
    def test_invalid(self):
        for x in (True,1j,[],{},float('nan'),float('inf'),10**1000):
            with self.assertRaises(ValueError): triple_poles(x)
    def test_characteristic_independent(self):
        for k in (0,1,7.9,8,20):
            for z in triple_poles(k): self.assertLess(abs((z+1)**3+k),1e-11)
    def test_boundary(self):
        self.assertAlmostEqual(triple_poles(8)[1].real,0)
        self.assertAlmostEqual(triple_poles(8)[1].imag,math.sqrt(3))
        self.assertLess(max(z.real for z in triple_poles(7)),0)
        self.assertGreater(max(z.real for z in triple_poles(9)),0)
        self.assertEqual(triple_routh(8)[2],0)
    def test_injection_original_equations(self):
        for r,di,do,n in ((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1),(2,-3,4,5)):
            v=injection(2,3,r,di,do,n)
            self.assertAlmostEqual(v['u'],3*(r-v['y']-n))
            self.assertAlmostEqual(v['y'],2*(v['u']+di)+do)
    def test_sensitivity_finite(self):
        delta=.2; old=injection(2,3,r=1); new=injection(2*(1+delta),3,r=1)
        self.assertAlmostEqual(new['y']/old['y']-1,delta*old['S']/(1+old['T']*delta))
    def test_lead_nodal(self):
        for w in (0,100,1e5):
            rf,rg,cf=90000,10000,1e-9
            zf=rf/(1+1j*w*rf*cf)
            self.assertAlmostEqual(abs(lead_beta(rf,rg,cf,w)-rg/(rg+zf)),0)
    def test_isolation_kcl(self):
        for w in (0,1e3,1e6):
            h=isolated_load(100,1000,1e-6,w)
            self.assertLess(abs((1-h)/100-h/1000-1j*w*1e-6*h),1e-15)
    def test_wien_impedances(self):
        r,c=10000,1e-8; w=1/(r*c)
        zp=1/(1/r+1j*w*c); zs=r+1/(1j*w*c)
        self.assertLess(abs(wien_beta(r,c,w)-zp/(zp+zs)),1e-15)
        self.assertAlmostEqual(wien_beta(r,c,w).real,1/3)
    def test_radius_ode_and_limits(self):
        for mu in (-2,0,2):
            t=.2; h=1e-5; r=radius(t,.3,mu,2)
            derivative=(radius(t+h,.3,mu,2)-radius(t-h,.3,mu,2))/(2*h)
            self.assertAlmostEqual(derivative,mu*r-2*r**3,places=8)
        self.assertEqual(radius(1,0,2,2),0)
        self.assertAlmostEqual(radius(10,.1,2,2),1,places=8)
        with self.assertRaises(ValueError): radius(100,1,100,1)
        with self.assertRaises(ValueError): radius(1,1,1e-300,1)
        with self.assertRaises(ValueError): radius(1,1e-300,1,1)
    def test_nested_trace_det(self):
        roots=nested_poles(1,1,2,2)
        self.assertAlmostEqual((roots[0]+roots[1]).real,-2)
        self.assertAlmostEqual((roots[0]*roots[1]).real,-3)
        self.assertEqual(set(round(z.real) for z in roots),{-3,1})
    def test_delay_original_characteristic(self):
        v=delay_limit(2,1000); w=v['omega_c']; tau=v['tau_critical']
        self.assertLess(abs(1+1j*w/1000+2*complex(math.cos(w*tau),-math.sin(w*tau))),1e-14)
        roots=delay_phase_crossings(1000,.001,30000)
        self.assertGreater(len(roots),1)
        for m,w in enumerate(roots): self.assertAlmostEqual(math.atan(w/1000)+w*.001,(2*m+1)*math.pi)
        with self.assertRaises(ValueError): delay_phase_crossings(1,10,1e9)
    def test_robust_exact(self):
        self.assertAlmostEqual(robust_onepole(9,.2),.18)
        self.assertGreater(robust_onepole(9,2),1)
    def test_step_independent_rk4(self):
        for k in (1,8,20):
            z=[0.,0.,0.]; h=.0005
            def f(v): return [k*(1-v[2])-v[0],v[0]-v[1],v[1]-v[2]]
            for _ in range(4000):
                a=f(z); b=f([z[i]+h*a[i]/2 for i in range(3)])
                c=f([z[i]+h*b[i]/2 for i in range(3)]); d=f([z[i]+h*c[i] for i in range(3)])
                z=[z[i]+h*(a[i]+2*b[i]+2*c[i]+d[i])/6 for i in range(3)]
            self.assertAlmostEqual(z[2],triple_step(k,2),places=9)
        with self.assertRaises(ValueError): triple_step(1,1e-20)
    def test_step_physical_time_scaling(self):
        for k in (1,8,20):
            for p in (.5,1000):
                with self.subTest(k=k,p=p):
                    self.assertAlmostEqual(triple_step(k,2/p,p),triple_step(k,2),places=10)
        self.assertAlmostEqual(triple_step(1,.002,1000),.3069960619144711,places=12)
    def test_step_original_physical_ode(self):
        for k in (1,8,20):
            for p in (.5,1000):
                z=[0.,0.,0.]; h=2/p/4000
                def f(v): return [p*(k*(1-v[2])-v[0]),p*(v[0]-v[1]),p*(v[1]-v[2])]
                for _ in range(4000):
                    a=f(z); b=f([z[i]+h*a[i]/2 for i in range(3)])
                    c=f([z[i]+h*b[i]/2 for i in range(3)]); d=f([z[i]+h*c[i] for i in range(3)])
                    z=[z[i]+h*(a[i]+2*b[i]+2*c[i]+d[i])/6 for i in range(3)]
                with self.subTest(k=k,p=p):
                    self.assertAlmostEqual(z[2],triple_step(k,2/p,p),places=9)
    def test_pure_import(self):
        source=pathlib.Path(__file__).with_name('models.py')
        code="import sys,runpy;sys.argv=['models.py','--bad'];runpy.run_path("+repr(str(source))+");assert 'matplotlib' not in sys.modules;assert 'numpy' not in sys.modules"
        r=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        builder=source.with_name('build.py')
        code="import sys,runpy;sys.argv=['build.py','--bad'];sys.path.insert(0,"+repr(str(source.parent))+");runpy.run_path("+repr(str(builder))+");assert 'matplotlib' not in sys.modules;assert 'numpy' not in sys.modules"
        r=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        r=subprocess.run([sys.executable,'-B',str(builder)],capture_output=True,text=True)
        self.assertEqual(r.returncode,2)
if __name__=='__main__': unittest.main()
