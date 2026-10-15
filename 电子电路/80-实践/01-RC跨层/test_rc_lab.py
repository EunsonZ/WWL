"""Independent physical/analytic expectations plus adversarial contracts."""
import math
import unittest
import numpy as np
from rc_lab import RC, QFormat


class RCTest(unittest.TestCase):
    def test_hand_values_and_units(self):
        rc = RC()
        self.assertAlmostEqual(rc.tau, 0.001)
        self.assertAlmostEqual(rc.step([0.001])[0], 0.6321205588285577)
        self.assertAlmostEqual(abs(rc.frequency([1/(2*math.pi*.001)])[0]), 1/math.sqrt(2))
        self.assertAlmostEqual(np.angle(rc.frequency([1/(2*math.pi*.001)])[0]), -math.pi/4)

    def test_loaded_dc_kcl_independent(self):
        rc = RC(rs=200, rl=10000)
        dc = rc.step([1], level=1)[0]
        # DC capacitor current is zero: source current equals load current.
        self.assertAlmostEqual((1-dc)/1200, dc/10000)
        self.assertAlmostEqual(rc.tau, (1/(1/1200+1/10000))*1e-6)
        self.assertAlmostEqual(rc.step([0], v0=.4)[0], .4)

    def test_exact_samples_against_continuous_ivp(self):
        rc = RC(c=1.3e-6, rs=50, rl=5000)
        h = .0007
        y = rc.simulate(np.ones(20)*.8, h, v0=-.2)
        # Independently solve C v' = U/Rt - (1/Rt+1/RL)v.
        rate = (1/1050 + 1/5000)/1.3e-6
        steady = (.8/1050)/(1/1050+1/5000)
        ref = steady + (-.2-steady)*np.exp(-rate*np.arange(21)*h)
        np.testing.assert_allclose(y, ref, rtol=3e-15, atol=3e-16)

    def test_piecewise_input_integral_and_blocks(self):
        rc = RC()
        u = np.array([1., -1., .5, .5, 0., 0., 1.])
        h = .00025
        y = rc.simulate(u, h, v0=.2)
        # Duhamel integral summed per hold interval, independent of recurrence.
        t = len(u)*h
        ref = .2*math.exp(-t/.001)
        for j, uj in enumerate(u):
            ref += uj*(math.exp(-(t-(j+1)*h)/.001)-math.exp(-(t-j*h)/.001))
        self.assertAlmostEqual(y[-1], ref, places=14)
        first = rc.simulate(u[:3], h, v0=.2)
        last = rc.simulate(u[3:], h, v0=first[-1])
        np.testing.assert_array_equal(y, np.r_[first, last[1:]])

    def test_zero_input_energy_balance(self):
        rc = RC(rs=200, rl=10000)
        t = np.linspace(0, .01, 101)
        v = rc.step(t, level=0, v0=.8)
        e = .5*rc.c*v*v
        self.assertTrue(np.all(np.diff(e) < 0))
        # Integral of losses: (1/Rt+1/RL)*v0^2*tau/2*(1-exp(-2t/tau)).
        dissipated = (1/1200+1/10000)*.8**2*rc.tau/2*(1-np.exp(-2*t/rc.tau))
        np.testing.assert_allclose(e+dissipated, .5*1e-6*.8**2, rtol=5e-15)

    def test_euler_accuracy_order_and_instability(self):
        rc = RC()
        errors = []
        for n in (20, 40, 80):
            y = rc.simulate(np.ones(n), .001/n, method="euler")
            errors.append(abs(y[-1]-(1-math.exp(-1))))
        self.assertTrue(1.95 < errors[0]/errors[1] < 2.08)
        self.assertTrue(1.95 < errors[1]/errors[2] < 2.08)
        y = rc.simulate(np.ones(4), .0025, method="euler")
        np.testing.assert_allclose(y, [0, 2.5, -1.25, 4.375, -4.0625])
        exact = rc.simulate(np.ones(4), .0025)
        self.assertTrue(np.all((exact >= 0) & (exact < 1)))
        self.assertEqual(rc.coefficients(.002, "euler")[0], -1)

    def test_convex_hull_and_initial_response(self):
        rc = RC(rl=2000)
        u = np.array([-1, 2, .5, -2, 0])
        y = rc.simulate(u, .005, v0=.3)
        lo, hi = min(.3, rc.gain*u.min()), max(.3, rc.gain*u.max())
        self.assertTrue(np.all((y >= lo) & (y <= hi)))
        a = rc.step([0, .001], v0=.3)
        b = rc.step([0, .001], v0=0)
        np.testing.assert_allclose(a-b, .3*np.exp(-np.array([0,.001])/rc.tau))

    def test_fixed_point_rounding_saturation_and_error_bound(self):
        q = QFormat()
        self.assertEqual(q(.5*q.quantum), 0)
        self.assertEqual(q(1.5*q.quantum), 2*q.quantum)
        self.assertEqual(q(100), 2-q.quantum)
        self.assertEqual(q(-100), -2)
        rc, h = RC(), .00025
        exact = rc.simulate(np.ones(40), h)
        quant = rc.simulate(np.ones(40), h, quantizer=q)
        a, b = rc.coefficients(h)
        aq = q(a)
        # No saturation here. Coefficient defects and state rounding each <= q/2.
        # States/reference/input are <=1, so per-step defect <=1.5q.
        bound = 1.5*q.quantum/(1-abs(aq))
        self.assertLessEqual(np.max(np.abs(quant-exact)), bound)
        first = rc.simulate(np.ones(13), h, quantizer=q)
        rest = rc.simulate(np.ones(27), h, v0=first[-1], quantizer=q)
        np.testing.assert_array_equal(quant, np.r_[first, rest[1:]])

    def test_tiny_step_does_not_cancel(self):
        b = RC().coefficients(1e-20)[1]
        self.assertGreater(b, 0)
        self.assertAlmostEqual(b/1e-17, 1)

    def test_invalid_parameters_and_shapes(self):
        for kw in ({"r":0},{"c":-1},{"rs":-1},{"rl":0},{"r":math.nan},
                   {"c":math.inf},{"rl":-math.inf},{"r":1e308,"rs":1e308}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                RC(**kw)
        rc = RC()
        for args in (([1],0),([1],-1),([math.nan],.001),([[1]],.001)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                rc.simulate(*args)
        with self.assertRaises(ValueError): rc.simulate([1], .001, method="bogus")
        with self.assertRaises(ValueError): rc.step([-1])
        with self.assertRaises(ValueError): rc.step([1,0])
        with self.assertRaises(ValueError): rc.frequency([-1])
        with self.assertRaises(ValueError): rc.simulate([1], .001, v0=math.inf)
        with self.assertRaises(ValueError): QFormat(fractional_bits=16)
        with self.assertRaises(ValueError): QFormat(total_bits=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
