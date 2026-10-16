import copy
import json
import math
import os
from pathlib import Path
import unittest
import numpy as np
import db2_lab as lab

ROOT=Path(os.environ.get('WWL_DB2_ROOT','/Users/ysz/Misc/Obsidian/Valults/WLM/WWL'))
CONFIG=json.loads(Path(__file__).with_name('fixed-inputs.json').read_text())


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h,cls.g,offline,cls.refs=lab.load_published(ROOT)
        cls.offline=staticmethod(offline)

    def test_fixed_null_exact_direction(self):
        # Analytic direction, not obtained from tested analysis or numerical SVD.
        x=np.zeros(10);x[:2]=[math.sqrt(3)/2,-.5]
        aa,dd=lab.analysis(x,self.h,self.g,self.offline,'zero_full')
        self.assertLess(max(np.max(np.abs(aa[1:])),np.max(np.abs(dd[1:]))),2e-15)
        restored,_=lab.synthesis(aa,dd,self.h,self.g,self.offline,10,'zero_full')
        np.testing.assert_allclose(restored,x,rtol=0,atol=2e-15)
        self.assertAlmostEqual(float(aa[0]**2+dd[0]**2),1.,places=14)

    def test_arbitrary_full_packet_uses_transpose(self):
        # Each of the 12 coefficient impulses has explicit support 2m..2m+3.
        for k in range(12):
            a=np.zeros(6);d=np.zeros(6)
            (a if k<6 else d)[k%6]=1.
            y,_=lab.synthesis(a,d,self.h,self.g,self.offline,10,'zero_full')
            expected=np.zeros(10);m=k%6-1;mask=self.h if k<6 else self.g
            for n,v in enumerate(mask):
                if 0<=2*m+n<10:expected[2*m+n]+=v
            np.testing.assert_allclose(y,expected,rtol=0,atol=2e-15)

    def test_circle_inverse_and_wrong_no_denominator(self):
        d=np.array([1.,0.]);a=.5
        q=lab.unmix(d,a)
        np.testing.assert_allclose(q,[4/3,-2/3],rtol=0,atol=2e-15)
        np.testing.assert_allclose(lab.mix(q,a),d,rtol=0,atol=2e-15)
        np.testing.assert_allclose(lab.mix(d-a*np.roll(d,1),a),.75*d,rtol=0,atol=2e-15)

    def test_odd_alternating_endpoint_instability(self):
        for M in (8,32,128):
            q=np.array([(-1)**k/math.sqrt(M) for k in range(M)])
            y=np.r_[q,0]+np.r_[0,q]
            self.assertAlmostEqual(float(y@y),2/M,places=14)
            self.assertEqual(float(lab.mix(q,1)@lab.mix(q,1)),0.)

    def test_validation_bool_finite_and_budget(self):
        for key,value in [('mix_a',True),('mix_a',1),('samples_V',[1]*7),('basis_lengths',[True]),
                          ('cascade_levels',[False]),('sample_rate_Hz',float('nan')),
                          ('dual_last_shift',0),('instability_lengths',[8,8])]:
            c=copy.deepcopy(CONFIG);c[key]=value
            with self.assertRaises(ValueError,msg=key):lab.validate(c)

    def test_zero_a_and_large_legal_amplitude(self):
        c=copy.deepcopy(CONFIG);c['samples_V']=[1e6]*6;c['mix_a']=0;c['basis_lengths']=[4];c['cascade_levels']=[1]
        r=lab.run(c,ROOT)
        np.testing.assert_allclose(r['record']['biorth_periodic']['restored'],c['samples_V'],rtol=0,atol=1e-8)
        self.assertEqual(r['biorth_exact_example']['analysis_squared_sum'],1.)
        self.assertEqual(r['cascade']['dual_tail_L2_bound_for_exact_psi'],0.)

    def test_cascade_start_is_finite_piecewise_model(self):
        r=lab.cascade(self.h,self.g,[1],16,1,.5)
        # First iterate has four width-1/2 cells exactly sqrt2*h.
        d=r['finite_iterate_checks'][0]
        self.assertEqual(d['cell_count'],4)
        self.assertAlmostEqual(d['integral'],1.,places=14)
        self.assertAlmostEqual(d['norm_squared'],1.,places=14)
        curve=r['curves'][0]; idx=curve['tau'].index(.5)
        self.assertAlmostEqual(curve['phi_cascade'][idx],math.sqrt(2)*self.h[1],places=14)

if __name__=='__main__':unittest.main()
