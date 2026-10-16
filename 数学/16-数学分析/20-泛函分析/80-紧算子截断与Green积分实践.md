---
type: lab
domain: mathematics
title: 紧算子截断与Green积分实践
stage: 2
aliases:
  - 紧算子的有限复算
sources: []
prerequisites:
  - "[[数学/16-数学分析/20-泛函分析/01-有界算子紧性与逆的稳定性]]"
  - "[[数学/16-数学分析/20-泛函分析/04-一维Green算子的紧性与边界谱]]"
---
# 紧算子截断与Green积分实践

本实践将两个已证明的结论放到有限输入上复算：截断对角算子更准确，却有更大的逆放大；连续 Green 核的中点积分应接近独立推导的解析解。源码是 [compact_green_lab.py](compact_green_lab.py)，全部输入固定在文件中，只依赖 Python 标准库，单线程，无联网和新依赖。

## 先写判断，再运行

| 断言及重要性 | 固定输入 | 独立预期和验收界 |
|---|---|---|
| 前向尾部小不代表反向稳定，重要性中；它检验读者是否混用两个方向 | $N=4,16,64$，尾部向量 $e_{N+1}$，末坐标数据噪声 $10^{-3}$ | 尾部见证分别为 $1/5,1/17,1/65$；恢复误差 $0.004,0.016,0.064$，绝对差小于 $10^{-14}$ |
| Green 符号决定解的正负，重要性中；避免直接复制来源误植 | $f=1$、$m=64,128,256$，在中点计算 Dirichlet 核和 | 解析解 $x(1-x)/2$；中点法对该折线核的偏差恰为 $+1/(8m^2)$，公式残差小于 $2\times10^{-13}$ |
| 相容性与离散残差不同，重要性中 | 同网格的 Neumann 核，常源与 $k=1,3$ 余弦源 | 常源积分为1，原 Neumann 方程无解；核算子把它去均值后映成0。中点核和却残留 $1/(12m^2)$；不要把求积偏差当新零模 |
| 完整谱定理及域的识别，重要性高 | 三课的一般证明、所有 $L^2$ 的量词 | 由非作者检查极值取得、余空间不变、完备性及域；下列有限计算不验收这项 |

谱模式的独立目标是 $K_D(\sqrt2\sin k\pi x)=(k\pi)^{-2}\sqrt2\sin k\pi x$、$K_N(\sqrt2\cos k\pi x)=(k\pi)^{-2}\sqrt2\cos k\pi x$。代码直接对核求和，再与这两个 ODE 推得的公式比较，没有调用生产求和结果生成答案。

各中点单元宽 $h=1/m$。若被积函数 Lipschitz 常数为 $L_g$，单元误差至多 $L_g\int_{-h/2}^{h/2}|s|ds=L_gh^2/4$，合计至多 $L_g/(4m)$。对上述模式，可用 $L_g=\sqrt2(1+Ck\pi)$，Dirichlet 取核上界 $C=1/4$，Neumann 取 $C=1/3$。代码验收为这个严格而保守的一阶界加 $2\times10^{-13}$ 浮点余量；实际误差更快下降不等于已经证明所有源具有二阶收敛。

常源偏差也可手算：除包含 $x$ 的中点单元外，Dirichlet 的核是线性，积分恰被中点求积；该单元的斜率跳跃 $-1$ 使中点矩形多出 $h^2/8$。Neumann 核多一个 $\xi^2/2$，它在整个区间的中点误差为 $-h^2/24$，合计 $h^2/8-h^2/24=h^2/12$。

## 运行与结果

从库根执行，结果路径必须是新文件，已有结果会拒绝覆盖：

```bash
python3 -B 数学/16-数学分析/20-泛函分析/compact_green_lab.py --out /private/tmp/compact-green-reproduced.json
```

输入规模最大256个积分中点，不形成大型矩阵，不启动多线程库；建议单次上限60秒。改变核、边界、模式或网格时，另选新结果路径，并重新判断解析目标和误差界是否适用。输入是函数采样值；这不同于正文证明中对阶梯核使用精确单元积分，但二者均由已给出的连续积分误差控制。

本次本机通过共享数值槽 runner 执行同一源码，退出码0，Python 3.14.7，脚本记录耗时约0.040秒。实际结果为 [compact-green-20261016.json](实践结果/compact-green-20261016.json)。Dirichlet/Neumann 的 $k=1$ 模式最大采样误差随 $m=64,128,256$ 约为 $2.877\times10^{-5},7.193\times10^{-6},1.798\times10^{-6}$；Neumann 输出均值的绝对值小于 $1.2\times10^{-19}$。截断噪声恢复误差与表格一致，常源偏差公式的浮点残差小于 $1.9\times10^{-17}$。

