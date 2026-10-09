"""Analytic oracles remain independent of the experiment's estimated statistics."""
from fractions import Fraction as F
import cmath
import math
import unittest
import wiener_lab as lab


class WienerTests(unittest.TestCase):
    def test_two_sample_normal_equations_exact(self):
        R = [[F(2), F(1, 2)], [F(1, 2), F(2)]]
        p, w = [F(1), F(1, 2)], [F(7, 15), F(2, 15)]
        self.assertEqual([sum(a*b for a, b in zip(row, w)) for row in R], p)
        mse = F(1)-2*sum(a*b for a, b in zip(w, p))+sum(w[i]*R[i][j]*w[j] for i in range(2) for j in range(2))
        self.assertEqual(mse, F(7, 15))
        actual = lab.solve(R, p)
        for a, b in zip(actual, w): self.assertAlmostEqual(a, float(b), places=14)

    def test_singular_duplicate_output_and_solver_refusal(self):
        for w in [[F(1), F(0)], [F(1, 2), F(1, 2)], [F(3), F(-2)]]:
            self.assertEqual(sum(w), 1)
        with self.assertRaises(ValueError): lab.solve([[1, 1], [1, 1]], [1, 1])

    def test_three_point_nonlinear_mmse_counterexample(self):
        x = [F(-1), F(0), F(1)]
        d = [v*v-F(2, 3) for v in x]
        self.assertEqual(sum(x), 0)
        self.assertEqual(sum(d), 0)
        self.assertEqual(sum(a*b for a, b in zip(x, d)), 0)
        self.assertEqual(sum(v*v for v in d)/3, F(2, 9))

    def test_same_target_smoothing_and_noise_migration(self):
        R = [[F(2), F(1, 2), F(1, 4)], [F(1, 2), F(2), F(1, 2)], [F(1, 4), F(1, 2), F(2)]]
        p, w = [F(1, 2), F(1), F(1, 2)], [F(1, 8), F(7, 16), F(1, 8)]
        self.assertEqual([sum(a*b for a, b in zip(row, w)) for row in R], p)
        self.assertEqual(1-sum(a*b for a, b in zip(w, p)), F(7, 16))
        old = [F(7, 15), F(2, 15)]
        newR = [[F(2), F(1)], [F(1), F(2)]]
        self.assertEqual(1-2*(old[0]+old[1]/2)+sum(old[i]*newR[i][j]*old[j] for i in range(2) for j in range(2)), F(119, 225))

    def test_complex_delay_cross_spectrum_order(self):
        theta = math.pi/4
        G, Sxx = cmath.exp(-2j*theta), 2.
        Sdx = G*Sxx
        self.assertAlmostEqual((Sdx/Sxx).imag, -1.)
        self.assertAlmostEqual((Sdx.conjugate()/Sxx).imag, 1.)

    def test_causal_factor_and_riccati_independent_identity(self):
        P, r = 2*math.sqrt(3)-3, 2-math.sqrt(3)
        self.assertAlmostEqual(P*P+6*P-3, 0., places=13)
        self.assertAlmostEqual(.5*(1-P), r, places=14)
        impulse = lab.causal_filter([1.]+[0.]*20)
        for k, value in enumerate(impulse): self.assertAlmostEqual(value, P*r**k, places=14)
        K = (2+math.sqrt(3))/2
        for theta in [.0, .3, 1.2, 2.9]:
            q = cmath.exp(-1j*theta)
            factor = math.sqrt(K)*(1-r*q)/(1-.5*q)
            Sx = (2-math.cos(theta))/(1.25-math.cos(theta))
            self.assertAlmostEqual(abs(factor)**2, Sx, places=12)

    def test_DC_zero_mean_square_recovery_is_not_inverse_truncation(self):
        # Independent covariance quadratic: X_j = u[-j]-u[-j-1],
        # Cov(X_i,X_j)=2 on diagonal, -1 on adjacent indices; target u[0].
        # This oracle uses no filtering helper or telescoping implementation.
        for N in [1, 2, 7, 32]:
            def exact_loss(weights):
                output_power = sum(weights[i]*weights[j]*
                    (2 if i == j else -1 if abs(i-j) == 1 else 0)
                    for i in range(N) for j in range(N))
                return 1-2*weights[0]+output_power
            tapered = [1-F(j, N) for j in range(N)]
            self.assertEqual(exact_loss(tapered), F(1, N))
            self.assertEqual(exact_loss([F(1)]*N), F(1))

    def test_model_reproducibility_and_shape_contracts(self):
        self.assertEqual(lab.model(17, 8), lab.model(17, 8))
        self.assertNotEqual(lab.model(17, 8), lab.model(18, 8))
        for args in [([], []), ([[1], [1, 2]], [1, 2])]:
            with self.assertRaises(ValueError): lab.fit(*args)
        with self.assertRaises(ValueError): lab.model(1, 8, 1.)
        with self.assertRaises(ValueError): lab.experiments(repeats=True)


if __name__ == '__main__':
    unittest.main()
