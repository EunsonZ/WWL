---
type: experiment
domain: mathematics
stage: 1
prerequisites:
  - "[[数学/70-信号处理与多模态数学/03-STFT窗覆盖与可逆重建]]"
tags:
  - mathematics/signal-processing
---

# STFT 重建与边界实验

这个标准库实验使用完整复数 DFT，不调用 FFT 或音频库。它把“每个加窗帧的逆变换”与“原记录逐点恢复”分开：后者返回恢复值和实际有限窗平方分母；分母不大于阈值的位置返回 `None`，不会用零冒充未知样本。

## 运行与对象

从库根运行，不写文件：

```bash
python3 -B 数学/70-信号处理与多模态数学/81-STFT重建与边界实验.py
```

输入为八样本 `[1,2,3,4,5,6,7,8]`，周期 Hann 窗 `[0,0.5,1,0.5]`，DFT 点数 8。`stft` 保存帧起点集合、零延拓约定和完整复数系数；`reconstruct` 使用同一实窗合成与平方分母，只有同一未修改记录的谱才能由该公式保证恢复。输入窗口不做幅度归一化。与既有 [[数学/70-信号处理与多模态数学/80-多模态数学最小实验|80 实验]] 的原始平方幅度 Mel 特征属于不同目的，旧 API 保持不变。

## 独立预期与恢复区间

- 四点索引 1 脉冲的闭式谱为 `[1,-i,-1,i]`，不由待测正变换生成预期值；四个常数谱的逆为索引 0 脉冲。
- 完整帧起点 `0,2,4`，手算分母 `[0,1/4,1,1/2,1,1/2,1,1/4]`；只恢复索引 1..7。
- 边界起点 `-2,0,2,4,6`，手算分母 `[1,1/2,1,1/2,1,1/2,1,1/2]`；恢复原始索引 0..7，不把延拓区算进原记录。
- 删中帧后未知点为 0 与 4；保留覆盖点仍能恢复。
- 丢相位后覆盖虽正，重建明显偏离原记录。它验证一个失败例，不证明所有幅度谱的非唯一结构。
- 空向量、非有限输入、过短 FFT、重复起点、复窗、非法记录长度、负阈值、不同谱长度被拒绝。

短序列验证容差为 $10^{-12}$；这是本实验浮点尺度，不能替代真实录音、长窗或小分母的误差分析。算法直接求和 $O(N^2)$，适合教学与短片段，不是长录音高效前端。全部恢复值保持复数，舍入产生的微小虚部计入绝对误差。

## 源码镜像

