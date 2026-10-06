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

# signal_lab 源码镜像

规范真源是上一级 [signal_lab.py](../signal_lab.py)。本块供阅读与正式code-sync检查；修改须同时更新真源和镜像，运行协议见 [[信号与系统/80-实践/01-采样与系统辨别/README|实验说明]]。

<!-- code-sync: ../signal_lab.py -->
```python
"""Deterministic CPU teaching examples; voltage in V and time in seconds.

Uniform samples are exact-time model values before value quantization.
No ADC, sound device, random clock model or hardware inference is performed.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import platform
import numpy as np


def finite_scalar(value, name):
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value):
        raise ValueError(f'{name} must be a finite real scalar')
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f'{name} must be a finite real scalar') from exc
    if not np.isfinite(result):
        raise ValueError(f'{name} must be finite')
    return result


def real_vector(values, name, *, nonempty=True):
    raw = np.asarray(values)
    if np.iscomplexobj(raw):
        raise ValueError(f'{name} must be real')
    try:
        result = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must be a finite real vector') from exc
    if result.ndim != 1 or (nonempty and result.size == 0) or not np.all(np.isfinite(result)):
        raise ValueError(f'{name} must be a finite one-dimensional vector')
    return result


def sample_times(fs_hz, count, offset_s=0.0):
    fs = finite_scalar(fs_hz, 'fs_hz')
    offset = finite_scalar(offset_s, 'offset_s')
    if fs <= 0:
        raise ValueError('fs_hz must be positive')
    if isinstance(count, (bool, np.bool_)) or not isinstance(count, (int, np.integer)) or count < 1:
        raise ValueError('count must be a positive integer')
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        result = np.arange(int(count), dtype=np.float64) / fs + offset
    if not np.all(np.isfinite(result)):
        raise ValueError('sample times overflowed')
    return result


def tone(times_s, frequency_hz, amplitude_v=1.0, phase_rad=0.0, *, sine=False):
    times = real_vector(times_s, 'times_s')
    f = finite_scalar(frequency_hz, 'frequency_hz')
    a = finite_scalar(amplitude_v, 'amplitude_v')
    phase = finite_scalar(phase_rad, 'phase_rad')
    if not isinstance(sine, (bool, np.bool_)):
        raise ValueError('sine must be boolean')
    with np.errstate(over='raise', invalid='raise'):
        angle = 2 * np.pi * f * times + phase
        return a * (np.sin(angle) if sine else np.cos(angle))


def quantize(values_v, delta_v):
    """Infinite-level nearest grid, half-grid ties toward the greater value.

    Uses floor(v/delta+1/2). There is no clipping or claim about a bit count.
    """
    values = real_vector(values_v, 'values_v')
    delta = finite_scalar(delta_v, 'delta_v')
    if delta <= 0:
        raise ValueError('delta_v must be positive')
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        return delta * np.floor(values / delta + 0.5)


def pulse(times_s, start_s, stop_s, amplitude_v=1.0):
    times = real_vector(times_s, 'times_s')
    start = finite_scalar(start_s, 'start_s')
    stop = finite_scalar(stop_s, 'stop_s')
    a = finite_scalar(amplitude_v, 'amplitude_v')
    if stop <= start:
        raise ValueError('stop_s must exceed start_s')
    return a * ((times >= start) & (times < stop)).astype(float)


def linear_convolution(x, h):
    """Finite linear convolution with support indices starting at zero."""
    return np.convolve(real_vector(x, 'x'), real_vector(h, 'h'), mode='full')


def first_order_step(times_s, tau_s, initial_v=0.0, step_v=1.0):
    """Zero input + zero state, for t>=0 and a fixed initial value y(0)."""
    times = real_vector(times_s, 'times_s')
    tau = finite_scalar(tau_s, 'tau_s')
    initial = finite_scalar(initial_v, 'initial_v')
    step = finite_scalar(step_v, 'step_v')
    if tau <= 0 or np.any(times < 0):
        raise ValueError('positive tau_s and nonnegative times_s required')
    decay = np.exp(-times / tau)
    zi = initial * decay
    zs = step * (-np.expm1(-times / tau))
    return zi, zs, zi + zs


def one_sided_amplitude(values_v, fs_hz):
    """Rectangular-window DFT amplitude in V, not PSD or continuous spectrum.

    Internal positive frequencies are doubled; DC and even-N Nyquist are not.
    """
    values = real_vector(values_v, 'values_v')
    fs = finite_scalar(fs_hz, 'fs_hz')
    if fs <= 0:
        raise ValueError('fs_hz must be positive')
    n = len(values)
    amplitudes = np.abs(np.fft.rfft(values)) / n
    if n % 2 == 0:
        amplitudes[1:-1] *= 2
    else:
        amplitudes[1:] *= 2
    return np.fft.rfftfreq(n, d=1 / fs), amplitudes


def write_csv(path, columns):
    if len({len(v) for v in columns.values()}) != 1:
        raise ValueError('column lengths differ')
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(zip(*columns.values()))


def render(output, dense_t, times, low, high, ny0, ny90, quant_input, quant_output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import font_manager
    from PIL import Image
    import matplotlib.pyplot as plt
    font_manager.findfont('Arial Unicode MS', fallback_to_default=False)
    plt.rcParams.update({'font.family': 'Arial Unicode MS', 'font.size': 13,
                         'svg.fonttype': 'none', 'svg.hashsalt': 'wwl-signals-u2-v1',
                         'axes.unicode_minus': False})

    def save(fig, stem):
        fig.savefig(output / (stem + '.svg'), metadata={'Date': None})
        fig.savefig(output / (stem + '.png'), dpi=160)
        plt.close(fig)
        with Image.open(output / (stem + '.png')) as im:
            width = 425
            im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS).save(
                output / (stem + '-425.png'))

    fig, axes = plt.subplots(2, 1, figsize=(5.1, 7.2), layout='constrained')
    ax = axes[0]
    ax.plot(dense_t, tone(dense_t, 2), label='2 Hz，phase=0', color='#185f9e')
    ax.plot(dense_t, tone(dense_t, 6), '--', label='6 Hz，phase=0', color='#8b4c21')
    visible = times <= 1
    ax.plot(times[visible], low[visible], 'ko', markersize=4, label='共同样本，8 Hz')
    ax.set(xlim=(0, 1), ylim=(-1.2, 1.2), xlabel='时间 t（s）', ylabel='电压（V）', title='连续不同，采样值相同')
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(alpha=.2)
    ax = axes[1]
    f, amp = one_sided_amplitude(low, 8)
    ax.stem(f, amp, basefmt=' ', linefmt='C0-', markerfmt='C0o')
    ax.set(xlabel='DFT频率标签（Hz）', ylabel='单边幅值（V）', title='两份列表：同一个2 Hz峰', xlim=(-.1, 4.1), ylim=(0, 1.2))
    ax.text(.12, .82, 'N=32，矩形窗，4 s\n不是PSD或连续频谱', transform=ax.transAxes, fontsize=11)
    ax.grid(alpha=.2)
    save(fig, 'alias-spectrum')

    fig, axes = plt.subplots(2, 1, figsize=(5.1, 7.2), layout='constrained')
    ax = axes[0]
    ax.plot(dense_t, tone(dense_t, 4, sine=True), label='4 Hz，phase=0', color='#185f9e')
    ax.plot(dense_t, tone(dense_t, 4, phase_rad=np.pi / 2, sine=True), '--', label='4 Hz，phase=π/2', color='#8b4c21')
    ax.plot(times[visible], ny0[visible], 'o', color='#185f9e', markersize=4)
    ax.plot(times[visible], ny90[visible], 's', color='#8b4c21', markersize=4)
    ax.set(xlim=(0, .5), ylim=(-1.2, 1.2), xlabel='时间 t（s）', ylabel='电压（V）', title='Nyquist边界：相位决定可见值')
    ax.legend(fontsize=10, loc='lower left')
    ax.grid(alpha=.2)
    ax = axes[1]
    sel = times <= 1
    ax.plot(times[sel], quant_input[sel], 'o-', label='1 Hz理想样本', color='#185f9e', markersize=4)
    ax.plot(times[sel], quant_output[sel], 's--', label='Δ=0.25 V量化值', color='#8b4c21', markersize=4)
    ax.set(xlabel='采样时刻（s）', ylabel='电压（V）', title='无混叠的输入仍有量化误差', ylim=(-1, 1))
    ax.legend(fontsize=10, loc='lower left')
    ax.grid(alpha=.2)
    save(fig, 'nyquist-quantization')

    fig, axes = plt.subplots(2, 1, figsize=(5.1, 6.7), layout='constrained')
    for ax, right in zip(axes, (True, False)):
        ax.axvspan(-1 if right else -3, 2 if right else -1, color='#dae7f3')
        ax.axvline(-1, color='#333333', linestyle='--')
        ax.axvline(0, color='#777777')
        ax.plot([-1], [0], 'x', color='black', markersize=9)
        ax.set(xlim=(-3, 2), ylim=(-2, 2), xlabel='Re s（s⁻¹）', ylabel='Im s（rad/s）',
               title='X(s)=1/(s+1 s⁻¹)')
        label = '右侧：Re s > −1 s⁻¹\n虚轴在ROC内' if right else '左侧：Re s < −1 s⁻¹\n虚轴不在ROC内'
        ax.text(.05, .85, label, transform=ax.transAxes, fontsize=12)
        ax.grid(alpha=.18)
    save(fig, 'roc')

    fig, ax = plt.subplots(figsize=(5.1, 7.2), layout='constrained')
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    boxes = [(.87, '连续电压 x(t)，V\n先说明允许信号类别'),
             (.66, '模拟抗混叠：改变波形\n带宽与带外衰减有预算'),
             (.45, '取样：t_n=n/f_s 秒\n列表 x[n]，V'),
             (.24, '量化：Δ格点（V）\n教学模型未限幅'),
             (.03, '数字处理：同列表同输出\n不能一般撤销混叠')]
    for y, label in boxes:
        ax.text(.5, y + .035, label, ha='center', va='center', fontsize=13,
                bbox={'boxstyle': 'round,pad=.55', 'facecolor': '#f5f7fa', 'edgecolor': '#333333'})
    for (y1, _), (y2, _) in zip(boxes, boxes[1:]):
        ax.annotate('', xy=(.5, y2 + .115), xytext=(.5, y1 - .045),
                    arrowprops={'arrowstyle': '->', 'color': 'black', 'lw': 1.5})
    ax.set_title('箭头表示数学操作；三种对象别混用', fontsize=13)
    save(fig, 'sampling-flow')


    fig, axes = plt.subplots(4, 1, figsize=(5.1, 9.2), layout='constrained')
    k = np.arange(-2, 4)
    x = np.where(k == 0, 1., np.where(k == 1, 2., 0.))
    h = np.where(k == 0, 1., np.where(k == 1, .5, 0.))
    flip = np.where(k == 0, 1., np.where(k == -1, .5, 0.))
    shifted = np.where(k == 1, 1., np.where(k == 0, .5, 0.))
    for ax, values, label, title in zip(axes, [x, h, flip, shifted],
            ['x[k]（V）', 'h[k]（无量纲）', 'h[−k]（无量纲）', 'h[1−k]（无量纲）'],
            ['输入：两次冲激的权重', '冲激响应：原索引', '翻转：k换为−k', '平移一拍：求y[1]']):
        ax.stem(k, values, linefmt='C0-', markerfmt='C0o', basefmt=' ')
        ax.set(xlabel='求和索引 k（整数）', ylabel=label, title=title, ylim=(-.1, 2.5))
        ax.set_xticks(k)
        ax.grid(alpha=.2)
    axes[-1].text(.32, .8, 'y[1] = 1×0.5 + 2×1\n= 2.5 V', transform=axes[-1].transAxes, fontsize=12)
    save(fig, 'convolution')


def generate(output):
    output = Path(output).resolve()
    source = Path(__file__).parent.resolve()
    if output == source or source in output.parents and output.name != 'assets':
        raise ValueError('use assets or a separate output directory')
    output.mkdir(parents=True, exist_ok=True)
    times = sample_times(8, 32)
    dense = np.linspace(0, 1, 1001)
    low = tone(times, 2)
    high = tone(times, 6)
    ny0 = tone(times, 4, sine=True)
    ny90 = tone(times, 4, phase_rad=np.pi / 2, sine=True)
    qinput = tone(times, 1, .83, .3)
    qoutput = quantize(qinput, .25)
    missing = pulse(times, .03, .08)
    shifted = sample_times(8, 32, .01)
    f, amp = one_sided_amplitude(low, 8)
    ct = np.array([0, .001, .002, .005])
    zi, zs, response = first_order_step(ct, .001, .4)
    write_csv(output / 'samples.csv', {'n': np.arange(32), 't_s': times, 'cos2_v': low,
              'cos6_v': high, 'nyquist_phase0_v': ny0, 'nyquist_phase90_v': ny90,
              'quant_input1hz_v': qinput, 'quant_delta025_v': qoutput,
              'quant_error_v': qoutput - qinput, 'missed_pulse_v': missing})
    write_csv(output / 'waveforms.csv', {'t_s': dense, 'cos2_v': tone(dense, 2),
              'cos6_v': tone(dense, 6), 'nyquist_phase0_v': tone(dense, 4, sine=True),
              'nyquist_phase90_v': tone(dense, 4, phase_rad=np.pi / 2, sine=True)})
    write_csv(output / 'dft-amplitude.csv', {'f_hz': f, 'amplitude_v': amp})
    write_csv(output / 'first-order.csv', {'t_s': ct, 'zero_input_v': zi, 'zero_state_v': zs, 'total_v': response})
    k = np.arange(-2, 4)
    xk = np.where(k == 0, 1., np.where(k == 1, 2., 0.))
    h1k = np.where(k == 1, 1., np.where(k == 0, .5, 0.))
    write_csv(output / 'convolution-terms.csv', {'k': k, 'x_v': xk, 'h1minus_k': h1k, 'product_v': xk * h1k})
    summary = {
        'schema': 'wwl-signals-u2-v1', 'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'machine': platform.machine()},
        'sampling': {'fs_hz': 8, 'count': 32, 'start_s': 0, 'phase2_rad': 0, 'phase6_rad': 0},
        'dft': {'N': 32, 'window': 'rectangular', 'normalization': '|rfft|/N; double internal bins only', 'units': 'V, not PSD'},
        'quantizer': {'delta_v': .25, 'rule': 'floor(v/delta+0.5)', 'half_ties': 'greater grid value', 'clipping': False},
        'alias_max_sample_error_v': float(np.max(np.abs(low - high))),
        'alias_difference_at_1_16_s_v': float(tone([1 / 16], 2)[0] - tone([1 / 16], 6)[0]),
        'nyquist_phase0_max_v': float(np.max(np.abs(ny0))),
        'quant_max_error_v': float(np.max(np.abs(qoutput - qinput))),
        'quant_first_input_v': float(qinput[0]), 'quant_first_output_v': float(qoutput[0]),
        'constant_quant_error_v': float(quantize([.1], .25)[0] - .1),
        'pulse_visible_sample_count': int(np.count_nonzero(missing)),
        'fixed_offset_s': .01,
        'shifted_alias_max_difference_v': float(np.max(np.abs(tone(shifted, 2) - tone(shifted, 6)))),
        'scope': 'deterministic ideal/analytical CPU teaching models; no ADC, instrument, random jitter, human or production evidence'}
    (output / 'results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    render(output, dense, times, low, high, ny0, ny90, qinput, qoutput)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
```
