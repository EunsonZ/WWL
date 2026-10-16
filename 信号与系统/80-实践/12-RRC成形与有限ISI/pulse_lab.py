#!/usr/bin/env python3
"""Finite RRC chain, real noise covariance, and alternate frequency quadrature.

All transforms use exp(-j*2*pi*f*t), f in Hz. Continuous p(t)=r(t/T)/sqrt(T).
Discrete u[n]=r((n-D)/L)/sqrt(sum(r^2)) has Euclidean energy 1.
No RF, ADC, timing acquisition, or Gaussian-tail Monte Carlo is performed.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import platform
import sys
import time


def need(ok, message):
    if not ok:
        raise ValueError(message)


def real(v):
    return type(v) in (int, float) and math.isfinite(v)


def validate(c):
    keys = {'T_s', 'Eb_J', 'N0_J', 'bits', 'betas', 'spans_symbols',
            'samples_per_symbol', 'timing_offset_T', 'frequency_simpson_panels'}
    need(type(c) is dict and set(c) == keys, 'unexpected/missing input fields')
    for key in ('T_s', 'Eb_J', 'N0_J'):
        need(real(c[key]) and 1e-15 <= c[key] <= 1, key+' outside finite budget')
    need(type(c['bits']) is str and 1 <= len(c['bits']) <= 32
         and set(c['bits']) <= {'0', '1'}, 'bits must contain 1..32 binary digits')
    for key, low, high in [('spans_symbols', 2, 16), ('samples_per_symbol', 4, 32)]:
        seq = c[key]
        need(type(seq) is list and 1 <= len(seq) <= 2, 'one or two '+key)
        need(all(type(v) is int and low <= v <= high and v % 2 == 0 for v in seq)
             and len(set(seq)) == len(seq), key+' must be distinct even integers')
    beta = c['betas']
    need(type(beta) is list and 1 <= len(beta) <= 4, 'one to four betas')
    need(all(real(v) and 0 <= v <= 1 for v in beta)
         and len(set(beta)) == len(beta), 'betas must be distinct within [0,1]')
    offset = c['timing_offset_T']
    need(real(offset) and 0 <= offset <= .5, 'offset outside [0,0.5]')
    need(all(abs(offset*L-round(offset*L)) < 1e-12
             for L in c['samples_per_symbol']), 'offset must lie on each sample grid')
    panels = c['frequency_simpson_panels']
    need(type(panels) is int and 256 <= panels <= 8192 and panels % 2 == 0,
         'Simpson panels must be even within 256..8192')
    return c


def sinc(x):
    return 1.0 if abs(x) < 1e-14 else math.sin(math.pi*x)/(math.pi*x)


def rc(x, beta):
    """Dimensionless ideal g(T*x), including removable singularities."""
    if beta == 0:
        return sinc(x)
    if abs(abs(2*beta*x)-1) < 1e-10:
        return beta/2*math.sin(math.pi/(2*beta))
    return sinc(x)*math.cos(math.pi*beta*x)/(1-(2*beta*x)**2)


def rrc(x, beta):
    """Dimensionless sqrt(T)*p(T*x), positive real spectral square root."""
    if beta == 0:
        return sinc(x)
    if abs(x) < 1e-14:
        return 1+beta*(4/math.pi-1)
    if abs(abs(4*beta*x)-1) < 1e-10:
        return beta/math.sqrt(2)*((1+2/math.pi)*math.sin(math.pi/(4*beta))
                                +(1-2/math.pi)*math.cos(math.pi/(4*beta)))
    return (math.sin(math.pi*(1-beta)*x)+4*beta*x*math.cos(math.pi*(1+beta)*x)) / (
            math.pi*x*(1-(4*beta*x)**2))


def rc_spectrum(nu, beta):
    """R(nu)=G(f)/T, nu=f*T. beta=0 uses half heights at jump endpoints."""
    z = abs(nu)
    if beta == 0:
        return 1.0 if z < .5 else (.5 if z == .5 else 0.0)
    left, right = (1-beta)/2, (1+beta)/2
    if z <= left:
        return 1.0
    if z >= right:
        return 0.0
    return math.cos(math.pi*(z-left)/(2*beta))**2


def simpson(fun, left, right, panels):
    if right == left:
        return 0.0
    dx = (right-left)/panels
    return dx/3*math.fsum(fun(left+i*dx)*(1 if i in (0, panels)
                                             else (4 if i % 2 else 2))
                           for i in range(panels+1))


def spectral_integral(beta, x, power, panels):
    """2*integral_0^B R(nu)^power cos(2*pi*nu*x) dnu.

    This alternate author path splits at spectral corners and does not call
    rc()/rrc(). At beta=0 the integrand uses its interior endpoint limit 1.
    """
    left = (1-beta)/2
    flat = simpson(lambda nu: math.cos(2*math.pi*nu*x), 0, left, panels)
    if beta == 0:
        return 2*flat
    ramp = simpson(lambda nu: math.cos(math.pi*(nu-left)/(2*beta))**(2*power)
                   * math.cos(2*math.pi*nu*x), left, (1+beta)/2, panels)
    return 2*(flat+ramp)


def conv(a, b):
    result = [0.0]*(len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i+j] += x*y
    return result


def taps(beta, span, L):
    D = span*L//2
    r = [rrc((i-D)/L, beta) for i in range(2*D+1)]
    raw_square_sum = math.fsum(x*x for x in r)
    u = [x/math.sqrt(raw_square_sum) for x in r]
    return u, raw_square_sum/L


def weights(h, output_index, input_count):
    return [h[output_index-j] if 0 <= output_index-j < len(h) else 0.0
            for j in range(input_count)]


def noise_ensemble(h, L, offset_samples, variance):
    """Finite ensemble ±sqrt(N*v)*e_j has exact covariance v*I.

    It proves these linear maps' second moments, NOT a Gaussian noise law.
    Every reported steady output has all h taps inside the input noise window.
    """
    q0 = len(h)-1
    indices = [q0, q0+L, q0+offset_samples]
    N = max(indices)+1
    coeff = [weights(h, n, N) for n in indices]
    amplitude = math.sqrt(N*variance)
    outputs = [[sign*amplitude*w[j] for w in coeff]
               for j in range(N) for sign in (-1, 1)]
    means = [math.fsum(row[k] for row in outputs)/len(outputs) for k in range(3)]
    covariance = [[math.fsum(row[i]*row[j] for row in outputs)/len(outputs)
                   - means[i]*means[j] for j in range(3)] for i in range(3)]
    partial = weights(h, 0, N)
    partial_variance = variance*math.fsum(x*x for x in partial)
    return {'noise_input_dimension': N, 'ensemble_size': 2*N,
            'output_indices': indices, 'means_sqrtJ': means,
            'covariance_J': covariance,
            'startup_zero_padded_variance_J': partial_variance,
            'full_support_variance_J': covariance[0][0]}


def one_case(c, beta, span, L):
    u, raw_energy = taps(beta, span, L)
    h = list(reversed(u))
    gd = conv(u, h)
    center = len(u)-1
    symbols = [1 if b == '1' else -1 for b in c['bits']]
    A, T = math.sqrt(c['Eb_J']), c['T_s']
    impulse = [0.0]*((len(symbols)-1)*L+1)
    for k, a in enumerate(symbols):
        impulse[k*L] = A*a
    tx = conv(impulse, u)
    rx = conv(tx, h)
    lag = {str(m): gd[center+m*L] for m in range(-span, span+1)}
    delay = center
    shift = round(c['timing_offset_T']*L)
    exact, shifted = [], []
    max_superposition_gap = 0.0
    for k in range(len(symbols)):
        q = delay+k*L
        reconstructed = A*math.fsum(a*gd[center+(k-j)*L]
                         for j, a in enumerate(symbols) if 0 <= center+(k-j)*L < len(gd))
        max_superposition_gap = max(max_superposition_gap, abs(rx[q]-reconstructed))
        exact.append(rx[q]/A)
        shifted.append(rx[q+shift]/A)
    frame_energy = math.fsum(x*x for x in tx)
    gram_energy = c['Eb_J']*math.fsum(a*b*gd[center+(i-j)*L]
                     for i, a in enumerate(symbols) for j, b in enumerate(symbols)
                     if 0 <= center+(i-j)*L < len(gd))
    noise = noise_ensemble(h, L, shift, c['N0_J']/2)
    energy = math.fsum(x*x for x in u)
    need(abs(energy-1) <= 2e-13, 'tap normalization')
    need(abs(gd[center]-1) <= 2e-13, 'matched center gain')
    need(abs(frame_energy-gram_energy) <= 2e-12*max(frame_energy, c['Eb_J']),
         'finite frame Gram energy')
    need(max_superposition_gap <= 2e-12*A, 'chain versus symbol superposition')
    v = c['N0_J']/2
    need(abs(noise['full_support_variance_J']-v) <= 2e-12*v, 'noise variance')
    need(abs(noise['covariance_J'][0][1]-v*gd[center+L]) <= 2e-12*v,
         'symbol-spaced noise covariance')
    summary = {'beta': beta, 'span_symbols': span, 'sps': L,
        'dt_s': T/L, 'fs_Hz': L/T, 'ideal_bandlimit_Hz': (1+beta)/(2*T),
        'tap_count': len(u), 'single_filter_delay_samples': center//2,
        'pair_delay_samples': delay, 'pair_delay_s': delay*T/L,
        'raw_sampled_pulse_energy': raw_energy, 'normalized_tap_energy': energy,
        'matched_center': gd[center], 'symbol_lags': lag,
        'max_abs_symbol_sidelobe': max(abs(vv) for m, vv in lag.items() if int(m) != 0),
        'sum_abs_symbol_sidelobes': math.fsum(abs(vv) for m, vv in lag.items() if int(m) != 0),
        'full_tx_frame_energy_J': frame_energy, 'frame_energy_via_Gram_J': gram_energy,
        'frame_cross_energy_J': frame_energy-len(symbols)*c['Eb_J'],
        'unitpulse_expected_frame_energy_J_if_orthogonal': len(symbols)*c['Eb_J'],
        'tx_sample_count': len(tx), 'rx_sample_count': len(rx),
        'decision_indices': [delay+k*L for k in range(len(symbols))],
        'noiseless_Y_over_A': exact, 'offset_Y_over_A': shifted,
        'offset_samples': shift,
        'max_abs_noiseless_ISI_over_A': max(abs(y-a) for y,a in zip(exact, symbols)),
        'max_abs_offset_error_over_A': max(abs(y-a) for y,a in zip(shifted, symbols)),
        'wrong_delay_Y_over_A': [rx[k*L]/A for k in range(len(symbols))],
        'max_chain_superposition_gap_sqrtJ': max_superposition_gap,
        'wrong_unnormalized_tap_energy': raw_energy*L,
        'noise': noise}
    return summary, u, gd, tx, rx


def theory_checks(c):
    rows = []
    panels = c['frequency_simpson_panels']
    for beta in c['betas']:
        points = sorted(set([0, .25, .5, 1, 2, 3]
                            + ([] if beta == 0 else [z for z in [1/(4*beta), 1/(2*beta)] if z <= 8])))
        for x in points:
            gq = spectral_integral(beta, x, 1, panels)
            pq = spectral_integral(beta, x, .5, panels)
            rows.append({'beta': beta, 'x_t_over_T': x, 'rc_closed': rc(x,beta),
                'rc_frequency_integral': gq, 'rrc_closed': rrc(x,beta),
                'rrc_frequency_integral': pq})
            need(abs(gq-rc(x,beta)) <= 2e-9, 'RC time/frequency disagreement')
            need(abs(pq-rrc(x,beta)) <= 2e-9, 'RRC time/frequency disagreement')
        need(abs(spectral_integral(beta,0,1,panels)-1) <= 2e-9, 'RRC spectral energy')
        need(abs(spectral_integral(beta,0,2,panels)-(1-beta/4)) <= 2e-9,
             'RC peak is not energy normalization')
    return rows


def write_csv(path, names, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(names)
        writer.writerows(rows)


def run(c, output):
    validate(c)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    theory_rows = theory_checks(c)
    all_cases, pulse_rows, wave_rows, spectrum_rows = [], [], [], []
    for beta in c['betas']:
        for span in c['spans_symbols']:
            for L in c['samples_per_symbol']:
                summary,u,gd,tx,rx = one_case(c,beta,span,L)
                all_cases.append(summary)
                D, A = (len(u)-1)//2, math.sqrt(c['Eb_J'])
                for n, value in enumerate(u):
                    pulse_rows.append([beta,span,L,n,(n-D)/L,value,
                                       value/math.sqrt(c['T_s']/L)])
                # Keep full waveforms only for the higher-resolution grid.
                if L == max(c['samples_per_symbol']):
                    for n, value in enumerate(rx):
                        wave_rows.append([beta,span,L,n,n*c['T_s']/L,(n-(len(u)-1))/L,
                                          tx[n]/math.sqrt(c['T_s']/L) if n<len(tx) else 0,
                                          value/A])
                # Every chosen case answers rolloff/span/grid; this is not a search.
                for j in range(151):
                    nu = j/100
                    re = math.fsum(v*math.cos(2*math.pi*nu*(n-D)/L)
                                   for n,v in enumerate(u))
                    im = math.fsum(-v*math.sin(2*math.pi*nu*(n-D)/L)
                                   for n,v in enumerate(u))
                    spectrum_rows.append([beta,span,L,nu,rc_spectrum(nu,beta),
                                          (re*re+im*im)/L])
    # Alias counterexample: two distinct real tones within beta=.5 ideal band.
    alias_error = max(abs(math.cos(2*math.pi*.4*n)-math.cos(2*math.pi*.6*n))
                      for n in range(16))
    need(alias_error <= 1e-12, 'tone alias example')
    result = {'model': 'finite-unit-energy-RRC-real-matched-chain', 'inputs': c,
        'environment': {'python': sys.version, 'platform': platform.platform(),
                        'executable': sys.executable, 'processes': 1, 'threads': 1},
        'theory_comparisons': theory_rows, 'cases': all_cases,
        'rc_matched_symbol_correlation': [{'beta': b,
            'lag1': spectral_integral(b,1,2,c['frequency_simpson_panels'])/(1-b/4)}
            for b in c['betas']],
        'alias_distinct_tones_max_sample_gap': alias_error,
        'elapsed_s': time.monotonic()-start, 'checks': 'PASS'}
    (output/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    write_csv(output/'pulse.csv', ['beta','span','sps','n','centered_t_over_T','u',
                                  'p_s_inv_sqrt'], pulse_rows)
    write_csv(output/'waveform.csv', ['beta','span','sps','n','physical_t_s','delay_removed_t_over_T',
                                     'tx_sqrtW','matched_Y_over_A'], wave_rows)
    write_csv(output/'spectrum.csv', ['beta','span','sps','nu_fT','ideal_G_over_T',
                                     'finite_P_squared_over_T'], spectrum_rows)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(json.loads(args.inputs.read_text()),args.output)
    except (ValueError, OSError) as e:
        parser.exit(2,str(e)+'\n')
    print(json.dumps({'checks':result['checks'],'cases':len(result['cases']),
                      'elapsed_s':result['elapsed_s'],'output':str(args.output)}))


if __name__ == '__main__':
    main()
