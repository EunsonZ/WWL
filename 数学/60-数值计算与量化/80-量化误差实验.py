#!/usr/bin/env python3
"""Deterministic affine-quantization experiments using only the standard library."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Quantized:
    codes: tuple[int, ...]
    reconstructed: tuple[float, ...]
    scale: float
    zero_point: int
    qmin: int
    qmax: int
    clipped_count: int
    calibration_low: float
    calibration_high: float


def percentile(values: Sequence[float], percent: float) -> float:
    """Return a linearly interpolated percentile for a non-empty sequence."""
    if not values:
        raise ValueError("percentile needs at least one value")
    if not 0.0 <= percent <= 100.0:
        raise ValueError("percent must be in [0, 100]")

    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * percent / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def choose_calibration_range(
    values: Sequence[float],
    *,
    symmetric: bool,
    clip_percentile: float | None,
) -> tuple[float, float]:
    if not values:
        raise ValueError("quantization needs at least one value")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("all inputs must be finite")

    if symmetric:
        magnitudes = [abs(value) for value in values]
        limit = max(magnitudes)
        if clip_percentile is not None:
            limit = percentile(magnitudes, clip_percentile)
        return -limit, limit

    if clip_percentile is None:
        return min(values), max(values)
    tail = (100.0 - clip_percentile) / 2.0
    return percentile(values, tail), percentile(values, 100.0 - tail)


def supported_number(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ArithmeticError(name + " exceeds numerical support")
    return value


def supported_scale(value: float) -> float:
    if not math.isfinite(value) or value <= 0.0:
        raise ArithmeticError("quantization scale must be finite and positive; unsupported range")
    return value


def affine_quantize(
    values: Iterable[float],
    *,
    bits: int,
    symmetric: bool,
    clip_percentile: float | None = None,
) -> Quantized:
    """Quantize and dequantize values with round-to-nearest, ties-to-even."""
    data = tuple(float(value) for value in values)
    if type(bits) is not int or bits < 2 or bits > 16:
        raise ValueError("this lesson supports bit widths from 2 through 16")
    if clip_percentile is not None and not 0.0 < clip_percentile <= 100.0:
        raise ValueError("clip_percentile must be in (0, 100]")

    low, high = choose_calibration_range(
        data,
        symmetric=symmetric,
        clip_percentile=clip_percentile,
    )

    if (clip_percentile is not None and low == high and any(value != 0.0 for value in data)):
        raise ValueError(
            "percentile calibration collapsed to a zero-width range for nonzero input"
        )

    # Affine zero-point quantization must include real zero in its range.
    if not symmetric:
        low = min(low, 0.0)
        high = max(high, 0.0)

    if symmetric:
        qmax = (1 << (bits - 1)) - 1
        qmin = -qmax
        zero_point = 0
        limit = max(abs(low), abs(high))
        scale = supported_scale(limit / qmax if limit > 0.0 else 1.0)
    else:
        qmin = 0
        qmax = (1 << bits) - 1
        if high == low:
            if high > 0.0:
                scale = supported_scale(high / qmax)
                zero_point = 0
            elif low < 0.0:
                scale = supported_scale(-low / qmax)
                zero_point = qmax
            else:
                scale = 1.0
                zero_point = 0
        else:
            scale = supported_scale((high - low) / (qmax - qmin))
            proposed = round(supported_number(qmin - low / scale, "zero-point quotient"))
            zero_point = max(qmin, min(qmax, proposed))

    codes: list[int] = []
    reconstructed: list[float] = []
    clipped_count = 0
    for value in data:
        unbounded = round(supported_number(value / scale, "code quotient")) + zero_point
        code = max(qmin, min(qmax, unbounded))
        clipped_count += int(code != unbounded)
        codes.append(code)
        reconstructed.append(supported_number(scale * (code - zero_point), "reconstruction"))

    return Quantized(
        codes=tuple(codes),
        reconstructed=tuple(reconstructed),
        scale=scale,
        zero_point=zero_point,
        qmin=qmin,
        qmax=qmax,
        clipped_count=clipped_count,
        calibration_low=low,
        calibration_high=high,
    )


def grouped_quantize(
    values: Sequence[float],
    *,
    bits: int,
    group_size: int,
    symmetric: bool,
    clip_percentile: float | None = None,
) -> tuple[tuple[float, ...], tuple[Quantized, ...]]:
    if type(group_size) is not int or group_size <= 0:
        raise ValueError("group_size must be positive")
    reconstructed: list[float] = []
    groups: list[Quantized] = []
    for start in range(0, len(values), group_size):
        group = affine_quantize(
            values[start : start + group_size],
            bits=bits,
            symmetric=symmetric,
            clip_percentile=clip_percentile,
        )
        groups.append(group)
        reconstructed.extend(group.reconstructed)
    return tuple(reconstructed), tuple(groups)


def error_metrics(reference: Sequence[float], estimate: Sequence[float]) -> dict[str, float]:
    if len(reference) != len(estimate) or not reference:
        raise ValueError("metric inputs must have the same non-zero length")
    errors = [approximation - truth for truth, approximation in zip(reference, estimate)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    maximum = max(abs(error) for error in errors)
    dot = sum(x * y for x, y in zip(reference, estimate))
    reference_norm = math.sqrt(sum(x * x for x in reference))
    estimate_norm = math.sqrt(sum(y * y for y in estimate))
    cosine = dot / (reference_norm * estimate_norm) if reference_norm and estimate_norm else math.nan
    return {"mae": mae, "rmse": rmse, "max_abs": maximum, "cosine": cosine}


def print_report(name: str, reference: Sequence[float], estimate: Sequence[float]) -> None:
    metrics = error_metrics(reference, estimate)
    print(
        f"{name:26s} "
        f"MAE={metrics['mae']:.6f} "
        f"RMSE={metrics['rmse']:.6f} "
        f"MAX={metrics['max_abs']:.6f} "
        f"COS={metrics['cosine']:.8f}"
    )


def main() -> None:
    in_range = (-1.4, -0.26, 0.0, 0.31, 1.4)
    bounded = affine_quantize(in_range, bits=4, symmetric=True)
    maximum_error = max(
        abs(approximation - truth)
        for truth, approximation in zip(in_range, bounded.reconstructed)
    )
    assert bounded.clipped_count == 0
    assert maximum_error <= bounded.scale / 2.0 + 1e-12
    assert bounded.codes[2] == bounded.zero_point == 0
    print("1) No-clipping bound")
    print(f"scale={bounded.scale:.6f}, max_error={maximum_error:.6f}, scale/2={bounded.scale / 2:.6f}")

    positive_only = affine_quantize((1.0, 2.0), bits=8, symmetric=False)
    negative_only = affine_quantize((-2.0, -1.0), bits=8, symmetric=False)
    assert positive_only.calibration_low == 0.0
    assert negative_only.calibration_high == 0.0
    assert positive_only.clipped_count == negative_only.clipped_count == 0
    assert positive_only.codes[0] < positive_only.codes[1] == positive_only.qmax
    assert negative_only.codes[0] == negative_only.qmin < negative_only.codes[1]
    assert positive_only.zero_point == positive_only.qmin
    assert negative_only.zero_point == negative_only.qmax
    print("\n2) One-sided asymmetric ranges include zero")
    print(
        f"positive codes={positive_only.codes}, zero_point={positive_only.zero_point}; "
        f"negative codes={negative_only.codes}, zero_point={negative_only.zero_point}"
    )

    weights = (
        12.0,
        -0.95,
        -0.70,
        -0.45,
        -0.30,
        -0.18,
        -0.07,
        0.02,
        0.08,
        0.17,
        0.29,
        0.43,
        0.56,
        0.72,
        0.89,
        1.05,
    )
    per_tensor = affine_quantize(weights, bits=4, symmetric=True)
    grouped_values, groups = grouped_quantize(
        weights,
        bits=4,
        group_size=4,
        symmetric=True,
    )
    clipped = affine_quantize(
        weights,
        bits=4,
        symmetric=True,
        clip_percentile=90.0,
    )

    print("\n3) Outlier, grouping, and clipping")
    print_report("per-tensor 4-bit", weights, per_tensor.reconstructed)
    print_report("per-group(4) 4-bit", weights, grouped_values)
    print_report("per-tensor p90 clip", weights, clipped.reconstructed)
    print("group scales:", ", ".join(f"{group.scale:.6f}" for group in groups))
    print(f"p90 clipped values: {clipped.clipped_count}")

    bulk_reference = weights[1:]
    per_tensor_bulk = per_tensor.reconstructed[1:]
    clipped_bulk = clipped.reconstructed[1:]
    per_tensor_bulk_rmse = error_metrics(bulk_reference, per_tensor_bulk)["rmse"]
    clipped_bulk_rmse = error_metrics(bulk_reference, clipped_bulk)["rmse"]
    assert error_metrics(weights, grouped_values)["rmse"] < error_metrics(
        weights, per_tensor.reconstructed
    )["rmse"]
    assert clipped_bulk_rmse < per_tensor_bulk_rmse
    print(
        "bulk RMSE (outlier excluded): "
        f"min-max={per_tensor_bulk_rmse:.6f}, p90={clipped_bulk_rmse:.6f}"
    )
    print("The p90 choice improves the bulk but clips the outlier; global RMSE tells the other side.")

    activations = (
        0.60,
        -1.10,
        0.30,
        0.05,
        -0.70,
        0.90,
        -0.40,
        0.20,
        1.20,
        -0.80,
        0.15,
        0.50,
        -0.25,
        0.75,
        -0.55,
        0.10,
    )
    quantized_weights = affine_quantize(weights, bits=8, symmetric=False)
    quantized_activations = affine_quantize(activations, bits=8, symmetric=False)
    integer_accumulator = sum(
        (weight_code - quantized_weights.zero_point)
        * (activation_code - quantized_activations.zero_point)
        for weight_code, activation_code in zip(
            quantized_weights.codes,
            quantized_activations.codes,
        )
    )
    quantized_dot = (
        quantized_weights.scale
        * quantized_activations.scale
        * integer_accumulator
    )
    reference_dot = sum(weight * activation for weight, activation in zip(weights, activations))

    print("\n4) Asymmetric 8-bit integer dot product")
    print(
        f"weight scale={quantized_weights.scale:.8f}, zero_point={quantized_weights.zero_point}; "
        f"activation scale={quantized_activations.scale:.8f}, "
        f"zero_point={quantized_activations.zero_point}"
    )
    print(f"integer accumulator={integer_accumulator}")
    print(
        f"reference dot={reference_dot:.8f}, "
        f"dequantized dot={quantized_dot:.8f}, "
        f"absolute error={abs(quantized_dot - reference_dot):.8f}"
    )


if __name__ == "__main__":
    main()
