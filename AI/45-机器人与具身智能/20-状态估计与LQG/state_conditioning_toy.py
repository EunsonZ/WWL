"""Pure-stdlib independent 2D Gaussian-conditioning arithmetic check."""
import math
import unittest

def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def valid_psd_2x2(cov):
    a, b = cov[0]; c, d = cov[1]
    return a >= 0 and d >= 0 and a * d - b * c >= 0

def condition_position(mean, cov, measurement, r):
    if not isinstance(mean, (list, tuple)) or len(mean) != 2 or not all(finite_number(x) for x in mean): raise ValueError("need finite 2D mean")
    if not isinstance(cov, (list, tuple)) or len(cov) != 2 or any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in cov): raise ValueError("need 2D covariance")
    if not all(finite_number(x) for row in cov for x in row): raise ValueError("covariance must be finite")
    if cov[0][1] != cov[1][0]: raise ValueError("covariance must be symmetric")
    if not valid_psd_2x2(cov): raise ValueError("covariance must be PSD")
    if not finite_number(measurement): raise ValueError("measurement must be finite")
    if not finite_number(r) or r <= 0: raise ValueError("measurement variance must be finite and positive")
    s = cov[0][0] + r
    if not math.isfinite(s) or s <= 0: raise ValueError("innovation variance must be positive")
    k = [cov[0][0] / s, cov[1][0] / s]
    innovation = measurement - mean[0]
    posterior_mean = [mean[i] + k[i] * innovation for i in range(2)]
    posterior_cov = [[cov[i][j] - k[i] * cov[0][j] for j in range(2)] for i in range(2)]
    return posterior_mean, posterior_cov, k

class ConditioningTest(unittest.TestCase):
    def test_hand_example(self):
        mean, cov, gain = condition_position([0, 0], [[4, 2], [2, 3]], 5, 1)
        self.assertEqual(gain, [0.8, 0.4]); self.assertEqual(mean, [4.0, 2.0])
        for actual, expected in zip(sum(cov, []), [0.8, 0.4, 0.4, 2.2]):
            self.assertAlmostEqual(actual, expected)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): condition_position([0, 0], [[1, 0], [0, 1]], 0, 0)
        with self.assertRaises(ValueError): condition_position([0, 0], [[4, 100], [2, 3]], 5, 1)
        with self.assertRaises(ValueError): condition_position([0, 0], [[-1, 0], [0, 1]], 5, 1)
        with self.assertRaises(ValueError): condition_position([0, 0], [[0, 0], [0, 1]], 5, 0)
        with self.assertRaises(ValueError): condition_position([0, 0], [[1, 0], [0, 1]], 5, float("nan"))
        with self.assertRaises(ValueError): condition_position([0, 0], [[1, 0], [0, float("inf")]], 5, 1)
        with self.assertRaises(ValueError): condition_position([0], [[1, 0], [0, 1]], 5, 1)

if __name__ == "__main__": unittest.main()
