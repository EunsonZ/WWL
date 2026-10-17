import copy
import importlib.util
import json
import math
from pathlib import Path
import unittest
import numpy as np
import synth_rx as model
ROOT=Path(__file__).parent

class Contracts(unittest.TestCase):
    def setUp(self):self.c=json.loads((ROOT/'spec.json').read_text())
    def test_CP_charge_exact_and_no_free_pump(self):
        p=self.c['pll'];p['duration_s']=5e-6
        z=.7;initial={'z_V':z,'feedback_phase_cycles':0.,'reference_Hz':10e6}
        run=model.hybrid(p,1000,initial)
        for a,b in zip(run['trace'],run['trace'][1:]):
            self.assertAlmostEqual(b[1]-a[1],a[3]*p['Icp_A']/p['C_F']*(b[0]-a[0]),places=13)
        # Exactly aligned no-error equilibrium does not generate charge.
        run=model.hybrid(p,1000,{'z_V':.9,'feedback_phase_cycles':0.,'reference_Hz':10e6})
        self.assertTrue(all(abs(x[1]-.9)<1e-12 for x in run['trace']))
    def test_local_characteristic_and_different_noise_ports(self):
        p=self.c['pll'];s=model.spectrum(p,self.c['noise'],2000)
        self.assertEqual(s['a_per_s'],400000.)
        self.assertEqual(s['b_per_s2'],2e10)
        T,S=model.loop(p,2000,10000)
        self.assertAlmostEqual(abs(T+S-1),0,places=14)
        self.assertNotAlmostEqual(abs(T),abs(S))
        self.assertTrue(all(z[0]<0 for z in s['roots_per_s']))
    def test_R10k_not_silently_called_unclipped(self):
        self.c['pll']['designs'][0]['R_ohm']=10000
        with self.assertRaisesRegex(ValueError,'headroom'):model.validate(self.c)
    def test_budget_and_bool_rejections(self):
        for mutate in [lambda c:c['pll'].__setitem__('N',True),lambda c:c['pll'].__setitem__('Icp_A',float('nan')),lambda c:c['pll']['designs'][0].__setitem__('name','../escape'),lambda c:c['pll'].__setitem__('duration_s',.003),lambda c:c['noise'].__setitem__('integration_Hz',[100,20e6])]:
            c=copy.deepcopy(self.c);mutate(c)
            with self.assertRaises((ValueError,TypeError)):model.validate(c)
    def test_rational_integer_N_resolution(self):
        p=self.c['pll'];self.assertEqual(p['N']*p['reference_Hz'],100e6)
        self.assertGreater(p['N']*12e6,p['center_Hz']+p['Kv_Hz_per_V']*(1.8-.9))
    def test_IP3_and_front_loss_different_orders(self):
        # Independent Fourier expansion x^3: coefficient at 2f1-f2 is 3A^3/4.
        f=np.arange(8192)/8192*2*math.pi
        x=np.cos(13*f)+np.cos(15*f)
        coefficient=2*np.mean(x**3*np.cos(11*f))
        self.assertAlmostEqual(coefficient,.75,places=12)
        # Attenuation of power L -> amplitude 1/sqrt L, IM3 power 1/L³.
        self.assertAlmostEqual((.75/8)**2/(.75**2),1/64)
if __name__=='__main__':unittest.main()
