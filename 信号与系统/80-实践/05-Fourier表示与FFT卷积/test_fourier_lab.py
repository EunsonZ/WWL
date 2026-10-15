"""Independent explicit-sum and fixed-integer oracles; does not write files."""
import itertools
import math
import unittest
import fourier_lab as lab


def explicit_transform(x, inverse=False):
    """Independent real cosine/sine sum, no lab.dft or FFT dependency."""
    n = len(x)
    sign = 1 if inverse else -1
    return [sum(complex(value) * complex(math.cos(sign*2*math.pi*k*m/n),
                                         math.sin(sign*2*math.pi*k*m/n))
                for m, value in enumerate(x)) / (n if inverse else 1)
            for k in range(n)]


def convolution_oracle(x, h):
    if not x:
        return []
    result = [0] * (len(x)+len(h)-1)
    for n, a in enumerate(x):
        for m, b in enumerate(h):
            result[n+m] += a*b
    return result


def partitions(x):
    for cuts in itertools.product((False, True), repeat=max(0, len(x)-1)):
        blocks, start = [], 0
        for stop, cut in enumerate(cuts, 1):
            if cut:
                blocks.append(x[start:stop]); start = stop
        blocks.append(x[start:])
        yield blocks


class FourierTests(unittest.TestCase):
    def close(self, got, expected, tol=2e-11):
        self.assertEqual(len(got), len(expected))
        for actual, target in zip(got, expected):
            self.assertLessEqual(abs(actual-target), tol*(1+abs(target)))

    def test_four_dft_butterfly_scale_and_energy(self):
        x = [1, 2, 1, 0]
        target = [4, -2j, 0, 2j]
        self.close(lab.dft(x), target)
        self.close(lab.fft(x), target)
        self.close(lab.fft(x[::2]), [2, 0])
        self.close(lab.fft(x[1::2]), [2, 2])
        self.close([value/4 for value in lab.fft(x)], [1, -.5j, 0, .5j])
        self.assertAlmostEqual(sum(abs(v)**2 for v in target)/4, 6)
        self.assertAlmostEqual(sum(abs(v/4)**2 for v in target), 1.5)
        self.assertLess(abs(lab.dtft(x, math.pi/4) -
                            (1+math.sqrt(2))*(1-1j)), 1e-13)

    def test_general_complex_fft_against_independent_sum(self):
        for n in [1, 2, 4, 8, 16]:
            x = [complex((k*3 % 7)-2, (k*5 % 11)-4) for k in range(n)]
            self.close(lab.fft(x), explicit_transform(x))
            self.close(lab.ifft(lab.fft(x)), x)
            self.close(lab.idft(explicit_transform(x)), x)
        self.close(lab.dft([1, 2, 4]), explicit_transform([1, 2, 4]))
        with self.assertRaises(ValueError):
            lab.fft([1, 2, 4])

    def test_padding_foldback_and_asymmetric_correlation(self):
        x, h = [1, 2, 4], [1, 2]
        expected = [1, 4, 8, 8]
        self.assertEqual(convolution_oracle(x, h), expected)
        self.close(lab.linear_convolution(x, h), expected)
        self.close(lab.circular_convolution(x, h, 3), [9, 4, 8])
        self.close(lab.frequency_convolution(x, h, 3, False), [9, 4, 8])
        self.close(lab.frequency_convolution(x, h, 4), expected)
        self.close(lab.valid_correlation(x, h), [5, 10])
        self.close(lab.linear_convolution(x, h[::-1]), [2, 5, 10, 4])
        self.close(lab.fft_linear_convolution(x, h[::-1])[1:3], [5, 10])
        self.close(lab.linear_convolution([1, 2, 1, 0], [1, 1, 1]),
                   [1, 3, 4, 3, 1, 0])
        self.close(lab.circular_convolution([1, 2, 1, 0], [1, 1, 1], 4),
                   [2, 3, 4, 3])

    def test_finite_and_periodic_shift_operators(self):
        x = [1, 2, 4]
        self.close(lab.right_correlation(lab.shift(x)), [2, 5, 2])
        self.close(lab.shift(lab.right_correlation(x)), [0, 5, 10])
        self.close(lab.right_correlation(lab.shift(x, True), True), [6, 5, 10])
        self.close(lab.shift(lab.right_correlation(x, True), True), [6, 5, 10])
        # Exhaustive small integer inputs test the actual periodic matrices,
        # while the manuscript supplies the general commutation proof.
        for x in itertools.product([-1, 0, 2], repeat=3):
            self.close(lab.right_correlation(lab.shift(x, True), True),
                       lab.shift(lab.right_correlation(x, True), True))

    def test_all_block_cuts_against_outer_product_oracle(self):
        x = [1, -2, 3, 0, 4, -1]
        for h in [[2], [1, 2], [1, -1, 2, .5], [1]*9]:
            target = convolution_oracle(x, h)
            for blocks in partitions(x):
                expanded = [[], *blocks, []]
                output, events = lab.stream_blocks(expanded, h)
                self.close(output, target)
                offsets = [event['offset'] for event in events]
                self.assertEqual(offsets, sorted(offsets))
                self.assertEqual(events[-1]['offset'], len(x))
        output, _ = lab.stream_blocks([[1, 2], [], [1, 0]], [1, 1, 1])
        self.close(output, [1, 3, 4, 3, 1, 0])
        output, _ = lab.stream_blocks([[2], [], [-1, 3]], [2, -1])
        self.close(output, [4, -4, 7, -3])

    def test_stream_invalid_input_is_atomic_and_eof_is_explicit(self):
        stream = lab.OverlapAdd([1, 2, 3])
        self.close(stream.push([1]), [1])
        before = stream.snapshot
        self.assertEqual(stream.push([]), [])
        self.assertEqual(stream.snapshot, before)
        for bad in [[2, float('nan')], [True], [[1]], '12', None]:
            with self.assertRaises(ValueError):
                stream.push(bad)
            self.assertEqual(stream.snapshot, before)
        self.close(stream.flush(), [2, 3])
        self.assertEqual(stream.flush(), [])
        with self.assertRaises(ValueError):
            stream.push([])
        self.assertEqual(lab.OverlapAdd([1, 2]).flush(), [])

    def test_padding_only_samples_same_dtft(self):
        record = [math.cos(2*math.pi*1.25*n/4) for n in range(4)]
        padded = lab.dft(record + [0]*12)
        for k, value in enumerate(padded):
            expected = sum(v*complex(math.cos(-2*math.pi*k*n/16),
                                     math.sin(-2*math.pi*k*n/16))
                           for n, v in enumerate(record))
            self.assertLess(abs(value-expected), 1e-12)
        self.close(padded[::4], lab.dft(record))

    def test_declared_input_boundaries(self):
        for values in [[], [True], [float('inf')], [complex(0, float('nan'))]]:
            with self.assertRaises(ValueError):
                lab.dft(values)
        for n in [0, True, 2.0, 2]:
            with self.assertRaises(ValueError):
                lab.circular_convolution([1, 2, 4], [1, 2], n)
        self.assertEqual(lab.fft_linear_convolution([], [1, 2]), [])
        with self.assertRaises(ValueError):
            lab.valid_correlation([1j, 2], [1])


if __name__ == '__main__':
    unittest.main()
