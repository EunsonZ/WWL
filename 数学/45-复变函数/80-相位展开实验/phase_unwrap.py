"""One Python-standard-library demonstration of finite phase representatives.

Rational inputs use pi rad and s; numeric outputs use binary64 rad.
The algorithm chooses increments in [-pi, pi), including a -pi tie convention.
It does not infer a physical prior or recover phase where amplitude is zero.
"""
from __future__ import annotations

import argparse
import cmath
import csv
import html
import json
import math
import sys
from fractions import Fraction
from pathlib import Path


FIELDS = {'phase_unit', 'time_unit', 'initial_phase_pi', 'samples',
          'velocity_A_pi_per_s', 'velocity_B_pi_per_s', 'intervals_s',
          'noise_safe_pi', 'noise_unsafe_pi', 'delay_samples',
          'frequency_step_pi_per_sample', 'amplitude_demo'}


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('rational values must be finite numbers or rational strings')
    try:
        result = Fraction(str(value))
        numeric = float(result)
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise ValueError('invalid or non-finite rational value') from error
    if not math.isfinite(numeric) or (result != 0 and numeric == 0):
        raise ValueError('nonzero rational values must have finite nonzero float representations')
    return result


def load_inputs(input_path):
    card = json.loads(input_path.read_text())
    if not isinstance(card, dict) or set(card) != FIELDS:
        raise ValueError('input fields must match the documented fixed card')
    if card['phase_unit'] != 'pi rad' or card['time_unit'] != 's':
        raise ValueError('units must be phase_unit="pi rad", time_unit="s"')
    n = card['samples']
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 64:
        raise ValueError('samples must be an integer from 2 to 64')
    for name in ['initial_phase_pi', 'velocity_A_pi_per_s', 'velocity_B_pi_per_s',
                 'frequency_step_pi_per_sample']:
        card[name] = rational(card[name])
    if card['frequency_step_pi_per_sample'] <= 0:
        raise ValueError('frequency step must be positive')
    if not isinstance(card['intervals_s'], list) or not 1 <= len(card['intervals_s']) <= 8:
        raise ValueError('intervals_s must contain from 1 to 8 positive intervals')
    card['intervals_s'] = [rational(v) for v in card['intervals_s']]
    if any(v <= 0 for v in card['intervals_s']) or len(set(card['intervals_s'])) != len(card['intervals_s']):
        raise ValueError('intervals must be positive and distinct')
    for name in ['noise_safe_pi', 'noise_unsafe_pi', 'amplitude_demo']:
        if not isinstance(card[name], list) or len(card[name]) != n:
            raise ValueError(f'{name} must have samples entries')
        card[name] = [rational(v) for v in card[name]]
    if any(v < 0 for v in card['amplitude_demo']):
        raise ValueError('amplitudes must be nonnegative')
    delays = card['delay_samples']
    if (not isinstance(delays, list) or not 1 <= len(delays) <= 8
            or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in delays)
            or len(set(delays)) != len(delays)):
        raise ValueError('delays must be 1 to 8 distinct nonnegative integers')
    return card


def radians(value):
    result = float(value)*math.pi
    if not math.isfinite(result):
        raise ValueError('generated angle exceeds the finite numeric domain')
    return result


def representative(phase):
    return (phase+math.pi) % (2*math.pi)-math.pi


def unwrap(principals, initial_lift):
    """Choose short increments; the exact half-turn convention chooses -pi.

    Existence/uniqueness of true phases requires the separate strict <pi prior.
    Callers supply the compatible initial lift, including its integer layer.
    """
    if not principals or not all(math.isfinite(v) for v in [*principals, initial_lift]):
        raise ValueError('unwrap needs finite nonempty representatives and initial lift')
    if abs(representative(initial_lift-principals[0])) > 1e-9:
        raise ValueError('initial lift must agree with the first circle observation')
    result = [initial_lift]
    for previous, current in zip(principals, principals[1:]):
        result.append(result[-1]+representative(current-previous))
    return result


def phases(card, velocity, interval):
    return [radians(card['initial_phase_pi']+velocity*interval*k) for k in range(card['samples'])]


def circle_and_principal(phases_rad):
    circle = [cmath.exp(1j*v) for v in phases_rad]
    return circle, [representative(cmath.phase(v)) for v in circle]


