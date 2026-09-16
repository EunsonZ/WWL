#!/usr/bin/env python3
"""Pure-standard-library LoRA matrix toy with checkpoint and resume support.

It is a verification aid for the low-rank update shape and resume semantics,
not an LLM trainer and not an implementation of quantized matrix kernels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Matrix = list[list[float]]
Vector = list[float]
ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts" / "toy-lora"
BASE: Matrix = [[1.0, 0.2, -0.3], [0.5, -0.4, 0.8]]
DELTA: Matrix = [[0.7, -0.3, 0.5], [-0.2, 0.4, -0.6]]
EXAMPLES: list[Vector] = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, -1.0, 0.5]]


def zeros(rows: int, columns: int) -> Matrix:
    return [[0.0 for _ in range(columns)] for _ in range(rows)]


def matvec(matrix: Matrix, vector: Vector) -> Vector:
    return [sum(weight * value for weight, value in zip(row, vector)) for row in matrix]


def target(vector: Vector) -> Vector:
    base = matvec(BASE, vector)
    delta = matvec(DELTA, vector)
    return [left + right for left, right in zip(base, delta)]


def lora_delta(a: Matrix, b: Matrix, alpha: float) -> Matrix:
    rank = len(a)
    scale = alpha / rank
    return [[scale * sum(b[out][k] * a[k][inn] for k in range(rank)) for inn in range(len(a[0]))] for out in range(len(b))]


def predict(vector: Vector, a: Matrix, b: Matrix, alpha: float) -> Vector:
    update = lora_delta(a, b, alpha)
    return [left + right for left, right in zip(matvec(BASE, vector), matvec(update, vector))]


def loss(a: Matrix, b: Matrix, alpha: float) -> float:
    total = 0.0
    for vector in EXAMPLES:
        for actual, expected in zip(predict(vector, a, b, alpha), target(vector)):
            total += (actual - expected) ** 2
    return total / (len(EXAMPLES) * len(BASE))


def initial_state(rank: int = 2, alpha: float = 2.0) -> dict[str, Any]:
    if rank <= 0:
        raise ValueError("rank must be positive")
    # B starts at zero so the base model is initially unchanged; A is nonzero so B gets gradient.
    a = [[0.05 * (row + column + 1) for column in range(len(BASE[0]))] for row in range(rank)]
    return {"step": 0, "rank": rank, "alpha": alpha, "a": a, "b": zeros(len(BASE), rank)}


def train_step(state: dict[str, Any], learning_rate: float) -> None:
    a: Matrix = state["a"]
    b: Matrix = state["b"]
    rank = state["rank"]
    scale = state["alpha"] / rank
    grad_a = zeros(rank, len(BASE[0]))
    grad_b = zeros(len(BASE), rank)
    count = len(EXAMPLES) * len(BASE)
    for vector in EXAMPLES:
        error = [actual - expected for actual, expected in zip(predict(vector, a, b, state["alpha"]), target(vector))]
        for out in range(len(BASE)):
            grad_update = 2.0 * error[out] / count
            for k in range(rank):
                grad_b[out][k] += scale * grad_update * sum(a[k][inn] * vector[inn] for inn in range(len(BASE[0])))
                for inn in range(len(BASE[0])):
                    grad_a[k][inn] += scale * b[out][k] * grad_update * vector[inn]
    for out in range(len(BASE)):
        for k in range(rank):
            b[out][k] -= learning_rate * grad_b[out][k]
    for k in range(rank):
        for inn in range(len(BASE[0])):
            a[k][inn] -= learning_rate * grad_a[k][inn]
    state["step"] += 1


def train(state: dict[str, Any], epochs: int, learning_rate: float) -> dict[str, Any]:
    for _ in range(epochs):
        train_step(state, learning_rate)
    return state


def save_checkpoint(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite checkpoint: {path}")
    with path.open("x", encoding="utf-8") as checkpoint_file:
        checkpoint_file.write(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def load_checkpoint(path: Path) -> dict[str, Any]:
    state = json.loads(path.read_text(encoding="utf-8"))
    for key in ("step", "rank", "alpha", "a", "b"):
        if key not in state:
            raise ValueError(f"checkpoint missing {key}")
    return state


def require_artifact_path(path: Path, *, must_exist: bool = False) -> Path:
    """仅允许根内非链接路径；本机非敌对目录，不能消除检查/使用竞态。"""

    root = ARTIFACT_ROOT.resolve()
    original = path.expanduser().absolute()
    # Check before resolve; checking the resolved target loses symlink identity.
    # Stop at the resolved temporary/system anchor, preserving macOS /tmp alias use.
    for component in (original, *original.parents):
        if component == root.parent:
            break
        if component.is_symlink():
            raise ValueError("checkpoint path and in-tree parents must not be symlinks")
    candidate = original.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"checkpoint must stay under {root}") from error
    if must_exist and (not candidate.is_file() or candidate.is_symlink()):
        raise ValueError(f"resume checkpoint must be a regular non-symlink file: {candidate}")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=0.5)
    parser.add_argument("--resume", type=Path, help="existing toy checkpoint")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=ARTIFACT_ROOT / "demo-run" / "checkpoint.json",
    )
    args = parser.parse_args()
    checkpoint = require_artifact_path(args.checkpoint)
    resume = require_artifact_path(args.resume, must_exist=True) if args.resume else None
    state = load_checkpoint(resume) if resume else initial_state()
    before = loss(state["a"], state["b"], state["alpha"])
    train(state, args.epochs, args.learning_rate)
    after = loss(state["a"], state["b"], state["alpha"])
    save_checkpoint(checkpoint, state)
    print(json.dumps({"step": state["step"], "loss_before": before, "loss_after": after, "checkpoint": str(checkpoint)}, ensure_ascii=False))
    return 0 if after < before else 1


if __name__ == "__main__":
    raise SystemExit(main())
