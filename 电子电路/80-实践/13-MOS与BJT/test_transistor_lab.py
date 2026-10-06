import math
import unittest
import transistor_lab as t

class Models(unittest.TestCase):
    def test_dc_invalid_before_cast(self):
        for value in [1j,1+0j,float('nan'),float('inf'),True,'1',[1]]:
            with self.subTest(value=value),self.assertRaises(ValueError):t.mos(value,1)
        for value in [-1,1j,float('nan')]:
            with self.assertRaises(ValueError):t.ac_gain(value)
    def test_output_overflow_rejected(self):
        with self.assertRaises(ValueError):t.mos(1e200,1e200,k=1e200)
        with self.assertRaises(ValueError):t.ebers(1,0,is_=1e300)
        with self.assertRaises(ValueError):t.ac_gain(1e308)

    def test_mos_integral(self):
        # Separate midpoint integration of local channel-charge polynomial.
        n=10000;vd=.3;ov=1
        integ=sum((ov-(j+.5)*vd/n)*vd/n for j in range(n))
        self.assertAlmostEqual(t.mos(1.5,vd,lam=0)['id'],.002*integ,places=12)
    def test_regions_limits(self):
        self.assertEqual(t.mos(.2,3)['region'],'cutoff')
        self.assertEqual(t.mos(1.5,0)['id'],0)
        self.assertAlmostEqual(t.mos(1.5,1-1e-9)['id'],t.mos(1.5,1+1e-9)['id'],places=10)
    def test_partial_difference(self):
        h=1e-6;vg=1.5;vd=3;vsb=.2;m=t.mos(vg,vd,vsb)
        for field,x in [('gm',0),('gds',1),('gmb',2)]:
            a=[vg,vd,vsb];b=a[:];a[x]+=h;b[x]-=h
            derivative=(t.mos(*a)['id']-t.mos(*b)['id'])/(2*h)
            if x==2:derivative=-derivative
            self.assertAlmostEqual(m[field],derivative,places=10)
    def test_bias_algebra(self):
        q=t.bias(1.5,lam=0)
        self.assertAlmostEqual(q['vd'],3,places=8)
        self.assertAlmostEqual(q['id'],.001,places=12)
        q=t.bias(1.5,lam=.02)
        # In sat: (5-d)/2000=.001*(1+.02*d), an independent closed form.
        self.assertAlmostEqual(q['vd'],3/1.04,places=8)
    def test_failure_budget(self):
        with self.assertRaises(RuntimeError):t.bias(1.5,max_iter=1,tol=1e-30)
        with self.assertRaises(RuntimeError):t.bias(1.12,max_iter=100,tol=1e-40)
        with self.assertRaises(ValueError):t.bias(1.5,max_iter=True)
    def test_body_off(self):
        self.assertEqual(t.mos(1.5,3,gamma=0)['gmb'],0)
        self.assertGreater(t.threshold(.2),t.threshold(0))
    def test_ebers_kcl_and_reciprocity(self):
        for be,bc in [(.7,-2.3),(-.2,.5),(.7,.5),(-.2,-.3),(0,0)]:
            r=t.ebers(be,bc);self.assertAlmostEqual(sum(r.values()),0,places=12)
        a=t.ebers(.3,-.1,beta_f=10,beta_r=10)
        b=t.ebers(-.1,.3,beta_f=10,beta_r=10)
        self.assertAlmostEqual(a['ic'],b['ie'],places=12)
    def test_bjt_beta_forward(self):
        r=t.ebers(.7,-2.3);self.assertAlmostEqual(r['ic']/r['ib'],100,places=7)
    def test_moscap_derivative(self):
        p=.3;h=1e-6;a=t.moscap(p+h);b=t.moscap(p-h)
        numerical=-(a['qd']-b['qd'])/(a['vgb']-b['vgb'])
        self.assertAlmostEqual(t.moscap(p)['c'],numerical,places=11)
    def test_weak_slope_difference(self):
        m=t.weak(.4,.2);h=1e-6
        derivative=(t.weak(.4+h,.2)['id']-t.weak(.4-h,.2)['id'])/(2*h)
        self.assertAlmostEqual(m['gm'],derivative,places=13)
        self.assertAlmostEqual(t.weak(.4,0)['id'],0)
        self.assertAlmostEqual(t.weak(.3,.4)['id']/t.weak(.3+.039*math.log(10),.4)['id'],.1,places=8)
    def test_dibl_derivative(self):
        h=1e-6;m=t.weak(.3,.5,dibl=.08)
        d=(t.weak(.3,.5+h,dibl=.08)['id']-t.weak(.3,.5-h,dibl=.08)['id'])/(2*h)
        self.assertAlmostEqual(m['gds'],d,places=12)
    def test_source_gain_large_finite_decimal(self):
        from decimal import Decimal, localcontext
        with localcontext() as context:
            context.prec=80
            gm=Decimal('1e200'); rs=Decimal('1e200')
            gd=1/Decimal(2000)+1/Decimal(10000)
            expected=float(-gm/(gd+gd*rs*gm))
        actual=t.source_gain(gm=1e200,gmb=0,go=0,rsource=1e200)
        self.assertNotEqual(actual,0.)
        self.assertLess(abs(actual/expected-1),2e-15)
        with self.assertRaises(ValueError):
            t.source_gain(gm=1e308,gmb=0,go=0,rd=1e-308,rl=1e-308,rsource=1e308)

    def test_body_network_independent_kcl(self):
        import numpy as np
        gm=.002;gb=.0005;go=.00002;gd=1/2000+1/10000;rs=100
        # Unknowns drain/source. Each controlled branch contributes opposite KCL rows.
        matrix=np.array([[gd+go,-(go+gm+gb)],[-go,1/rs+go+gm+gb]])
        vd,vs=np.linalg.solve(matrix,np.array([-gm,gm]))
        self.assertAlmostEqual(t.source_gain(gm=gm,gmb=gb,go=go,rsource=rs),vd,places=12)
        self.assertAlmostEqual(vs/rs,-gd*vd,places=12)
        self.assertAlmostEqual(t.source_gain(go=0,rsource=0),-gm/gd,places=12)

    def test_ac_independent_elimination(self):
        f=1e5;s=complex(0,2*math.pi*f)
        yout=1/2000+1/10000+s*12e-12
        local=-(.002-s*2e-12)/yout
        vg=(1/10000)/(1/10000+s*20e-12+s*2e-12*(1-local))
        self.assertAlmostEqual(abs(t.ac_gain(f)-local*vg),0,places=12)
        self.assertAlmostEqual(t.ac_gain(0).real,-.002/(1/2000+1/10000))
        self.assertEqual(t.ac_gain(0).imag,0)

if __name__=='__main__':unittest.main()
