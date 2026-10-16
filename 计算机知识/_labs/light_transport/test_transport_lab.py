"""Analytic and independent quadrature constraints for finite teaching contracts."""
import math
import unittest
import numpy as np
import transport_lab as lab


class TransportTests(unittest.TestCase):
    def test_hemisphere_pdf_and_lambert_moments(self):
        # Deterministic quadrature splits at the visibility jump; independent of sampler transforms.
        x, w = np.polynomial.legendre.leggauss(64)
        for scenario in lab.SCENARIOS:
            for method in lab.SAMPLERS:
                expectation, second = 0., 0.
                for lo, hi in ((0, .5), (.5, 1)):
                    if method == 'cap' and lo == 0:
                        continue
                    mu, weights = lo+(x+1)*(hi-lo)/2, w*(hi-lo)/2
                    pdf = np.full_like(mu, 1/(2*np.pi)) if method == 'uniform' else mu/np.pi
                    if method == 'cap':
                        pdf = np.full_like(mu, 1/np.pi)
                    f = (.6/np.pi)*2*mu
                    if scenario != 'constant' and lo == 0:
                        f *= 0
                    expectation += np.sum(weights*2*np.pi*f)
                    second += np.sum(weights*2*np.pi*f*f/pdf)
                expected = lab.lambert_theory(.6, 2, method, scenario)
                self.assertAlmostEqual(expectation, expected['mean'], places=12)
                self.assertAlmostEqual(second-expectation**2, expected['single_variance'], places=12)
        u = np.array([[.125, .125], [.375, .375], [.625, .625], [.875, .875]])
        for method in lab.SAMPLERS:
            direction, pdf = lab.hemisphere(u, method)
            np.testing.assert_allclose(np.sum(direction**2, axis=1), 1, atol=1e-14)
            self.assertTrue(np.all(pdf > 0))
        np.testing.assert_allclose(lab.lambert_samples(.6, 2, 'uniform', 'constant', u), [.3, .9, 1.5, 2.1])
        np.testing.assert_allclose(lab.lambert_samples(.6, 2, 'cosine', 'constant', u), 1.2)

    def test_actual_aperture_visibility_and_missing_factor(self):
        for mu, expected in ((.25, 0), (.75, 1)):
            d = np.array([math.sqrt(1-mu*mu), 0, mu])
            self.assertEqual(lab.aperture_visibility(d), expected)
        theory = lab.lambert_theory(.6, 2, 'cosine', 'visibility')
        self.assertAlmostEqual(theory['mean'], .9)
        self.assertAlmostEqual(theory['single_variance'], .27)
        self.assertAlmostEqual(lab.lambert_theory(.6, 2, 'cap', 'constant')['bias'], -.3)
        self.assertEqual(lab.lambert_theory(.6, 2, 'cap', 'cone')['bias'], 0)

    def test_disk_area_solid_and_analytic_quadrature(self):
        x, w = np.polynomial.legendre.leggauss(128)
        uv = np.column_stack([(x+1)/2, np.full_like(x, .25)])
        for radius, distance in ((1, 2), (2, 4), (.3, 5), (4, .5)):
            points, a, o, wrong = lab.disk_samples(.6, 4, radius, distance, uv)
            np.testing.assert_allclose(a, o, atol=1e-13)
            expected = lab.disk_theory(.6, 4, radius, distance)
            self.assertAlmostEqual(float(w @ a/2), expected['mean'], places=10)
            self.assertAlmostEqual(float(w @ (a*a)/2)-(float(w @ a/2))**2,
                                   expected['single_variance'], places=8)
            self.assertAlmostEqual(float(w @ wrong/2), expected['wrong_pdf_numeric_mean_not_radiance'], places=9)
        expected = lab.disk_theory(.6, 4, 1, 2)
        self.assertAlmostEqual(expected['mean'], .48)
        self.assertAlmostEqual(expected['single_variance'], .00384)
        tiny = lab.disk_theory(.6, 4, .01, 100)
        self.assertGreater(tiny['single_variance'], 0)
        self.assertAlmostEqual(tiny['single_variance']/1.9199999424e-32, 1, places=12)

    def test_fixed_path_geometry_throughput_and_series(self):
        u = np.full((1, 5, 2), .75)
        origin = np.array([[0., 0., -2.]])
        values, log = lab.fixed_paths(origin, u)
        np.testing.assert_allclose(values[0], [2.4, 3.12, 3.336])
        self.assertEqual([v['surface'] for v in log], ['floor', 'ceiling', 'floor', 'ceiling', 'floor'])
        for i, row in enumerate(log):
            a = np.array(row['origin_m']); d = np.array(row['direction'])
            np.testing.assert_allclose(a+row['distance_m']*d, row['hit_m'], atol=1e-13)
            self.assertAlmostEqual(np.linalg.norm(d), 1)
            self.assertEqual(row['hit_m'][2], 2 if i % 2 == 0 else -2)
            self.assertAlmostEqual(row['pdf_sr_inverse'], math.sqrt(.75)/math.pi)
        theory = lab.path_theory()
        self.assertAlmostEqual(theory['full_mean'], 18/7)
        np.testing.assert_allclose([r['mean'] for r in theory['finite']], [1.8, 2.34, 2.502])
        # Solve coupled floor/ceiling diffuse balance independently as a 2x2 system.
        balanced = np.linalg.solve([[1, -.6], [-.5, 1]], [1.8, 0])
        self.assertAlmostEqual(balanced[0], theory['full_mean'])

    def test_rr_full_paths_and_finite_variance(self):
        n = 32768
        values, record = lab.rr_paths(np.tile([0., 0., -2.], (n, 1)), np.random.default_rng(16939))
        theory = lab.path_theory()
        se = math.sqrt(theory['rr_single_variance']/n)
        self.assertLess(abs(float(values.mean())-theory['full_mean']), 7*se)
        self.assertLess(abs(float(values.var())-theory['rr_single_variance']), .15*theory['rr_single_variance'])
        self.assertGreater(record['total_ray_segments'], n)
        self.assertGreater(record['max_emission_visits'], 1)
        zeros, _ = lab.rr_paths(np.tile([0., 0., -2.], (4, 1)), np.random.default_rng(2), rho_floor=0)
        np.testing.assert_array_equal(zeros, 0)

    def test_ggx_normalization_and_display(self):
        x, w = np.polynomial.legendre.leggauss(256)
        mu = (x+1)/2
        for alpha in (.15, .5, 1):
            self.assertAlmostEqual(float(np.sum(w/2*2*np.pi*mu*lab.ggx_ndf(mu, alpha))), 1, places=10)
            self.assertAlmostEqual(float(lab.ggx_ndf(1, alpha)), 1/(math.pi*alpha*alpha))
        self.assertAlmostEqual(float(lab.tone_map(18/7)), .72)
        self.assertAlmostEqual(float(lab.tone_map(1)), .5)
        self.assertAlmostEqual(float(lab.tone_map(2, exposure=.5)), .5)

    def test_observation_uses_existing_array_contract(self):
        coords, points, screen = lab.observation()
        self.assertTrue(np.all(points[:, 2] == -2))
        self.assertTrue(np.all(coords >= 0) and np.all(coords < 64))
        # Independent pinhole camera ray: at z=-2, x=(pixel_center/32-1)*2.
        np.testing.assert_allclose(points[:, 0], 2*((coords[:, 0]+.5)/32-1), atol=1e-13)
        np.testing.assert_allclose(points[:, 1], 2*(1-(coords[:, 1]+.5)/32), atol=1e-13)

    def test_invalid_contracts_rejected(self):
        u = np.full((1, 5, 2), .5)
        for bad in (True, float('nan'), float('inf'), -.1, 1.1):
            with self.assertRaises(ValueError):
                lab.lambert_samples(bad, 2, 'cosine', 'constant', [[.5, .5]])
        for bad in ([[0, .5]], [[float('nan'), .5]], [[True, False]], [[1.1, .5]], [[.5]]):
            with self.assertRaises(ValueError):
                lab.hemisphere(bad, 'cosine')
        with self.assertRaises(ValueError):
            lab.hemisphere([[.5, .5]], 'miracle')
        with self.assertRaises(ValueError):
            lab.fixed_paths([[0, 0, -2]], u[:, :4])
        with self.assertRaises(ValueError):
            lab.fixed_paths([[0, 0, 0]], u)
        with self.assertRaises(ValueError):
            lab.path_parameters(.9, .9, 4, .5, .5)
        with self.assertRaises(ValueError):
            lab.ggx_ndf(.5, 0)
        with self.assertRaises(ValueError):
            lab.tone_map([-1])


if __name__ == '__main__':
    unittest.main()
