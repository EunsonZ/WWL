#!/usr/bin/env python3
"""Observe binary64 rounding, cancellation, stable formulas, and subnormals."""

from __future__ import annotations

import math
import sys


def stable_sqrt_difference(value: float) -> float:
    """Compute sqrt(value + 1) - sqrt(value) without subtracting close roots."""
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("value must be a finite non-negative number")
    return 1.0 / (math.sqrt(value + 1.0) + math.sqrt(value))


def main() -> None:
    decimal_sum = 0.1 + 0.2
    assert decimal_sum != 0.3
    assert math.isclose(decimal_sum, 0.3)
    print("1) Decimal fractions are rounded to a binary grid")
    print(f"0.1 + 0.2 = {decimal_sum:.17g}; exact comparison with 0.3 is {decimal_sum == 0.3}")

    terms = (1e16, 1.0, -1e16)
    sequential = 0.0
    for term in terms:
        sequential += term
    compensated = math.fsum(terms)
    assert sequential == 0.0
    assert compensated == 1.0
    print("\n2) Summation order and retained low bits matter")
    print(f"left_fold{terms}={sequential:.1f}; math.fsum{terms}={compensated:.1f}")

    large = 1e16
    cancellation = math.sqrt(large + 1.0) - math.sqrt(large)
    rationalized = stable_sqrt_difference(large)
    assert cancellation == 0.0
    assert rationalized > 0.0
    assert math.isclose(rationalized, 5e-9, rel_tol=1e-15)
    print("\n3) An equivalent formula avoids catastrophic cancellation")
    print(f"direct={cancellation:.1f}; rationalized={rationalized:.17g}")

    tiny = 1e-16
    direct_log = math.log(1.0 + tiny)
    stable_log = math.log1p(tiny)
    assert 1.0 + tiny == 1.0
    assert direct_log == 0.0
    assert math.isclose(stable_log, tiny, rel_tol=1e-15)
    print("\n4) log1p preserves an increment lost by 1 + x")
    print(f"log(1 + 1e-16)={direct_log:.1f}; log1p(1e-16)={stable_log:.17g}")

    smallest_normal = sys.float_info.min
    half_normal = smallest_normal / 2.0
    smallest_subnormal = math.ulp(0.0)
    assert 0.0 < smallest_subnormal < half_normal < smallest_normal
    print("\n5) This runtime exposes gradual underflow below the normal range")
    print(f"min normal={smallest_normal:.17e}")
    print(f"half min normal={half_normal:.17e}")
    print(f"min subnormal={smallest_subnormal:.17e}")

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
