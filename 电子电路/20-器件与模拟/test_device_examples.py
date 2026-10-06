"""Behavioral checks: analytic roots, derivatives, model/domain boundaries."""
import math
import unittest
import device_examples as m

class DeviceTests(unittest.TestCase):
    def test_diode_kcl_and_unique_bracket(self):
        for vs,r in [(0,1),(3,2200),(5,4700),(100,10000)]:
            q=m.diode_bias(vs,r)
            self.assertLess(abs(q['kcl_A']),1e-12)
            self.assertLessEqual(q['voltage'],vs+1e-12)
            self.assertAlmostEqual(m.diode_current(q['voltage']),q['current'],places=12)
    def test_diode_slope_not_dc_ratio(self):
        q=m.diode_bias(5,4700); h=1e-7
        derivative=(m.diode_current(q['voltage']+h)-m.diode_current(q['voltage']-h))/(2*h)
        self.assertAlmostEqual(derivative,1/q['rd'],places=8)
        self.assertGreater(q['voltage']/q['current'],10*q['rd'])
    def test_mos_regions_and_continuity_without_clm(self):
        self.assertEqual(m.mos_current(-1,2),0)
        self.assertAlmostEqual(m.mos_current(1,1-1e-8,lam=0),m.mos_current(1,1,lam=0),places=10)
        self.assertLess(m.mos_current(1,.5),m.mos_current(1,1,lam=0))
        self.assertAlmostEqual(m.mos_current(1,1-1e-8),m.mos_current(1,1),places=10)
    def test_mos_derivatives_inside_regions(self):
        for u,d in [(1,.4),(1,2)]:
            gm,go=m.mos_small(u,d); h=1e-6
            self.assertAlmostEqual((m.mos_current(u+h,d)-m.mos_current(u-h,d))/(2*h),gm,places=9)
            self.assertAlmostEqual((m.mos_current(u,d+h)-m.mos_current(u,d-h))/(2*h),go,places=9)
    def test_bias_residual_and_invalid_saturation(self):
        q=m.mos_bias(5,2000,1)
        self.assertAlmostEqual(q['current'],.0011/1.04)
        self.assertLess(abs(q['kcl_A']),1e-14)
        self.assertEqual(m.mos_bias(5,2000,1,lam=0)['ro'],math.inf)
        with self.assertRaises(ValueError): m.mos_bias(1,2000,1)
    def test_bjt_units(self):
        gm,rpi,ro=m.bjt_small(.001,100,.026,100,2)
        self.assertAlmostEqual(gm*rpi,100); self.assertEqual(ro,102000)
    def test_opamp_distinct_limits(self):
        q=m.opamp(20000,2e6,20,20000,2,1e6)
        self.assertTrue(q['sr_ok']); self.assertLess(q['normalized_magnitude'],.99)
        self.assertFalse(m.opamp(1e5,1e6,10,50000,2,.5e6)['sr_ok'])
        self.assertAlmostEqual(m.opamp(1e5,1e6,10,0,0,.5e6)['normalized_magnitude'],1)
    def test_periodic_mean_charge_and_review_counterexample(self):
        # Independent equally spaced periodic quadrature; sin and sin^2 means
        # come from discrete trigonometric sums, not author mean formulas.
        n=256; currents=[]; voltages=[]; loads=[]; old_loads=[]
        for j in range(n):
            phase=2*math.pi*j/n
            q=m.mos_periodic_candidate(.35,phase)
            self.assertTrue(q['instantaneous_saturation_ok'])
            self.assertLess(abs(q['kcl_A']),1e-15)
            currents.append(q['current']); voltages.append(q['vd']); loads.append(q['load_current'])
            old_v=3-(5000/3)*.001*((1+.35*math.sin(phase))**2-1)
            old_loads.append((old_v-3)/10000)
        self.assertAlmostEqual(sum(currents)/n,.00106125,places=12)
        self.assertAlmostEqual(sum(voltages)/n,2.8775,places=12)
        self.assertLess(abs(sum(loads)/n),1e-15)  # integral / period = 0
        self.assertAlmostEqual(sum(old_loads)/n,-10.2083333333333e-6,places=12)
        self.assertAlmostEqual(m.mos_periodic_candidate(.35,math.pi/2)['vd'],1.60875,places=12)
    def test_finite_c_periodic_state_equation(self):
        # Numerical derivative verifies physical C*dVc/dt = IL. Take omega=1,
        # C=x/(RD+RL). Phase derivative then equals time derivative.
        for x in [2.,1000.]:
            for phase in [.2,1.7,4.4]:
                h=1e-5; q=m.mos_periodic_candidate(.1,phase,coupling_x=x)
                plus=m.mos_periodic_candidate(.1,phase+h,coupling_x=x)
                minus=m.mos_periodic_candidate(.1,phase-h,coupling_x=x)
                c=x/12000
                self.assertAlmostEqual(c*(plus['vc']-minus['vc'])/(2*h),q['load_current'],places=11)
                repeat=m.mos_periodic_candidate(.1,phase+2*math.pi,coupling_x=x)
                self.assertAlmostEqual(q['vc'],repeat['vc'],places=12)
            loads=[m.mos_periodic_candidate(.1,2*math.pi*j/128,coupling_x=x)['load_current'] for j in range(128)]
            self.assertLess(abs(sum(loads)/128),1e-15)
        q=m.mos_periodic_candidate(.35,1.1,coupling_x=1e6)
        ideal=m.mos_periodic_candidate(.35,1.1)
        self.assertLess(abs(q['vd']-ideal['vd']),1e-6)
    def test_periodic_work_region_boundary_and_transfer(self):
        for rd,rl in [(2000.,10000.),(3000.,6000.)]:
            boundary=m.mos_periodic_boundary(rd=rd,rl=rl)
            self.assertAlmostEqual(m.mos_periodic_candidate(boundary,math.pi/2,rd=rd,rl=rl)['saturation_margin'],0,places=12)
            for j in range(128):
                self.assertTrue(m.mos_periodic_candidate(boundary-1e-5,2*math.pi*j/128,rd=rd,rl=rl)['instantaneous_saturation_ok'])
            self.assertFalse(m.mos_periodic_candidate(boundary+1e-5,math.pi/2,rd=rd,rl=rl)['instantaneous_saturation_ok'])
        self.assertAlmostEqual(m.mos_periodic_boundary(),(-26+math.sqrt(1204))/22,places=12)
        self.assertAlmostEqual(m.mos_periodic_boundary(rd=3000,rl=6000),(-5+math.sqrt(35))/5,places=12)
        q=m.mos_periodic_candidate(.5,math.pi/2,rd=3000,rl=6000)
        self.assertAlmostEqual(q['mean_vd'],1.625)
        self.assertAlmostEqual(q['vd'],-.625)
        self.assertFalse(q['instantaneous_saturation_ok'])
        with self.assertRaises(ValueError): m.mos_periodic_candidate(.1,1,coupling_x=0)
        with self.assertRaises(ValueError): m.mos_periodic_boundary(vs=1)

    def test_invalid_inputs(self):
        for bad in [math.nan,math.inf,True,'1',complex(1,0)]:
            with self.assertRaises(ValueError): m.diode_current(bad)
        for action in [lambda:m.diode_bias(5,0),lambda:m.diode_current(1,vt=0),lambda:m.mos_current(1,-1),lambda:m.mos_current(1,2,lam=-1),lambda:m.bjt_small(0,100,.026,100,2),lambda:m.opamp(1e5,1e6,.5,1,1,1),lambda:m.diode_current(1e6)]:
            with self.assertRaises(ValueError): action()

if __name__=='__main__': unittest.main()
