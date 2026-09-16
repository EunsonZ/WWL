from __future__ import annotations

import math
import unittest

import numpy as np

from mechanisms import (
    affine_flow_log_density,
    autoregressive_joint,
    beta_bernoulli_update,
    finite_class_gap,
    gmm_responsibilities,
    grouped_and_pooled_rates,
    kmeans_step,
    logistic_gradient,
    ridge_solution,
    td_targets,
    value_iteration,
)


class FoundationsTests(unittest.TestCase):
    def test_ridge_and_logistic(self) -> None:
        self.assertAlmostEqual(ridge_solution([1, 2], [1, 3], 0), 7 / 5)
        self.assertAlmostEqual(ridge_solution([1, 2], [1, 3], 1), 1.0)
        grad_w, grad_b = logistic_gradient([2, -1], 1, [0, 0])
        np.testing.assert_allclose(grad_w, [-1.0, 0.5])
        self.assertAlmostEqual(grad_b, -0.5)

    def test_finite_class_bound(self) -> None:
        self.assertAlmostEqual(finite_class_gap(8, 200, 0.05), math.sqrt(math.log(320) / 400))

    def test_kmeans_and_gmm(self) -> None:
        assignment, centers = kmeans_step([0, 1, 9, 10], [0, 10])
        np.testing.assert_array_equal(assignment, [0, 0, 1, 1])
        np.testing.assert_allclose(centers, [0.5, 9.5])
        resp = gmm_responsibilities(1.0, [0.5, 0.5], [0.0, 2.0], [1.0, 1.0])
        np.testing.assert_allclose(resp, [0.5, 0.5])
        self.assertAlmostEqual(float(resp.sum()), 1.0)
        far_resp = gmm_responsibilities(1e6, [0.5, 0.5], [0.0, 2.0], [1.0, 1.0])
        self.assertAlmostEqual(float(far_resp.sum()), 1.0)
        self.assertGreater(far_resp[1], far_resp[0])
        page_resp = gmm_responsibilities(0.5, [0.5, 0.5], [0.0, 2.0], [1.0, 1.0])
        self.assertAlmostEqual(float(page_resp[0]), 1.0 / (1.0 + math.exp(-1.0)))

    def test_rl_targets(self) -> None:
        reward = np.array([[0.0, 1.0], [0.0, 2.0]])
        transition = np.array([[[1, 0], [0, 1]], [[1, 0], [0, 1]]], dtype=float)
        values = value_iteration(reward, transition, gamma=0.5, steps=2)
        np.testing.assert_allclose(values[0], [0, 0])
        np.testing.assert_allclose(values[1], [1, 2])
        np.testing.assert_allclose(values[2], [2, 3])
        self.assertEqual(td_targets(1, 0.9, [2, 4], 0), (2.8, 4.6))

    def test_beta_and_group_rates(self) -> None:
        self.assertEqual(beta_bernoulli_update(1, 1, 3, 1), (4, 2, 2 / 3))
        self.assertEqual(beta_bernoulli_update(2, 2, 3, 1), (5, 3, 0.625))
        successes = np.array([[81, 192], [234, 55]])
        totals = np.array([[87, 263], [270, 80]])
        strata, pooled = grouped_and_pooled_rates(successes, totals)
        self.assertGreater(strata[0, 0], strata[1, 0])
        self.assertGreater(strata[0, 1], strata[1, 1])
        self.assertLess(pooled[0], pooled[1])

    def test_generative_normalization_and_flow(self) -> None:
        joint = autoregressive_joint(0.4, [0.25, 0.75])
        self.assertTrue(np.all(joint >= 0))
        self.assertAlmostEqual(float(joint.sum()), 1.0)
        self.assertAlmostEqual(affine_flow_log_density(1.0, 2.0, 1.0), -0.5 * math.log(2 * math.pi) - math.log(2))

    def test_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            finite_class_gap(0, 10, 0.1)
        with self.assertRaises(ValueError):
            affine_flow_log_density(0, 0, 0)
        with self.assertRaises(ValueError):
            beta_bernoulli_update(0, 1, 1, 1)
        with self.assertRaises(ValueError):
            ridge_solution([0, 0], [1, 2], 0)
        with self.assertRaises(ValueError):
            ridge_solution([1, math.nan], [1, 2], 1)
        with self.assertRaises(ValueError):
            autoregressive_joint(0.5, [0.2, math.nan])
        with self.assertRaises(ValueError):
            grouped_and_pooled_rates(np.array([[-1.0]]), np.array([[1.0]]))
        with self.assertRaises(ValueError):
            grouped_and_pooled_rates(np.array([[0.0]]), np.array([[math.inf]]))
        with self.assertRaises(ValueError):
            value_iteration(
                np.zeros((2, 1)), np.array([[[-1.0, 2.0]], [[0.0, 1.0]]]), gamma=0.5, steps=1
            )


if __name__ == "__main__":
    unittest.main()
