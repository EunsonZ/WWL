#!/usr/bin/env python3
"""重绘同目录混叠与 STFT 教学 SVG；需要已有 NumPy/Matplotlib 和本地中文字体。

从库根运行：
python3 -B 数学/70-信号处理与多模态数学/assets/generate_sampling_stft_figures.py
不读取音频、访问网络或下载字体；仅覆盖本脚本生成的两个同目录 SVG。
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

OUT = Path(__file__).resolve().parent


def configure_plotting():
    for path in (Path('/System/Library/Fonts/PingFang.ttc'),
                 Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')):
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
            break
    else:
        installed = {font.name for font in font_manager.fontManager.ttflist}
        family = next((name for name in ('Noto Sans CJK SC', 'Noto Sans CJK TC',
                       'Microsoft YaHei', 'SimHei', 'Arial Unicode MS')
                       if name in installed), None)
        if family is None:
            raise RuntimeError('重绘需本机已有中文字体；现有 SVG 阅读不受影响。')
    plt.rcParams.update({'font.family': family, 'font.size': 11,
                         'axes.titlesize': 12, 'axes.labelsize': 11,
                         'legend.fontsize': 9, 'xtick.labelsize': 10,
                         'ytick.labelsize': 10, 'axes.unicode_minus': False,
                         'svg.fonttype': 'path', 'svg.hashsalt': 'wwl-sampling-stft-v2'})


def save_svg(fig, filename, description):
    fig.savefig(OUT / filename, format='svg', bbox_inches='tight', metadata={
        'Title': filename.removesuffix('.svg'), 'Description': description,
        'Creator': 'WWL 本地可复现教学绘图脚本', 'Date': None})
    plt.close(fig)


def generate_aliasing_figure():
    dense = np.linspace(0, 1, 2001)
    samples = np.arange(9) / 8
    sampled = np.sin(2 * np.pi * 6 * samples)
    assert np.allclose(sampled, np.sin(2 * np.pi * -2 * samples), rtol=0, atol=1e-12)
    fig, ax = plt.subplots(figsize=(7, 5), layout='constrained')
    ax.plot(dense, np.sin(2 * np.pi * 6 * dense), lw=1.8, label='连续 6 Hz')
    ax.plot(dense, np.sin(2 * np.pi * -2 * dense), '--', lw=1.8, label='连续 -2 Hz')
    ax.scatter(samples, sampled, c='black', s=34, zorder=5, label=r'共同样本 $t_n=n/8$ s')
    ax.axhline(0, color='0.45', lw=.8)
    fig.suptitle('不同连续信号在 8 Hz 采样点上不可区分', fontsize=12)
    ax.set(xlabel='时间 t（秒）',
           ylabel='幅度（无量纲）', xlim=(0, 1), ylim=(-1.15, 1.15))
    ax.set_xticks(np.arange(9) / 8)
    ax.grid(True, alpha=.22)
    ax.legend(loc='lower center', bbox_to_anchor=(.5, 1.02), ncol=2, framealpha=.92)
    save_svg(fig, 'aliasing-8hz.svg',
             'fs=8 Hz；6 Hz 与 -2 Hz 正弦在 t=n/8 秒样本同值0,-1,0,1,...；连续曲线不同。')


def stft_data():
    fs, duration, length, hop, nfft = 16000, .8, 400, 160, 512
    if nfft < length:
        raise ValueError('本例只使用 NFFT>=L 的零填充。')
    time = np.arange(int(fs * duration)) / fs
    signal = np.where(time < .4, np.sin(2 * np.pi * 440 * time),
                      np.sin(2 * np.pi * 1760 * time))
    starts = np.arange(0, signal.size - length + 1, hop)
    window = np.hanning(length)
    frames = np.stack([signal[start:start + length] * window for start in starts])
    # 实际窗口长度400；rfft在末尾补零到512，不截断窗口。
    magnitude = np.abs(np.fft.rfft(frames, n=nfft, axis=1)).T
    db = 20 * np.log10(np.maximum(magnitude / magnitude.max(), 1e-6))
    centers = (starts + (length - 1) / 2) / fs
    freqs = np.fft.rfftfreq(nfft, d=1 / fs)
    peaks = freqs[np.argmax(magnitude, axis=0)]
    assert len(starts) == 78
    assert np.median(peaks[centers < .35]) == 437.5
    assert np.median(peaks[centers > .45]) == 1750
    return time, signal, centers, freqs, db


def generate_stft_figure():
    time, signal, centers, freqs, db = stft_data()
    fig, (wave, spec) = plt.subplots(2, 1, figsize=(7.2, 8),
                                    height_ratios=(.95, 1.55), layout='constrained')
    zoomed = (time >= .14) & (time <= .20)
    wave.plot(time[zoomed], signal[zoomed], color='.18', lw=.9)
    for start, color, label in [(.15, '#3b82f6', '窗 1：25 ms'),
                                (.16, '#f59e0b', '窗 2：25 ms')]:
        wave.axvspan(start, start + .025, color=color, alpha=.22, label=label)
        wave.axvline(start, color=color, lw=.9)
    wave.annotate('', xy=(.15, 1.03), xytext=(.16, 1.03),
                  arrowprops={'arrowstyle': '<->', 'lw': 1, 'color': '.2'})
    wave.text(.155, 1.07, 'hop = 10 ms', ha='center', va='bottom', fontsize=9)
    wave.set(title='局部波形：0.14–0.20 s（仅 440 Hz 段）', xlabel='局部时间 t（秒）',
             ylabel='波形幅度', xlim=(.14, .20), ylim=(-1.18, 1.35))
    wave.grid(True, alpha=.18)
    wave.legend(loc='lower left', ncol=1, framealpha=.92)
    shown = freqs <= 2500
    # 坐标是bin中心；nearest从中心推导边界，不能把0和2500Hz当外边界。
    mesh = spec.pcolormesh(centers, freqs[shown], db[shown], shading='nearest',
                           vmin=-60, vmax=0, cmap='magma', rasterized=True)
    spec.axvline(.4, color='white', ls=':', lw=1.2)
    for x, y, label in [(.18, 505, '约 440 Hz'), (.62, 1820, '约 1760 Hz')]:
        spec.text(x, y, label, color='white', ha='center', va='bottom')
    spec.set(title='完整 0.8 s 的 STFT 相对幅度\n'
             r'$L=400,\ H=160,\ N_{\rm FFT}=512,\ \Delta f=31.25$ Hz',
             xlabel='完整信号的帧中心时间（秒）', ylabel='频率（Hz）',
             xlim=(0, .8), ylim=(0, 2500))
    fig.colorbar(mesh, ax=spec, pad=.02, shrink=.92).set_label('相对峰值幅度（dB）')
    save_svg(fig, 'stft-two-tone.svg',
             'fs=16000Hz，前0.4秒440Hz，后0.4秒1760Hz；上图放大0.14–0.20秒，'
             '阴影为Hann窗覆盖区间，窗长25ms，hop10ms；下图完整0.8秒，'
             'NFFT512，频率中心网格31.25Hz，幅度dB而非PSD；仅完整窗共78帧。')


def main():
    configure_plotting()
    generate_aliasing_figure()
    generate_stft_figure()
    print('已生成 aliasing-8hz.svg、stft-two-tone.svg')


if __name__ == '__main__':
    main()
