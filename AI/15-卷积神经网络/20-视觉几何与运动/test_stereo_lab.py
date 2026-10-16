"""Behavior checks; expected quantities use independent Fraction/ray equations."""
from fractions import Fraction as Q
from pathlib import Path
import json
import unittest
import numpy as np
import stereo_lab as s


class StereoChecks(unittest.TestCase):
    def test_known_projection_and_inverse(self):
        # Row-batch protocol is shared with the existing graphics renderer.
        p = np.array([[.3, 0., 2.], [-.2, .1, 1.], [.6, -.2, 4.]])
        left, right = s.stereo_project(p, 800, .1)
        np.testing.assert_allclose(left, [[120, 0], [-160, 80], [120, -40]], atol=1e-10, rtol=0)
        np.testing.assert_allclose(right, [[80, 0], [-240, 80], [100, -40]], atol=1e-10, rtol=0)
        np.testing.assert_allclose(s.reconstruct(left, right, 800, .1), p, atol=1e-10, rtol=0)

    def test_interval_is_exact_not_symmetric(self):
        for b, d, expected in [(.1, 40, [Q(80,41), Q(80,39)]),
                                (.05, 20, [Q(40,21), Q(40,19)])]:
            value = s.depth_interval(d, 1, 800, b)
            np.testing.assert_allclose(value, list(map(float,expected)), atol=1e-12, rtol=0)
            self.assertGreater(value[1]-2, 2-value[0])

    def test_ray_intersection_and_principal_offset(self):
        # Solve slopes a=X/Z and b=(X-B)/Z through a linear system.
        # This is an alternative to calling fB/d again.
        a, b = Q(3,20), Q(1,10)
        z = Q(1,10)/(a-b)
        x = a*z
        np.testing.assert_allclose([float(x), float(z)], [.3, 2.], atol=1e-12, rtol=0)
        left, right = s.stereo_project([[float(x), .25, float(z)]], 800, .1, [320,240])
        np.testing.assert_allclose(left, [[440,340]], atol=1e-10, rtol=0)
        np.testing.assert_allclose(s.reconstruct(left,right,800,.1,[320,240]),
                                   [[.3,.25,2]], atol=1e-10, rtol=0)

    def test_positive_scale_and_wrong_association(self):
        p = [[.3,0,2]]
        l, r = s.stereo_project(p,800,.1)
        l3, r3 = s.stereo_project(np.asarray(p)*3,800,.3)
        np.testing.assert_allclose(l3,l,atol=1e-10,rtol=0)
        np.testing.assert_allclose(r3,r,atol=1e-10,rtol=0)
        wrong = s.reconstruct([[120,0]],[[20,0]],800,.1)
        np.testing.assert_allclose(wrong,[[.12,0,.8]],atol=1e-10,rtol=0)
        np.testing.assert_allclose(s.stereo_project(wrong,800,.1),[[[120,0]],[[20,0]]],atol=1e-10,rtol=0)

    def test_invalid_model_and_pairs(self):
        calls = [
            lambda: s.project([[0,0,0]],800),
            lambda: s.project([[0,0,-1]],800),
            lambda: s.project([[0,0,1]],0),
            lambda: s.project([[0,0,1]],float('inf')),
            lambda: s.project([[0,float('nan'),1]],800),
            lambda: s.project([[0,0]],800),
            lambda: s.project([],800),
            lambda: s.project([[0,0,1]],800,[0]),
            lambda: s.stereo_project([[0,0,1]],800,-.1),
            lambda: s.stereo_project([[0,0,1]],800,0),
            lambda: s.stereo_project([[0,0,1]],800,True),
            lambda: s.reconstruct([[20,0]],[[20,0]],800,.1),
            lambda: s.reconstruct([[19,0]],[[20,0]],800,.1),
            lambda: s.reconstruct([[40,0]],[[20,1]],800,.1),
            lambda: s.reconstruct([[40,0]],[[20,0],[10,0]],800,.1),
            lambda: s.depth_interval(1,1,800,.1),
            lambda: s.depth_interval(1,2,800,.1),
            lambda: s.depth_interval(40,-1,800,.1),
        ]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()


if __name__ == '__main__':
    unittest.main()