<!-- code-sync: ./81-STFT重建与边界实验.py -->
```python
"""Finite complex STFT reconstruction lab; standard library, no import side effects."""
import cmath
import json
import math


def finite(values):
    return all(math.isfinite(complex(v).real) and math.isfinite(complex(v).imag) for v in values)


def transform(values, inverse=False):
    """Unscaled DFT; inverse divides by N. Full complex coefficients only."""
    values = [complex(v) for v in values]
    if not values or not finite(values):
        raise ValueError("nonempty finite vector required")
    n = len(values)
    sign = 1 if inverse else -1
    scale = n if inverse else 1
    return [sum(v * cmath.exp(sign * 2j * math.pi * k * r / n)
                for r, v in enumerate(values)) / scale for k in range(n)]


def stft(samples, window, starts, nfft):
    """Zero extension outside record; zero pad each frame at its right to nfft."""
    samples = [complex(v) for v in samples]
    window = list(window)
    starts = list(starts)
    if not samples or not window or not finite(samples) or not finite(window):
        raise ValueError("nonempty finite record/window required")
    if any(complex(w).imag for w in window):
        raise ValueError("real window required")
    if isinstance(nfft, bool) or not isinstance(nfft, int) or nfft < len(window):
        raise ValueError("integer nfft >= window length required")
    if not starts or any(isinstance(s, bool) or not isinstance(s, int) for s in starts):
        raise ValueError("nonempty integer starts required")
    if len(set(starts)) != len(starts):
        raise ValueError("duplicate starts rejected")
    spectra = []
    for start in starts:
        frame = [(samples[start+r] if 0 <= start+r < len(samples) else 0) * w
                 for r, w in enumerate(window)]
        spectra.append(transform(frame + [0] * (nfft-len(window))))
    return spectra


def reconstruct(spectra, window, starts, length, tolerance=1e-12):
    """Return (samples or None at uncovered points, actual finite denominator)."""
    window, starts, spectra = list(window), list(starts), list(spectra)
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        raise ValueError("positive record length required")
    if not window or not finite(window) or any(complex(w).imag for w in window):
        raise ValueError("nonempty finite real window required")
    if not starts or len(starts) != len(spectra) or len(set(starts)) != len(starts):
        raise ValueError("matching distinct starts and spectra required")
    if any(isinstance(s, bool) or not isinstance(s, int) for s in starts):
        raise ValueError("integer starts required")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("finite nonnegative tolerance required")
    nfft = len(spectra[0])
    if nfft < len(window) or any(len(frame) != nfft for frame in spectra):
        raise ValueError("consistent full spectra >= window length required")
    numerator, denominator = [0j] * length, [0.0] * length
    for start, spectrum in zip(starts, spectra):
        frame = transform(spectrum, inverse=True)
        for r, w in enumerate(window):
            index = start+r
            if 0 <= index < length:
                w = float(complex(w).real)
                numerator[index] += frame[r] * w
                denominator[index] += w*w
    return ([a/d if d > tolerance else None for a, d in zip(numerator, denominator)],
            denominator)


def error(restored, original):
    return max((abs(a-b) for a, b in zip(restored, original) if a is not None), default=0.0)


def run_checks():
    # Independent closed form DFT of the index-one impulse: exp(-2 pi i k / 4).
    impulse = [0, 1, 0, 0]
    assert max(abs(a-b) for a, b in zip(transform(impulse), [1, -1j, -1, 1j])) < 1e-14
    # Independent inverse of the constant spectrum is the index-zero impulse.
    assert max(abs(a-b) for a, b in zip(transform([1]*4, True), [1, 0, 0, 0])) < 1e-14
    x, w = list(range(1, 9)), [0, 0.5, 1, 0.5]  # periodic Hann L=4
    starts = [0, 2, 4]
    spectra = stft(x, w, starts, 8)
    result, d = reconstruct(spectra, w, starts, 8)
    # Hand-computed oracle independent of the reconstruction function.
    assert d == [0, 0.25, 1, 0.5, 1, 0.5, 1, 0.25]
    assert result[0] is None and error(result, x) < 1e-12
    # Negative start is a real boundary policy; restore all original indices 0..7.
    padded_starts = [-2, 0, 2, 4, 6]
    full, full_d = reconstruct(stft(x, w, padded_starts, 8), w, padded_starts, 8)
    assert full_d == [1, 0.5, 1, 0.5, 1, 0.5, 1, 0.5]
    assert all(v is not None for v in full) and error(full, x) < 1e-12
    # Dropping middle frame: index 4 loses its only nonzero weight.
    dropped, dropped_d = reconstruct([spectra[0], spectra[2]], w, [0, 4], 8)
    assert dropped_d[4] == 0 and dropped[4] is None
    # Dropping phase fails even when coverage remains positive.
    phase_lost = [[abs(z) for z in frame] for frame in stft(x, w, padded_starts, 8)]
    phase_result, _ = reconstruct(phase_lost, w, padded_starts, 8)
    phase_error = error(phase_result, x)
    assert phase_error > 1
    invalid_checks = 0
    for call in (lambda: transform([]), lambda: transform([float('nan')]),
                 lambda: stft(x, w, [0], 3), lambda: stft(x, w, [0, 0], 8),
                 lambda: stft(x, [1j], [0], 8),
                 lambda: reconstruct(spectra, w, starts, 0),
                 lambda: reconstruct(spectra, w, starts, 8, -1),
                 lambda: reconstruct([spectra[0][:-1], spectra[1]], w, [0, 2], 8)):
        try:
            call()
        except ValueError:
            invalid_checks += 1
        else:
            raise AssertionError("invalid input accepted")
    return {"unextended_recoverable_indices": [1, 7], "unextended_denominator": d,
            "extended_recoverable_indices": [0, 7], "extended_denominator": full_d,
            "unextended_max_error": error(result, x), "extended_max_error": error(full, x),
            "dropped_frame_zero_indices": [i for i, a in enumerate(dropped) if a is None],
            "phase_lost_max_error": phase_error, "invalid_cases_rejected": invalid_checks,
            "fixed_fs_nfft_bin_hz": 16000/512}


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2, ensure_ascii=False))
```

## 图与证据边界

可编辑覆盖图由标准库生成源制作，必须显式指定输出；建议实验写入库外：

```bash
python3 -B 数学/70-信号处理与多模态数学/assets/generate_stft_reconstruction.py --output /private/tmp/stft-reconstruction.svg
```

脚本导入只定义函数，不写入文件。覆盖图画的是上述独立手算分母，不用待测恢复函数画“预期”。未验证 SciPy/其他音频库的运行、硬件采集或人的听感；这些不是本实验通过项。完整推导与迁移题见 [[数学/70-信号处理与多模态数学/03-STFT窗覆盖与可逆重建|窗覆盖主解释]]。
