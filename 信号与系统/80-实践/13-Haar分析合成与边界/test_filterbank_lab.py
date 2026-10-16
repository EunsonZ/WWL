"""Author regression checks; independent exact matrix/z-domain audit is separate."""
import copy
import json
import math
from pathlib import Path
import unittest
import numpy as np
import filterbank_lab as lab


class FilterBankChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=lab.load_source(lab.source_default())
    def setUp(self):
        self.c=json.loads((Path(__file__).parent/'fixed-inputs.json').read_text())
    def test_four_point_literal_coefficients_and_error(self):
        r=lab.record([1,3,2,6],'zero',self.source,.5)
        np.testing.assert_allclose(r['a_V'],[2*math.sqrt(2),4*math.sqrt(2)],atol=1e-13,rtol=0)
        np.testing.assert_allclose(r['d_V'],[-math.sqrt(2),-2*math.sqrt(2)],atol=1e-13,rtol=0)
        np.testing.assert_allclose(r['restored_crop_V'],[1,3,2,6],atol=1e-13,rtol=0)
        np.testing.assert_allclose(r['low_only_crop_V'],[2,2,4,4],atol=1e-13,rtol=0)
        self.assertAlmostEqual(r['coefficient_squared_norm_V2'],50,places=12)
        self.assertAlmostEqual(r['detail_squared_norm_V2'],10,places=12)
        self.assertAlmostEqual(r['low_only_crop_error_V2'],10,places=12)
    def test_bad_high_sign_predictable_pair_swap(self):
        r=lab.record([1,3,2,6],'zero',self.source,.5)
        np.testing.assert_allclose(r['wrong_detail_sign_crop_V'],[3,1,6,2],atol=1e-13,rtol=0)
        self.assertAlmostEqual(r['wrong_detail_sign_error_V2'],40,places=12)
    def test_phase0_delay_is_not_phase1(self):
        r=lab.record([1,3,2,6],'zero',self.source,.5)
        np.testing.assert_allclose(r['phase0_correct_delay_crop_V'],[1,3,2,6],atol=1e-13,rtol=0)
        np.testing.assert_allclose(r['phase0_wrong_crop_V'],[0,1,3,2],atol=1e-13,rtol=0)
    def test_odd_zero_crop_loses_projection_property(self):
        r=lab.record([1,3,2,6,5],'zero',self.source,.5)
        np.testing.assert_allclose(r['low_only_crop_V'],[2,2,4,4,2.5],atol=1e-13,rtol=0)
        self.assertAlmostEqual(r['low_only_crop_error_V2'],16.25,places=12)
        self.assertAlmostEqual(r['detail_squared_norm_V2'],22.5,places=12)
        b=lab.finite_basis(5,'zero',self.source,.5)
        self.assertAlmostEqual(b['low_operator_idempotence_error'],.25,places=12)
    def test_repeat_boundary_energy_is_extended_energy(self):
        r=lab.record([1,3,2,6,5],'repeat',self.source,.5)
        self.assertAlmostEqual(r['input_squared_norm_V2'],75,places=12)
        self.assertAlmostEqual(r['coefficient_squared_norm_V2'],100,places=12)
        self.assertAlmostEqual(r['low_only_crop_error_V2'],10,places=12)
    def test_shear_inverse_does_not_imply_parseval(self):
        r=lab.record([1,3,2,6],'zero',self.source,.5)
        np.testing.assert_allclose(r['shear_low_only_crop_V'],[1.5,1.5,3,3],atol=1e-13,rtol=0)
        self.assertAlmostEqual(r['shear_coefficient_squared_norm_V2'],32.5,places=12)
        self.assertAlmostEqual(r['shear_low_only_error_V2'],12.5,places=12)
        b=lab.finite_basis(4,'zero',self.source,.5)
        self.assertLess(b['shear_low_idempotence_error'],1e-13)
        self.assertAlmostEqual(b['shear_low_symmetry_error'],.5,places=12)
    def test_legal_large_input_does_not_cap_internal_coefficients(self):
        c=copy.deepcopy(self.c);c['samples_V']=[1e6]*4
        lab.validate(c)
        r=lab.record(c['samples_V'],'zero',self.source,.5)
        self.assertGreater(r['a_V'][0],1e6)
        np.testing.assert_allclose(r['restored_crop_V'],c['samples_V'],atol=2e-6,rtol=0)
        with self.assertRaises(ValueError):
            c['samples_V']=[1000001]*4;lab.validate(c)

    def test_bad_inputs(self):
        for key,value in [('samples_V',[1,True,2,6]),('fs_Hz',0),
                          ('basis_lengths',[True,4]),('boundary_modes',['wrap']),
                          ('shear_lambda',float('nan'))]:
            c=copy.deepcopy(self.c);c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):lab.validate(c)


if __name__=='__main__':unittest.main()
