"""Finite Fourier/FFT examples. Standard library only; import has no I/O.

Forward transforms are unnormalized; inverse divides by N. Real/complex
finite inputs retain complex outputs. This is a teaching CPU model, not an
audio driver, a CNN API wrapper, or a general Fourier convergence solver.
"""
import argparse
import cmath
import json
import math
from numbers import Complex
from pathlib import Path


def scalar(value):
    if isinstance(value, bool) or not isinstance(value, Complex):
        raise ValueError('finite numeric scalar required')
    try:
        result = complex(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError('finite complex range required') from exc
    if not (math.isfinite(result.real) and math.isfinite(result.imag)):
        raise ValueError('finite numeric scalar required')
    return result


def vector(values, allow_empty=False):
    if isinstance(values, (str, bytes)):
        raise ValueError('numeric iterable required')
    try:
        result = [scalar(value) for value in values]
    except TypeError as exc:
        raise ValueError('numeric iterable required') from exc
    if not result and not allow_empty:
        raise ValueError('nonempty vector required')
    return result


def positive_int(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError('positive integer required')
    return value


def sum_complex(values):
    values = list(values)
    try:
        return scalar(complex(math.fsum(v.real for v in values),
                              math.fsum(v.imag for v in values)))
    except OverflowError as exc:
        raise ValueError('derived result outside finite range') from exc


def dtft(values, theta):
    x = vector(values)
    theta = scalar(theta)
    if theta.imag:
        raise ValueError('real angle required')
    return sum_complex(value * cmath.exp(-1j * theta.real * n)
                       for n, value in enumerate(x))


def dft(values):
    x = vector(values)
    n = len(x)
    return [dtft(x, 2 * math.pi * k / n) for k in range(n)]


def idft(values):
    spectrum = vector(values)
    n = len(spectrum)
    return [scalar(sum_complex(value * cmath.exp(2j * math.pi * k * m / n)
                               for k, value in enumerate(spectrum)) / n)
            for m in range(n)]


def _fft(x):
    n = len(x)
    if n == 1:
        return x[:]
    even, odd = _fft(x[::2]), _fft(x[1::2])
    rotated = [scalar(cmath.exp(-2j * math.pi * k / n) * odd[k])
               for k in range(n // 2)]
    return ([scalar(even[k] + rotated[k]) for k in range(n // 2)] +
            [scalar(even[k] - rotated[k]) for k in range(n // 2)])


def fft(values):
    x = vector(values)
    if len(x) & (len(x) - 1):
        raise ValueError('radix-2 FFT requires power-of-two length')
    return _fft(x)


def ifft(values):
    spectrum = vector(values)
    return [scalar(value.conjugate() / len(spectrum))
            for value in fft([s.conjugate() for s in spectrum])]


def next_power_two(value):
    n = positive_int(value)
    return 1 << (n - 1).bit_length()


def linear_convolution(values, kernel):
    x, h = vector(values, True), vector(kernel)
    if not x:
        return []
    return [sum_complex(x[k] * h[n-k] for k in range(len(x))
                        if 0 <= n-k < len(h))
            for n in range(len(x) + len(h) - 1)]


def circular_convolution(values, kernel, n):
    x, h, n = vector(values), vector(kernel), positive_int(n)
    if n < max(len(x), len(h)):
        raise ValueError('N must not truncate either input')
    xp, hp = x + [0j] * (n-len(x)), h + [0j] * (n-len(h))
    return [sum_complex(xp[k] * hp[(m-k) % n] for k in range(n))
            for m in range(n)]


def frequency_convolution(values, kernel, n, radix_two=True):
    """N-point circular output; caller owns padding/full cropping convention."""
    x, h, n = vector(values), vector(kernel), positive_int(n)
    if n < max(len(x), len(h)):
        raise ValueError('N must not truncate either input')
    forward, inverse = (fft, ifft) if radix_two else (dft, idft)
    a = forward(x + [0j] * (n-len(x)))
    b = forward(h + [0j] * (n-len(h)))
    return inverse([scalar(u*v) for u, v in zip(a, b)])


def fft_linear_convolution(values, kernel):
    x, h = vector(values, True), vector(kernel)
    if not x:
        return []
    length = len(x) + len(h) - 1
    return frequency_convolution(x, h, next_power_two(length))[:length]


def valid_correlation(values, kernel):
    """Real CNN-style valid correlation; no conjugate and no bias, stride 1."""
    x, h = vector(values), vector(kernel)
    if any(v.imag for v in x + h):
        raise ValueError('this correlation example requires real values')
    if len(x) < len(h):
        raise ValueError('input must be at least as long as kernel')
    return [sum_complex(h[r] * x[n+r] for r in range(len(h)))
            for n in range(len(x)-len(h)+1)]


def shift(values, periodic=False):
    x = vector(values)
    return [x[-1] if periodic else 0j] + x[:-1]


def right_correlation(values, periodic=False):
    """C0 or Cp, the fixed real h=(1,2) rule, preserving input length."""
    x = vector(values)
    if any(v.imag for v in x):
        raise ValueError('real fixed correlation example required')
    return [scalar(x[n] + 2*(x[(n+1) % len(x)]
                            if periodic or n+1 < len(x) else 0j))
            for n in range(len(x))]


class OverlapAdd:
    """Variable contiguous blocks; push emits P points, flush M-1 tail points.

    Empty push has no clock advance. Invalid or overflowing computation does
    not commit state. No-input flush emits nothing. Repeated flush is empty;
    push after closed raises even for an empty block. No implicit missing-data
    recovery. consumed is input count, also the next output's global index.
    """
    def __init__(self, kernel):
        self._h = tuple(vector(kernel))
        self._tail = [0j] * (len(self._h)-1)
        self.consumed = 0
        self.closed = False

    @property
    def snapshot(self):
        return self.consumed, self.closed, tuple(self._tail)

    def push(self, values):
        if self.closed:
            raise ValueError('stream is closed')
        block = vector(values, True)
        if not block:
            return []
        local = fft_linear_convolution(block, self._h)
        for n, value in enumerate(self._tail):
            local[n] = scalar(local[n] + value)
        emitted, tail = local[:len(block)], local[len(block):]
        self._tail = tail
        self.consumed += len(block)
        return emitted

    def flush(self):
        if self.closed:
            return []
        result = self._tail[:] if self.consumed else []
        self.closed = True
        self._tail = [0j] * len(self._tail)
        return result


def stream_blocks(blocks, kernel):
    stream = OverlapAdd(kernel)
    output, events = [], []
    for block in blocks:
        offset = stream.consumed
        emitted = stream.push(block)
        events.append({'offset': offset, 'emitted': emitted,
                       'state': stream.snapshot})
        output.extend(emitted)
    tail = stream.flush()
    events.append({'offset': stream.consumed, 'tail': tail})
    output.extend(tail)
    return output, events


def cases():
    four = [1, 2, 1, 0]
    x, h = [1, 2, 4], [1, 2]
    stream, events = stream_blocks([[1, 2], [], [1, 0]], [1, 1, 1])
    leakage = [math.cos(2 * math.pi * 1.25 * n / 4) for n in range(4)]
    return {
        'normalization': 'forward unnormalized; inverse 1/N',
        'four': {'input': four, 'dft': dft(four), 'fft': fft(four),
                 'dtfs': [v/4 for v in dft(four)],
                 'dtft_pi_over_four': dtft(four, math.pi/4)},
        'symmetric_kernel': {'linear': linear_convolution(four, [1, 1, 1]),
                             'circular_n4': circular_convolution(four, [1, 1, 1], 4),
                             'fft_full': fft_linear_convolution(four, [1, 1, 1])},
        'asymmetric': {'input': x, 'kernel': h,
                       'linear': linear_convolution(x, h),
                       'circular_n3': circular_convolution(x, h, 3),
                       'dft_n3': frequency_convolution(x, h, 3, False),
                       'fft_n4': frequency_convolution(x, h, 4),
                       'valid_correlation': valid_correlation(x, h),
                       'flipped_full': linear_convolution(x, h[::-1])},
        'boundary': {'C0_S0': right_correlation(shift(x)),
                     'S0_C0': shift(right_correlation(x)),
                     'Cp_Sp': right_correlation(shift(x, True), True),
                     'Sp_Cp': shift(right_correlation(x, True), True)},
        'ola': {'output': stream, 'events': events},
        'window': {'fs_hz': 8, 'record_length': 4,
                   'input': leakage, 'dft_n4': dft(leakage),
                   'dft_n16': dft(leakage + [0]*12),
                   'grid_hz_n4': 2, 'grid_hz_n16': .5,
                   'rectangle_first_zero_halfwidth_hz': 2},
    }


def json_ready(value):
    if isinstance(value, complex):
        return {'re': value.real, 'im': value.imag}
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def generate(output):
    destination = Path(output).resolve()
    if destination.exists() or any((p/'AGENTS.md').exists()
                                    for p in [destination, *destination.parents]):
        raise ValueError('new external output directory required')
    data = json_ready(cases())
    destination.mkdir(parents=True)
    (destination/'results.json').write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                   allow_nan=False) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    generate(parser.parse_args().output)


if __name__ == '__main__':
    main()
