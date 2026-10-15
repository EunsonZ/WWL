from __future__ import annotations

import numpy as np


def truncated_svd(matrix: np.ndarray, rank: int) -> tuple[np.ndarray, np.ndarray]:
    """Return the best rank-k approximation and all singular values."""
    if matrix.ndim != 2 or 0 in matrix.shape:
        raise ValueError("matrix must be a non-empty two-dimensional array")
    if not np.isfinite(matrix).all():
        raise ValueError("matrix entries must all be finite")
    if isinstance(rank, (bool, np.bool_)) or not isinstance(rank, (int, np.integer)):
        raise ValueError("rank 必须是整数，不接受浮点数或布尔值")
    max_rank = min(matrix.shape)
    if not 1 <= rank <= max_rank:
        raise ValueError(f"rank must be between 1 and {max_rank}")

    u, singular_values, vt = np.linalg.svd(matrix, full_matrices=False)
    approximation = (u[:, :rank] * singular_values[:rank]) @ vt[:rank, :]
    return approximation, singular_values


def frobenius_error(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right, ord="fro"))


def main() -> None:
    rng = np.random.default_rng(7)
    true_rank = 2
    left = rng.normal(size=(8, true_rank))
    right = rng.normal(size=(true_rank, 6))
    clean = left @ right
    observed = clean + 0.05 * rng.normal(size=clean.shape)

    _, singular_values = truncated_svd(observed, rank=1)
    errors: list[float] = []

    print("singular values:", np.round(singular_values, 4))
    print("rank | reconstruction error | discarded-value formula | error to clean")
    for rank in range(1, min(observed.shape) + 1):
        approximation, _ = truncated_svd(observed, rank)
        reconstruction_error = frobenius_error(observed, approximation)
        theoretical_error = float(np.sqrt(np.sum(singular_values[rank:] ** 2)))
        clean_error = frobenius_error(clean, approximation)
        errors.append(reconstruction_error)

        assert np.isclose(reconstruction_error, theoretical_error, atol=1e-10)
        print(
            f"{rank:>4} | {reconstruction_error:>20.6f} |"
            f" {theoretical_error:>23.6f} | {clean_error:>14.6f}"
        )

    assert all(new <= old + 1e-12 for old, new in zip(errors, errors[1:]))
    rank_two, _ = truncated_svd(observed, rank=true_rank)
    noisy_error = frobenius_error(clean, observed)
    denoised_error = frobenius_error(clean, rank_two)
    print(f"noise error: {noisy_error:.6f}")
    print(f"rank-{true_rank} error to clean: {denoised_error:.6f}")


if __name__ == "__main__":
    main()
