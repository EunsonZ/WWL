"""Behavioral tests of units, integration, stability and failed specifications."""
import unittest
import math
from dataclasses import replace
import frontend_budget as m

class FrontendTests(unittest.TestCase):
    def test_psd_units_and_temperature_scaling(self):
        self.assertAlmostEqual(m.thermal_psd(2000,300),3.3135576e-17,places=28)
        self.assertAlmostEqual(m.thermal_psd(2000,600)/m.thermal_psd(2000,300),2)
        self.assertAlmostEqual(m.shot_psd(1e-6),3.204353268e-25,places=35)
        one=m.thermal_psd(1000,300)*1000
        two=2*(m.thermal_psd(1000,300)/2)*1000
        self.assertEqual(one,two)
    def test_integral_against_independent_closed_forms(self):
        expected=m.rectangular_variance(1.2e-16,2e-15,.1,10000)
        actual=m.integrate_log(lambda f:1.2e-16+2e-15/f,.1,10000,n=4096)
        self.assertLess(abs(actual/expected-1),1e-10)
        fc=1000.;lo=.1;hi=1e6
        exact=fc*(math.atan(hi/fc)-math.atan(lo/fc))
        self.assertLess(abs(m.integrate_log(lambda f:1/(1+(f/fc)**2),lo,hi)/exact-1),1e-10)
    def test_correlated_noise_cannot_default_to_zero(self):
        self.assertAlmostEqual(m.correlated_psd(4,9,0),13)
        self.assertAlmostEqual(m.correlated_psd(4,9,1),25)
        self.assertAlmostEqual(m.correlated_psd(4,9,-1),1)
        self.assertEqual(m.correlated_psd(4,4,1,1,-1),0)
        with self.assertRaises(ValueError):m.correlated_psd(4,9,1.01)
        self.assertEqual(m.correlated_psd(1e200,1e200,0),2e200)
        self.assertEqual(m.correlated_psd(1e200,1e200,-.5),1e200)
        self.assertEqual(m.correlated_psd(1e-200,1e-200,1),4e-200)
    def test_reference_and_finite_a_dc(self):
        v=m.noninverting_dc(1.65,1.65,1000,1e5)
        self.assertAlmostEqual(v,1.65*100000/101000,places=12)
        self.assertLess(v,2.)  # not 1650 V
        h=1e-6
        slope=(m.noninverting_dc(1.65+h,1.65,20,1e6)-m.noninverting_dc(1.65-h,1.65,20,1e6))/(2*h)
        self.assertAlmostEqual(slope,1e6/(1+1e6/20),places=6)
    def test_one_two_three_pole_counterexample(self):
        results=[m.loop_metrics(20,[1000]*n) for n in [1,2,3]]
        self.assertEqual([q['stable'] for q in results],[True,True,False])
        self.assertAlmostEqual(results[1]['crossover_hz'],1000*math.sqrt(19),places=8)
        self.assertAlmostEqual(results[2]['gain_margin_ratio'],.4,places=12)
        # Independent analytic cubic roots: x=-1 + cube roots of -T0.
        positive_real=-1+20**(1/3)*math.cos(math.pi/3)
        self.assertGreater(positive_real,0)
        self.assertFalse(m.loop_metrics(8,[1000]*3)['stable'])
        self.assertTrue(m.loop_metrics(7.9,[1000]*3)['stable'])
        self.assertIsNone(m.loop_metrics(.5,[1000])['phase_margin_deg'])
    def test_unequal_pole_routh_against_eigenvalues(self):
        import numpy as np
        for poles in [[100,2000,30000],[1000,1200,1700],[2,100,500]]:
            for t0 in [2,8,20,100]:
                # Form normalized characteristic polynomial by multiplying roots
                # in an independent polynomial library, then add loop DC numerator.
                poly=np.poly([-p/poles[0] for p in poles]);poly/=poly[-1];poly[-1]+=t0
                expected=bool(np.all(np.real(np.roots(poly))<0))
                self.assertEqual(m.loop_metrics(t0,poles)['stable'],expected)
    def test_rc_half_lsb_and_scale(self):
        eps=m.half_lsb(3.3,16);required=200*20e-12*math.log(3.3/eps)
        self.assertAlmostEqual(m.settling_error(3.3,200,20e-12,required),eps,places=16)
        self.assertAlmostEqual(required/(200*20e-12),17*math.log(2),places=12)
        self.assertAlmostEqual(m.settling_error(3.3,10000,20e-12,.5e-6),.270880495458866,places=12)
    def test_acquisition_two_pole_against_rk4(self):
        # Independent state integration for linear cascaded poles after slew delay.
        # tau_driver=2 s, tau_RC=1 s. step=1, time=5, effectively zero slew delay.
        y1=y2=0.;dt=5/8000
        def rhs(a,b):return ((1-a)/2,a-b)
        for _ in range(8000):
            k1=rhs(y1,y2);k2=rhs(y1+dt*k1[0]/2,y2+dt*k1[1]/2)
            k3=rhs(y1+dt*k2[0]/2,y2+dt*k2[1]/2);k4=rhs(y1+dt*k3[0],y2+dt*k3[1])
            y1+=dt*(k1[0]+2*k2[0]+2*k3[0]+k4[0])/6
            y2+=dt*(k1[1]+2*k2[1]+2*k3[1]+k4[1])/6
        actual=m.acquisition_error(1,1,1,5,1/(4*math.pi),1e30)
        self.assertAlmostEqual(actual,1-y2,places=11)
        self.assertEqual(m.acquisition_error(3.3,200,20e-12,.1e-6,20e6,10e6),3.3)
        # Repeated poles have a t*exp(-t/tau) tail, not a single exponential.
        self.assertAlmostEqual(m.acquisition_error(1,1,1,5,1/(2*math.pi),1e30),6*math.exp(-5),places=12)
    def test_filter_alias_and_model_scope(self):
        self.assertAlmostEqual(m.butterworth_power(5000,5000,4),.5)
        self.assertLess(.1*math.sqrt(m.butterworth_power(99000,5000,4)),5e-6)
        self.assertGreater(.1*math.sqrt(m.butterworth_power(49000,5000,4)),5e-6)
        # A digital filter after sampling cannot distinguish the 99kHz alias
        # from the desired 1kHz sequence sampled at 100kHz.
        for k in range(10):self.assertAlmostEqual(math.cos(2*math.pi*99000*k/100000),math.cos(2*math.pi*1000*k/100000),places=12)
    def test_budget_success_failure_and_convergence(self):
        good=m.evaluate(m.Budget(),n=2048);fine=m.evaluate(m.Budget(),n=4096)
        self.assertTrue(good['teaching_budget_pass'])
        self.assertLess(abs(good['input_noise_rms']/fine['input_noise_rms']-1),1e-8)
        self.assertLess(good['noise_tail_bound_V2'],1e-18)
        bad=m.evaluate(m.fail_case(),n=2048)
        for name in ['output_window','common_mode','magnitude','dc_offset','rc_acquisition','driver_acquisition','antialias_tone']:self.assertFalse(bad['flags'][name])
        self.assertTrue(bad['flags']['sine_sr'])  # sine SR alone does not prove acquisition
    def test_transfer_has_new_failure_despite_higher_bits(self):
        cfg=replace(m.Budget(),peak=.0005,source_r=20000.,signal_hz=2000.,bits=18,fsr=2.5,midpoint=1.25,driver_r=1000.,acq=.1e-6,temperature=330.)
        result=m.evaluate(cfg,n=2048)
        self.assertFalse(result['flags']['driver_acquisition']);self.assertTrue(result['flags']['noise'])
        redesign=m.evaluate(replace(cfg,acq=2e-6),n=2048)
        self.assertTrue(redesign['teaching_budget_pass'])
    def test_dc_bias_current_ports_and_independent_counterexample(self):
        base=m.Budget();initial=m.evaluate(base)
        # Independent finite-A node equations give H1*H2*Ib*Req1/G.
        # 10 nA through 1 kohm = 10 uV; the finite-A attenuation is
        # 1/[(1+20/1e6)*(1+10/1e6)] for stage 1.
        changed=m.evaluate(replace(base,ibminus1=10e-9))
        increment=10e-6/((1+20/1e6)*(1+10/1e6))
        self.assertAlmostEqual(changed['offset_input_bound']-initial['offset_input_bound'],increment,places=15)
        self.assertGreater(changed['offset_input_bound'],20e-6)
        self.assertFalse(changed['flags']['dc_offset'])
        self.assertEqual(changed['input_noise_rms'],initial['input_noise_rms'])
        # Each port uses its own resistor, never ASD or the other input's Rs.
        for field,expected in [('ibplus1',20e-6/((1+20/1e6)*(1+10/1e6))),
                               ('ibminus2',20e-6/(20*(1+10/1e6))),
                               ('ibplus2',1e-6/(20*(1+10/1e6)))]:
            result=m.evaluate(replace(base,**{field:10e-9}))
            self.assertAlmostEqual(result['offset_input_bound']-initial['offset_input_bound'],expected,places=15)
        for field in ['ibplus1','ibminus1','ibplus2','ibminus2']:
            with self.assertRaises(ValueError):m.evaluate(replace(base,**{field:-1e-9}))
    def test_zero_signal_is_explicitly_outside_snr_contract(self):
        # validate itself must reject zero before any log10 is attempted.
        with self.assertRaises(ValueError):m.validate(replace(m.Budget(),peak=0.))
        with self.assertRaises(ValueError):m.evaluate(replace(m.Budget(),peak=0.))
    def test_invalid_inputs(self):
        for value in [math.nan,math.inf,True,'1',1j]:
            with self.assertRaises(ValueError):m.thermal_psd(value,300)
        for call in [lambda:m.rectangular_variance(1,1,0,100),lambda:m.rectangular_variance(1,1,100,1),lambda:m.integrate_log(lambda f:1,1,2,n=3),lambda:m.integrate_log(lambda f:-1,1,2),lambda:m.loop_metrics(2,[100,-100]),lambda:m.half_lsb(3.3,16.),lambda:m.settling_error(1,0,1,1),lambda:m.acquisition_error(1,1,1,1,1,0),lambda:m.evaluate(replace(m.Budget(),g1=.5)),lambda:m.evaluate(replace(m.Budget(),fs=1000))]:
            with self.assertRaises(ValueError):call()

if __name__=='__main__':unittest.main()
