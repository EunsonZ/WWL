"""Independent ambient formulas, invariants, and invalid-input tests."""
import unittest
import numpy as np
import geometry_lab as lab


class GeometryTests(unittest.TestCase):
    def test_frenet_ambient_derivatives(self):
        for t in (0, .4, 1.7):
            frame, kappa, tau = lab.helix_frame(t)
            np.testing.assert_allclose(frame.T@frame, np.eye(3), atol=1e-14)
            self.assertAlmostEqual(np.linalg.det(frame), 1)
            first = np.array([-2*np.sin(t), 2*np.cos(t), 1])
            second = np.array([-2*np.cos(t), -2*np.sin(t), 0])
            third = np.array([2*np.sin(t), -2*np.cos(t), 0])
            cross = np.cross(first, second)
            self.assertAlmostEqual(kappa, np.linalg.norm(cross)/np.linalg.norm(first)**3)
            self.assertAlmostEqual(tau, np.dot(cross, third)/np.dot(cross, cross))

    def test_shape_from_normal_differential(self):
        for kind in ("sphere", "cylinder"):
            metric, second, shape = lab.forms(kind, 2)
            np.testing.assert_allclose(metric@shape, second)
            expected = [-.5, -.5] if kind == "sphere" else [-.5, 0]
            np.testing.assert_allclose(np.diag(shape), expected)
        # Independent finite differences of the ambient OUTWARD normal.
        phi, theta, h = np.pi/3, .4, 1e-5
        sphere_basis = np.column_stack([
            2*np.array([np.cos(phi)*np.cos(theta), np.cos(phi)*np.sin(theta), -np.sin(phi)]),
            2*np.array([-np.sin(phi)*np.sin(theta), np.sin(phi)*np.cos(theta), 0])])
        def normal(ph, th):
            return np.array([np.sin(ph)*np.cos(th), np.sin(ph)*np.sin(th), np.cos(ph)])
        dnormal = np.column_stack([(normal(phi+h,theta)-normal(phi-h,theta))/(2*h),
                                    (normal(phi,theta+h)-normal(phi,theta-h))/(2*h)])
        _, _, shape = lab.forms("sphere", 2, phi)
        np.testing.assert_allclose(sphere_basis@shape, -dnormal, atol=2e-11)
        cylinder_basis = np.column_stack([2*np.array([-np.sin(theta),np.cos(theta),0]), [0,0,1]])
        dnormal = np.column_stack([np.array([-np.sin(theta),np.cos(theta),0]), [0,0,0]])
        _, _, shape = lab.forms("cylinder", 2)
        np.testing.assert_allclose(cylinder_basis@shape, -dnormal, atol=1e-14)

    def test_sphere_convergence_and_invariants(self):
        errors = []
        for n in (10, 20, 40):
            s, y = lab.integrate_sphere([np.pi/3, 0, 0, 1/np.sqrt(3)], steps=n)
            xyz = lab.sphere_xyz(y[:, :2]); exact = lab.great_circle(s)
            np.testing.assert_allclose(np.linalg.norm(exact, axis=1), 2, atol=1e-14)
            errors.append(np.max(np.linalg.norm(xyz-exact, axis=1)))
            speed2, angular = lab.invariants(y)
            self.assertLess(np.max(abs(speed2-1)), 2e-6)
            self.assertLess(np.max(abs(angular-np.sqrt(3))), 2e-6)
        for coarse, fine in zip(errors, errors[1:]):
            self.assertGreater(coarse/fine, 12)
            self.assertLess(coarse/fine, 20)

    def test_equator_and_meridian(self):
        s, y = lab.integrate_sphere([np.pi/2, 0, 0, .5], steps=20)
        np.testing.assert_allclose(y[:, 0], np.pi/2, atol=1e-14)
        np.testing.assert_allclose(y[:, 1], s/2, atol=1e-14)
        s, y = lab.integrate_sphere([np.pi/3, 0, .5, 0], length=.5, steps=10)
        np.testing.assert_allclose(y[:, 0], np.pi/3+s/2, atol=1e-14)

    def test_cylinder_global_branches(self):
        values = dict(lab.cylinder_branches())
        self.assertAlmostEqual(values[0], np.pi*np.sqrt(5)/2)
        # Independent lift: Euclidean endpoint difference, Pythagoras
        for k, length in values.items():
            delta = np.array([np.pi+4*np.pi*k, np.pi/2])
            self.assertAlmostEqual(length, np.linalg.norm(delta))
        self.assertEqual(min(values, key=values.get), 0)
        tie = dict(lab.cylinder_branches(delta_theta=np.pi, delta_z=0, windings=(-1, 0)))
        self.assertAlmostEqual(tie[-1], tie[0])

    def test_reject_invalid_inputs(self):
        cases = [lambda: lab.forms("sphere", 0), lambda: lab.forms("sphere", 1e308), lambda: lab.forms("sphere", 2, 0),
                 lambda: lab.forms("x", 2), lambda: lab.helix_frame(float("nan")),
                 lambda: lab.sphere_xyz([1]), lambda: lab.sphere_xyz(np.empty((0,2))), lambda: lab.great_circle([]), lambda: lab.sphere_xyz([1, float("inf")]),
                 lambda: lab.integrate_sphere([0,0,1,0]),
                 lambda: lab.integrate_sphere([1,0,1,0], steps=0),
                 lambda: lab.integrate_sphere([1,0,1,0], steps=True),
                 lambda: lab.integrate_sphere([1,0,1,0], length=float("nan")),
                 lambda: lab.invariants(np.empty((0,4))),
                 lambda: lab.cylinder_branches(windings=[]),
                 lambda: lab.cylinder_branches(windings=[.5])]
        for case in cases:
            with self.assertRaises(ValueError): case()


if __name__ == "__main__": unittest.main()
