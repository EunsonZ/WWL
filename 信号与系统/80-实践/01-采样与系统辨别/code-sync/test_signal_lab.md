---
type: reference
domain: signals-and-systems
stage: 1
content_status: draft
evidence_status: partial
aliases: []
sources: []
prerequisites:
  - "[[信号与系统/80-实践/01-采样与系统辨别/README]]"
---

# test_signal_lab 源码镜像

规范真源是上一级 [test_signal_lab.py](../test_signal_lab.py)。本块供阅读与正式code-sync检查；修改须同时更新真源和镜像，运行协议见 [[信号与系统/80-实践/01-采样与系统辨别/README|实验说明]]。

<!-- code-sync: ../test_signal_lab.py -->
```python
"""Independent hand expectations, properties, and invalid-input tests."""
import math
import unittest
import numpy as np
from signal_lab import (sample_times, tone, pulse, quantize, linear_convolution,
                        first_order_step, one_sided_amplitude)


class SignalLabTests(unittest.TestCase):
    def test_four_samples_hand_values_and_alias(self):
        times = sample_times(8, 4)
        np.testing.assert_array_equal(times, [0, .125, .25, .375])
        expected = [1, 0, -1, 0]
        np.testing.assert_allclose(tone(times, 2), expected, atol=2e-15)
        np.testing.assert_allclose(tone(times, 6), expected, atol=2e-15)
        all_times = sample_times(8, 64)
        np.testing.assert_allclose(tone(all_times, 2), tone(all_times, 6), atol=1e-13)
        values = [tone([1 / 16], f)[0] for f in [2, 6]]
        self.assertAlmostEqual(values[0] - values[1], math.sqrt(2), places=14)

    def test_wrong_phase_or_new_sample_times_break_this_alias(self):
        times = sample_times(8, 16)
        self.assertGreater(np.max(np.abs(tone(times, 2) - tone(times, 6, phase_rad=.4))), .3)
        shifted = sample_times(8, 16, .01)
        self.assertGreater(np.max(np.abs(tone(shifted, 2) - tone(shifted, 6))), .4)

    def test_nyquist_zero_and_identifiability_failure(self):
        times = sample_times(8, 16)
        np.testing.assert_allclose(tone(times, 4, sine=True), 0, atol=2e-14)
        expected = [1 if n % 2 == 0 else -1 for n in range(16)]
        np.testing.assert_allclose(tone(times, 4, phase_rad=math.pi / 2, sine=True), expected, atol=2e-14)
        np.testing.assert_allclose(tone(times, 4, 1, math.pi / 6, sine=True),
                                   tone(times, 4, .5, math.pi / 2, sine=True), atol=2e-14)

    def test_quantizer_ties_and_hand_first_value(self):
        np.testing.assert_array_equal(quantize([-.375, -.125, .125, .375], .25), [-.25, 0, .25, .5])
        value = .83 * math.cos(.3)
        self.assertAlmostEqual(value, .792929285974253, places=14)
        self.assertEqual(quantize([value], .25)[0], .75)
        self.assertEqual(quantize([.1], .25)[0], 0)
        values = np.linspace(-3, 3, 1201)
        error = quantize(values, .25) - values
        self.assertLessEqual(np.max(np.abs(error)), .125 + 1e-14)
        # Value quantization cannot distinguish equal ideal-sample lists.
        t = sample_times(8, 16)
        np.testing.assert_allclose(quantize(tone(t, 2), .25), quantize(tone(t, 6), .25), atol=0)

    def test_no_alias_still_has_quantization_error(self):
        times = sample_times(8, 32)
        values = tone(times, 1, .83, .3)
        self.assertGreater(np.max(np.abs(values - quantize(values, .25))), .04)
        self.assertLessEqual(np.max(np.abs(values - quantize(values, .25))), .125)

    def test_nonbandlimited_pulse_missed_and_endpoint_protocol(self):
        np.testing.assert_array_equal(pulse(sample_times(8, 32), .03, .08), np.zeros(32))
        np.testing.assert_array_equal(pulse([.029, .03, .079, .08], .03, .08), [0, 1, 1, 0])

    def test_linear_convolution_independent_expectations(self):
        np.testing.assert_array_equal(linear_convolution([1, 2], [1, .5]), [1, 2.5, 1])
        np.testing.assert_array_equal(linear_convolution([1, -1], [1, -.5]), [1, -1.5, .5])
        x, z, h = np.array([1, 3, -2]), np.array([2, -1, 0]), np.array([.5, 1])
        np.testing.assert_allclose(linear_convolution(2 * x - z, h),
                                   2 * linear_convolution(x, h) - linear_convolution(z, h), atol=0)

    def test_first_order_zero_input_state_units(self):
        zi, zs, total = first_order_step([0, .001], .001, .4)
        np.testing.assert_allclose(zi, [.4, .4 / math.e], atol=2e-16)
        np.testing.assert_allclose(zs, [0, 1 - 1 / math.e], atol=2e-16)
        np.testing.assert_allclose(total, [.4, 1 - .6 / math.e], atol=2e-16)
        # Stable first-order DC gain one and nonzero initial contribution dies.
        zi, zs, total = first_order_step([100], 1, 3, 2)
        self.assertLess(abs(total[0] - 2), 1e-14)
        self.assertLess(abs(zi[0]), 1e-40)

    def test_dft_normalization_dc_nyquist_and_odd_length(self):
        f, a = one_sided_amplitude([2] * 8, 8)
        self.assertEqual(a[0], 2)
        np.testing.assert_allclose(a[1:], 0, atol=1e-15)
        f, a = one_sided_amplitude([1, -1] * 4, 8)
        self.assertEqual(f[-1], 4)
        self.assertEqual(a[-1], 1)
        np.testing.assert_allclose(a[:-1], 0, atol=1e-15)
        f, a = one_sided_amplitude(tone(sample_times(9, 9), 2, .7), 9)
        self.assertAlmostEqual(a[2], .7, places=14)
        self.assertAlmostEqual(f[2], 2, places=14)

    def test_joint_migration_independent_identity(self):
        t = sample_times(10, 40)
        np.testing.assert_allclose(tone(t, 3, .7, math.pi / 5),
                                   tone(t, 7, .7, -math.pi / 5), atol=2e-14)
        a = .7 * math.cos(.35 * math.pi)
        b = .7 * math.cos(.15 * math.pi)
        self.assertGreater(b - a, .3)
        self.assertAlmostEqual(tone([.025], 3, .7, math.pi / 5)[0], a, places=14)
        self.assertAlmostEqual(tone([.025], 7, .7, -math.pi / 5)[0], b, places=14)

    def test_invalid_parameters(self):
        for fs, n, offset in [(0, 4, 0), (-8, 4, 0), (math.inf, 4, 0), (8, 0, 0),
                              (8, True, 0), (8, 1.5, 0), (8, 4, math.nan), (True, 4, 0)]:
            with self.subTest(fs=fs, count=n, offset=offset), self.assertRaises(ValueError):
                sample_times(fs, n, offset)
        for values, delta in [([], .25), ([math.nan], .25), ([1], 0), ([1], -1),
                               ([1], math.inf), ([[1]], .25), ([1 + 2j], .25)]:
            with self.subTest(values=values, delta=delta), self.assertRaises(ValueError):
                quantize(values, delta)
        for t, tau in [([-1], 1), ([0], 0), ([0], -1), ([0], math.nan)]:
            with self.subTest(t=t, tau=tau), self.assertRaises(ValueError):
                first_order_step(t, tau)
        with self.assertRaises(ValueError):
            pulse([0], .1, .1)
        with self.assertRaises(ValueError):
            tone([0], math.nan)
        with self.assertRaises(ValueError):
            one_sided_amplitude([1], 0)
        with self.assertRaises(ValueError):
            linear_convolution([], [1])

    def test_complex_scalars_and_object_vectors_reject_before_float_conversion(self):
        for value in (1 + 0j, 1 + 2j, np.complex64(1), np.complex128(1 + 2j)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sample_times(value, 4)
        for value in (np.complex64(1), np.complex128(1 + 2j)):
            vector = np.array([value], dtype=object)
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                quantize(vector, .25)


if __name__ == '__main__':
    unittest.main()
```
