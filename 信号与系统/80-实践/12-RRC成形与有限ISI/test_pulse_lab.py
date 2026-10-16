"""Author regression checks; non-author frequency/Gram verification is separate."""
import copy
import json
import math
from pathlib import Path
import unittest
import pulse_lab as lab


class PulseChecks(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((Path(__file__).parent/'fixed-inputs.json').read_text())

    def test_singular_and_beta_zero_limits(self):
        for x in (0,.25,.5,1,2):
            self.assertAlmostEqual(lab.rc(x,0),lab.sinc(x),places=14)
            self.assertAlmostEqual(lab.rrc(x,0),lab.sinc(x),places=14)
        self.assertAlmostEqual(lab.rc(.5,1),.5,places=14)
        self.assertAlmostEqual(lab.rrc(.25,1),1,places=14)
        self.assertAlmostEqual(lab.rrc(0,.25),.75+1/math.pi,places=14)
        self.assertAlmostEqual(lab.rrc(1,.25),-(1-2/math.pi)/(4*math.sqrt(2)),places=14)

    def test_symbol_zeros_are_not_rrc_zeros(self):
        for beta in (0,.25,.5,1):
            self.assertAlmostEqual(lab.rc(0,beta),1,places=14)
            for k in range(1,7):
                self.assertLess(abs(lab.rc(k,beta)),1e-13)
        self.assertGreater(abs(lab.rrc(1,.25)),.06)

    def test_nyquist_spectral_partition(self):
        for beta in (0,.25,.5,1):
            for nu in (-.5,-.4,-.25,0,.1,.5):
                folded = sum(lab.rc_spectrum(nu+m,beta) for m in range(-2,3))
                self.assertAlmostEqual(folded,1,places=13)

    def test_literal_convolution_and_reversal(self):
        self.assertEqual(lab.conv([1,2],[3,-1]),[3,5,-2])
        u=[.6,.8]
        self.assertEqual(lab.conv(u,list(reversed(u))),[.48,1,.48])

    def test_noise_ensemble_support_and_covariance(self):
        # Three-tap unit energy matched filter, shift=1 sample: adjacent covariance .48*v.
        h=[.6,.8]
        r=lab.noise_ensemble(h,1,1,2)
        self.assertEqual(r['output_indices'],[1,2,2])
        self.assertAlmostEqual(r['full_support_variance_J'],2,places=13)
        self.assertAlmostEqual(r['covariance_J'][0][1],.96,places=13)
        self.assertAlmostEqual(r['startup_zero_padded_variance_J'],.72,places=13)

    def test_finite_chain_and_energy_not_assumed_additive(self):
        r,u,gd,tx,rx=lab.one_case(self.c,.25,6,8)
        self.assertAlmostEqual(sum(v*v for v in u),1,places=13)
        self.assertEqual(r['single_filter_delay_samples'],24)
        self.assertEqual(r['pair_delay_samples'],48)
        self.assertEqual(r['decision_indices'],[48,56,64,72,80,88,96])
        self.assertGreater(r['max_abs_symbol_sidelobe'],1e-4)
        self.assertAlmostEqual(r['full_tx_frame_energy_J'],r['frame_energy_via_Gram_J'],places=17)
        self.assertGreater(abs(r['frame_cross_energy_J']),1e-10)

    def test_rc_matched_twice_is_not_nyquist(self):
        # beta=1 gives R(nu)^2 energy=3/4 and lag-T integral=1/8 -> normalized 1/6.
        norm=lab.spectral_integral(1,0,2,1024)
        cross=lab.spectral_integral(1,1,2,1024)
        self.assertAlmostEqual(norm,.75,places=12)
        self.assertAlmostEqual(cross/norm,1/6,places=12)

    def test_bad_inputs(self):
        changes=[('Eb_J',True),('T_s',0),('N0_J',float('nan')),
                 ('bits','11012'),('betas',[.25,1.01]),('betas',[True]),
                 ('samples_per_symbol',[8,8]),('samples_per_symbol',[3,16]),
                 ('spans_symbols',[5]),('timing_offset_T',.1),
                 ('frequency_simpson_panels',255)]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                c=copy.deepcopy(self.c);c[key]=value
                with self.assertRaises(ValueError): lab.validate(c)


if __name__=='__main__':
    unittest.main()
