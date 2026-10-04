"""Independent geometry checks for the graph/flux illustration."""
import unittest
import numpy as np

import surface_flux_figures as model


class SurfaceFluxTests(unittest.TestCase):
    def test_derivatives_against_position_differences(self):
        h = 1e-5
        for u, v in [(0, 0), (.5, .5), (.2, .8), (1, 1)]:
            a, b = model.tangents(u, v)
            np.testing.assert_allclose(a, (model.points(u+h, v)-model.points(u-h, v))/(2*h), atol=2e-11)
            np.testing.assert_allclose(b, (model.points(u, v+h)-model.points(u, v-h))/(2*h), atol=2e-11)

    def test_gram_and_unit_normal_are_different_objects(self):
        a, b = model.tangents(.5, .5)
        n = model.normal_area(.5, .5)
        np.testing.assert_array_equal(n, [-1, -1, 1])
        gram = np.array([[a@a, a@b], [a@b, b@b]])
        self.assertAlmostEqual(np.linalg.det(gram), 3)
        self.assertAlmostEqual(n@n, np.linalg.det(gram))
        self.assertAlmostEqual(n@a, 0); self.assertAlmostEqual(n@b, 0)
        self.assertAlmostEqual(np.linalg.norm(n/np.linalg.norm(n)), 1)
        # Vertical field has projected magnitude 1/sqrt(3), not sqrt(3).
        self.assertAlmostEqual((n/np.linalg.norm(n))[2]*np.sqrt(3), 1)

    def test_flux_area_and_orientation_independent_references(self):
        area = model.integrate_square(lambda u, v: np.sqrt(1+4*u*u+4*v*v), 40)
        self.assertAlmostEqual(area, model.exact_area(), places=12)
        self.assertGreater(area, 1); self.assertLess(area, 3)
        up = model.integrate_square(lambda u, v: model.normal_area(u, v)[..., 2])
        down = model.integrate_square(lambda u, v: -model.normal_area(u, v)[..., 2])
        self.assertAlmostEqual(up, 1); self.assertAlmostEqual(down, -1)

    def test_coordinate_swap_requires_orientation_correction(self):
        # rho(s,t)=r(t,s); differentiate in the new order (s,t).
        a, b = model.tangents(.8, .2)
        swapped = np.cross(b, a)
        np.testing.assert_allclose(swapped, -model.normal_area(.8, .2))
        self.assertLess(swapped[2], 0)
        self.assertAlmostEqual((-swapped)[2], 1)

    def test_rescaling_preserves_surface_area_and_flux(self):
        # rho(s,t)=r(2s,t), 0<=s<=1/2, 0<=t<=1.
        # Map quadrature a in [0,1] to s=a/2: density factor 2 cancels ds=da/2.
        rescaled = model.integrate_square(lambda a, t: .5*np.linalg.norm(
            np.cross(2*model.tangents(a, t)[0], model.tangents(a, t)[1]), axis=-1))
        self.assertAlmostEqual(rescaled, model.exact_area(), places=12)
        flux = model.integrate_square(lambda a, t: .5*np.cross(
            2*model.tangents(a, t)[0], model.tangents(a, t)[1])[..., 2])
        self.assertAlmostEqual(flux, 1)

    def test_finite_patch_is_only_first_order_tangent_approximation(self):
        p = model.points(.5, .5)
        a, _ = model.tangents(.5, .5)
        errors = [np.linalg.norm(model.points(.5+h, .5)-p-h*a) for h in [.2, .1]]
        self.assertAlmostEqual(errors[0], .04)
        self.assertAlmostEqual(errors[1], .01)
        self.assertAlmostEqual(errors[0]/errors[1], 4)

    def test_transfer_nonvertical_field_and_new_domain(self):
        # r(s,t)=(2s,t,8s*s+t*t), downward orientation.
        def density(s, t):
            rs = np.stack((2*np.ones_like(s), np.zeros_like(s), 16*s), axis=-1)
            rt = np.stack((np.zeros_like(t), np.ones_like(t), 2*t), axis=-1)
            field = np.stack((2*s, np.zeros_like(s), np.ones_like(s)), axis=-1)
            return np.sum(field*(-np.cross(rs, rt)), axis=-1)
        self.assertAlmostEqual(model.integrate_square(density), 26/3, places=12)

    def test_invalid_inputs_are_rejected(self):
        for bad in [float("nan"), float("inf")]:
            with self.assertRaises(ValueError): model.points(bad, .5)
        for bad in [0, -1, 2.5, True]:
            with self.assertRaises(ValueError): model.integrate_square(lambda u, v: u, bad)
        with self.assertRaises(ValueError): model.integrate_square(lambda u, v: np.nan*u)


if __name__ == "__main__":
    unittest.main()
