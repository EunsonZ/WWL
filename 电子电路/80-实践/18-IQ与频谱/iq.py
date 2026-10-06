"""Peak-voltage IQ convention; no I/O or third-party imports at import time."""
import cmath
import math
import numbers

MAX_SAMPLES = 4096

def real(value, name):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(name + ' must be real, not bool or complex')
    try:
        out = float(value)
    except (OverflowError, ValueError):
        raise ValueError(name + ' must be finite') from None
    if not math.isfinite(out):
        raise ValueError(name + ' must be finite')
    return out

def series(values, complex_ok=False):
    """Bound an iterator before conversion; reject shape/type/nonfinite first."""
    result = []
    try:
        iterator = iter(values)
    except TypeError:
        raise ValueError('samples must be an iterable of numeric scalars') from None
    for value in iterator:
        if len(result) == MAX_SAMPLES:
            raise ValueError('sample budget exceeded')
        if complex_ok:
            if isinstance(value, bool) or not isinstance(value, numbers.Complex):
                raise ValueError('samples must be numeric scalars')
            a, b = real(value.real, 'real part'), real(value.imag, 'imag part')
            result.append(complex(a, b))
        else:
            result.append(real(value, 'sample'))
    n = len(result)
    if n < 2 or n & (n - 1):
        raise ValueError('length must be a power of two, 2..4096')
    return result

def checked(values):
    if any(not math.isfinite(v.real) or not math.isfinite(v.imag) for v in values):
        raise ValueError('derived numeric overflow')
    return values

def fft(values, inverse=False):
    """Radix-2 FFT, unscaled forward and 1/N inverse, finite bounded complex data."""
    if not isinstance(inverse, bool):
        raise ValueError('inverse must be bool')
    a = series(values, True)
    n, j = len(a), 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        root = cmath.exp((2j if inverse else -2j) * math.pi / length)
        for start in range(0, n, length):
            w = 1 + 0j
            for k in range(length // 2):
                u, v = a[start+k], a[start+k+length//2]*w
                a[start+k], a[start+k+length//2] = u+v, u-v
                w *= root
        checked(a)
        length *= 2
    return checked([v/n for v in a] if inverse else a)

def rates(fs, frequency, phase=0):
    fs, frequency, phase = real(fs, 'fs'), real(frequency, 'frequency'), real(phase, 'phase')
    if fs <= 0 or not 0 < frequency/fs < .5:
        raise ValueError('require fs>0 and 0<frequency<fs/2')
    return fs, frequency/fs, phase

def upconvert(envelope, fs, carrier):
    z = series(envelope, True)
    _, ratio, _ = rates(fs, carrier)
    return [v.real for v in checked([a*cmath.exp(2j*math.pi*ratio*n) for n,a in enumerate(z)])]

def mix(samples, fs, lo, phase=0):
    """2*x*exp(-j*(2*pi*fLO*n/fs+phase)); output is intentionally complex."""
    x = series(samples)
    _, ratio, phase = rates(fs, lo, phase)
    # Reduce phase before combining; huge finite phase never overflows the sum.
    phase = math.remainder(phase, 2*math.pi)
    return checked([2*a*cmath.exp(-1j*(2*math.pi*ratio*n+phase)) for n,a in enumerate(x)])

def bin_lowpass(values, fs, cutoff):
    a = series(values, True)
    fs, cutoff = real(fs, 'fs'), real(cutoff, 'cutoff')
    if fs <= 0 or not 0 <= cutoff/fs < .5:
        raise ValueError('require fs>0 and 0<=cutoff<fs/2')
    n = len(a)
    spectrum = fft(a)
    bound = cutoff/fs
    return fft([v if abs((k if k < n//2 else k-n)/n) <= bound else 0j
                for k,v in enumerate(spectrum)], inverse=True)

def demodulate(samples, fs, lo, cutoff, phase=0):
    """Periodic noncausal bin filter, not a hardware causal LPF design.

    Caller must establish occupied envelope support and image separation.
    cutoff < min(lo, fs/2-lo) is a conservative sampled no-overlap guard.
    """
    fs, ratio, _ = rates(fs, lo, phase)
    cutoff = real(cutoff, 'cutoff')
    if not 0 <= cutoff/fs < min(ratio, .5-ratio):
        raise ValueError('cutoff violates conservative image/Nyquist guard')
    return bin_lowpass(mix(samples, fs, lo, phase), fs, cutoff)

def case():
    fs, carrier, n = 128., 16., 128
    z = [2-1j + .5*cmath.exp(2j*math.pi*4*k/n) + .25*cmath.exp(-2j*math.pi*3*k/n) for k in range(n)]
    x = upconvert(z, fs, carrier)
    return fs, carrier, z, x, demodulate(x, fs, carrier, 4)