def demonstrate(input_path: Path, output_dir: Path):
    card = load_inputs(input_path)
    n = card['samples']; dt = card['intervals_s'][0]
    t = [float(k*dt) for k in range(n)]
    if (not all(math.isfinite(v) for v in t)
            or any(right <= left for left,right in zip(t,t[1:]))):
        raise ValueError('generated sample times must be finite and strictly increasing')
    a = phases(card, card['velocity_A_pi_per_s'], dt)
    b = phases(card, card['velocity_B_pi_per_s'], dt)
    z, alpha = circle_and_principal(a); zb, _ = circle_and_principal(b)
    u = unwrap(alpha, radians(card['initial_phase_pi']))
    raw = [alpha[k]-alpha[k-1] for k in range(1,n)]
    chosen = [u[k]-u[k-1] for k in range(1,n)]
    correction = [d-r for d,r in zip(chosen,raw)]
    layers = [round((v-p)/(2*math.pi)) for v,p in zip(u,alpha)]
    noise_runs = {}
    for name in ['safe', 'unsafe']:
        noise = [radians(v) for v in card[f'noise_{name}_pi']]
        noisy_true = [radians(card['initial_phase_pi']+card['velocity_A_pi_per_s']*dt*k+eta)
                      for k,eta in enumerate(card[f'noise_{name}_pi'])]
        _, observed = circle_and_principal(noisy_true)
        recovered = unwrap(observed, noisy_true[0])
        epsilon = max(abs(v) for v in noise)
        bound = radians(abs(card['velocity_A_pi_per_s']*dt)+2*max(abs(v) for v in card[f'noise_{name}_pi']))
        noise_runs[name] = {'epsilon_rad': epsilon, 'worst_increment_bound_rad': bound,
                            'strict_short_increment_guarantee': bound < math.pi,
                            'true_noisy_phase_rad': noisy_true, 'observed_representatives_rad': observed,
                            'unwrapped_rad': recovered,
                            'error_vs_noisy_truth_rad': [v-w for v,w in zip(recovered,noisy_true)],
                            'error_vs_clean_truth_rad': [v-w for v,w in zip(recovered,a)]}
    interval_runs = {}
    for interval in card['intervals_s']:
        truth = phases(card,card['velocity_A_pi_per_s'],interval)
        other = phases(card,card['velocity_B_pi_per_s'],interval)
        zz, pp = circle_and_principal(truth); zzb, _ = circle_and_principal(other)
        times = [float(k*interval) for k in range(n)]
        if (not all(math.isfinite(v) for v in times)
                or any(right <= left for left,right in zip(times,times[1:]))):
            raise ValueError('generated sample times must be finite and strictly increasing')
        interval_runs[str(interval)] = {'time_s': times, 'true_A_rad': truth,
            'unwrapped_A_rad': unwrap(pp,radians(card['initial_phase_pi'])),
            'max_A_B_complex_sample_difference': max(abs(v-w) for v,w in zip(zz,zzb))}
    omega = [radians(k*card['frequency_step_pi_per_sample']) for k in range(n)]
    delay_runs = {}
    for delay in card['delay_samples']:
        phi = [radians(-delay*k*card['frequency_step_pi_per_sample']) for k in range(n)]
        h, pp = circle_and_principal(phi)
        delay_runs[str(delay)] = {'phase_rad': phi, 'real_H': [v.real for v in h],
            'imag_H': [v.imag for v in h], 'unwrapped_rad': unwrap(pp,0.0),
            'analytic_delay_input_samples': delay}
    valid_phase = [p if amplitude>0 else None for p,amplitude in zip(alpha,card['amplitude_demo'])]
    summary = {'python_version': sys.version.split()[0], 'scope': 'finite synthetic teaching model',
        'implementation': 'one Python standard library short-increment demonstration',
        'initial_lift_rad': radians(card['initial_phase_pi']),
        'complex_A_B_max_difference_at_main_sample_times': max(abs(v-w) for v,w in zip(z,zb)),
        'A_reconstruction_max_error_rad': max(abs(v-w) for v,w in zip(u,a)),
        'B_reconstruction_error_rad': [v-w for v,w in zip(u,b)],
        'half_turn_plus_unwrap_rad': unwrap([0.0,math.pi],0.0),
        'half_turn_minus_unwrap_rad': unwrap([0.0,-math.pi],0.0),
        'half_turn_convention': 'choose -pi; both true histories remain possible',
        'noise_runs': noise_runs, 'interval_runs': interval_runs,
        'delay_frequency_rad_per_input_sample': omega, 'delay_runs': delay_runs,
        'zero_amplitude_valid_phase_rad': valid_phase,
        'zero_amplitude_library_numeric_angle_rad': cmath.phase(0j),
        'near_zero_example': [{'real_amplitude': r, 'imag_perturbation': 1e-6,
            'angle_rad': cmath.phase(r+1e-6j)} for r in [1.0,1e-3,1e-6,1e-9]],
        'fixed_closed_loop_example': {'interval_s': [0,4], 'windings_constant_and_one_turn_per_s': [0,4]}}
    # All input checks and finite computations finish before creating outputs.
    output_dir.mkdir(parents=True,exist_ok=True)
    with (output_dir/'samples.csv').open('w',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['k','time_s','real_z','imag_z','real_z_B','imag_z_B','principal_rad',
            'raw_delta_rad','step_compensation_rad','chosen_delta_rad','integer_layer',
            'unwrapped_rad','true_A_rad','true_B_rad'])
        for k in range(n):
            writer.writerow([k,t[k],z[k].real,z[k].imag,zb[k].real,zb[k].imag,alpha[k],
                raw[k-1] if k else '',correction[k-1] if k else '',chosen[k-1] if k else '',
                layers[k],u[k],a[k],b[k]])
    (output_dir/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    make_svg(output_dir/'samples.csv',output_dir/'phase-histories.svg',card)
    print(json.dumps({'python':summary['python_version'],'A_error_rad':summary['A_reconstruction_max_error_rad'],
        'same_sample_residual':summary['complex_A_B_max_difference_at_main_sample_times'],
        'safe_noise_lift_error_rad':max(abs(v) for v in noise_runs['safe']['error_vs_noisy_truth_rad']),
        'unsafe_noise_lift_error_rad':noise_runs['unsafe']['error_vs_noisy_truth_rad'],
        'output_dir':str(output_dir)},indent=2))


def make_svg(csv_path: Path, output_path: Path, card):
    with csv_path.open(newline='') as handle:
        rows=list(csv.DictReader(handle))
    times=[float(r['time_s']) for r in rows]; end=times[-1]
    angles=[float(r[field])/math.pi for r in rows for field in ['true_A_rad','true_B_rad','principal_rad']]
    low,high=min(angles),max(angles); pad=max((high-low)*.1,.2); low-=pad; high+=pad
    def x(t): return 95+float(t)/end*640
    def y(v): return 490-(float(v)-low)/(high-low)*260
    def poly(field): return ' '.join(f'{x(r["time_s"]):.3f},{y(float(r[field])/math.pi):.3f}' for r in rows)
    same=(card['velocity_A_pi_per_s']-card['velocity_B_pi_per_s'])*card['intervals_s'][0]/2
    equality='same circle samples' if same.denominator==1 else 'different circle samples'
    desc=(f"A speed {float(card['velocity_A_pi_per_s']):.6g} pi/s and B speed "
          f"{float(card['velocity_B_pi_per_s']):.6g} pi/s, initial lift {float(card['initial_phase_pi']):.6g} pi rad. "
          f"Sample times 0 to {end:.6g} s: {equality}. Lines are specified models, not measured interpolation. "
          "Black dots are A principal representatives; lower dots show A real and imaginary observations.")
    svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 735" role="img" aria-labelledby="title desc">',
        '<title id="title">Circle observations and candidate phase histories</title>',
        f'<desc id="desc">{html.escape(desc)}</desc>', '<rect width="840" height="735" fill="white"/>',
        '<g font-family="Arial, sans-serif" font-size="15" fill="#17212b">',
        '<text x="60" y="35" font-size="22">Circle observations and candidate histories</text>',
        '<text x="60" y="62">Phase / pi rad; candidate lines are models, dots are A samples</text>',
        f'<text x="420" y="103" fill="#005c97">A: {float(card["velocity_A_pi_per_s"]):+.6g} pi / s (solid)</text>',
        f'<text x="420" y="130" fill="#a33d00">B: {float(card["velocity_B_pi_per_s"]):+.6g} pi / s (dashed)</text>',
        f'<text x="420" y="157">initial lift: {float(card["initial_phase_pi"]):.6g} pi rad</text>',
        f'<text x="420" y="184">{equality}</text>']
    for k in range(6):
        tick=low+(high-low)*k/5; yy=y(tick)
        svg += [f'<path d="M95 {yy:.3f}H735" stroke="#ddd"/>',f'<text x="25" y="{yy+5:.3f}">{tick:.4g}</text>']
    # Six actual time ticks keep variants with many observations legible.
    for k in range(6):
        tick=end*(k/5); xx=x(tick)
        svg += [f'<path d="M{xx:.3f} 230V490" stroke="#ddd"/>',f'<text x="{xx-7:.3f}" y="513">{tick:.4g}</text>',
                f'<text x="{xx-7:.3f}" y="698">{tick:.4g}</text>']
    svg += [f'<polyline points="{poly("true_A_rad")}" fill="none" stroke="#005c97" stroke-width="3"/>',
            f'<polyline points="{poly("true_B_rad")}" fill="none" stroke="#a33d00" stroke-width="3" stroke-dasharray="9 5"/>']
    for r in rows:
        svg += [f'<circle cx="{x(r["time_s"]):.3f}" cy="{y(float(r["principal_rad"])/math.pi):.3f}" r="5" fill="#222"/>']
    svg += ['<text x="365" y="542">time / s</text>',
            '<text x="60" y="576">A samples: real (blue circle), imaginary (orange square)</text>']
    for tick in [-1,0,1]:
        yy=638-35*tick
        svg += [f'<path d="M95 {yy}H735" stroke="#ddd"/>',f'<text x="55" y="{yy+5}">{tick}</text>']
    for r in rows:
        xx=x(r['time_s']); ry=638-35*float(r['real_z']); iy=638-35*float(r['imag_z'])
        svg += [f'<circle cx="{xx:.3f}" cy="{ry:.3f}" r="5" fill="#005c97"/>',
                f'<rect x="{xx-4:.3f}" y="{iy-4:.3f}" width="8" height="8" fill="#a33d00"/>']
    svg+=['<text x="365" y="725">time / s</text>','</g></svg>']
    output_path.write_text('\n'.join(svg)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output',type=Path,required=True,help='Output CSV/JSON/SVG directory')
    args=parser.parse_args()
    try:
        demonstrate(args.input,args.output)
    except (ValueError,OverflowError,KeyError) as error:
        parser.error(str(error))
