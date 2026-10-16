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
