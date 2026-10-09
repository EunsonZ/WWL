"""Butterworth coefficients and finite-precision teaching probes; stdlib only.

No import-time I/O. Outputs are CPU models, not audio/DSP-chip measurements.
The ideal filter and the exact binary64-section model are distinct references.
"""
import argparse
import cmath
from decimal import (Decimal, localcontext, Context, ROUND_FLOOR, ROUND_CEILING,
                     ROUND_HALF_EVEN, Overflow, Underflow, Subnormal, Clamped, Inexact)
from fractions import Fraction
import json
import math
from pathlib import Path
import struct


def real(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('finite real scalar required')
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError('finite real range required') from exc
    if not math.isfinite(result):
        raise ValueError('finite real scalar required')
    return result


def design(fs=48000, fp=6000, fsb=8000, pass_error=.01, stop=.001):
    fs, fp, fsb, pass_error, stop = map(real, (fs, fp, fsb, pass_error, stop))
    if not (0 < fp < fsb < fs/2 and 0 < stop < 1-pass_error < 1):
        raise ValueError('ordered bands and positive tolerances required')
    wp, ws = 2*fs*math.tan(math.pi*fp/fs), 2*fs*math.tan(math.pi*fsb/fs)
    ep2, es2 = (1-pass_error)**-2-1, stop**-2-1
    estimate = math.log(es2/ep2)/(2*math.log(ws/wp))
    n = math.ceil(estimate)
    lower, upper = wp/ep2**(1/(2*n)), ws/es2**(1/(2*n))
    wc = math.sqrt(lower*upper)
    analog = [wc*cmath.exp(1j*(math.pi/2+(2*k+1)*math.pi/(2*n)))
              for k in range(n)]
    poles = [(2*fs+p)/(2*fs-p) for p in analog]
    sections = []
    for k in range(n//2):
        pole = poles[k]
        a1, a2 = -2*pole.real, abs(pole)**2
        b0 = (1+a1+a2)/4
        sections.append([b0, 2*b0, b0, 1., a1, a2])
    if n % 2:
        pole = (2*fs-wc)/(2*fs+wc)
        b0 = (1-pole)/2
        sections.append([b0, b0, 0., 1., -pole, 0.])
    # Radius order is a declared comparison, not an optimality claim.
    sections.sort(key=section_radius)
    return {'fs': fs, 'fp': fp, 'fsb': fsb, 'pass_error': pass_error,
            'stop': stop, 'estimate': estimate, 'order': n,
            'wp': wp, 'ws': ws, 'wc_bounds': [lower, upper], 'wc': wc,
            'cutoff_hz': fs/math.pi*math.atan(wc/(2*fs)),
            'poles': poles, 'sections': sections}


def section_radius(section):
    _, _, _, _, a1, a2 = section
    if a2 == 0:
        return abs(a1)
    root = cmath.sqrt(a1*a1-4*a2)
    return max(abs((-a1+root)/2), abs((-a1-root)/2))


def response(sections, theta):
    q = cmath.exp(-1j*real(theta))
    result = 1+0j
    for b0, b1, b2, _, a1, a2 in sections:
        result *= (b0+b1*q+b2*q*q)/(1+a1*q+a2*q*q)
    return result


def ideal_amplitude(spec, theta):
    if theta == math.pi:
        return 0.
    ratio = 2*spec['fs']*math.tan(theta/2)/spec['wc']
    power = 2*spec['order']*math.log(abs(ratio)) if ratio else -math.inf
    return math.exp(-.5*power) if power > 700 else 1/math.sqrt(1+math.exp(power))


def amplitude_cell(sections, theta, halfwidth):
    """Continuous enclosure from triangle/quotient/product bounds, float arithmetic.

    Bounds apply to the fixed coefficient rational function, not a rounded
    recursive trajectory. No assumption that its magnitude is monotone.
    """
    q = cmath.exp(-1j*theta)
    factors, derivatives = [], []
    center = 1+0j
    for b0, b1, b2, a0, a1, a2 in sections:
        if a0 != 1.:
            raise ValueError('normalized section denominator required')
        numerator = b0+b1*q+b2*q*q
        denominator = 1+a1*q+a2*q*q
        nprime, dprime = abs(b1)+2*abs(b2), abs(a1)+2*abs(a2)
        upper_n = abs(numerator)+nprime*halfwidth
        lower_d = abs(denominator)-dprime*halfwidth
        if lower_d <= 0:
            raise ValueError('cell too wide to enclose denominator away from zero')
        factors.append(upper_n/lower_d)
        derivatives.append(nprime/lower_d+upper_n*dprime/lower_d**2)
        center *= numerator/denominator
    # Prefix/suffix products avoid division by a factor vanishing at Nyquist.
    prefix = [1.]
    for factor in factors:
        prefix.append(prefix[-1]*factor)
    suffix = [1.]*(len(factors)+1)
    for i in range(len(factors)-1, -1, -1):
        suffix[i] = factors[i]*suffix[i+1]
    derivative = sum(value*prefix[i]*suffix[i+1]
                     for i, value in enumerate(derivatives))
    center_abs, margin = abs(center), derivative*halfwidth
    return {'center_amplitude': center_abs, 'derivative_bound': derivative,
            'margin': margin, 'lower': max(0., center_abs-margin),
            'upper': center_abs+margin}


def amplitude_estimate(spec, sections=None, intervals=65536):
    """Cover both closed bands with local enclosures; not outward interval rounding."""
    if isinstance(intervals, bool) or not isinstance(intervals, int) or intervals < 1:
        raise ValueError('positive band interval count required')
    sections = spec['sections'] if sections is None else sections
    bands = {'pass': (0., 2*math.pi*spec['fp']/spec['fs']),
             'stop': (2*math.pi*spec['fsb']/spec['fs'], math.pi)}
    result = {'intervals_per_band': intervals,
              'floating_bound_not_interval_arithmetic': True}
    for name, (start, stop) in bands.items():
        width = (stop-start)/intervals
        lower, upper, largest_margin = math.inf, 0., 0.
        for k in range(intervals):
            cell = amplitude_cell(sections, start+(k+.5)*width, width/2)
            lower, upper = min(lower, cell['lower']), max(upper, cell['upper'])
            largest_margin = max(largest_margin, cell['margin'])
        result[name] = {'theta_rad_per_sample': [start, stop],
                        'lower': lower, 'upper': upper,
                        'max_cell_margin': largest_margin}
    result['estimate_within_amplitude_contract'] = (
        result['pass']['lower'] >= 1-spec['pass_error'] and
        result['pass']['upper'] <= 1+spec['pass_error'] and
        result['stop']['upper'] <= spec['stop'])
    return result


def delay(poles, theta):
    q = cmath.exp(-1j*theta)
    return .5*sum((1-abs(p)**2)/abs(1-p*q)**2 for p in poles)


def ideal_pole_delay_estimate(spec, intervals=32768):
    if isinstance(intervals, bool) or not isinstance(intervals, int) or intervals < 1:
        raise ValueError('positive grid interval count required')
    edge = 2*math.pi*spec['fp']/spec['fs']
    distances = []
    for p in spec['poles']:
        angle = cmath.phase(p)
        candidates = [abs(1-p), abs(1-p*cmath.exp(-1j*edge))]
        if 0 <= angle <= edge:
            candidates.append(1-abs(p))
        distances.append(min(candidates))
    bound = sum((1-abs(p)**2)*abs(p)/d**4
                for p, d in zip(spec['poles'], distances))
    values = [delay(spec['poles'], edge*k/intervals) for k in range(intervals+1)]
    maximum = max(values)
    margin = bound*edge/(2*intervals)
    return {'dc_samples': values[0], 'min_grid_samples': min(values),
            'max_grid_samples': maximum, 'derivative_bound': bound,
            'grid_margin_samples': margin, 'upper_samples': maximum+margin,
            'budget_samples': .002*spec['fs'], 'intervals': intervals,
            'floating_bound_not_interval_arithmetic': True}


class Outward:
    """Decimal endpoints; every arithmetic result rounds away from its interval.

    Float coefficients enter through Decimal.from_float (exact conversion),
    never str(float). Contexts are private and independent of getcontext().
    Exceptional range behavior raises; it cannot produce a certificate.
    """
    def __init__(self, precision=80):
        if isinstance(precision, bool) or not isinstance(precision, int) or precision < 24:
            raise ValueError('at least 24 decimal digits required')
        self.down = Context(prec=precision, rounding=ROUND_FLOOR)
        self.up = Context(prec=precision, rounding=ROUND_CEILING)
        for ctx in [self.down, self.up]:
            for signal in [Overflow, Underflow, Subnormal, Clamped]:
                ctx.traps[signal] = True

    def point(self, value):
        if isinstance(value, bool):
            raise ValueError('finite exact scalar required')
        if isinstance(value, float):
            value = Decimal.from_float(value)
        elif isinstance(value, (str, int)):
            value = Decimal(value)
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError('finite exact scalar required')
        return value, value

    def add(self, x, y):
        return self.down.add(x[0], y[0]), self.up.add(x[1], y[1])

    def sub(self, x, y):
        return self.down.subtract(x[0], y[1]), self.up.subtract(x[1], y[0])

    def mul(self, x, y):
        pairs = [(a, b) for a in x for b in y]
        return (min(self.down.multiply(a, b) for a, b in pairs),
                max(self.up.multiply(a, b) for a, b in pairs))

    def square(self, x):
        if x[0] <= 0 <= x[1]:
            return Decimal(0), max(self.up.multiply(v, v) for v in x)
        return (min(self.down.multiply(v, v) for v in x),
                max(self.up.multiply(v, v) for v in x))

    def div(self, x, y):
        if y[0] <= 0 <= y[1]:
            raise ValueError('interval divisor contains zero')
        pairs = [(a, b) for a in x for b in y]
        return (min(self.down.divide(a, b) for a, b in pairs),
                max(self.up.divide(a, b) for a, b in pairs))

    def polynomial(self, coefficients, x):
        result = self.point(0)
        for coefficient in coefficients[::-1]:
            result = self.add(self.mul(result, x), coefficient)
        return result


def strict_sections(sections, arithmetic):
    """Bind fixed binary coefficients, exact binomial numerators and Jury tests."""
    prepared, records = [], []
    iv = arithmetic
    for row in sections:
        if len(row) != 6:
            raise ValueError('six coefficients per SOS required')
        if any(not isinstance(v, float) for v in row):
            raise ValueError('fixed binary floating coefficients required')
        values = [iv.point(v)[0] for v in row]
        b0, b1, b2, a0, a1, a2 = values
        exact = [Fraction(v) for v in values]
        eb0, eb1, eb2, ea0, ea1, ea2 = exact
        if ea0 != 1 or eb0 == 0:
            raise ValueError('normalized nonzero binomial numerator required')
        degree = 1 if eb2 == ea2 == 0 else 2
        if degree == 1:
            valid = eb1 == eb0 and abs(ea1) < 1
        else:
            valid = (eb2 == eb0 and eb1 == 2*eb0 and -1 < ea2 < 1
                     and 1+ea1+ea2 > 0 and 1-ea1+ea2 > 0)
        if not valid:
            raise ValueError('exact binomial shape or Schur stability conditions failed')
        A1, A2 = iv.point(a1), iv.point(a2)
        one, two, four = iv.point(1), iv.point(2), iv.point(4)
        # Q(c)=|1+a1 q+a2 q^2|^2. All polynomial coefficients enclosed.
        Q = [iv.add(iv.square(iv.sub(one, A2)), iv.square(A1)),
             iv.mul(two, iv.mul(A1, iv.add(one, A2))), iv.mul(four, A2)]
        # Group delay uses this same denominator, not separately computed poles.
        if degree == 1:
            J = [iv.div(iv.sub(one, iv.square(A1)), two)]
        else:
            J = [iv.sub(one, iv.square(A2)), iv.mul(A1, iv.sub(one, A2))]
        prepared.append({'b0_squared': iv.square(iv.point(b0)),
                         'degree': degree, 'Q': Q, 'J': J})
        records.append({'decimal_exact': [str(v) for v in values],
                        'dyadic_ratios': [[f.numerator, f.denominator] for f in exact],
                        'numerator_degree': degree, 'exact_schur_conditions': True})
    if not prepared:
        raise ValueError('nonempty cascade required')
    return prepared, records


def strict_cell(prepared, left, right, arithmetic, with_delay):
    """Enclose every c in the entire closed cell by outward polynomial algebra."""
    iv, c = arithmetic, (left, right)
    amplitude_squared, group_delay = iv.point(1), iv.point(0)
    smallest_denominator = None
    factor = iv.add(iv.point(2), iv.mul(iv.point(2), c))
    for section in prepared:
        Q = iv.polynomial(section['Q'], c)
        if Q[0] <= 0:
            return None
        smallest_denominator = (Q[0] if smallest_denominator is None
                                else min(smallest_denominator, Q[0]))
        binomial = factor if section['degree'] == 1 else iv.square(factor)
        P = iv.mul(section['b0_squared'], binomial)
        amplitude_squared = iv.mul(amplitude_squared, iv.div(P, Q))
        if with_delay:
            J = iv.polynomial(section['J'], c)
            group_delay = iv.add(group_delay, iv.div(J, Q))
    return {'amplitude_squared': amplitude_squared,
            'group_delay_samples': group_delay if with_delay else None,
            'minimum_Q_lower': smallest_denominator}


def strict_machine_certificate(spec, sections=None, precision=80,
                               max_depth=24, max_cells=131072):
    """Rigorous closed-band certificate for the declared primary 48k design.

    Unsupported specifications, arithmetic failures, unresolved cells or a
    resource cap can never return certified=True. Finite adaptive bisection
    certifies every point in the union of accepted closed cells, not samples.
    """
    for value in [max_depth, max_cells]:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError('positive integer refinement limits required')
    if max_depth > 28:
        raise ValueError('max_depth must be at most 28 for exact midpoint context')
    primary = (spec['fs'], spec['fp'], spec['fsb'], spec['pass_error'], spec['stop'])
    if primary != (48000., 6000., 8000., .01, .001):
        return {'status': 'unsupported_specification', 'certified': False}
    iv = Outward(precision)
    selected = spec['sections'] if sections is None else sections
    prepared, coefficients = strict_sections(selected, iv)
    # This decimal is a rational. Fraction multiplication proves c_lo <= sqrt(1/2).
    c_lo = Decimal('0.707106781186547524400844362104849039284835937688474036588339868')
    ratio = Fraction(c_lo)
    if not (ratio > 0 and ratio*ratio <= Fraction(1, 2)):
        raise ValueError('passband rational endpoint failed its exact square proof')
    exact_midpoint = Context(prec=200, rounding=ROUND_HALF_EVEN)
    exact_midpoint.traps[Inexact] = True
    # max_depth<=28, initial decimal has <80 digits; every midpoint has <110.
    bands = {'pass': (c_lo, Decimal(1)), 'stop': (Decimal(-1), Decimal('0.5'))}
    results = {}
    for band, (left, right) in bands.items():
        stack, accepted, unresolved = [(left, right, 0)], [], []
        evaluations = 0
        with_delay = band == 'pass'
        while stack:
            lo, hi, depth = stack.pop()
            if evaluations >= max_cells:
                unresolved.append({'c': [lo, hi], 'reason': 'max_cells'})
                unresolved.extend({'c': [a, b], 'reason': 'max_cells'} for a, b, _ in stack)
                stack.clear()
                break
            evaluations += 1
            cell = strict_cell(prepared, lo, hi, iv, with_delay)
            if cell is None:
                fits = False
            elif with_delay:
                amp, lag = cell['amplitude_squared'], cell['group_delay_samples']
                fits = (amp[0] >= Decimal('0.9801') and amp[1] <= Decimal('1.0201')
                        and lag[0] >= 0 and lag[1] <= Decimal(96))
            else:
                fits = cell['amplitude_squared'][1] <= Decimal('0.000001')
            if fits:
                accepted.append({'c': [lo, hi], 'depth': depth, **cell})
            elif depth >= max_depth:
                unresolved.append({'c': [lo, hi], 'reason': 'max_depth', 'enclosure': cell})
            else:
                mid = exact_midpoint.divide(exact_midpoint.add(lo, hi), Decimal(2))
                if not lo < mid < hi:
                    raise ValueError('exact midpoint cannot split cell')
                stack.extend([(mid, hi, depth+1), (lo, mid, depth+1)])
        accepted.sort(key=lambda item: item['c'][0])
        # Exact endpoint adjacency is an independent coverage invariant of the loop.
        partition = sorted([item['c'] for item in accepted+unresolved], key=lambda x: x[0])
        covered = (bool(partition) and partition[0][0] == left and partition[-1][1] == right
                   and all(a[1] == b[0] for a, b in zip(partition, partition[1:])))
        complete = covered and not unresolved
        results[band] = {'c_domain': [left, right], 'partition_covers_closed_domain': covered,
                         'certified': complete, 'cell_evaluations': evaluations,
                         'accepted_cells': accepted, 'unresolved_cells': unresolved,
                         'amplitude_squared_lower': min((v['amplitude_squared'][0]
                             for v in accepted), default=None),
                         'amplitude_squared_upper': max((v['amplitude_squared'][1]
                             for v in accepted), default=None),
                         'delay_samples_lower': min((v['group_delay_samples'][0]
                             for v in accepted), default=None) if with_delay else None,
                         'delay_samples_upper': max((v['group_delay_samples'][1]
                             for v in accepted), default=None) if with_delay else None}
    certified = all(item['certified'] for item in results.values())
    return {'status': 'certified' if certified else 'not_certified', 'certified': certified,
            'coefficient_model': 'fixed exact dyadic real SOS; no operation-rounding model',
            'coefficients': coefficients, 'decimal_precision': precision,
            'rounding': ['ROUND_FLOOR', 'ROUND_CEILING'],
            'pass_endpoint_proof': {'c_lo': c_lo, 'rational': [ratio.numerator, ratio.denominator],
                                    'positive_and_square_le_half_exact': True},
            'limits': {'max_depth': max_depth, 'max_cells_per_band': max_cells},
            'bands': results}


def decimal(value):
    return Decimal.from_float(float(value))


def polynomial_product(a, b):
    out = [Decimal(0)]*(len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i+j] += x*y
    return out


def expand(sections):
    """80-place product of exact binary64 input coefficients, not rounded roots."""
    with localcontext() as ctx:
        ctx.prec = 80
        b, a = [Decimal(1)], [Decimal(1)]
        for b0, b1, b2, _, a1, a2 in sections:
            numerator, denominator = [decimal(b0), decimal(b1)], [Decimal(1), decimal(a1)]
            if b2 or a2:
                numerator.append(decimal(b2)); denominator.append(decimal(a2))
            b, a = polynomial_product(b, numerator), polynomial_product(a, denominator)
        return b, a


def decimal_sos(sections, inputs):
    with localcontext() as ctx:
        ctx.prec = 80
        states = [[Decimal(0), Decimal(0)] for _ in sections]
        coefficients = [[decimal(v) for v in row] for row in sections]
        output = []
        for original in inputs:
            u = decimal(original)
            for i, (b0, b1, b2, _, a1, a2) in enumerate(coefficients):
                s1, s2 = states[i]
                y = b0*u+s1
                states[i] = [b1*u-a1*y+s2, b2*u-a2*y]
                u = y
            output.append(u)
        return output


def decimal_direct(b, a, inputs):
    with localcontext() as ctx:
        ctx.prec = 80
        state = [Decimal(0)]*(len(a)-1)
        output = []
        for original in inputs:
            u = decimal(original)
            y = b[0]*u+state[0]
            state = [(state[i+1] if i+1 < len(state) else Decimal(0)) +
                     b[i+1]*u-a[i+1]*y for i in range(len(state))]
            output.append(y)
        return output


def binary32(value):
    return struct.unpack('!f', struct.pack('!f', real(value)))[0]


def float_structure(b, a, inputs, cast=binary32):
    """Transposed DFII, each coefficient/product/addition/storage rounded; no FMA."""
    b, a = [cast(v) for v in b], [cast(v) for v in a]
    state = [0.]*(len(a)-1)
    output, peak = [], 0.
    for n, u in enumerate(inputs):
        try:
            u = cast(u)
            y = cast(cast(b[0]*u)+state[0])
            new = [cast(cast((state[i+1] if i+1 < len(state) else 0.) +
                             cast(b[i+1]*u))-cast(a[i+1]*y))
                   for i in range(len(state))]
        except (OverflowError, ValueError):
            return {'status': 'finite_range_exceeded', 'first_sample': n,
                    'output': output, 'peak_state': peak}
        state = new
        peak = max(peak, *(abs(v) for v in state))
        output.append(y)
    return {'status': 'complete', 'output': output, 'peak_state': peak}


def float_sos(sections, inputs, cast=binary32):
    values = list(inputs)
    metrics = []
    for row in sections:
        b, a = row[:3], row[3:]
        if row[2] == row[5] == 0:
            b, a = b[:2], a[:2]
        result = float_structure(b, a, values, cast)
        metrics.append({'status': result['status'], 'peak_state': result['peak_state'],
                        'peak_output': max(map(abs, result['output']), default=0.)})
        if result['status'] != 'complete':
            return {'status': result['status'], 'failed_section': len(metrics)-1,
                    'section_metrics': metrics, 'output': result['output']}
        values = result['output']
    return {'status': 'complete', 'section_metrics': metrics, 'output': values}


def round_even_ratio(n, denominator=16):
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), denominator)
    return sign*(q+(2*r > denominator or (2*r == denominator and q % 2)))


