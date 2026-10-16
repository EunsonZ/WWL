"""Analytic fixtures for the bounded teaching consumer; independent review is separate."""
import math
import unittest
import numpy as np
import texture_lab as lab


def primitive(x):
    u = x - 2*math.floor(x/2)
    return u if u <= 1 else 2-u


def checker_box_reference(uv, width):
    signed = []
    for c, d in zip(np.array(uv)*32, width):
        signed.append((primitive(c+d/2)-primitive(c-d/2))/d)
    return (1-signed[0]*signed[1])/2


class TextureTests(unittest.TestCase):
    def setUp(self):
        self.checker = (np.indices((32, 32)).sum(axis=0) % 2).astype(float)

    def test_centers_repeat_and_tent(self):
        for x, y in ((0, 0), (1, 0), (31, 31), (-1, 0)):
            uv = [(x+.5)/32, (y+.5)/32]
            expected = (x+y) % 2
            self.assertEqual(lab.nearest(self.checker, uv), expected)
            self.assertEqual(lab.bilinear(self.checker, uv), expected)
        self.assertEqual(lab.nearest(self.checker, [0, 0]), 0)
        self.assertEqual(lab.bilinear(self.checker, [0, 0]), .5)
        self.assertEqual(lab.bilinear(self.checker, [3.25/32, 29.25/32]), .375)

    def test_exact_cell_integral_independent_primitive(self):
        for uv in ((0, 0), (.17, .29), (-.33, 1.25), (31.75/32, .5/32)):
            for widths in ((.5, .75), (1, 1), (1.5, 3.25), (2, 2), (4, 4), (32, 64)):
                self.assertAlmostEqual(lab.box_average(self.checker, uv, widths),
                                       checker_box_reference(uv, widths), places=12)
        const = np.full((4, 8), .37)
        self.assertAlmostEqual(lab.box_average(const, [-.1, 1.2], [9.3, 3.7]), .37)

    def test_mip_levels_and_anisotropy(self):
        levels = lab.mip_chain(self.checker)
        self.assertEqual([a.shape[0] for a in levels], [32, 16, 8, 4, 2, 1])
        for a in levels[1:]:
            np.testing.assert_array_equal(a, .5*np.ones_like(a))
        value, lod = lab.mip_sample(self.checker, [.5/32, .5/32], [math.sqrt(2)]*2)
        self.assertAlmostEqual(lod, .5)
        self.assertAlmostEqual(value, .25)
        stripes = np.tile(np.arange(32) % 2, (32, 1))
        self.assertEqual(lab.box_average(stripes, [.5/32, .5/32], [1, 8]), 0)
        self.assertEqual(lab.mip_sample(stripes, [.5/32, .5/32], [1, 8])[0], .5)

    def test_projected_uv_and_array_consumer(self):
        r, _ = lab.renderer()
        for scale, width in ((1, 1), (.5, 2), (.25, 4)):
            screen, uv, w, coeff, jacobian = lab.projected(scale)
            np.testing.assert_allclose(jacobian, np.eye(2)*width, atol=1e-13)
            for x, y, weights in list(r.samples(screen, 64, 64))[::31]:
                np.testing.assert_allclose(r.interpolate(weights, w, uv),
                                          [x+.5, y+.5, 1] @ coeff, atol=1e-13)
            for phase in (0, .25):
                for method in lab.METHODS:
                    image, mask = lab.render_texture(scale, phase, method)
                    self.assertTrue(np.isfinite(image).all())
                    self.assertTrue(np.all((image >= 0) & (image <= 1)))
                    self.assertTrue(np.all(image[~mask] == 0))
                    if width >= 2 and method in ('box', 'mip'):
                        np.testing.assert_allclose(image[mask], .5, atol=1e-12)

    def test_geometric_coverage_is_separate(self):
        result = lab.edge_probe()
        self.assertAlmostEqual(result['exact_white_on_black_area'], .32)
        self.assertEqual(result['regular_n_by_n_coverage']['1'], 0)
        self.assertAlmostEqual(result['regular_n_by_n_coverage']['4'], .375)
        self.assertAlmostEqual(result['regular_n_by_n_coverage']['8'], .328125)
        self.assertLess(abs(result['regular_n_by_n_coverage']['32']-.32), .02)

    def test_linear_light(self):
        r, _ = lab.renderer()
        self.assertAlmostEqual(float(r.srgb(.5)), .7353569830524495)
        self.assertAlmostEqual(((.5+.055)/1.055)**2.4, .21404114048223255)

    def test_rejections_before_sampling(self):
        for bad in (True, float('nan'), float('inf'), 0, 1.1):
            with self.assertRaises(ValueError):
                lab.projected(bad)
        for bad in ([True, False], [float('nan'), 0], [0], [1e7, 0]):
            with self.assertRaises(ValueError):
                lab.nearest(self.checker, bad)
        for bad in ([0, 2], [65, 1], [True, False], [float('inf'), 1]):
            with self.assertRaises(ValueError):
                lab.box_average(self.checker, [0, 0], bad)
        for bad in (np.ones((3, 3)), np.ones((2, 4))):
            with self.assertRaises(ValueError):
                lab.mip_chain(bad)
        with self.assertRaises(ValueError):
            lab.render_texture(.5, 0, 'magic-antialias')
        with self.assertRaises(ValueError):
            lab.texture([[1.1]])


if __name__ == '__main__':
    unittest.main()
