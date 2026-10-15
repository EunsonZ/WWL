import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


MODULE_PATH = Path(__file__).with_name("lqg_state_estimation_lab.py")
SPEC = importlib.util.spec_from_file_location("lqg_state_estimation_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class LqgStateEstimationLabTests(unittest.TestCase):
    def test_three_manual_steps_and_units(self):
        A, B, H = lab.double_integrator(0.2)
        np.testing.assert_allclose(A, [[1, 0.2], [0, 1]])
        np.testing.assert_allclose(B, [[0.02], [0.2]])
        np.testing.assert_allclose(H, [[1, 0]])
        W = 0.2**2 * (B @ B.T)
        result = lab.filter_sequence(
            [0, 0], np.diag([0.04, 0.25]), A, B, H, W, [[0.01]],
            [[0.5], [-0.2]], [[0.10], [0.14], [0.18]],
        )
        np.testing.assert_allclose(result["gains"][0, :, 0], [0.8, 0.0], atol=1e-12)
        np.testing.assert_allclose(result["means"][0], [0.08, 0.0], atol=1e-12)
        np.testing.assert_allclose(result["gains"][1, :, 0], [0.6430611079, 1.7904054826], rtol=1e-10)
        np.testing.assert_allclose(result["means"][1], [0.1221530554, 0.1895202741], rtol=3e-10)
        np.testing.assert_allclose(result["means"][2], [0.1720402530, 0.1896554730], rtol=1e-9)
        np.testing.assert_allclose(
            result["covariances"][2],
            [[0.0066755279, 0.0167628884], [0.0167628884, 0.0788702399]],
            rtol=5e-9,
        )

    def test_batch_gaussian_condition_matches_recursive_filter(self):
        result = lab.compute_demo(steps=40)
        self.assertLess(result["batch_mean_error"], 1e-12)
        self.assertLess(result["batch_covariance_error"], 1e-12)

    def test_joseph_covariance_is_symmetric_psd(self):
        H = np.array([[1.0, -0.3]])
        prior = np.array([[2.0, 0.7], [0.7, 0.5]])
        _, post, _, _, gain = lab.kalman_update([0, 0], prior, H, [[0.04]], [1.2])
        self.assertTrue(np.allclose(post, post.T, atol=1e-14))
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(post))), -1e-13)
        direct = prior - prior @ H.T @ np.linalg.solve(H @ prior @ H.T + [[0.04]], H @ prior)
        np.testing.assert_allclose(post, direct, atol=1e-12)
        self.assertEqual(gain.shape, (2, 1))

    def test_observability_detectability_and_stabilizability(self):
        A, B, H = lab.double_integrator(0.2)
        self.assertEqual(np.linalg.matrix_rank(lab.observability_matrix(A, H)), 2)
        self.assertTrue(lab.detectable(A, H))
        self.assertTrue(lab.stabilizable(A, B))
        self.assertFalse(lab.detectable(A, np.zeros((1, 2))))
        stable_A = np.diag([0.8, 0.5])
        self.assertTrue(lab.detectable(stable_A, np.zeros((1, 2))))

    def test_steady_riccati_solutions_and_poles(self):
        A, B, H = lab.double_integrator(0.2)
        W = 0.2**2 * (B @ B.T); R = np.array([[0.05**2]])
        prior, post, gain, _ = lab.steady_kalman(A, H, W, R)
        recomputed = A @ post @ A.T + W
        np.testing.assert_allclose(prior, recomputed, atol=2e-13)
        self.assertLess(np.max(np.abs(np.linalg.eigvals((np.eye(2)-gain@H)@A))), 1.0)
        value, control_gain, _ = lab.steady_lqr(A, B, np.diag([1.0,0.1]), [[0.05]])
        rhs = np.diag([1.0,0.1]) + A.T@value@A - A.T@value@B@np.linalg.solve([[0.05]]+B.T@value@B, B.T@value@A)
        np.testing.assert_allclose(value, rhs, atol=2e-12)
        self.assertLess(np.max(np.abs(np.linalg.eigvals(A-B@control_gain))), 1.0)

    def test_separation_matrix_has_union_of_poles(self):
        result = lab.compute_demo(steps=40)
        expected = np.sort_complex(np.r_[result["controller_poles"], result["filter_poles"]])
        actual = np.sort_complex(result["augmented_poles"])
        np.testing.assert_allclose(actual, expected, atol=1e-12)
        self.assertLess(np.max(np.abs(actual)), 1.0)

    def test_fixed_seed_failure_diagnostics(self):
        result = lab.compute_demo(steps=160)
        self.assertGreater(result["mismatched_nis_mean_after_burn"], 2.0 * result["nominal_nis_mean_after_burn"])
        self.assertLess(abs(result["biased_estimated_position_mean_last20"]), 0.04)
        self.assertLess(abs(result["biased_true_position_mean_last20"] + 0.15), 0.05)
        self.assertGreater(result["saturation_fraction"], 0.0)

    def test_cli_artifacts_are_deterministic_and_invalid_inputs_fail(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.assertEqual(lab.main(["--output-dir", first, "--steps", "40"]), 0)
            self.assertEqual(lab.main(["--output-dir", second, "--steps", "40"]), 0)
            names = {"kalman-error-diagnostics.svg", "lqg-separation-poles.svg", "lqg-failure-boundaries.svg", "demo-summary.json"}
            self.assertEqual({p.name for p in Path(first).iterdir()}, names)
            for name in names:
                self.assertEqual((Path(first)/name).read_bytes(), (Path(second)/name).read_bytes())
            json.loads((Path(first)/"demo-summary.json").read_text())
        with self.assertRaises(ValueError):
            lab.double_integrator(0)
        with self.assertRaises(ValueError):
            lab.kalman_update([0,0], np.eye(2), [[1,0]], [[0]], [1])
        with self.assertRaises(ValueError):
            lab.simulate_lqg(seed=1, steps=1)


if __name__ == "__main__":
    unittest.main()
