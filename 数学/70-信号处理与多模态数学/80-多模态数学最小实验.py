"""用 Python 标准库验证 Patch、频谱/Mel 汇总、score 与 SDE 缩放。"""

import cmath
import math
import random


def patch_means(image: list[list[float]], patch_size: int) -> list[float]:
    """返回不重叠方形 Patch 的均值，要求高宽都可整除。"""
    if type(patch_size) is not int or patch_size <= 0:
        raise ValueError("patch_size 必须为正整数")
    if not image or not image[0] or any(len(row) != len(image[0]) for row in image):
        raise ValueError("image 必须是非空矩形网格")
    if any(not math.isfinite(value) for row in image for value in row):
        raise ValueError("image 必须只包含有限实数")
    height = len(image)
    width = len(image[0])
    if height % patch_size or width % patch_size:
        raise ValueError("图像高宽必须都能被 patch_size 整除")
    means = []
    for top in range(0, height, patch_size):
        for left in range(0, width, patch_size):
            values = [
                image[row][column]
                for row in range(top, top + patch_size)
                for column in range(left, left + patch_size)
            ]
            means.append(sum(values) / len(values))
    return means


def dft_magnitudes(samples: list[float]) -> list[float]:
    """直接按定义计算 DFT 幅度；只适合本课的小数组。"""
    if not samples or any(not math.isfinite(sample) for sample in samples):
        raise ValueError("samples 必须是非空有限实数序列")
    count = len(samples)
    spectrum = []
    for frequency_bin in range(count):
        value = sum(
            sample * cmath.exp(-2j * math.pi * frequency_bin * index / count)
            for index, sample in enumerate(samples)
        )
        spectrum.append(abs(value))
    return spectrum


def dominant_positive_frequency(samples: list[float], sample_rate: float) -> float:
    """返回实信号正频率半区中幅度最大的频率。"""
    if len(samples) < 2:
        raise ValueError("主频估计至少需要两个样本")
    if not math.isfinite(sample_rate) or sample_rate <= 0.0:
        raise ValueError("sample_rate 必须是正的有限数")
    magnitudes = dft_magnitudes(samples)
    positive_bins = range(1, len(samples) // 2 + 1)
    peak_bin = max(positive_bins, key=magnitudes.__getitem__)
    return peak_bin * sample_rate / len(samples)


def one_sided_power_spectrum(
    frame: list[float], window: list[float]
) -> list[float]:
    """兼容名称：返回原始单边 |DFT|² 特征，非归一化能量或 PSD。

    不按采样率/窗归一化、不加倍正频率；保留原 Mel 特征约定。
    """
    if not frame or len(frame) != len(window):
        raise ValueError("frame 与 window 必须具有相同的非零长度")
    if any(not math.isfinite(value) for value in frame + window):
        raise ValueError("frame 与 window 必须只包含有限实数")
    windowed = [sample * weight for sample, weight in zip(frame, window)]
    magnitudes = dft_magnitudes(windowed)
    return [value * value for value in magnitudes[: len(frame) // 2 + 1]]


def filterbank_energy(power: list[float], weights: list[float]) -> float:
    """兼容名称：对原始平方幅度加权求和，不自动赋予物理能量单位。"""
    if (
        not power
        or len(power) != len(weights)
        or any(not math.isfinite(value) or value < 0.0 for value in power)
        or any(not math.isfinite(weight) or weight < 0.0 for weight in weights)
    ):
        raise ValueError("功率与滤波器权重必须等长、非空且只含非负有限数")
    return sum(value * weight for value, weight in zip(power, weights))


image = [
    [1.0, 1.0, 4.0, 4.0],
    [1.0, 1.0, 4.0, 4.0],
    [2.0, 2.0, 8.0, 8.0],
    [2.0, 2.0, 8.0, 8.0],
]
means = patch_means(image, patch_size=2)
assert means == [1.0, 4.0, 2.0, 8.0]

sample_rate = 8.0
sample_count = 8
samples = [
    math.sin(2 * math.pi * 6.0 * index / sample_rate)
    for index in range(sample_count)
]
aliased_frequency = dominant_positive_frequency(samples, sample_rate)
assert math.isclose(aliased_frequency, 2.0)

power = one_sided_power_spectrum(samples, [1.0] * sample_count)
triangular_weights = [0.0, 0.5, 1.0, 0.5, 0.0]
band_energy = filterbank_energy(power, triangular_weights)
assert power.index(max(power)) == 2
assert math.isclose(band_energy, power[2], rel_tol=1e-12, abs_tol=1e-12)

random.seed(7)
x_zero = 3.0
alpha = 0.8
sigma = 0.6
epsilon = random.gauss(0.0, 1.0)
x_t = alpha * x_zero + sigma * epsilon
score_from_residual = -(x_t - alpha * x_zero) / sigma**2
score_from_noise = -epsilon / sigma
assert math.isclose(score_from_residual, score_from_noise)

step_size = 0.04
coarse_noise_scale = math.sqrt(step_size)
quarter_step_noise_scale = math.sqrt(step_size / 4.0)
assert math.isclose(quarter_step_noise_scale, coarse_noise_scale / 2.0)

print(f"Patch 均值：{means}")
print(f"6 Hz 信号以 8 Hz 采样后的主频：{aliased_frequency:.1f} Hz")
print(f"单帧三角滤波器原始平方幅度特征：{band_energy:.6f}")
print(f"条件 score 两种算法一致：{score_from_residual:.6f}")
print(f"SDE 四分之一步长的噪声尺度：{quarter_step_noise_scale:.3f}")
