"""Independent rational objectives, noise moments and finite LMS enumeration."""
from fractions import Fraction as F
import itertools
import math
import unittest
import identification_lab as lab


def exact_two_parameter_objective(rows, y, lam, prior, center):
    # Independently build the weighted objective and use the 2x2 determinant,
    # rather than calling lab.batch, lab.solve, or its recursive update.
    n = len(rows)
    aa, bb, cc = prior*lam**n, F(0), prior*lam**n
    p, q = aa*center[0], cc*center[1]
    for k, ((u, v), d) in enumerate(zip(rows, y)):
        weight = lam**(n-k-1)
        aa += weight*u*u
        bb += weight*u*v
        cc += weight*v*v
        p += weight*u*d
        q += weight*v*d
    det = aa*cc-bb*bb
    return [(cc*p-bb*q)/det, (aa*q-bb*p)/det]


class IdentificationTests(unittest.TestCase):
    def test_impulse_and_constant_information(self):
        truth = [F(1, 2), F(-1, 4)]
        self.assertEqual([sum(h for h in truth)]*3, [F(1, 4)]*3)
        self.assertEqual(lab.solve([[1, 0], [0, 1]], [.5, -.25]), [.5, -.25])
        with self.assertRaises(ValueError): lab.solve([[3, 3], [3, 3]], [.75, .75])
        # One finite impulse identifies both, yet the average information tends 0.
        impulse_rows = [[F(1), F(0)], [F(0), F(1)]]+[[F(0), F(0)]]*998
        average = [[sum(row[i]*row[j] for row in impulse_rows)/1000 for j in range(2)] for i in range(2)]
        self.assertEqual(average, [[F(1, 1000), F(0)], [F(0), F(1, 1000)]])

    def test_RLS_matches_exact_weighted_prior_every_prefix(self):
        rows = [[F(1), F(0)], [F(0), F(1)], [F(1), F(1)]]
        y = [F(1, 2), F(-1, 4), F(1, 4)]
        for lam, expected in [(F(1), [F(9, 32), F(-3, 32)]),
                              (F(1, 2), [F(31, 79), F(-13, 79)])]:
            self.assertEqual(exact_two_parameter_objective(rows, y, lam, F(1), [F(0), F(0)]), expected)
            for center in [[F(0), F(0)], [F(1, 3), F(-2, 5)]]:
                online = lab.rls(rows, y, lam=float(lam), prior=1., theta0=center)
                for k in range(1, 4):
                    oracle = exact_two_parameter_objective(rows[:k], y[:k], lam, F(1), center)
                    batch = lab.batch(rows[:k], y[:k], lam=float(lam), prior=1., theta0=center)
                    for a, b, c in zip(online['trajectory'][k-1], batch['theta'], oracle):
                        self.assertAlmostEqual(a, float(c), places=13)
                        self.assertAlmostEqual(b, float(c), places=13)

    def test_measurement_noise_path_exact_covariance(self):
        moments = []
        ideal = []
        for signs in itertools.product([-1, 1], repeat=4):
            xold, vold, vnow, wnow = map(F, signs)
            vold, vnow = vold/2, vnow/2
            effective = wnow+vnow-vold/2
            moments.append((xold+vold)*effective)
            ideal.append(xold*wnow)
        self.assertEqual(sum(ideal)/len(ideal), 0)
        self.assertEqual(sum(moments)/len(moments), F(-1, 8))
        self.assertEqual(F(1, 2)/F(5, 4), F(2, 5))

    def test_closed_loop_OLS_and_reference_IV_four_states(self):
        for kappa, expected_OLS in [(F(0), F(1, 2)), (F(1), F(-1, 4))]:
            data = []
            for r, e in itertools.product([F(-1), F(1)], repeat=2):
                u = (r-kappa*e)/(1+kappa/2)
                y = u/2+e
                data.append((r, e, u, y))
            OLS = sum(u*y for _, _, u, y in data)/sum(u*u for _, _, u, _ in data)
            IV = sum(r*y for r, _, _, y in data)/sum(r*u for r, _, u, _ in data)
            self.assertEqual(OLS, expected_OLS)
            self.assertEqual(IV, F(1, 2))

    def test_LMS_mean_does_not_imply_mean_square(self):
        mu, root = 1.5, math.sqrt(2)
        initial_error = [1., 2.]
        outputs = []
        for phi in [[root, 0.], [-root, 0.], [0., root], [0., -root]]:
            # lab starts at zero; theta*=-initial_error, noiseless target.
            truth = [-v for v in initial_error]
            y = sum(a*b for a, b in zip(phi, truth))
            theta = lab.lms([phi], [y], mu=mu)['theta']
            outputs.append([a-b for a, b in zip(theta, truth)])
        mean = [sum(v[i] for v in outputs)/4 for i in range(2)]
        for a, b in zip(mean, initial_error): self.assertAlmostEqual(a, -.5*b, places=13)
        self.assertAlmostEqual(sum(sum(x*x for x in a) for a in outputs)/4, 2.5*5, places=12)

    def test_parameter_coordinates_preserve_prior_objective(self):
        theta, center, D = [F(1, 2), F(-1, 4)], [F(1, 5), F(-1, 3)], [F(10), F(1, 10)]
        z, z0 = [theta[i]/D[i] for i in range(2)], [center[i]/D[i] for i in range(2)]
        for phi in [[F(1), F(2)], [F(-1), F(3)]]:
            self.assertEqual(sum(phi[i]*theta[i] for i in range(2)), sum(phi[i]*D[i]*z[i] for i in range(2)))
        original = sum((theta[i]-center[i])**2 for i in range(2))
        transformed = sum(D[i]**2*(z[i]-z0[i])**2 for i in range(2))
        self.assertEqual(original, transformed)
        self.assertNotEqual(original, sum((z[i]-z0[i])**2 for i in range(2)))

    def test_one_step_and_free_run_have_different_histories(self):
        # A short record may fit with tiny one-step residual while unstable
        # free-run errors multiply 1.1 each step; exact algebra, not a plot.
        coefficient, delta = F(11, 10), F(1, 100)
        observed = [coefficient**k for k in range(101)]
        result = lab.ar_predictions([coefficient, F(0)], observed, [F(0)]*101, 1, free_initial=1-delta)
        self.assertEqual(result['one_step'], observed[1:])
        for k, free in enumerate(result['free_run'], start=1):
            self.assertEqual(observed[k]-free, delta*coefficient**k)
        self.assertGreater(observed[-1]-result['free_run'][-1], delta)

    def test_AR_report_input_residual_lags_use_physical_time(self):
        # First pin the centering, lag sign and full-window denominator on
        # an exact finite fixture. This is not a fitted-parameter oracle.
        finite = lab.diagnostics([F(1), F(4), F(-2)], [F(2), F(-1), F(3)], maxlag=2)
        self.assertEqual(finite['input_residual_covariance'], [F(-4), F(5, 3), F(0)])
        # Then check the actual AR report against independently indexed raw
        # physical samples. This catches a call-site u[k-1]/e[k] shift even
        # when diagnostics itself is correct. No lab prediction/diagnostic
        # helper is used in this second oracle path.
        report, data = lab.experiments()
        raw = list(data['ar'])
        start, stop = report['AR_splits']['test']
        n = stop-start
        u = [row[1] for row in raw]
        input_mean = sum(u[start:stop])/n
        for name, output_column in [('ideal_observation', 2), ('output_measurement_noise', 3)]:
            fitted = report['same_physical_AR_two_noise_paths'][name]
            a, b = fitted['fit']['theta']
            error = [raw[k][output_column]-a*raw[k-1][output_column]-b*u[k-1]
                     for k in range(start, stop)]
            error_mean = sum(error)/n
            expected = [sum((u[k-lag]-input_mean)*(error[k-start]-error_mean)
                            for k in range(start+lag, stop))/n for lag in range(9)]
            actual = fitted['diagnostics']['input_residual_covariance']
            self.assertEqual(len(actual), 9)
            for lag, (observed, oracle) in enumerate(zip(actual, expected)):
                with self.subTest(model=name, physical_lag=lag):
                    self.assertAlmostEqual(observed, oracle, places=13)

    def test_shapes_nonfinite_and_parameter_domains(self):
        for rows, y in [([], []), ([[1., 2.]], []), ([[float('nan')]], [1.])]:
            with self.assertRaises(ValueError): lab.rls(rows, y)
        for lam in [0., 1.1, float('nan')]:
            with self.assertRaises(ValueError): lab.batch([[1., 0.]], [1.], lam=lam)
        for mu in [0., -1., float('inf')]:
            with self.assertRaises(ValueError): lab.lms([[1.]], [1.], mu=mu)
        with self.assertRaises(ValueError): lab.rls([[1., 0.]], [1.], theta0=[0.])


if __name__ == '__main__':
    unittest.main()
