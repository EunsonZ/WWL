"""Regression contracts for finite-precision softmax behavior."""

from __future__ import annotations

import math
import unittest

import softmax_stability as softmax


class SoftmaxStabilityContracts(unittest.TestCase):
    def test_huge_equal_logits_and_old_counterexample(self) -> None:
        logits = [1e16, 1e16]
        old_probabilities = [
            math.exp(value - softmax.logsumexp(logits)) for value in logits
        ]
        self.assertEqual(sum(old_probabilities), 2.0)
        self.assertEqual(softmax.stable_softmax(logits), [0.5, 0.5])
        self.assertAlmostEqual(
            softmax.cross_entropy_from_logits(logits, 0), math.log(2.0)
        )
        self.assertAlmostEqual(softmax.log_softmax(logits)[0], -math.log(2.0))

    def test_gradient_and_translation_invariance(self) -> None:
        logits = [2.0, 1.0, -2.0]
        probabilities = softmax.stable_softmax(logits)
        translated = softmax.stable_softmax(
            [value + 12345.0 for value in logits]
        )
        for actual, expected in zip(probabilities, translated):
            self.assertAlmostEqual(actual, expected, places=12)

        step = 1e-5
        for index in range(len(logits)):
            plus = logits.copy()
            minus = logits.copy()
            plus[index] += step
            minus[index] -= step
            derivative = (
                softmax.cross_entropy_from_logits(plus, 1)
                - softmax.cross_entropy_from_logits(minus, 1)
            ) / (2.0 * step)
            expected = probabilities[index] - (index == 1)
            self.assertAlmostEqual(derivative, expected, places=8)

    def test_invalid_and_extreme_inputs(self) -> None:
        invalid = [
            ([], 1.0),
            ([math.nan], 1.0),
            ([math.inf], 1.0),
            ([1.0], 0.0),
            ([1.0], math.inf),
            ([1.0], -1.0),
        ]
        for logits, temperature in invalid:
            with self.subTest(logits=logits, temperature=temperature):
                with self.assertRaises(ValueError):
                    softmax.stable_softmax(logits, temperature)
        self.assertEqual(
            softmax.stable_softmax([1000.0, 999.0], 1e-308), [1.0, 0.0]
        )
        with self.assertRaises(ValueError):
            softmax.stable_softmax([-1e308, 1e308])


if __name__ == "__main__":
    unittest.main()
