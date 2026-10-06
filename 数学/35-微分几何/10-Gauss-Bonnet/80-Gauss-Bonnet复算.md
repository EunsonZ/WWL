---
type: lab
stage: 1
aliases:
  - Gauss-Bonnet数值核查
sources:
  - https://www.maths.gla.ac.uk/~mpowell/M435-chapter-6-gauss-bonnet.pdf
prerequisites:
  - "[[数学/35-微分几何/10-Gauss-Bonnet/04-四个算例与失效边界]]"
---
# Gauss–Bonnet复算

这个实验用 Python 标准库的复合 Simpson 公式重算四个例子的 $\int KdA$ 与 $\int k_gds$，再与解析角点项、$2\pi\chi$ 比较。它检查符号、参数和手算实现；有限采样不证明一般 Gauss–Bonnet，也不验证三角剖分前提。

## 从发布后的库根运行

不安装依赖。发布目录必须保持本页、源码和测试同级：

```bash
python3 -B 数学/35-微分几何/10-Gauss-Bonnet/gauss_bonnet_lab.py
python3 -B -m unittest discover -s 数学/35-微分几何/10-Gauss-Bonnet -p 'test_gauss_bonnet_lab.py' -v
```

候选区实际执行 $R=2,\varphi_0=\pi/3,N=4096$ 得：

| 例子 | $\int KdA$ | $\int k_gds$ | $\sum\alpha$ | $2\pi\chi$ | 浮点残差 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 平面圆盘 | 0 | 6.28318530718 | 0 | 6.28318530718 | 0 |
| 球面第一卦限三角形 | 1.57079632679 | 0 | 4.71238898038 | 6.28318530718 | $8.882\times10^{-16}$ |
| 北球帽 $\varphi_0=\pi/3$ | 3.14159265359 | 3.14159265359 | 0 | 6.28318530718 | $1.776\times10^{-15}$ |
| 圆柱带 | 0 | 0 | 0 | 0 | 0 |

半径在球面积元 $R^2\sin\varphi$ 与 $K=1/R^2$ 中抵消；测试用 $R=0.5,2,7$ 和三个帽角重复检查。另用 $\int_0^{1.1}\sin x\,dx$ 检查 Simpson 步数减半的四阶趋势；这只验证该光滑标量被积函数。错误方向测试把圆盘边界项取反，得到 $-2\pi$ 而不是 $+2\pi$，确保符号错误不会悄悄通过。

输入限制：半径、高度须为有限正数；球帽余纬严格在 $(0,\pi)$；积分端点有限且不同；步数须为2到1000000之间的正偶整数，布尔值拒绝。测试覆盖这些拒绝分支，但不覆盖任意曲面、奇异边界、非紧致极限或真实 Obsidian 渲染。

## 源码与镜像

同目录 Python 文件是真源。下面两个代码块必须逐字同步；代码只做复算，不参与正文的一般证明。

<!-- code-sync: ./gauss_bonnet_lab.py -->
```python
"""Numerically recompute four Gauss--Bonnet examples.

This script checks stated integrals with composite Simpson quadrature.  It does
not prove Gauss--Bonnet.  Angles are radians and every radius is positive.
"""
from __future__ import annotations

import argparse
import math


def positive(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def even_steps(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2 or value > 1_000_000 or value % 2:
        raise ValueError("steps must be an even integer from 2 to 1000000")
    return value


def simpson(function, lower: float, upper: float, steps: int = 4096) -> float:
    """Composite Simpson rule on one finite interval."""
    steps = even_steps(steps)
    lower, upper = float(lower), float(upper)
    if not math.isfinite(lower) or not math.isfinite(upper) or lower == upper:
        raise ValueError("integration bounds must be distinct and finite")
    width = (upper - lower) / steps
    total = function(lower) + function(upper)
    for index in range(1, steps):
        total += (4.0 if index % 2 else 2.0) * function(lower + index * width)
    return total * width / 3.0


def terms(curvature: float, boundary: float, corners: float, chi: int) -> dict[str, float]:
    total = curvature + boundary + corners
    target = 2.0 * math.pi * chi
    return {
        "curvature": curvature,
        "boundary": boundary,
        "corners": corners,
        "chi": float(chi),
        "total": total,
        "target": target,
        "residual": total - target,
    }


def plane_disk(radius: float = 3.0, steps: int = 4096) -> dict[str, float]:
    radius = positive(radius, "radius")
    # Positive boundary is counterclockwise: kg=1/r and ds=r dt.
    boundary = simpson(lambda _t: (1.0 / radius) * radius, 0.0, 2.0 * math.pi, steps)
    return terms(0.0, boundary, 0.0, 1)


def sphere_octant(radius: float = 2.0, steps: int = 4096) -> dict[str, float]:
    radius = positive(radius, "radius")
    # 0<=phi<=pi/2, 0<=theta<=pi/2. Integrating theta first gives pi/2.
    curvature = simpson(
        lambda phi: (1.0 / radius**2) * radius**2 * math.sin(phi) * (math.pi / 2.0),
        0.0,
        math.pi / 2.0,
        steps,
    )
    return terms(curvature, 0.0, 3.0 * math.pi / 2.0, 1)


def sphere_cap(radius: float = 2.0, phi0: float = math.pi / 3.0, steps: int = 4096) -> dict[str, float]:
    radius = positive(radius, "radius")
    phi0 = float(phi0)
    if not math.isfinite(phi0) or not 0.0 < phi0 < math.pi:
        raise ValueError("phi0 must lie strictly between 0 and pi")
    curvature = simpson(
        lambda phi: (1.0 / radius**2) * radius**2 * math.sin(phi) * 2.0 * math.pi,
        0.0,
        phi0,
        steps,
    )
    # T points east, JT points into the north cap: kg=cot(phi0)/R.
    boundary = simpson(
        lambda _theta: (math.cos(phi0) / (radius * math.sin(phi0))) * radius * math.sin(phi0),
        0.0,
        2.0 * math.pi,
        steps,
    )
    return terms(curvature, boundary, 0.0, 1)


def cylinder_band(radius: float = 2.0, height: float = 3.0) -> dict[str, float]:
    positive(radius, "radius")
    positive(height, "height")
    # K=0. Both boundary circles have tangential acceleration zero, hence kg=0.
    return terms(0.0, 0.0, 0.0, 0)


def report(radius: float, phi0: float, steps: int) -> list[tuple[str, dict[str, float]]]:
    rows = [
        ("plane disk", plane_disk(radius, steps)),
        ("sphere octant", sphere_octant(radius, steps)),
        ("sphere cap", sphere_cap(radius, phi0, steps)),
        ("cylinder band", cylinder_band(radius, 3.0)),
    ]
    print("example | int KdA | int kg ds | corners | 2pi chi | residual")
    for name, row in rows:
        print(
            f"{name} | {row['curvature']:.12g} | {row['boundary']:.12g} | "
            f"{row['corners']:.12g} | {row['target']:.12g} | {row['residual']:.3e}"
        )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=float, default=2.0)
    parser.add_argument("--phi0", type=float, default=math.pi / 3.0)
    parser.add_argument("--steps", type=int, default=4096)
    arguments = parser.parse_args()
    report(arguments.radius, arguments.phi0, arguments.steps)
```

