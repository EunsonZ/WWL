"""Independent original KCL/KVL integration and finite boundary regressions."""
import math
import unittest
from decimal import Decimal, localcontext
import numpy as np

from storage_models import rc_interval, piecewise_rc, rlc_state, storage_energy, mutual_energy


def rk4(field, state, final, n):
    x = np.array(state, dtype=float)
    step = final / n
    for _ in range(n):
        k1 = field(x)
        k2 = field(x + step * k1 / 2)
        k3 = field(x + step * k2 / 2)
        k4 = field(x + step * k3)
        x += step * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    return x


class Models(unittest.TestCase):
    def test_piecewise_values_and_contract(self):
        rows = [dict(duration_s=.001, source_V=1, source_R_ohm=1000, C_F=1e-6),
                dict(duration_s=.001, source_V=2, source_R_ohm=2000, C_F=1e-6, load_R_ohm=4000)]
        times, volts = piecewise_rc(.4, rows)
        self.assertEqual(times, [0, .001, .002])
        self.assertEqual(len(volts), len(rows) + 1)
        self.assertEqual(volts[0], .4)
        np.testing.assert_allclose(volts[1:], [.7792723352971346, 1.071613449682728], rtol=1e-14)
        first = rk4(lambda x: np.array([(1-x[0])/.001]), [.4], .001, 800)[0]
        second = rk4(lambda x: np.array([((2-x[0])/2000-x[0]/4000)/1e-6]), [first], .001, 800)[0]
        self.assertAlmostEqual(second, volts[-1], places=12)

    def test_rc_initial_cancellation_and_tiny_time(self):
        self.assertEqual(rc_interval(.4, 0, 1e16, 1000, 1e-6)[0], .4)
        value = rc_interval(.4, 1e-30, 1e16, 1000, 1e-6)[0]
        self.assertAlmostEqual(value, .4 + 1e-11, places=15)

    def test_loaded_rc_derived_ratio_overflow_is_explicit(self):
        # Finite input must not silently turn a nonzero source into zero.
        with self.assertRaises(ValueError):
            rc_interval(0, 1e-20, 1e308, 1e300, 1, 1e-20)

    def test_rlc_tiny_time_preserves_initial_and_source_response(self):
        self.assertEqual(rlc_state(1e-30, 50, .01, 1e-6, .4, 0, source=1e16)[0], .4)
        self.assertAlmostEqual(rlc_state(1e-20, 50, .01, 1e-6, .4, 0, source=1e16)[0], .4, places=15)
        v, i = rlc_state(1e-12, 50, .01, 1e-6, 0, 0, source=1)
        self.assertGreater(v, 0)
        self.assertAlmostEqual(v / 4.9999999916666665e-17, 1, places=14)
        self.assertAlmostEqual(i / 9.999999975e-11, 1, places=14)
        v, i = rlc_state(1e-12, 200, .01, 1e-6, 0, 0, topology='parallel', source=1)
        self.assertGreater(i, 0)
        self.assertAlmostEqual(i / 4.9999999916666665e-17, 1, places=14)
        self.assertAlmostEqual(v / 9.999999975e-7, 1, places=14)
        v, i = rlc_state(1e-30, 200, .01, 1e-6, .4, .004, topology='parallel', source=1e16)
        self.assertAlmostEqual(v, .4+1e-8, places=15)
        self.assertEqual(i, .004)

    def test_strong_overdamping_small_response_by_decimal_roots(self):
        with localcontext() as ctx:
            ctx.prec = 80
            d = Decimal
            r, l, c, t = d('2e8'), d('.01'), d('1e-6'), d('1e-7')
            alpha, w2 = r/(2*l), 1/(l*c)
            delta = (alpha*alpha-w2).sqrt()
            slow, fast = -alpha+delta, -alpha-delta
            # Independent high precision zero-state step solution.
            truth = 1-(fast*(slow*t).exp()-slow*(fast*t).exp())/(fast-slow)
        value = rlc_state(float(t), float(r), float(l), float(c), 0, 0, source=1)[0]
        self.assertGreater(value, 0)
        self.assertAlmostEqual(value/float(truth), 1, places=13)

    def test_all_damping_topologies_by_original_equations(self):
        l, c, final = .01, 1e-6, .0004
        for kind, resistors, source in [('series', [0, 50, 200, 400], .7), ('parallel', [200, 50, 25], .004)]:
            for r in resistors:
                if kind == 'series':
                    field = lambda x: np.array([x[1]/c, (source-r*x[1]-x[0])/l])
                else:
                    field = lambda x: np.array([(source-x[0]/r-x[1])/c, x[0]/l])
                truth = rk4(field, [.3, -.002], final, 1600)
                result = rlc_state(final, r, l, c, .3, -.002, topology=kind, source=source)
                np.testing.assert_allclose(result, truth, atol=3e-13, rtol=3e-11)

    def test_critical_and_nearcritical(self):
        t, w = .0003, 10000
        exact = (1+w*t)*math.exp(-w*t)
        self.assertAlmostEqual(rlc_state(t, 200, .01, 1e-6, 1, 0)[0], exact, places=15)
        for r in [200*(1-1e-10), 200*(1+1e-10)]:
            self.assertAlmostEqual(rlc_state(t, r, .01, 1e-6, 1, 0)[0], exact, places=9)

    def test_original_course_step_peak_and_power(self):
        wd = math.sqrt(1e8-2500**2)
        peak_time = math.pi / wd
        v, i = rlc_state(peak_time, 50, .01, 1e-6, 0, 0, source=1)
        self.assertAlmostEqual(v, 1+math.exp(-2500*peak_time), places=14)
        self.assertAlmostEqual(i, 0, places=15)
        self.assertAlmostEqual(peak_time, .00032446229407788894, places=16)

    def test_lossless_energy_and_euler_counterexample(self):
        e0 = .5e-6
        for t in np.linspace(0, .002, 31):
            v, i = rlc_state(t, 0, .01, 1e-6, 1, 0)
            self.assertAlmostEqual(storage_energy(v, i, .01, 1e-6), e0, places=19)
        x = np.array([1., 0.])
        h = 20e-6
        x += h*np.array([x[1]/1e-6, -x[0]/.01])
        self.assertGreater(storage_energy(*x, .01, 1e-6), e0)

    def test_energy_power_differential_balance(self):
        for kind, r, source in [('series', 50, .8), ('parallel', 200, .005)]:
            t, h = .00037, 1e-9
            xm = rlc_state(t-h, r, .01, 1e-6, .4, -.003, topology=kind, source=source)
            xp = rlc_state(t+h, r, .01, 1e-6, .4, -.003, topology=kind, source=source)
            v, i = rlc_state(t, r, .01, 1e-6, .4, -.003, topology=kind, source=source)
            derivative = (storage_energy(*xp, .01, 1e-6)-storage_energy(*xm, .01, 1e-6))/(2*h)
            power = source*i-r*i*i if kind == 'series' else source*v-v*v/r
            self.assertAlmostEqual(derivative, power, delta=2e-11)

    def test_mutual_energy_and_coordinate_reversal(self):
        e, a, b, m = mutual_energy(.02, -.005, .01, .04, .8)
        np.testing.assert_allclose([e, a, b, m], [.9e-6, .12e-3, .12e-3, .016], rtol=2e-15)
        reversed_e = mutual_energy(.02, .005, .01, .04, -.8)[0]
        self.assertAlmostEqual(reversed_e, e, places=20)
        self.assertAlmostEqual(mutual_energy(.02, -.01, .01, .04, 1)[0], 0, places=20)
        with self.assertRaises(ValueError): mutual_energy(.02, -.01, .01, .04, 1.25)

    def test_energy_integral_balance_independent_power(self):
        for kind, r, source in [('series', 50, .8), ('parallel', 200, .005)]:
            times = np.linspace(0, .001, 4001)
            vals = [rlc_state(t, r, .01, 1e-6, .4, -.003, topology=kind, source=source) for t in times]
            watts = [source*i-r*i*i if kind=='series' else source*v-v*v/r for v,i in vals]
            observed = np.trapezoid(watts, times)
            expected = storage_energy(*vals[-1], .01, 1e-6)-storage_energy(*vals[0], .01, 1e-6)
            self.assertAlmostEqual(observed, expected, delta=5e-12)

    def test_real_finite_inputs_and_invalid_intervals(self):
        for bad in [True, 1+0j, np.array(1+2j), np.array([1.]), [1.], float('nan'), float('inf'), 10**1000]:
            with self.assertRaises(ValueError): rc_interval(bad, .001, 1, 1000, 1e-6)
        for rows in [[], {}, [{}], [dict(duration_s=-1)], [dict(duration_s=.1, extra=3)]]:
            with self.assertRaises(ValueError): piecewise_rc(.4, rows)
        with self.assertRaises(ValueError): rlc_state(.1, 0, .01, 1e-6, 1, 0, topology='parallel')
        with self.assertRaises(ValueError): rlc_state(.1, 50, .01, 1e-6, 1+2j, 0)
        with self.assertRaises(ValueError): rlc_state(.1, 50, 1e308, 1e308, 1, 0)


if __name__ == '__main__':
    unittest.main()
