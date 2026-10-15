"""Checks against exhaustive paths and closed-form conditional moments."""
from fractions import Fraction
from math import comb
import unittest

from inference_selection_lab import (
    conditioning_moments, markov_path_probability, randomized_upper_test,
    stopping_dp, uniform_maximum, upper_tail,
)


class ExactExperiments(unittest.TestCase):
    def test_exhaustive_oracle(self):
        # Explicit paths use integer comparisons, independent of DP/Fraction tails.
        for steps in (1, 4, 5, 8, 12):
            first_counts = {rule: [0] * (steps + 1) for rule in ("peek", "lr")}
            for path in range(2 ** steps):
                heads, seen = 0, set()
                for n in range(1, steps + 1):
                    heads += (path >> (n - 1)) & 1
                    reject = {
                        "peek": 20 * sum(comb(n, k) for k in range(heads, n + 1)) <= 2 ** n,
                        "lr": 3 ** heads >= 20 * 2 ** n,
                    }
                    for rule, crosses in reject.items():
                        if crosses and rule not in seen:
                            first_counts[rule][n] += 1
                            seen.add(rule)
            for rule in ("peek", "lr"):
                rejection, first = stopping_dp(steps, rule)
                self.assertEqual(rejection, Fraction(sum(first_counts[rule]), 2 ** steps))
                for n in range(1, steps + 1):
                    self.assertEqual(first[n], Fraction(first_counts[rule][n], 2 ** steps))
        self.assertEqual(upper_tail(20, 15), Fraction(5425, 262144))
        self.assertEqual(stopping_dp(20, "peek")[0], Fraction(6467, 65536))
        self.assertEqual(stopping_dp(20, "lr")[0], Fraction(5541, 262144))

    def test_boundary_and_absorption(self):
        self.assertEqual(upper_tail(0, 0), 1)
        self.assertEqual(upper_tail(20, 14), Fraction(15115, 262144))
        self.assertEqual(stopping_dp(0), (0, {}))
        for n in range(1, 5):
            self.assertEqual(stopping_dp(n)[0], 0)
        self.assertEqual(stopping_dp(5)[0], Fraction(1, 32))
        self.assertEqual(stopping_dp(7, "lr")[0], 0)
        self.assertEqual(stopping_dp(8, "lr")[0], Fraction(1, 256))
        # Once all first five flips are heads, later tails retain rejection.
        self.assertGreaterEqual(stopping_dp(20)[0], Fraction(1, 32))

    def test_conditioning_and_markov(self):
        for p in (Fraction(1, 2), Fraction(1, 4)):
            report = conditioning_moments(4, p)
            self.assertEqual(report["variance_before"], p * (1 - p))
            self.assertEqual(report["variance_after"], p * (1 - p) / 4)
        self.assertEqual(markov_path_probability((0, 0, 1, 1)), Fraction(9, 128))
        self.assertEqual(markov_path_probability((0, 1, 0, 1)), Fraction(1, 128))

    def test_invalid_inputs(self):
        for args in ((-1, 0), (2, 3), (2.0, 1)):
            with self.assertRaises(ValueError):
                upper_tail(*args)
        with self.assertRaises(ValueError):
            stopping_dp(-1)
        with self.assertRaises(ValueError):
            stopping_dp(rule="unknown")
        with self.assertRaises(ValueError):
            conditioning_moments(p=0)

    def test_randomized_boundary(self):
        report = randomized_upper_test(4, Fraction(1, 2), Fraction(3, 4), Fraction(1, 10))
        self.assertEqual(report, {"cutoff": 3, "rho": Fraction(3, 20),
                                  "size": Fraction(1, 10), "power": Fraction(243, 640)})
        report20 = randomized_upper_test(20, Fraction(1, 2), Fraction(4, 5), Fraction(1, 20))
        self.assertEqual(report20["cutoff"], 14)
        self.assertEqual(report20["rho"], Fraction(38411, 48450))
        self.assertEqual(report20["size"], Fraction(1, 20))
        for alpha in (Fraction(0), Fraction(1)):
            boundary = randomized_upper_test(4, Fraction(1, 2), Fraction(3, 4), alpha)
            self.assertEqual(boundary["size"], alpha)
            self.assertEqual(boundary["power"], alpha)

    def test_uniform_polynomial_integral(self):
        report = uniform_maximum()
        self.assertEqual(report["mean_max"], Fraction(4, 5))
        self.assertEqual(report["second_moment_max"], Fraction(2, 3))
        self.assertEqual(report["variance_max"], Fraction(2, 75))
        self.assertEqual(report["mean_corrected"], 1)
        self.assertEqual(report["variance_corrected"], Fraction(1, 24))
        for n in (1, 2, 7):
            for theta in (Fraction(1), Fraction(3, 2)):
                candidate = uniform_maximum(n, theta)
                self.assertEqual(candidate["variance_corrected"], theta ** 2 / (n * (n + 2)))


if __name__ == "__main__":
    unittest.main()