<!-- code-sync: ./test_gauss_bonnet_lab.py -->
```python
"""Exact targets, convergence, orientation, and invalid-input checks."""
import math
import unittest

import gauss_bonnet_lab as lab


class GaussBonnetLabTests(unittest.TestCase):
    def assert_gauss_bonnet(self, row, places=11):
        self.assertAlmostEqual(row["total"], row["target"], places=places)
        self.assertAlmostEqual(row["residual"], 0.0, places=places)

    def test_four_examples_same_accounting(self):
        disk = lab.plane_disk(radius=3.0)
        octant = lab.sphere_octant(radius=2.0)
        cap = lab.sphere_cap(radius=2.0, phi0=math.pi / 3.0)
        band = lab.cylinder_band(radius=2.0, height=3.0)
        for row in (disk, octant, cap, band):
            self.assert_gauss_bonnet(row)
        self.assertAlmostEqual(disk["boundary"], 2.0 * math.pi)
        self.assertAlmostEqual(octant["curvature"], math.pi / 2.0)
        self.assertAlmostEqual(octant["corners"], 3.0 * math.pi / 2.0)
        self.assertAlmostEqual(cap["curvature"], math.pi)
        self.assertAlmostEqual(cap["boundary"], math.pi)
        self.assertEqual(band["chi"], 0.0)

    def test_cap_radius_cancels_and_phi_changes_split(self):
        for radius in (0.5, 2.0, 7.0):
            for phi0 in (math.pi / 6.0, math.pi / 2.0, 5.0 * math.pi / 6.0):
                row = lab.sphere_cap(radius, phi0)
                self.assert_gauss_bonnet(row)
                self.assertAlmostEqual(row["curvature"], 2.0 * math.pi * (1.0 - math.cos(phi0)), places=11)
                self.assertAlmostEqual(row["boundary"], 2.0 * math.pi * math.cos(phi0), places=11)

    def test_simpson_converges_on_nonpolynomial_integrand(self):
        exact = 1.0 - math.cos(1.1)
        errors = [abs(lab.simpson(math.sin, 0.0, 1.1, n) - exact) for n in (4, 8, 16)]
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])
        self.assertGreater(errors[0] / errors[1], 14.0)
        self.assertGreater(errors[1] / errors[2], 14.0)

    def test_wrong_boundary_orientation_is_detectable(self):
        disk = lab.plane_disk()
        wrong_total = disk["curvature"] - disk["boundary"] + disk["corners"]
        self.assertAlmostEqual(wrong_total, -2.0 * math.pi)
        self.assertNotAlmostEqual(wrong_total, disk["target"])

    def test_reject_invalid_inputs(self):
        cases = [
            lambda: lab.plane_disk(0.0),
            lambda: lab.sphere_octant(float("inf")),
            lambda: lab.sphere_cap(2.0, 0.0),
            lambda: lab.sphere_cap(2.0, math.pi),
            lambda: lab.cylinder_band(2.0, -1.0),
            lambda: lab.simpson(math.sin, 0.0, 1.0, 3),
            lambda: lab.simpson(math.sin, 0.0, 1.0, True),
            lambda: lab.simpson(math.sin, 1.0, 1.0, 4),
        ]
        for case in cases:
            with self.assertRaises(ValueError):
                case()


if __name__ == "__main__":
    unittest.main()
```
