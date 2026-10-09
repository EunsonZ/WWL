"""Independent deterministic checks; no Monte Carlo experiment on import."""
import json
import math
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import ou_lab


C = json.loads(Path(__file__).with_name('fixed-input.json').read_text())


def kernel_mse(c, m):
    """Independent integral of exact kernel minus EM kernel, Decimal 60 digits.
    It never calls ou_lab.analytic or uses fine EM as truth.
    """
    with localcontext() as context:
        context.prec = 60
        k, s, T = (Decimal(str(c[key])) for key in ('kappa', 'sigma', 'T'))
        h = T / m
        a = 1 - k * h
        mean_error = (Decimal(str(c['x0'])) - Decimal(str(c['mu']))) * (a ** m - (-k * T).exp())
        noise = Decimal(0)
        for j in range(m):
            lo, hi = j * h, (j + 1) * h
            first = ((-k * lo).exp() - (-k * hi).exp()) / k
            second = ((-2 * k * lo).exp() - (-2 * k * hi).exp()) / (2 * k)
            noise += a ** (2 * j) * h - 2 * a ** j * first + second
        return float(mean_error ** 2 + s ** 2 * noise)


class OUChecks(unittest.TestCase):
    def test_analytic_mse_against_independent_kernel_integral(self):
        for m in C['steps']:
            expected = kernel_mse(C, m)
            self.assertAlmostEqual(ou_lab.analytic(C, m)['strong_mse'], expected, delta=2e-15)

    def test_exact_transition_moments_via_independent_recurrence(self):
        mt, vt = ou_lab.exact_moments(C)
        for m in C['steps']:
            r = math.exp(-C['kappa'] * C['T'] / m)
            local_var = C['sigma'] ** 2 * (1 - r * r) / (2 * C['kappa'])
            mean, var = C['x0'], 0.0
            for _ in range(m):
                mean = C['mu'] + r * (mean - C['mu'])
                var = r * r * var + local_var
            self.assertAlmostEqual(mean, mt, delta=2e-15)
            self.assertAlmostEqual(var, vt, delta=2e-15)

    def test_joint_gaussian_covariance_by_linear_map(self):
        h = C['T'] / C['fine_steps']
        _, v, cov, residual = ou_lab.segment_constants(C['kappa'], h)
        transform = np.array([[math.sqrt(h), 0.0], [cov / math.sqrt(h), math.sqrt(residual)]])
        np.testing.assert_allclose(transform @ transform.T, [[h, cov], [cov, v]], rtol=2e-15, atol=1e-17)

    def test_coarse_aggregation_is_associative_and_same_brownian(self):
        dw = np.arange(16, dtype=float).reshape(2, 8) / 31
        j = np.arange(16, dtype=float).reshape(2, 8) / 43
        d4, j4 = ou_lab.aggregate_segments(dw, j, 4, C['kappa'], C['T'])
        d2, j2 = ou_lab.aggregate_segments(d4, j4, 2, C['kappa'], C['T'])
        direct_d2, direct_j2 = ou_lab.aggregate_segments(dw, j, 2, C['kappa'], C['T'])
        np.testing.assert_allclose(d2, direct_d2, rtol=1e-15)
        np.testing.assert_allclose(j2, direct_j2, rtol=1e-15)
        np.testing.assert_allclose(d2.sum(axis=1), dw.sum(axis=1), rtol=1e-15)
        fine = ou_lab.evolve(j, math.exp(-C['kappa'] * C['T'] / 8), C['sigma'], C['x0'], C['mu'])
        coarse = ou_lab.evolve(j2, math.exp(-C['kappa'] * C['T'] / 2), C['sigma'], C['x0'], C['mu'])
        np.testing.assert_allclose(coarse, fine[:, ::4], rtol=1e-15, atol=1e-15)

    def test_independent_noise_is_a_negative_control(self):
        _, vt = ou_lab.exact_moments(C)
        fine = ou_lab.analytic(C, 4096)
        self.assertGreater(fine['independent_noise_mse'], 1.99 * vt)
        self.assertLess(fine['strong_mse'], 1e-7)

    def test_rejects_invalid_grids_and_unstable_scope(self):
        for patch in ({'steps': [7]}, {'sigma': -1}, {'steps': [1]}, {'seed': C['independent_seed']}):
            with self.assertRaises(ValueError):
                ou_lab.validate(dict(C, **patch))


if __name__ == '__main__':
    unittest.main()