这些结果是指定中点、模式与参数的实际执行，不证明一般谱定理，不认证任意 $L^2$ 初值、Obsidian 排版、物理测量或真人理解。带结果返回 [[数学/16-数学分析/20-泛函分析/04-一维Green算子的紧性与边界谱#一个可算的源，三种不同的收敛结论|Green 三种收敛]]：指出哪些数字属于采样误差，哪些是统一算子范数，哪些需要域内二阶导数。

## 同版源码镜像

<!-- code-sync: ./compact_green_lab.py -->
```python
"""Finite checks for compact truncation and Green quadrature; standard library only."""
from __future__ import annotations

import argparse
import json
import math
import platform
import time
from pathlib import Path


def green_dirichlet(x: float, y: float) -> float:
    return min(x, y) - x * y


def green_neumann(x: float, y: float) -> float:
    return (x * x + y * y) / 2 - max(x, y) + 1 / 3


def apply_midpoint(kernel, points: list[float], values: list[float]) -> list[float]:
    m = len(points)
    return [math.fsum(kernel(x, y) * v for y, v in zip(points, values)) / m
            for x in points]


def max_error(left: list[float], right: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right))


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def calculate() -> dict:
    start = time.perf_counter()
    truncations = []
    for n in (4, 16, 64):
        # e_(N+1) is a lower-bound witness for the infinite tail norm.
        x = [0.0] * (n + 1)
        x[-1] = 1.0
        full = [v / (i + 1) for i, v in enumerate(x)]
        cut = full[:-1] + [0.0]
        tail = math.sqrt(math.fsum((a - b) ** 2 for a, b in zip(full, cut)))
        eta = 0.001
        data = [0.0] * n
        data[-1] = eta
        recovered = [(i + 1) * v for i, v in enumerate(data)]
        error = math.sqrt(math.fsum(v * v for v in recovered))
        require(abs(tail - 1 / (n + 1)) < 1e-14, 'tail witness')
        require(abs(error - n * eta) < 1e-14, 'inverse amplification')
        truncations.append(dict(n=n, tail_witness=tail, inverse_error=error,
                                noise=eta, inverse_gain=error / eta))

    quadrature = []
    for m in (64, 128, 256):
        points = [(j + 0.5) / m for j in range(m)]
        ones = [1.0] * m
        d_constant = apply_midpoint(green_dirichlet, points, ones)
        exact = [x * (1 - x) / 2 for x in points]
        # Piecewise linear midpoint sums can be evaluated exactly by hand.
        d_bias_error = max_error(d_constant, [v + 1 / (8 * m * m) for v in exact])
        n_constant = apply_midpoint(green_neumann, points, ones)
        n_bias_error = max(abs(v - 1 / (12 * m * m)) for v in n_constant)
        require(d_bias_error < 2e-13, 'Dirichlet constant-source midpoint bias')
        require(n_bias_error < 2e-13, 'Neumann constant-mode midpoint bias')
        boundary = max(abs(green_dirichlet(x, y)) for x in (0.0, 1.0) for y in points)
        require(boundary < 1e-14, 'Dirichlet kernel boundary')
        for kind, kernel, trig in [('dirichlet', green_dirichlet, math.sin),
                                    ('neumann', green_neumann, math.cos)]:
            for k in (1, 3):
                mode = [math.sqrt(2) * trig(k * math.pi * x) for x in points]
                observed = apply_midpoint(kernel, points, mode)
                mu = 1 / (k * math.pi) ** 2
                expected = [mu * v for v in mode]
                error = max_error(observed, expected)
                # A rigorous midpoint bound from the integrand's Lipschitz constant.
                kernel_bound = 0.25 if kind == 'dirichlet' else 1 / 3
                lipschitz = math.sqrt(2) * (1 + kernel_bound * k * math.pi)
                tolerance = lipschitz / (4 * m) + 2e-13
                require(error <= tolerance, 'mode quadrature Lipschitz bound')
                mean = math.fsum(observed) / m
                if kind == 'neumann':
                    require(abs(mean) < 2e-13, 'Neumann mean-zero output')
                quadrature.append(dict(kind=kind, cells=m, mode=k, max_error=error,
                                       rigorous_bound=tolerance, output_mean=mean,
                                       constant_bias_roundoff=(d_bias_error if kind == 'dirichlet'
                                                               else n_bias_error)))
    # The physical Neumann compatibility failure is integral(1)=1, not a solver residual.
    return dict(status='PASS', python=platform.python_version(),
                elapsed_seconds=time.perf_counter() - start, threads=1,
                inputs=dict(truncation_n=[4, 16, 64], cells=[64, 128, 256], modes=[1, 3]),
                truncations=truncations, quadrature=quadrature,
                neumann_constant_source_integral=1,
                not_verified=['general spectral theorem', 'all L2 inputs',
                              'Obsidian rendering', 'physical apparatus', 'human understanding'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new result JSON path')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output exists; select a new path')
    result = calculate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also prevents overwriting a result created during calculation.
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(f"PASS: {args.out}; elapsed={result['elapsed_seconds']:.4f}s; threads=1")


if __name__ == '__main__':
    main()
```