def fixed_order(high_first=True):
    """W8/F4, output and state saturation, exact guarded 24-bit accumulators."""
    stages = [[64, 0, 0, -8, 0], [1, 0, 0, -8, 0]]
    if not high_first:
        stages.reverse()
    states, output, events = [[0, 0], [0, 0]], [], []
    counts, peaks = [0, 0], [0, 0]
    def store(n, index):
        if not -(1 << 23) <= n < (1 << 23):
            raise OverflowError('24-bit accumulator exceeded')
        raw = round_even_ratio(n)
        counts[index] += int(raw < -128 or raw > 127)
        return min(127, max(-128, raw))
    for n in range(20):
        u, intermediate = 32, []
        for i, (b0, b1, b2, a1, a2) in enumerate(stages):
            s1, s2 = states[i]
            y = store(b0*u+16*s1, i)
            states[i] = [store(b1*u-a1*y+16*s2, i), store(b2*u-a2*y, i)]
            peaks[i] = max(peaks[i], abs(y), *map(abs, states[i]))
            intermediate.append(y)
            u = y
        output.append(u)
        events.append({'n': n, 'intermediate_codes': intermediate,
                       'states': [s[:] for s in states]})
    return {'output_codes': output, 'saturations': counts,
            'peak_codes': peaks, 'events': events,
            'W': 8, 'F': 4, 'accumulator_bits': 24, 'input_code': 32}


