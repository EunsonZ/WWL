"""Declared finite-sampling examples; standard library, stdout only.

Run without arguments for JSON, or --table for the lesson's extrapolation table.
Exact Fraction identities are references; complex double output is an observation,
not a certified rounding bound or a proof for all holomorphic functions.
"""
import argparse
import cmath
from fractions import Fraction
import json
import math


RHO = Fraction(7, 10)
Z = Fraction(2, 5)
TARGET = Fraction(1, 5)
COUNTS = (8, 12, 16, 32)
EXPONENTS = (4, 8, 16, 32, 64)


def pair(value):
    return [value.real, value.imag]


def roots(count):
    return [float(RHO) * cmath.exp(2j * math.pi * j / count)
            for j in range(count)]


def cauchy_sum(values, nodes, target):
    return sum(value * node / (node - target)
               for value, node in zip(values, nodes)) / len(nodes)


def polynomial(value):
    # Degree 7, coefficients (-1)^k/(k+1). Horner vs Lagrange below.
    result = 0j
    for k in reversed(range(8)):
        result = result * value + (-1)**k / (k + 1)
    return result


def lagrange(values, nodes, target):
    result = 0j
    for j, node in enumerate(nodes):
        weight = 1 + 0j
        for k, other in enumerate(nodes):
            if k != j:
                weight *= (target - other) / (node - other)
        result += values[j] * weight
    return result


def extrapolation_table():
    lines = ["| $n$ | 观测盘 $\\lvert z\\rvert\\le1/2$ 上误差 $2^{-n}$ | 目标 $z=1$ 的误差 |",
             "| --- | --- | --- |"]
    for n in EXPONENTS:
        lines.append(f"| {n} | {float(Fraction(1, 2**n)):.6e} | 1 |")
    return "\n".join(lines)


def report():
    quadrature = []
    f_target = 1 / (2 - Z) + TARGET**2
    assert f_target == Fraction(133, 200)
    for count in COUNTS:
        nodes = roots(count)
        values = [1 / (2 - float(Z)) + node**2 for node in nodes]
        computed = cauchy_sum(values, nodes, float(TARGET))
        q_power = (TARGET / RHO)**count
        exact_sum = f_target / (1 - q_power)
        exact_error = exact_sum - f_target
        # The geometric-series reference does not use the summation loop.
        residual = abs(computed - float(exact_sum))
        assert residual < 2e-14
        quadrature.append({"N": count, "computed": pair(computed),
                           "exact_ideal_sum_fraction": str(exact_sum),
                           "exact_quadrature_error_fraction": str(exact_error),
                           "ideal_quadrature_error": float(exact_error),
                           "observed_residual_to_rounded_reference": residual})
    aliases = []
    for count in (8, 12):
        nodes = roots(count)
        values = [(node / float(RHO))**count - 1 for node in nodes]
        residual = max(map(abs, values))
        assert residual < 5e-14
        aliases.append({"N": count, "floating_sample_residual": residual,
                        "exact_samples": "all zero by root-of-unity identity",
                        "exact_target_zero": -1,
                        "target_069_exact_fraction": str((Fraction(69, 100) / RHO)**count - 1),
                        "reconstruction_at_zero": pair(cauchy_sum(values, nodes, 0))})
    nodes = roots(8)
    recovered = lagrange([polynomial(node) for node in nodes], nodes, float(TARGET))
    polynomial_error = abs(recovered - polynomial(float(TARGET)))
    assert polynomial_error < 2e-14
    # Fixed bounded synthetic sample perturbations, chosen to align kernel terms.
    # This observes finite sample propagation, not a continuous-noise experiment.
    noise = []
    epsilon = 1e-6
    for target in (0., .2, .69):
        kernels = [node / (node - target) for node in nodes]
        eta = [epsilon * kernel.conjugate() / abs(kernel) for kernel in kernels]
        propagated = abs(cauchy_sum(eta, nodes, target))
        gain = sum(map(abs, kernels)) / len(nodes)
        coarse_bound = float(RHO) / (float(RHO) - abs(target))
        assert propagated <= epsilon * coarse_bound * (1 + 1e-12)
        assert abs(propagated / epsilon - gain) < 1e-11
        noise.append({"N": 8, "target": target, "epsilon": epsilon,
                      "finite_sample_gain": gain, "coarse_gain_bound": coarse_bound,
                      "observed_noise_output": propagated})
    return {"inputs": {"rho_exact": str(RHO), "z_exact": str(Z),
                       "target_exact": str(TARGET), "quadrature_N": COUNTS,
                       "alias_N": [8, 12], "extrapolation_n": EXPONENTS},
            "quadrature": quadrature, "alias": aliases,
            "degree7_lagrange_error": polynomial_error,
            "sample_noise": noise,
            "extrapolation": [{"n": n, "observation_error_exact": str(Fraction(1, 2**n)),
                               "target_error_exact": 1} for n in EXPONENTS],
            "evidence_boundary": "Author checks only. Exact algebra supplies the claims; floats check fixed implementations. No certified roundoff bound, Obsidian or human learning test."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', action='store_true', help='print generated lesson table')
    args = parser.parse_args()
    if args.table:
        print(extrapolation_table())
    else:
        print(json.dumps(report(), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
