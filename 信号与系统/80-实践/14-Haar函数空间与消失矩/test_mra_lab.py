import copy
import json
import math
import os
from pathlib import Path
import unittest
import mra_lab as lab


class AnalyticContracts(unittest.TestCase):
    def test_ramp_projection_error(self):
        for j in range(7):
            p = lab.projection([[0,1,[0,1]]], j)
            self.assertAlmostEqual(p['error_squared'], 1/(12*4**j), delta=2e-13)
            self.assertAlmostEqual(p['projection_norm_squared'], 1/3-1/(12*4**j), delta=2e-13)

    def test_edge_alignment(self):
        expected = [15/64, 3/32, 1/16, 0, 0, 0, 0]
        for j, error in enumerate(expected):
            self.assertAlmostEqual(lab.projection([[3/8,1,[1]]], j)['error_squared'], error, delta=2e-13)

    def test_coarse_origin_boundary(self):
        for j in range(-6,1):
            p = lab.projection([[-1,0,[1]],[0,1,[-1]]], j)
            self.assertAlmostEqual(p['projection_norm_squared'], 2**(j+1), delta=2e-13)
            self.assertEqual(len(p['cells']), 2)

    def test_four_cell_continuous_normalization(self):
        segs = [[i/4,(i+1)/4,[v]] for i,v in enumerate([1,3,2,6])]
        p = lab.projection(segs, 2)
        self.assertEqual([t['coefficient'] for t in p['cells']], [.5,1.5,1,3])
        self.assertEqual(p['input_norm_squared'], 12.5)
        self.assertEqual(p['error_squared'], 0)

    def test_published_bridge_and_discrete_moments(self):
        bank = lab.load_module(os.environ['WWL_HAAR_SOURCE'], 'test_published_haar')
        source = lab.load_module(os.environ['WWL_RESAMPLE_SOURCE'], 'test_published_resample')
        b = lab.bridge([[0,1,[0,1]]], 5, bank, source)
        self.assertLess(b['max_coefficient_difference'], 1e-13)
        f = {x['name']:x for x in lab.filters(16, source)}
        self.assertAlmostEqual(f['haar']['g_discrete_moments_0_1_2'][1], -1/math.sqrt(2))
        self.assertAlmostEqual(f['db2_mask']['g_discrete_moments_0_1_2'][0], 0)
        self.assertAlmostEqual(f['db2_mask']['g_discrete_moments_0_1_2'][1], 0)
        self.assertAlmostEqual(f['db2_mask']['g_discrete_moments_0_1_2'][2], -math.sqrt(3/2))
        # The finite zero extension can create detail, even when the polynomial interior cancels.
        q = f['db2_mask']['polynomials'][1]
        self.assertLess(max(map(abs,q['direct_interior'])), 2e-14)
        self.assertGreater(max(map(abs,q['full_zero_extended_output'])), 1)

    def test_budget_separates_signal_and_coefficients(self):
        bank = lab.load_module(os.environ['WWL_HAAR_SOURCE'], 'test_high_haar')
        source = lab.load_module(os.environ['WWL_RESAMPLE_SOURCE'], 'test_high_resample')
        b = lab.bridge([[-2,2,[10000]]], 2, bank, source)
        self.assertLess(b['max_restoration_difference'], 1e-10)
        self.assertAlmostEqual(b['fine_projection_energy'], 4e8, delta=1e-6)

    def test_input_contract(self):
        c = json.loads((Path(__file__).parent/'fixed-inputs.json').read_text())
        lab.validate(c)
        mutations = [('levels',[True]),('levels',[1,1]),('finest_level',9),
                     ('filter_input_length',9),('polynomial_degrees',[0,1]),
                     ('polynomial_degrees',[False,True,2])]
        for key,value in mutations:
            d=copy.deepcopy(c); d[key]=value
            with self.assertRaises(ValueError):lab.validate(d)
        d=copy.deepcopy(c);d['signals'][0]['segments']=[[0,1,[float('nan')]]]
        with self.assertRaises(ValueError):lab.validate(d)
        d=copy.deepcopy(c);d['signals'][0]['segments']=[[0,.75,[1]],[.5,1,[2]]]
        with self.assertRaises(ValueError):lab.validate(d)


if __name__ == '__main__':
    unittest.main()
