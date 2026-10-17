"""Finite array fixtures: exact covariance, same held-out data, and model failure.
Run: python -B array_beamforming.py --output results
Only NumPy/Matplotlib; no network, random seed search, or hardware claims.
"""
from pathlib import Path
import argparse
import json
import os
import time

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/wwl-array-mpl')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def steering(q, count=8, spacing=0.5):
    """q=sin(theta); spacing in wavelengths; columns for an array of q."""
    return np.exp(2j * np.pi * spacing * np.arange(count)[:, None]
                  * np.atleast_1d(q)[None, :])


def frame(rows, samples):
    # Nonzero distinct DFT modes: zero row means and FF^H/T=I.
    if not 0 < rows < samples:
        raise ValueError('Require 0 < rows < samples')
    k = np.arange(1, rows + 1)[:, None]
    n = np.arange(samples)[None, :]
    return np.exp(2j * np.pi * k * n / samples)


def mvdr(matrix, a):
    z = np.linalg.solve(matrix, a)  # No explicit matrix inverse.
    den = np.vdot(a, z)
    if abs(den.imag) > 1e-10 or den.real <= 0:
        raise ValueError('Expected a positive Hermitian quadratic form')
    return z / den.real


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'results')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    m, tr_len, test_len = 8, 128, 256
    fs, c, carrier = 32.0, 343.0, 3430.0
    a = steering(0.0)[:, 0]
    ai = steering(0.3)[:, 0]
    power_i, delta = 100.0, 10.0
    r = np.eye(m) + power_i * np.outer(ai, ai.conj())
    train_modes = frame(m + 1, tr_len)
    train = 10 * ai[:, None] * train_modes[0] + train_modes[1:]
    rhat = train @ train.conj().T / tr_len
    test_modes = frame(m + 2, test_len)
    truth = test_modes[0]
    test_noise = 10 * ai[:, None] * test_modes[1] + test_modes[2:]
    test = a[:, None] * truth + test_noise
    weights = {
        'fixed': a / m,
        'mvdr': mvdr(rhat, a),
        'loaded': mvdr(rhat + delta * np.eye(m), a),
    }
    inner = np.vdot(ai, a)
    expected_fixed = 1 / m + power_i * abs(inner) ** 2 / m ** 2
    expected_mvdr = 1 / (m - power_i * abs(inner) ** 2 / (1 + power_i * m))
    # Independent rank-one expression; not obtained by calling mvdr.
    inv_a = a - power_i * ai * inner / (1 + power_i * m)
    explicit_w = inv_a / (m - power_i * abs(inner) ** 2 / (1 + power_i * m))
    outputs = {name: w.conj() @ test for name, w in weights.items()}
    metrics = {}
    for name, w in weights.items():
        mse = float(np.mean(abs(outputs[name] - truth) ** 2))
        model = float(np.vdot(w, r @ w).real)
        constraint = float(abs(np.vdot(w, a) - 1))
        assert constraint < 1e-11
        assert abs(mse - model) < 1e-9
        metrics[name] = dict(mse_pa2=mse, model_noise_pa2=model,
                             distortionless_residual=constraint,
                             weight_norm=float(np.linalg.norm(w)),
                             interference_gain=float(abs(np.vdot(w, ai))))
    assert abs(metrics['fixed']['mse_pa2'] - expected_fixed) < 1e-9
    assert abs(metrics['mvdr']['mse_pa2'] - expected_mvdr) < 1e-9
    assert np.max(abs(weights['mvdr'] - explicit_w)) < 1e-11
    covariance_error = float(np.max(abs(rhat - r)))
    assert covariance_error < 1e-10
    alias = float(np.max(abs(steering(0.3, spacing=1) - steering(-0.7, spacing=1))))
    endpoints = float(np.max(abs(steering(1) - steering(-1))))
    assert max(alias, endpoints) < 1e-12
    singular_r = np.diag([1., 0.])
    sa = np.ones(2)
    good, naive = np.array([0., 1.]), np.array([1., 0.])
    singular = dict(optimal_cost=float(good @ singular_r @ good),
                    naive_pseudoinverse_cost=float(naive @ singular_r @ naive),
                    constraints=[float(good @ sa), float(naive @ sa)])
    assert singular['optimal_cost'] == 0 and singular['naive_pseudoinverse_cost'] == 1
    # Rank shortage on 4 columns of the same training record, no arbitrary rcond claim.
    short = train[:, :4]
    short_rank = int(np.linalg.matrix_rank(short))
    assert short_rank <= 4
    b = steering(.08)[:, 0]
    powers = np.logspace(-2, 4, 81)
    mismatch = {name: [] for name in weights}
    mismatch_formula_errors = []
    for p in powers:
        rx = np.eye(m) + p * np.outer(b, b.conj())
        ws = {'fixed': a / m, 'mvdr': mvdr(rx, a),
              'loaded': mvdr(rx + delta * np.eye(m), a)}
        cross = np.vdot(a, b)
        exact_gain = cross / ((1 + p * m) * (m - p * abs(cross)**2 / (1 + p * m)))
        mismatch_formula_errors.append(abs(np.vdot(ws['mvdr'], b) - exact_gain))
        for name, w in ws.items():
            mismatch[name].append(float(abs(np.vdot(w, b))))
    assert max(mismatch_formula_errors) < 1e-9
    np.savez(args.output / 'same_data.npz', train=train, test=test, truth=truth,
             rhat=rhat, q_grid=np.sin(np.deg2rad(np.linspace(-90, 90, 721))), powers=powers,
             **{f'w_{k}': v for k, v in weights.items()},
             **{f'y_{k}': v for k, v in outputs.items()})
    fig, axs = plt.subplots(2, 2, figsize=(11.5, 7.5), constrained_layout=True)
    theta = np.linspace(-90, 90, 721)
    manifold = steering(np.sin(np.deg2rad(theta)))
    styles = {'fixed': '-', 'mvdr': '--', 'loaded': ':'}
    for name, w in weights.items():
        response = abs(w.conj() @ manifold)
        axs[0, 0].plot(theta, 20*np.log10(np.maximum(response, 1e-3)),
                       styles[name], label=name)
    axs[0, 0].axvline(np.rad2deg(np.arcsin(.3)), color='k', lw=.8, label='interferer')
    axs[0, 0].set(title='Matched look q=0; d/lambda=0.5', xlabel='theta from broadside (degree)',
                  ylabel='Amplitude response (dB)', ylim=(-60, 5))
    aliased_manifold = steering(np.sin(np.deg2rad(theta)), spacing=1)
    alias_w = steering(.3, spacing=1)[:, 0] / m
    axs[0, 1].plot(theta, 20*np.log10(np.maximum(abs(alias_w.conj() @ aliased_manifold), 1e-3)))
    for q in [.3, -.7]:
        axs[0, 1].plot(np.rad2deg(np.arcsin(q)), 0, 'ko')
    axs[0, 1].set(title='Spatial alias: q=0.3 and -0.7; d/lambda=1',
                  xlabel='theta from broadside (degree)', ylabel='Amplitude response (dB)', ylim=(-60, 5))
    n = np.arange(96)
    axs[1, 0].plot(n/fs, truth[:96].real, 'k-', lw=2, label='target')
    for name, y in outputs.items():
        axs[1, 0].plot(n/fs, y[:96].real, styles[name], label=name, alpha=.8)
    axs[1, 0].set(title='Same held-out record, real part', xlabel='Time (s)', ylabel='Envelope (Pa)')
    for name, gain in mismatch.items():
        axs[1, 1].loglog(powers, gain, styles[name], label=name)
    axs[1, 1].set(title='Wrong look: assumed q=0, true q=0.08',
                  xlabel='Target / per-channel noise power', ylabel='True target amplitude gain')
    for ax in axs.flat:
        ax.grid(alpha=.25)
    for index in [(0, 0), (1, 0), (1, 1)]:
        axs[index].legend(fontsize=8)
    fig.savefig(args.output / 'array_comparison.png', dpi=150)
    fig.savefig(args.output / 'array_comparison.svg', metadata={
        'Title': 'Array spatial aliasing and beamforming on fixed synthetic data',
        'Description': 'Four panels compare matched weights, exact spatial alias, same held-out record, and a separate steering mismatch condition.'})
    svg_path = args.output / 'array_comparison.svg'
    svg = svg_path.read_text()
    head_end = svg.index('>', svg.index('<svg ')) + 1
    svg_path.write_text(svg[:head_end] + '\n<title>Array spatial sampling and beamforming</title>'
                       + '<desc>Matched responses, exact alias, the same finite test record, and a separate steering mismatch experiment.</desc>'
                       + svg[head_end:])
    plt.close(fig)
    report = dict(status='PASS', input=dict(M=m, c_m_per_s=c, carrier_hz=carrier,
        d_m=.05, baseband_fs_hz=fs, declared_baseband_total_width_hz=5.,
        train_samples=tr_len, test_samples=test_len, look_q=0., interference_q=.3,
        interference_power_pa2=power_i, channel_noise_power_pa2=1., delta_pa2=delta,
        fixture='orthogonal deterministic complex exponentials, not random population evidence'),
        versions=dict(numpy=np.__version__, matplotlib=matplotlib.__version__),
        threads={k: os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']},
        covariance_max_abs_error=covariance_error, metrics=metrics,
        independent_expected=dict(fixed_noise_pa2=float(expected_fixed), mvdr_noise_pa2=float(expected_mvdr)),
        rank_one_weight_max_error=float(np.max(abs(weights['mvdr']-explicit_w))),
        alias_residual=alias, halfwave_endpoint_residual=endpoints,
        singular_example=singular, four_snapshot_rank=short_rank,
        mismatch=dict(q_true=.08, formula_max_error=float(max(mismatch_formula_errors)),
                      last_power=float(powers[-1]), last_gain={k:v[-1] for k,v in mismatch.items()}),
        elapsed_seconds=time.monotonic()-started,
        unverified=['real sensor calibration','real propagation/multipath','random covariance estimation consistency',
                    'Obsidian display','human transfer learning'])
    (args.output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
