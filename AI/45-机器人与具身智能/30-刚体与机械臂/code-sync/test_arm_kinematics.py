"""Finite analytic expectations and derivative checks, not hardware acceptance."""
import importlib.util
import os
from pathlib import Path
import unittest
import numpy as np

SPEC = importlib.util.spec_from_file_location('arm', Path(__file__).with_name('arm_kinematics.py'))
arm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arm)


class ArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        arm.set_base(os.environ.get('WWL_ROBOTICS_BASE'))

    def test_chain_and_regular_closed_form(self):
        t, elbow, endpoint = arm.forward([np.pi/6, -np.pi/3])
        np.testing.assert_allclose(elbow, [np.sqrt(3)/2, .5], atol=1e-14)
        np.testing.assert_allclose(endpoint, [np.sqrt(3), 0], atol=1e-14)
        np.testing.assert_allclose(t[:2, :2], arm.base().rotation(-np.pi/6), atol=1e-14)
        np.testing.assert_allclose(arm.jacobian([np.pi/6, -np.pi/3]),
                                   [[0., .5], [np.sqrt(3), np.sqrt(3)/2]], atol=1e-14)
        # Translation/rotation order already shares se2; this detects reversed chain factors.
        np.testing.assert_allclose(arm.forward([np.pi/2, 0])[2], [0, 2], atol=1e-14)

    def test_position_jacobian_differences_and_frame_change(self):
        h, worst = 1e-6, 0.
        for lengths in ([1., 1.], [1.3, .8]):
            for q in ([0., 0.], [.2, -1.1], [1., np.pi], [-.7, 1.2]):
                q = np.array(q)
                fd = np.column_stack([(arm.forward(q+h*np.eye(2)[i], lengths)[2]
                                        -arm.forward(q-h*np.eye(2)[i], lengths)[2])/(2*h)
                                       for i in range(2)])
                j = arm.jacobian(q, lengths)
                worst = max(worst, float(np.max(np.abs(fd-j))))
                np.testing.assert_allclose(fd, j, atol=5e-9, rtol=0)
                # A fixed observer rotation maps endpoint velocities, not qdot.
                r = arm.base().rotation(.4)
                force, qdot = np.array([2., -3.]), np.array([.3, .2])
                np.testing.assert_allclose((r@j).T@(r@force), j.T@force, atol=1e-14)
                self.assertAlmostEqual(float((r@force)@((r@j)@qdot)), float(force@(j@qdot)), places=13)
        print('author central-difference max_abs_error', worst)

    def test_inverse_branches_boundaries_family_and_hole(self):
        answer = arm.inverse([1., 1.])
        self.assertEqual(answer['kind'], 'two_branches')
        np.testing.assert_allclose(answer['branches'], [[0, np.pi/2], [np.pi/2, -np.pi/2]], atol=1e-14)
        for lengths, target in [([1.,1.],[1.,1.]), ([1.5,1.],[.5,0.]),
                                ([1.,1.5],[.5,0.]), ([1.,1.],[2.,0.]),
                                ([1.3,.8],[-.5,1.])]:
            result = arm.inverse(target, lengths)
            for q in result['branches']:
                np.testing.assert_allclose(arm.forward(q, lengths)[2], target, atol=1e-12)
        self.assertEqual(arm.inverse([0.,0.])['kind'], 'continuum')
        for q1 in [-2., -.3, 0., .7, 2.]:
            np.testing.assert_allclose(arm.forward([q1, np.pi])[2], [0.,0.], atol=1e-14)
        self.assertEqual(arm.inverse([.25,0.], [1.5,1.])['kind'], 'unreachable')
        self.assertEqual(arm.inverse([2.1,0.])['kind'], 'unreachable')
        self.assertEqual(arm.inverse([2.+1e-14,0.])['kind'], 'boundary')

    def test_singular_task_and_finite_null_curve(self):
        j = arm.jacobian([0.,0.])
        np.testing.assert_array_equal(j, [[0.,0.], [2.,1.]])
        self.assertEqual(np.linalg.matrix_rank(j), 1)
        self.assertEqual(np.linalg.matrix_rank(arm.pose_jacobian([0.,0.])), 2)
        np.testing.assert_array_equal(j@np.array([1.,-2.]), [0.,0.])
        for epsilon in [.005,.02,.1]:
            endpoint = arm.forward([epsilon,-2*epsilon])[2]
            np.testing.assert_allclose(endpoint, [2*np.cos(epsilon), 0.], atol=1e-14)
            self.assertGreater(2.-endpoint[0], 0.)
        with self.assertRaises(ValueError):
            arm.speed_request([0.,0.], [-.1,0.], 1.)

    def test_power_and_near_singular_limit(self):
        p = arm.power([0.,0.], [.3,-.2], [3.,-2.])
        np.testing.assert_allclose(p['velocity_m_s'], [0.,.4], atol=1e-14)
        np.testing.assert_allclose(p['torque_N_m'], [-4.,-2.], atol=1e-14)
        self.assertAlmostEqual(p['joint_power_W'], -.8)
        self.assertAlmostEqual(p['endpoint_power_W'], -.8)
        for epsilon in [.5,.1,.02,.005]:
            request = arm.speed_request([0.,epsilon], [-.1,0.], 1.)
            expected = [-.1/np.tan(epsilon), .1*(1+np.cos(epsilon))/np.sin(epsilon)]
            np.testing.assert_allclose(request['demand_rad_s'], expected, atol=1e-10)
            self.assertLessEqual(max(abs(np.array(request['scaled_rad_s']))), 1.+1e-14)
            np.testing.assert_allclose(request['scaled_velocity_m_s'], [-.1*request['scale'],0.], atol=1e-14)

    def test_reject_wrong_shapes_and_nonfinite(self):
        for q, lengths in [([0.,0.],[0.,1.]), ([0.,0.],[-1.,1.]), ([float('nan'),0.],[1.,1.]),
                           ([0.,0.,0.],[1.,1.]), ([0.,0.],[1.,float('inf')])]:
            with self.assertRaises(ValueError):
                arm.forward(q, lengths)
        with self.assertRaises(ValueError):
            arm.power([0.,0.], [.2,.3], [1.,2.,3.])


if __name__ == '__main__':
    unittest.main(verbosity=2)