def discrepancy(result, reference):
    count = len(result['output'])
    return {'status': result['status'], 'samples': count,
            'max_abs_error_v': max((abs(v-float(t)) for v, t in
                                    zip(result['output'], reference)), default=0.),
            'first_sample': result.get('first_sample'),
            'max_scaled_error_v': max((abs(v-float(t))/(1+abs(float(t)))
                for v, t in zip(result['output'], reference)), default=0.)}


def report():
    spec = design()
    x = [.6*math.cos(2*math.pi*1000*n/48000)+.3*math.cos(2*math.pi*10000*n/48000)
         for n in range(12000)]
    b, a = expand(spec['sections'])
    reference = decimal_sos(spec['sections'], x)
    direct = float_structure([float(v) for v in b], [float(v) for v in a], x)
    ascending = float_sos(spec['sections'], x)
    descending = float_sos(spec['sections'][::-1], x)
    wp, ws = 2*math.pi*6000/48000, 2*math.pi*8000/48000
    return {'design': spec, 'direct_coefficients': {'b': b, 'a': a},
            'amplitude_edges': {'ideal_pass': ideal_amplitude(spec, wp),
                                'ideal_stop': ideal_amplitude(spec, ws),
                                'sos_pass': abs(response(spec['sections'], wp)),
                                'sos_stop': abs(response(spec['sections'], ws))},
            'ideal_pole_delay_estimate': ideal_pole_delay_estimate(spec),
            'precision': {'input_length': len(x), 'input_bound_v': .9,
                          'binary32_each_operation_no_fma': True,
                          'reference': '80-place Decimal exact binary64 SOS coefficients',
                          'direct': discrepancy(direct, reference),
                          'ascending': discrepancy(ascending, reference),
                          'descending': discrepancy(descending, reference),
                          'direct_peak': direct['peak_state'],
                          'ascending_peaks': ascending['section_metrics'],
                          'descending_peaks': descending['section_metrics']},
            'fixed_high_first': fixed_order(True), 'fixed_low_first': fixed_order(False),
            'migration_96k': design(fs=96000), 'migration_5k': design(fp=5000),
            'machine_certificates': {
                'binary64_sos': strict_machine_certificate(spec),
                'binary32_sos': strict_machine_certificate(spec,
                    [[binary32(v) for v in row] for row in spec['sections']])},
            'binary32_section_radii': [section_radius([binary32(v) for v in row])
                                       for row in spec['sections']],
            'allpass_r99_dc_samples': 199,
            'finite_range_or_saturation_is_not_white_noise': True}


def json_ready(value):
    if isinstance(value, complex):
        return {'re': value.real, 'im': value.imag}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    destination = parser.parse_args().output.resolve()
    if destination.exists() or any((p/'AGENTS.md').exists()
                                    for p in [destination, *destination.parents]):
        raise ValueError('new external output directory required')
    data = json_ready(report())
    destination.mkdir(parents=True)
    (destination/'results.json').write_text(json.dumps(data, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
