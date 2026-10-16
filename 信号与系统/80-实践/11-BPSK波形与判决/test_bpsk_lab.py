"""Author regression checks: literal physical vectors and adversarial inputs.
These checks are not a non-author derivation or an independent mathematical proof.
"""
import copy
import json
import math
from pathlib import Path
import unittest
import bpsk_lab as lab


class BPSKChecks(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((Path(__file__).parent/'fixed-inputs.json').read_text())

    def test_physical_energy_and_variance_literals(self):
        rows, _ = lab.fixed_vectors(self.c)
        for r, variance in zip(rows, [.001, .004]):
            self.assertAlmostEqual(r['pulse_energy'], 1, places=12)
            self.assertAlmostEqual(r['signal_energy_J'], 1e-6, places=17)
            self.assertAlmostEqual(r['cell_noise_variance_W'], variance, places=14)
            self.assertAlmostEqual(r['projected_noise_variance_J'], 2.5e-7, places=18)

    def test_known_integral_not_dt_free_array_sum(self):
        # p=2 s^-1/2 over 1/4 s; r=[3,5] sqrt(W), dt=1/8 s.
        self.assertEqual(lab.inner_amplitude([3, 5], [2, 2], 1/8), 2)
        self.assertEqual(lab.coarsen([1, 3, -2, 6], 2), [2, 2])
        with self.assertRaises(ValueError):
            lab.coarsen([1, 2, 3], 2)

    def test_threshold_symmetry_and_literal_q(self):
        self.assertEqual(lab.threshold(1e-6, 5e-7, .5), 0)
        self.assertAlmostEqual(lab.threshold(1e-6, 5e-7, .9),
                               -0.00027465307216702745, places=16)
        self.assertAlmostEqual(lab.threshold(1e-6, 5e-7, .1),
                               0.00027465307216702745, places=16)
        self.assertAlmostEqual(lab.q(2), .02275013194817922, places=14)

    def test_density_balance_at_map_threshold(self):
        a, n0, pi = .001, .0000005, .9
        gamma = lab.threshold(a*a, n0, pi)
        # Unnormalized Gaussian densities cancel the common positive coefficient.
        weighted_plus = pi*math.exp(-(gamma-a)**2/n0)
        weighted_minus = (1-pi)*math.exp(-(gamma+a)**2/n0)
        self.assertAlmostEqual(weighted_plus, weighted_minus, places=14)
        self.assertLess(lab.theory(a*a, n0, pi)['p_error'], lab.q(2))
        self.assertGreater(lab.theory(a*a, n0, pi)['p_error_given_minus'], lab.q(2))

    def test_wrong_noise_contract_really_changes_variance(self):
        rows, _ = lab.fixed_vectors(self.c)
        self.assertAlmostEqual(rows[1]['wrong_projected_variance_J'] /
                               rows[0]['wrong_projected_variance_J'], .25)

    def test_cross_prior_derived_seed_collision_rejected(self):
        c = copy.deepcopy(self.c)
        c['seeds'] = [181, 1000000188]
        with self.assertRaisesRegex(ValueError, 'derived seeds collide'):
            lab.validate(c)

    def test_valid_card(self):
        self.assertIs(lab.validate(self.c), self.c)

    def test_bad_cards_fail_explicitly(self):
        changes = [('Eb_J', 0), ('N0_J', float('nan')), ('T_s', True),
                   ('grids', [4, 15]), ('grids', [4, 4]),
                   ('n_symbols', True), ('n_symbols', 100001),
                   ('seeds', [181, 181]), ('pi_plus', [0, .9]),
                   ('fixed_noise_sqrtW', [0]*15)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                c = copy.deepcopy(self.c)
                c[key] = value
                with self.assertRaises(ValueError):
                    lab.validate(c)


if __name__ == '__main__':
    unittest.main()
