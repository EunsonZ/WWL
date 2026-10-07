"""CPU teaching model. Samples in V; causal phase-zero 48k -> 16k FIR.

No device, deadline guarantee or ADC is modeled. Generators need --output.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np

FS = 48000
M = 3
TAPS = 193

def vector(x):
    raw = np.asarray(x)
    if np.iscomplexobj(raw) or raw.ndim != 1 or (raw.dtype == object and any(
            isinstance(v, (complex, np.complexfloating)) or np.iscomplexobj(v)
            for v in raw.flat)):
        raise ValueError('finite real one-dimensional vector required')
    a = np.asarray(raw, dtype=np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError('nonfinite value')
    return a

def positive_int(n):
    if type(n) is not int or n < 1:
        raise ValueError('positive integer required')
    return n

def design(taps=TAPS, cutoff=7000.0, fs=FS):
    positive_int(taps)
    if taps < 3 or taps % 2 == 0 or not math.isfinite(fs) or fs <= 0:
        raise ValueError('odd taps >= 3 and positive fs required')
    if not math.isfinite(cutoff) or not 0 < cutoff < fs / 2:
        raise ValueError('cutoff must lie inside Nyquist')
    scale = 2 * cutoff / fs
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('cutoff/fs cannot be represented for numerical design')
    k = np.arange(taps)
    # Subnormal parameters may pass mathematical bounds yet lose the kernel.
    # Permit harmless underflow in tails, reject zero/nonfinite normalization.
    with np.errstate(under='ignore', over='ignore', invalid='ignore', divide='ignore'):
        h = scale * np.sinc(scale * (k-(taps-1)/2))
        h *= np.blackman(taps)
        denominator = float(h.sum())
        if not np.all(np.isfinite(h)) or not math.isfinite(denominator) or denominator == 0:
            raise ValueError('kernel is not numerically normalizable')
        h = h / denominator
    if not np.all(np.isfinite(h)):
        raise ValueError('normalization produced nonfinite coefficients')
    return h

def offline(x, h, factor=M, phase=0):
    x, h = vector(x), vector(h)
    positive_int(factor)
    if len(h) == 0 or type(phase) is not int or not 0 <= phase < factor:
        raise ValueError('nonempty h and valid integer phase required')
    if not len(x):
        return np.empty(0)
    return np.convolve(x, h, mode='full')[phase::factor]

def polyphase(x, h, factor=M, phase=0):
    """Independent reference: only retained n=phase+m*factor, grouped k=qM+r."""
    x, h = vector(x), vector(h)
    positive_int(factor)
    if len(h) == 0 or type(phase) is not int or not 0 <= phase < factor:
        raise ValueError('invalid h or phase')
    if not len(x):
        return np.empty(0)
    out = []
    for n in range(phase, len(x)+len(h)-1, factor):
        s = 0.0
        for r in range(factor):
            for k in range(r, len(h), factor):
                j = n-k
                if 0 <= j < len(x):
                    s += h[k]*x[j]
        out.append(s)
    return np.array(out)

class Stream:
    """O(L) persistent ring. process preserves n; flush finalizes once, reset restarts."""
    def __init__(self, h, factor=M, phase=0):
        self.h = vector(h).copy()
        positive_int(factor)
        if not len(self.h) or type(phase) is not int or not 0 <= phase < factor:
            raise ValueError('invalid h or phase')
        self.factor, self.phase = factor, phase
        self.reset()

    def reset(self):
        self.ring = np.zeros(len(self.h))
        self.n = 0
        self.real_count = 0
        self.closed = False

    def _consume(self, a):
        out = []
        for value in a:
            self.ring[self.n % len(self.h)] = value
            if self.n % self.factor == self.phase:
                # Evaluate only kept outputs, in k order, using ring indices.
                indices = (self.n - np.arange(len(self.h))) % len(self.h)
                out.append(float(np.dot(self.h, self.ring[indices])))
            self.n += 1
        return np.array(out)

    def process(self, block):
        if self.closed:
            raise RuntimeError('closed: reset before a new record')
        a = vector(block)  # validate entire block before changing state
        self.real_count += len(a)
        return self._consume(a)

    def flush(self):
        if self.closed:
            return np.empty(0)
        self.closed = True
        if not self.real_count:
            return np.empty(0)
        return self._consume(np.zeros(len(self.h)-1))

def quantize_q15(x):
    """Round nearest, ties to even; saturate int16. 1 V is positive full-scale unit."""
    a = vector(x)
    return np.clip(np.rint(a*32768), -32768, 32767).astype(np.int64)

def round_div_even(n, divisor):
    """Exact integer nearest division with ties-to-even, including negatives."""
    q, r = divmod(abs(int(n)), divisor)
    if 2*r > divisor or (2*r == divisor and q % 2):
        q += 1
    return q if n >= 0 else -q

def fixed(x, h, factor=M, phase=0, acc_bits=40):
    """Bit-contract simulation: Q1.15 x,h, exact products, per-MAC acc saturation.

    Each retained output rounds once from Q2.30 to Q1.15, then saturates.
    Python integers do not emulate timing, SIMD, or implicit machine overflow.
    """
    x, h = vector(x), vector(h)
    positive_int(factor)
    if len(h) == 0 or type(phase) is not int or not 0 <= phase < factor:
        raise ValueError('invalid h or phase')
    if type(acc_bits) is not int or not 2 <= acc_bits <= 64:
        raise ValueError('acc_bits must be 2..64')
    xi, hi = quantize_q15(x), quantize_q15(h)
    amin, amax = -(1 << (acc_bits-1)), (1 << (acc_bits-1))-1
    mac_clips = output_clips = 0
    out = []
    for n in range(phase, len(x)+len(h)-1 if len(x) else phase, factor):
        acc = 0
        for k, coeff in enumerate(hi):
            j = n-k
            if 0 <= j < len(x):
                trial = acc + int(coeff)*int(xi[j])
                bounded = min(amax, max(amin, trial))
                mac_clips += int(bounded != trial)
                acc = bounded
        q = round_div_even(acc, 32768)
        bounded = min(32767, max(-32768, q))
        output_clips += int(bounded != q)
        out.append(bounded / 32768)
    return np.array(out), dict(input_clips=int(np.count_nonzero((x < -1) | (x > 32767/32768))),
                               coefficient_clips=int(np.count_nonzero((h < -1) | (h > 32767/32768))),
                               mac_clips=mac_clips, output_clips=output_clips,
                               worst_acc_bound=int(32768*sum(abs(int(i)) for i in hi)),
                               acc_bits=acc_bits)

def response(h, nfft=524288, fs=FS):
    h = vector(h)
    positive_int(nfft)
    if nfft < len(h) or nfft % 2 or not math.isfinite(fs) or fs <= 0:
        raise ValueError('even nfft >= taps and positive fs required')
    return np.fft.rfftfreq(nfft, 1/fs), np.abs(np.fft.rfft(h, nfft))

def certified_specs(h):
    """Grid + Lipschitz enclosure, includes band endpoints by direct evaluation.

    Bound holds for centered complex response; no linear-phase assumption needed.
    Floating point error is not enclosed; this is an analytic enclosure with CPU values.
    """
    h = vector(h)
    f, a = response(h)
    d = (len(h)-1)/2
    slope = float(np.sum(np.abs((np.arange(len(h))-d)*h)))
    margin = slope*math.pi/524288
    at = lambda hz: abs(np.sum(h*np.exp(-2j*np.pi*hz/FS*np.arange(len(h)))))
    pass_error = max(float(np.max(np.abs(a[f <= 6000]-1))), abs(at(6000)-1))
    stop = max(float(np.max(a[f >= 8000])), at(8000))
    return dict(grid_pass_error=pass_error, grid_stop_max=stop,
                lipschitz_margin=margin, pass_error_enclosure=pass_error+margin,
                stop_max_enclosure=stop+margin,
                enclosure_excludes_float_roundoff=True)

def single_amplitude(x, fs):
    x = vector(x)
    if not len(x) or not math.isfinite(fs) or fs <= 0:
        raise ValueError('nonempty record and positive fs required')
    a = np.abs(np.fft.rfft(x))/len(x)
    if len(x) % 2 == 0:
        a[1:-1] *= 2
    else:
        a[1:] *= 2
    return np.fft.rfftfreq(len(x), 1/fs), a

def experiment():
    h = design()
    n = np.arange(12000)
    x = .6*np.cos(2*np.pi*1000*n/FS) + .3*np.cos(2*np.pi*10000*n/FS)
    stream = Stream(h)
    pieces = []
    cursor = 0
    sizes = [1, 2, 17, 480, 31]
    while cursor < len(x):
        b = sizes[len(pieces) % len(sizes)]
        pieces.append(stream.process(x[cursor:cursor+b]))
        cursor += b
    pieces.append(stream.flush())
    y = offline(x,h)
    streamed = np.concatenate(pieces)
    yp = polyphase(x,h)
    # Full-support interval n=3m is 192..N-1. Pick 3840 outputs (integer tone periods).
    first, count = 64, 3840
    f, naive = single_amplitude(x[::3][first:first+count], FS/3)
    _, good = single_amplitude(y[first:first+count], FS/3)
    yq, stats = fixed(x,h)
    _, qspec = single_amplitude(yq[first:first+count], FS/3)
    results = dict(schema='u3-resample-v1', fs_in=FS, fs_out=FS//M, factor=M,
        phase=0, taps=len(h), cutoff_hz=7000, pass_edge_hz=6000, stop_edge_hz=8000,
        input_count=len(x), output_count=len(y), group_delay_input_samples=96,
        spectrum=dict(first_output_index=first, count=count, window='rectangular',
                      kind='one-sided peak amplitude', units='V', bin_hz=(FS/3)/count,
                      naive_6k=float(naive[np.argmin(abs(f-6000))]),
                      filtered_6k=float(good[np.argmin(abs(f-6000))]),
                      filtered_1k=float(good[np.argmin(abs(f-1000))])),
        stream_max_error=float(np.max(abs(y-streamed))),
        polyphase_max_error=float(np.max(abs(y-yp))),
        fixed_max_error=float(np.max(abs(y-yq))), fixed=stats,
        specs=certified_specs(h), q15_specs=certified_specs(quantize_q15(h)/32768),
        evidence='CPU teaching only; no sound device, WCET, ADC or production run')
    return dict(h=h,x=x,y=y,streamed=streamed,yq=yq,f=f,naive=naive,good=good,qspec=qspec,results=results)

def write_data(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data = experiment()
    np.savetxt(output/'coefficients.csv', np.column_stack([np.arange(TAPS),data['h'],quantize_q15(data['h'])]),
               delimiter=',',header='k,h_dimensionless,h_q15_integer',comments='',fmt=['%d','%.17g','%d'])
    np.savetxt(output/'spectrum.csv',np.column_stack([data['f'],data['naive'],data['good'],data['qspec']]),
               delimiter=',',header='f_Hz,naive_V,filtered_V,q15_V',comments='',fmt='%.17g')
    np.savetxt(output/'samples.csv',np.column_stack([np.arange(len(data['y'])),data['y'],data['streamed'],data['yq']]),
               delimiter=',',header='m,offline_V,stream_V,q15_V',comments='',fmt='%.17g')
    (output/'results.json').write_text(json.dumps(data['results'],ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    return data

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    data = write_data(args.output)
    print(json.dumps(data['results'],ensure_ascii=False,sort_keys=True))

if __name__ == '__main__':
    main()
