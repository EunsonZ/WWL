"""Exact targets, convergence, orientation, and invalid-input checks."""
import math
import unittest

import gauss_bonnet_lab as lab


class GaussBonnetLabTests(unittest.TestCase):
    def assert_gauss_bonnet(self, row, places=11):
        self.assertAlmostEqual(row["total"], row["target"], places=places)
        self.assertAlmostEqual(row["residual"], 0.0, places=places)

    def test_four_examples_same_accounting(self):
        disk = lab.plane_disk(radius=3.0)
        octant = lab.sphere_octant(radius=2.0)
        cap = lab.sphere_cap(radius=2.0, phi0=math.pi / 3.0)
        band = lab.cylinder_band(radius=2.0, height=3.0)
        for row in (disk, octant, cap, band):
            self.assert_gauss_bonnet(row)
        self.assertAlmostEqual(disk["boundary"], 2.0 * math.pi)
        self.assertAlmostEqual(octant["curvature"], math.pi / 2.0)
        self.assertAlmostEqual(octant["corners"], 3.0 * math.pi / 2.0)
        self.assertAlmostEqual(cap["curvature"], math.pi)
        self.assertAlmostEqual(cap["boundary"], math.pi)
        self.assertEqual(band["chi"], 0.0)

    def test_cap_radius_cancels_and_phi_changes_split(self):
        for radius in (0.5, 2.0, 7.0):
            for phi0 in (math.pi / 6.0, math.pi / 2.0, 5.0 * math.pi / 6.0):
                row = lab.sphere_cap(radius, phi0)
                self.assert_gauss_bonnet(row)
                self.assertAlmostEqual(row["curvature"], 2.0 * math.pi * (1.0 - math.cos(phi0)), places=11)
                self.assertAlmostEqual(row["boundary"], 2.0 * math.pi * math.cos(phi0), places=11)

    def test_simpson_converges_on_nonpolynomial_integrand(self):
        exact = 1.0 - math.cos(1.1)
        errors = [abs(lab.simpson(math.sin, 0.0, 1.1, n) - exact) for n in (4, 8, 16)]
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])
        self.assertGreater(errors[0] / errors[1], 14.0)
        self.assertGreater(errors[1] / errors[2], 14.0)

    def test_wrong_boundary_orientation_is_detectable(self):
        disk = lab.plane_disk()
        wrong_total = disk["curvature"] - disk["boundary"] + disk["corners"]
        self.assertAlmostEqual(wrong_total, -2.0 * math.pi)
        self.assertNotAlmostEqual(wrong_total, disk["target"])

    def test_radius_squared_and_cap_factor_support(self):
        # R cancels analytically, but this implementation constructs R^2 and 1/R^2.
        for radius in (1e-200,1e200):
            for fn in (lab.plane_disk,lab.sphere_octant,lab.sphere_cap,lab.cylinder_band):
                with self.subTest(radius=radius,fn=fn.__name__):
                    with self.assertRaises(ArithmeticError):fn(radius)
        with self.assertRaises(ArithmeticError):lab.sphere_cap(2.,math.ulp(0.),8)
        # A supported radius still gives the radius-independent pi/2 octant area term.
        self.assertAlmostEqual(lab.sphere_octant(.5,256)['curvature'],math.pi/2,places=10)

    def test_cap_large_radius_tiny_angle_cannot_return_infinite_terms(self):
        # Analytic boundary = 2*pi*cos(phi0), approximately 2*pi here.
        # The unreduced product (cos/(R*sin(phi0)))*R can overflow despite
        # finite square/reciprocal and the first division. Reject unsupported
        # arithmetic rather than returning a successful dictionary of infinities.
        for radius in (1e154,1e150):
            with self.subTest(radius=radius):
                with self.assertRaises(ArithmeticError):lab.sphere_cap(radius,1e-320,8)
        # Nearby supported parameter regimes still match the independent formula.
        for radius,phi0 in ((2.,1e-8),(1e150,1e-8),(1e154,1e-8)):
            row=lab.sphere_cap(radius,phi0,8)
            self.assertTrue(all(math.isfinite(value) for value in row.values()))
            self.assertAlmostEqual(row['boundary'],2*math.pi*math.cos(phi0),places=12)
            self.assertAlmostEqual(row['total'],2*math.pi,places=12)

    def test_reject_invalid_inputs(self):
        cases = [
            lambda: lab.plane_disk(0.0),
            lambda: lab.sphere_octant(float("inf")),
            lambda: lab.sphere_cap(2.0, 0.0),
            lambda: lab.sphere_cap(2.0, math.pi),
            lambda: lab.cylinder_band(2.0, -1.0),
            lambda: lab.simpson(math.sin, 0.0, 1.0, 3),
            lambda: lab.simpson(math.sin, 0.0, 1.0, True),
            lambda: lab.simpson(math.sin, 1.0, 1.0, 4),
        ]
        for case in cases:
            with self.assertRaises(ValueError):
                case()


if __name__ == "__main__":
    unittest.main()
