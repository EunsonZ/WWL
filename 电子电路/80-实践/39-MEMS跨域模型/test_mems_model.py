import math
import unittest
import mems_model as m

class ModelTests(unittest.TestCase):
    def test_moving_base_sign(self):
        p=m.mechanics(); x=m.displacement(m.G0).real
        self.assertAlmostEqual(p['k']*x,-p['m']*m.G0,places=20)
    def test_displacement_derived_finiteness(self):
        with self.assertRaises(ValueError):m.displacement(1e5,f=1000,zeta=1e-312)
        control=m.displacement(1e5,f=1000,zeta=1e-310)
        self.assertTrue(math.isfinite(control.real) and math.isfinite(control.imag))
        self.assertGreater(control.imag,1e307)
        self.assertLess(control.imag,1.3e307)

    def test_energy_from_original_force(self):
        p=m.mechanics();x=1e-7;v=.001;a=3.;F=1e-9
        dx,dv=m.state_rhs(x,v,a,F)
        self.assertAlmostEqual(p['m']*v*dv+p['k']*x*dx,-p['b']*v*v-p['m']*a*v+F*v,places=20)
    def test_zero_initial_acceleration(self):
        self.assertEqual(m.state_rhs(0,0,3.),(0.,-3.))
    def test_dc_scaling(self):
        self.assertAlmostEqual(m.displacement(1,f0=2000).real/m.displacement(1).real,.25)
    def test_undamped_resonance(self):
        with self.assertRaises(ValueError):m.displacement(1,1000,zeta=0)
    def test_cap_ratio_and_reversal(self):
        for r in [-.4,-.1,0,.1,.4]:
            p=m.capacitors(2e-6*r);q=m.capacitors(-2e-6*r)
            self.assertAlmostEqual(p['ratio'],r);self.assertAlmostEqual(p['plus'],q['minus'],places=24)
    def test_cap_common_parasitic(self):
        p=m.capacitors(.2e-6);q=m.capacitors(.2e-6,parasitic=m.EPS*4e-8/2e-6)
        self.assertLess(q['ratio'],p['ratio']);self.assertEqual(q['difference'],p['difference'])
    def test_contact_rejected(self):
        for x in [2e-6,-2e-6]:
            with self.assertRaises(ValueError):m.capacitors(x)
    def test_bridge_independent_dividers(self):
        d=.075;R=1000.;V=1.8
        va=V*R*(1-d)/(R*(1+d)+R*(1-d));vb=V*R*(1+d)/(R*(1-d)+R*(1+d))
        self.assertAlmostEqual(m.bridge(d,V)['vo'],vb-va)
    def test_beam_from_force(self):
        E=160e9;w=10e-6;t=2e-6;L=200e-6;F=1e-9
        I=w*t**3/12;x=F*L**3/(3*E*I);strain=F*L*t/(2*E*I)
        self.assertAlmostEqual(m.beam_strain(x,L,t),strain,places=20)
    def test_noise_sqrt_bandwidth(self):
        self.assertAlmostEqual(m.thermal(bandwidth=400)['accel_rms']/m.thermal()['accel_rms'],2.)
        p=m.mechanics();self.assertEqual(m.thermal()['equilibrium_x_variance']*p['k'],m.KB*300)
    def test_cross_axis_calibration(self):
        a=3.;at=2.;S=.1;B=.03;cross=.002;y=S*a+B+cross*at
        self.assertAlmostEqual(m.calibrate(y,S,B,cross,at),a)
    def test_feedback_saturation_balance(self):
        p=m.mechanics();K=9*p['k'];lim=2*p['m']*m.G0
        for a in [m.G0,8*m.G0,-8*m.G0]:
            r=m.feedback_static(a,K,lim);self.assertAlmostEqual(p['k']*r['x']+p['m']*a,r['force'],places=20)
            self.assertLessEqual(abs(r['force']),lim)
        self.assertAlmostEqual(m.feedback_static(m.G0,K,lim)['estimate']/m.G0,.9)
    def test_rectification_average(self):
        A=2*m.G0;q=.001;N=1000
        actual=math.fsum(q*(A*math.sin(2*math.pi*j/N))**2 for j in range(N))/N
        self.assertAlmostEqual(actual,m.vibration_bias(A,q))
    def test_invalid_before_conversion(self):
        class FloatOnly:
            def __float__(self):raise AssertionError('must not convert')
        for bad in [True,'1',1+0j,float('nan'),float('inf'),FloatOnly()]:
            with self.assertRaises(ValueError):m.capacitors(bad)
        for bad in [0,-1,1e99]:
            with self.assertRaises(ValueError):m.mechanics(m=bad)
    def test_calibration_output_overflow(self):
        with self.assertRaises(ValueError):m.calibrate(100,5e-324)

    def test_zero_scale_and_budget(self):
        with self.assertRaises(ValueError):m.calibrate(1,0)
        with self.assertRaises(ValueError):m.beam_strain(.1)
        with self.assertRaises(ValueError):m.thermal(bandwidth=1e99)

if __name__=='__main__':unittest.main()
