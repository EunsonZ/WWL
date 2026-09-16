"""Finite-difference checks for a hand-written two-layer tanh network."""

from __future__ import annotations

import math
from typing import Iterator


Params = dict[str, float | list[float] | list[list[float]]]


def make_params() -> Params:
    """Return deterministic parameters for a 2 -> 3 -> 1 network."""
    return {
        "W1": [[0.20, -0.30], [0.40, 0.10], [-0.50, 0.20]],
        "b1": [0.01, -0.02, 0.03],
        "w2": [0.70, -0.60, 0.50],
        "b2": -0.10,
    }


def forward(params: Params, x: list[float], target: float) -> tuple[float, dict[str, object]]:
    """Compute 0.5 * (prediction - target)^2 and cache intermediates."""
    w1 = params["W1"]
    b1 = params["b1"]
    w2 = params["w2"]
    b2 = params["b2"]
    assert isinstance(w1, list) and isinstance(b1, list)
    assert isinstance(w2, list) and isinstance(b2, float)

    z1 = [sum(row[i] * x[i] for i in range(2)) + b1[j] for j, row in enumerate(w1)]
    h = [math.tanh(value) for value in z1]
    prediction = sum(w2[j] * h[j] for j in range(3)) + b2
    error = prediction - target
    loss = 0.5 * error * error
    return loss, {"x": x, "h": h, "error": error, "w2": w2}


def backward(cache: dict[str, object], inject_bug: bool = False) -> Params:
    """Return gradients with exactly the same nested shapes as the parameters."""
    x = cache["x"]
    h = cache["h"]
    error = cache["error"]
    w2 = cache["w2"]
    assert isinstance(x, list) and isinstance(h, list)
    assert isinstance(error, float) and isinstance(w2, list)

    grad_w2 = [error * value for value in h]
    grad_b2 = error
    tanh_factor = [(1.0 - value * value) for value in h]
    if inject_bug:
        tanh_factor[0] = 1.0 + h[0] * h[0]
    grad_z1 = [error * w2[j] * tanh_factor[j] for j in range(3)]
    grad_w1 = [[grad_z1[j] * x[i] for i in range(2)] for j in range(3)]
    grad_b1 = grad_z1
    return {"W1": grad_w1, "b1": grad_b1, "w2": grad_w2, "b2": grad_b2}


def scalar_slots(tree: Params) -> Iterator[tuple[str, list[int]]]:
    """Yield stable paths to every scalar in the nested parameter dictionary."""
    for name in ("W1", "b1", "w2", "b2"):
        value = tree[name]
        if isinstance(value, float):
            yield name, []
        elif value and isinstance(value[0], list):
            for row_index, row in enumerate(value):
                for col_index, _ in enumerate(row):
                    yield name, [row_index, col_index]
        else:
            for index, _ in enumerate(value):
                yield name, [index]


def get_scalar(tree: Params, name: str, path: list[int]) -> float:
    value: object = tree[name]
    for index in path:
        assert isinstance(value, list)
        value = value[index]
    assert isinstance(value, float)
    return value


def set_scalar(tree: Params, name: str, path: list[int], new_value: float) -> None:
    if not path:
        tree[name] = new_value
        return
    container: object = tree[name]
    for index in path[:-1]:
        assert isinstance(container, list)
        container = container[index]
    assert isinstance(container, list)
    container[path[-1]] = new_value


def scaled_error(actual: float, expected: float) -> float:
    """Absolute error scaled by max(1, |actual|, |expected|)."""
    scale = max(1.0, abs(actual), abs(expected))
    return abs(actual - expected) / scale


def check_all_parameters(params: Params, x: list[float], target: float, epsilon: float) -> float:
    """Compare manual backprop with centered differences for every scalar."""
    _, cache = forward(params, x, target)
    analytic = backward(cache)
    max_error = 0.0
    for name, path in scalar_slots(params):
        original = get_scalar(params, name, path)
        set_scalar(params, name, path, original + epsilon)
        loss_plus, _ = forward(params, x, target)
        set_scalar(params, name, path, original - epsilon)
        loss_minus, _ = forward(params, x, target)
        set_scalar(params, name, path, original)

        numerical = (loss_plus - loss_minus) / (2.0 * epsilon)
        manual = get_scalar(analytic, name, path)
        max_error = max(max_error, scaled_error(manual, numerical))
    return max_error


def check_direction(params: Params, x: list[float], target: float, epsilon: float) -> float:
    """Check grad dot direction against one centered directional difference."""
    slots = list(scalar_slots(params))
    raw_direction = [float(index + 1) for index in range(len(slots))]
    norm = math.sqrt(sum(value * value for value in raw_direction))
    direction = [value / norm for value in raw_direction]

    _, cache = forward(params, x, target)
    analytic = backward(cache)
    analytic_directional = sum(
        get_scalar(analytic, name, path) * direction[index]
        for index, (name, path) in enumerate(slots)
    )

    originals = [get_scalar(params, name, path) for name, path in slots]
    for index, (name, path) in enumerate(slots):
        set_scalar(params, name, path, originals[index] + epsilon * direction[index])
    loss_plus, _ = forward(params, x, target)
    for index, (name, path) in enumerate(slots):
        set_scalar(params, name, path, originals[index] - epsilon * direction[index])
    loss_minus, _ = forward(params, x, target)
    for index, (name, path) in enumerate(slots):
        set_scalar(params, name, path, originals[index])

    numerical_directional = (loss_plus - loss_minus) / (2.0 * epsilon)
    return scaled_error(analytic_directional, numerical_directional)


def main() -> None:
    params = make_params()
    x = [0.5, -1.2]
    target = 0.3
    epsilon = 1e-5

    loss, _ = forward(params, x, target)
    parameter_error = check_all_parameters(params, x, target, epsilon)
    direction_error = check_direction(params, x, target, epsilon)
    checked = sum(1 for _ in scalar_slots(params))

    print(f"loss={loss:.8f}")
    print(f"checked_parameters={checked}")
    print(f"max_parameter_scaled_error={parameter_error:.3e}")
    print(f"directional_scaled_error={direction_error:.3e}")
    assert parameter_error < 1e-7
    assert direction_error < 1e-7
    print("PASS: manual backprop matches finite differences")


if __name__ == "__main__":
    main()
