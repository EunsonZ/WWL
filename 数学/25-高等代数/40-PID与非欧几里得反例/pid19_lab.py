"""Exact finite checks for the Q(sqrt(-19)) course.

The integer calculations below verify displayed examples and modular value
tables.  They do not prove Minkowski's theorem or the PID conclusion.
"""
from __future__ import annotations

import argparse
import math


def norm19(a: int, b: int) -> int:
    """Field norm of a + b*(1+sqrt(-19))/2."""
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("a and b must be integers")
    return a * a + a * b + 5 * b * b


def roots_mod_prime(constant: int, prime: int) -> tuple[int, ...]:
    """Roots of x^2-x+constant modulo a positive prime supplied by caller."""
    if isinstance(prime, bool) or not isinstance(prime, int) or prime < 2:
        raise ValueError("prime must be an integer at least 2")
    return tuple(x for x in range(prime) if (x * x - x + constant) % prime == 0)


def norm19_solutions(target: int) -> tuple[tuple[int, int], ...]:
    """Enumerate all integer pairs of a^2+ab+5b^2=target."""
    if isinstance(target, bool) or not isinstance(target, int) or target < 0:
        raise ValueError("target must be a nonnegative integer")
    # (a+b/2)^2 + 19*b^2/4 = target gives the finite coordinate bounds.
    b_bound = math.isqrt(4 * target // 19) + 1
    a_bound = math.isqrt(target) + (b_bound + 1) // 2 + 1
    return tuple(
        (a, b)
        for b in range(-b_bound, b_bound + 1)
        for a in range(-a_bound, a_bound + 1)
        if norm19(a, b) == target
    )


def minkowski_bound(abs_discriminant: int) -> float:
    """Imaginary-quadratic class bound (2/pi)*sqrt(|Delta|)."""
    if (
        isinstance(abs_discriminant, bool)
        or not isinstance(abs_discriminant, int)
        or abs_discriminant <= 0
    ):
        raise ValueError("absolute discriminant must be a positive integer")
    return 2.0 * math.sqrt(abs_discriminant) / math.pi


def norm_minus5(a: int, b: int) -> int:
    """Field norm of a+b*sqrt(-5)."""
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("a and b must be integers")
    return a * a + 5 * b * b


def report(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10_000:
        raise ValueError("limit must be an integer from 1 to 10000")
    print(f"M(-19) = {minkowski_bound(19):.12f}; floor = {math.floor(minkowski_bound(19))}")
    print(f"M(-11) = {minkowski_bound(11):.12f}; floor = {math.floor(minkowski_bound(11))}")
    print(f"M(-20) = {minkowski_bound(20):.12f}; floor = {math.floor(minkowski_bound(20))}")
    print(f"roots of x^2-x+5 mod 2: {roots_mod_prime(5, 2)}")
    print(f"roots of x^2-x+5 mod 3: {roots_mod_prime(5, 3)}")
    for target in range(1, limit + 1):
        print(f"N19={target}: {norm19_solutions(target)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=9)
    arguments = parser.parse_args()
    report(arguments.limit)
