"""Independent finite composition checks, not a simulator or hardware proof."""
import hashlib
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
import joint_lab as j

VAULT=Path(os.environ.get('WWL_SOURCE_VAULT',Path(__file__).resolve().parents[3]))

class JointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=j.run(VAULT)['cards']

    def test_rc_initial_and_sampled_closed_form(self):
        x=self.data['L02']
        for row in x['rows']:
            t=row['k']*.00025
            self.assertAlmostEqual(row['v_V'],1-.6*math.exp(-t/.001),places=13)
            self.assertAlmostEqual(row['zero_input_V'],.4*math.exp(-t/.001),places=13)
            self.assertAlmostEqual(row['extra_register_V'],0 if row['k']==0 else 1-.6*math.exp(-(t-.00025)/.001),places=13)
        self.assertEqual(x['block_continuity_error_V'],0)
        self.assertAlmostEqual(x['loaded']['K'],25/28)
        self.assertAlmostEqual(x['loaded']['tau_s'],3/2800)

    def test_rc_four_domain_units_and_first_impulse_index(self):
        x=self.data['L02'];a=x['z_pole']
        self.assertAlmostEqual(math.log(a)/.00025,x['s_pole_per_s'])
        self.assertAlmostEqual(x['fc_Hz']*.001*2*math.pi,1)
        self.assertEqual(x['z_h0'],0)
        self.assertAlmostEqual(x['z_h1'],1-a)
        h=x['phasor_at_fc'];self.assertAlmostEqual(h['real'],.5);self.assertAlmostEqual(h['imag'],-.5)
        self.assertNotAlmostEqual(x['discrete_at_Omega_025']['real'],h['real'],places=2)

    def test_diode_independent_monotone_bracket(self):
        # Independently evaluate the stated Shockley circuit, not source helper.
        lo,hi=0.,.6
        for _ in range(60):
            mid=lo+(hi-lo)/2
            if mid in (lo,hi):break
            residual=(mid-5)/1000+1e-12*math.expm1(mid/.025)
            if residual<0:lo=mid
            else:hi=mid
        self.assertLessEqual(abs(self.data['L04']['diode']['vd_V']-(lo+hi)/2),1e-10)
        trace=self.data['L04']['diode']['trace']
        self.assertTrue(all(abs(b['residual_A'])<abs(a['residual_A']) for a,b in zip(trace,trace[1:])))

    def test_mos_closed_load_line_and_narrow_newton_contract(self):
        with j.model(VAULT,'transistor') as m:
            for lam in (0.,.02,.05):
                for start in (.1,3.,4.9):
                    q=j.mos_newton(m,start,lam)
                    expected=3/(1+2*lam)
                    self.assertAlmostEqual(q['vd_V'],expected,places=9)
                    self.assertGreater(q['vd_V'],1.)
                    self.assertLess(abs((5-q['vd_V'])/2000-q['id_A']),1e-13)
            with self.assertRaises(ArithmeticError):j.mos_newton(m,.1,iterations=1)
        for bad in [True,complex(1,0),'3',[],math.inf,math.nan,1e300]:
            with self.assertRaises(ValueError):j.mos_newton(object(),bad)
        for bad in [True,0,65,1.5]:
            with self.assertRaises(ValueError):j.mos_newton(object(),iterations=bad)

    def test_huge_integer_rejected_before_device_call(self):
        class Untouched:
            def __init__(self):self.calls=0
            def mos(self,*args,**kwargs):
                self.calls+=1
                raise AssertionError('device called before complete validation')
        for start,lam in ((10**400,.02),(-10**400,.02),(3.,10**400),(3.,-10**400)):
            device=Untouched()
            with self.assertRaises(ValueError):j.mos_newton(device,start,lam)
            self.assertEqual(device.calls,0)

    def test_noise_reference_classification_and_joint_changes(self):
        x=self.data['L07'];g=x['good'];ib=x['bias_current_counterexample']
        self.assertEqual(g['input_noise_rms'],ib['input_noise_rms'])
        self.assertAlmostEqual(ib['offset_input_bound']-g['offset_input_bound'],10e-9*1000*(1e6/(1+1e6/20))*(1e6/(1+1e6/10))/200,places=14)
        self.assertFalse(ib['flags']['dc_offset']);self.assertTrue(g['flags']['dc_offset'])
        self.assertAlmostEqual(g['quantization_rms'],3.3/65536/math.sqrt(12))
        self.assertAlmostEqual(x['static_ADC_counterexample']['error_V'],3.3/131072)
        self.assertFalse(x['transfer']['flags']['driver_acquisition'])
        self.assertTrue(all(x['longer_acquisition']['flags'].values()))
        self.assertEqual(x['transfer']['input_noise_rms'],x['longer_acquisition']['input_noise_rms'])

    def test_buck_mode_observation_not_average_error_certificate(self):
        x=self.data['L11'];s=x['steady_closed_form']
        self.assertAlmostEqual(s['delta_i_A'],(12-5)*(5/12)/(100e-6*100e3))
        self.assertAlmostEqual(s['r_boundary_ohm'],2*100e-6*100e3/(1-5/12))
        self.assertGreater(x['valid_segmented']['minimum_i_A'],0)
        self.assertEqual(x['valid_segmented']['mode_counts'],{'initial':1,'on':12800,'off':12800})
        self.assertGreater(x['invalid_segmented']['mode_counts']['idle'],0)
        self.assertLess(x['invalid_CCM_average']['minimum_i_A'],0)
        d=x['dcm_R100'];area=.5*d['peak_dcm_A']*(5/12+d['d2'])
        self.assertAlmostEqual(area,d['v_V']/100)
        self.assertGreater(d['d3'],0);self.assertGreater(x['maximum_pointwise_difference']['v_V'],.1)
        self.assertAlmostEqual(x['losses_estimate']['total_W'],sum(x['losses_estimate']['parts'].values()))

    def test_exact_source_guard_and_temporary_module_cleanup(self):
        before=sys.modules.get('_wwl_joint_rc')
        with j.model(VAULT,'rc') as m:self.assertEqual(m.RC().tau,.001)
        self.assertIs(sys.modules.get('_wwl_joint_rc'),before)
        with tempfile.TemporaryDirectory() as tmp:
            key=json.loads((j.HERE/'inputs.json').read_text())['sources']['rc']['path'];p=Path(tmp)/key;p.parent.mkdir(parents=True);p.write_text('raise AssertionError("must not execute drift")\n')
            with self.assertRaisesRegex(ValueError,'byte drift'):
                with j.model(Path(tmp),'rc'):pass
        for cards in [(),('L02','L02'),('L99',),True]:
            with self.assertRaises(ValueError):j.run(VAULT,cards)

    def test_generation_preflight_new_output_and_fixed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a',Path(tmp)/'b';j.generate(a,VAULT,('L02',));j.generate(b,VAULT,('L02',))
            self.assertEqual((a/'results.json').read_bytes(),(b/'results.json').read_bytes())
            with self.assertRaises(FileExistsError):j.generate(a,VAULT,('L02',))
            c=Path(tmp)/'failure'
            with self.assertRaises(ValueError):j.generate(c,VAULT,('L99',))
            self.assertFalse(c.exists())
        with self.assertRaises(ValueError):j.generate(VAULT/'must-not-write',VAULT,('L02',))

if __name__=='__main__':unittest.main()
