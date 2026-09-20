import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


MODULE_PATH = Path(__file__).with_name("lqr_mpc_lab.py")
SPEC = importlib.util.spec_from_file_location("lqr_mpc_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class LqrMpcLabTests(unittest.TestCase):
    def test_double_integrator_units_and_exact_step(self):
        A, B = lab.double_integrator(0.2)
        np.testing.assert_allclose(A, [[1, 0.2], [0, 1]])
        np.testing.assert_allclose(B, [[0.02], [0.2]])
        states = lab.rollout(A, B, [0, 1], np.array([[2.0]]))
        np.testing.assert_allclose(states[-1], [0.24, 1.4])

    def test_two_step_riccati_hand_values_and_direct_oracle(self):
        A, B = lab.double_integrator(0.2)
        Q = np.diag([1.0, 0.1]); R = np.array([[0.05]]); Qf = np.diag([8.0, 2.0])
        gains, values = lab.finite_lqr(A, B, Q, R, Qf, 2)
        np.testing.assert_allclose(gains[1], [[1.2012012012, 3.2432432432]], rtol=1e-9)
        np.testing.assert_allclose(gains[0], [[3.8120857063, 2.9523387172]], rtol=1e-9)
        np.testing.assert_allclose(values[2], Qf)
        problem = lab.stack_quadratic(A, B, Q, R, Qf, 2, [1.0, 0.0])
        direct = lab.direct_unconstrained(problem)
        x = np.array([1.0, 0.0]); dynamic = []
        for K in gains:
            u = -K @ x; dynamic.append(float(u[0])); x = A @ x + B[:, 0] * u[0]
        np.testing.assert_allclose(dynamic, direct, atol=1e-11)
        states = lab.rollout(A, B, [1.0, 0.0], direct[:, None])
        self.assertAlmostEqual(lab.finite_cost(states, direct[:, None], Q, R, Qf), lab.stacked_objective(problem, direct))

    def test_dare_residual_and_closed_loop_poles_are_separate_checks(self):
        A, B = lab.double_integrator(0.2)
        Q = np.diag([1.0, 0.1]); R = np.array([[0.05]])
        S, K, iterations = lab.dare_iteration(A, B, Q, R)
        self.assertLess(iterations, 200)
        self.assertLess(lab.dare_residual(A, B, Q, R, S), 1e-10)
        self.assertLess(np.max(np.abs(np.linalg.eigvals(A - B @ K))), 1.0)
        np.testing.assert_allclose(K, [[3.21775154, 2.73329391]], rtol=2e-8)

        # Q=0 does not detect unstable A=2. Both S=0 and S=3 solve DARE,
        # but only S=3 gives the stabilizing pole 0.5.
        As = np.array([[2.0]]); Bs = np.array([[1.0]])
        Qs = np.array([[0.0]]); Rs = np.array([[1.0]])
        for candidate in (np.array([[0.0]]), np.array([[3.0]])):
            self.assertLess(lab.dare_residual(As, Bs, Qs, Rs, candidate), 1e-12)
        K0 = np.linalg.solve(Rs + Bs.T @ np.zeros((1, 1)) @ Bs, Bs.T @ np.zeros((1, 1)) @ As)
        K3 = np.linalg.solve(Rs + Bs.T @ np.array([[3.0]]) @ Bs, Bs.T @ np.array([[3.0]]) @ As)
        self.assertEqual(float((As - Bs @ K0)[0, 0]), 2.0)
        self.assertEqual(float((As - Bs @ K3)[0, 0]), 0.5)

    def test_clipping_is_feasible_but_not_optimal(self):
        *_, problem, _ = lab.default_problem()
        lower = np.full(8, -0.8); upper = np.full(8, 0.8)
        unconstrained = lab.direct_unconstrained(problem)
        clipped = np.clip(unconstrained, lower, upper)
        optimum = lab.solve_box_qp_active_set(problem.H, problem.f, lower, upper)
        self.assertIsNotNone(optimum)
        assert optimum is not None
        self.assertLess(lab.stacked_objective(problem, optimum.u), lab.stacked_objective(problem, clipped) - 0.6)
        self.assertLess(lab.box_kkt_violation(problem.H, problem.f, optimum.u, lower, upper), 1e-10)
        self.assertGreater(lab.box_kkt_violation(problem.H, problem.f, clipped, lower, upper), 0.1)

    def test_terminal_equality_and_recursive_shift_witness(self):
        result = lab.compute_demo()
        self.assertLess(result["terminal_residual"], 1e-12)
        self.assertLess(result["shifted_terminal_residual"], 1e-12)
        self.assertLessEqual(np.max(np.abs(result["controls"]["terminal_mpc"])), 0.8 + 1e-12)
        self.assertLessEqual(np.max(np.abs(np.r_[result["controls"]["terminal_mpc"][1:], 0.0])), 0.8 + 1e-12)

        A, B, Q, R, Qf, problem, x0 = lab.default_problem(x0=(0.6, 0.0))
        E = problem.M[-2:]; d = -problem.G[-2:] @ x0
        infeasible = lab.solve_box_qp_active_set(problem.H, problem.f, np.full(8, -0.8), np.full(8, 0.8), E=E, d=d)
        self.assertIsNone(infeasible)

    def test_cli_figure_outputs(self):
        result = lab.compute_demo()
        with tempfile.TemporaryDirectory() as directory:
            paths = lab.save_figures(result, Path(directory), 0.2, 0.8)
            self.assertEqual({p.name for p in paths}, {
                "finite-horizon-trajectories.svg", "clip-versus-box-qp.svg", "terminal-shift-witness.svg"
            })
            self.assertTrue(all(p.stat().st_size > 1000 for p in paths))

    def test_invalid_inputs(self):
        for dt in (0, -1, np.nan, np.inf, 1e-12):
            with self.assertRaises(ValueError): lab.double_integrator(dt)
        A, B = lab.double_integrator()
        with self.assertRaises(ValueError): lab.finite_lqr(A, B, np.diag([1, -1]), [[1]], np.eye(2), 3)
        with self.assertRaises(ValueError): lab.solve_box_qp_active_set(np.eye(11), np.zeros(11), -np.ones(11), np.ones(11))
        with self.assertRaises(ValueError): lab.default_problem(x0=(1,))


if __name__ == "__main__":
    unittest.main()
