"""Entity-disjoint calibration lab for UCI HAR (NumPy + Matplotlib only).

The CLI consumes the exact outer archive downloaded from UCI dataset 240.
It never downloads data itself and rejects archive-byte drift before reading.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np


UCI_URL = "https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip"
UCI_OUTER_SHA256 = "c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031"
UCI_INNER_SHA256 = "2045e435c955214b38145fb5fa00776c72814f01b203fec405152dac7d5bfeb0"
UCI_OUTER_BYTES = 61005872
FEATURE_COUNT = 561
CLASS_COUNT = 6
SPLIT_SEED = 20260920
TEMPERATURE_LOG_BOUNDS = (-3.0, 3.0)
SUBJECT_SPLITS = {
    "train": (2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 27),
    "dev": (1, 28, 29, 30),
    "cal": (5, 20, 25, 26),
    "test": (6, 10, 23, 24),
}
CLASS_NAMES = (
    "WALKING",
    "WALKING_UPSTAIRS",
    "WALKING_DOWNSTAIRS",
    "SITTING",
    "STANDING",
    "LAYING",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_text_matrix(zf: zipfile.ZipFile, name: str, dtype: type) -> np.ndarray:
    with zf.open(name) as handle:
        return np.loadtxt(handle, dtype=dtype)


def load_uci_har_archive(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Load all 10,299 feature rows from the fixed nested UCI archive."""
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) != UCI_OUTER_BYTES:
        raise ValueError(f"archive byte-length mismatch: expected {UCI_OUTER_BYTES}, got {len(raw)}")
    outer_hash = sha256_bytes(raw)
    if outer_hash != UCI_OUTER_SHA256:
        raise ValueError(f"archive SHA-256 mismatch: expected {UCI_OUTER_SHA256}, got {outer_hash}")
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        inner = outer.read("UCI HAR Dataset.zip")
    inner_hash = sha256_bytes(inner)
    if inner_hash != UCI_INNER_SHA256:
        raise ValueError(f"inner archive SHA-256 mismatch: expected {UCI_INNER_SHA256}, got {inner_hash}")
    prefix = "UCI HAR Dataset"
    blocks = []
    with zipfile.ZipFile(io.BytesIO(inner)) as zf:
        for part in ("train", "test"):
            x = _load_text_matrix(zf, f"{prefix}/{part}/X_{part}.txt", float)
            y = _load_text_matrix(zf, f"{prefix}/{part}/y_{part}.txt", int)
            subject = _load_text_matrix(zf, f"{prefix}/{part}/subject_{part}.txt", int)
            blocks.append((x, y, subject))
    x = np.vstack([b[0] for b in blocks]).astype(np.float64, copy=False)
    y = np.concatenate([b[1] for b in blocks]).astype(np.int64, copy=False) - 1
    subject = np.concatenate([b[2] for b in blocks]).astype(np.int64, copy=False)
    validate_dataset(x, y, subject)
    metadata = {
        "source_url": UCI_URL,
        "outer_bytes": len(raw),
        "outer_sha256": outer_hash,
        "inner_sha256": inner_hash,
        "rows": int(x.shape[0]),
        "features": int(x.shape[1]),
        "subjects": int(np.unique(subject).size),
        "classes": CLASS_COUNT,
    }
    return x, y, subject, metadata


def validate_dataset(x: np.ndarray, y: np.ndarray, subject: np.ndarray) -> None:
    if x.shape != (10299, FEATURE_COUNT):
        raise ValueError(f"expected X shape (10299, 561), got {x.shape}")
    if y.shape != (10299,) or subject.shape != (10299,):
        raise ValueError("label and subject arrays must each have shape (10299,)")
    if not np.isfinite(x).all() or np.min(x) < -1.000001 or np.max(x) > 1.000001:
        raise ValueError("features must be finite and within the documented [-1, 1] range")
    if set(np.unique(y).tolist()) != set(range(CLASS_COUNT)):
        raise ValueError("expected class labels 1..6 in the archive")
    if set(np.unique(subject).tolist()) != set(range(1, 31)):
        raise ValueError("expected subject IDs 1..30")
    all_ids = [s for values in SUBJECT_SPLITS.values() for s in values]
    if len(all_ids) != 30 or set(all_ids) != set(range(1, 31)):
        raise AssertionError("subject split must partition IDs 1..30 exactly once")


def split_by_subject(
    x: np.ndarray, y: np.ndarray, subject: np.ndarray
) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    result = {}
    seen = set()
    for name, ids in SUBJECT_SPLITS.items():
        mask = np.isin(subject, ids)
        result[name] = (x[mask], y[mask], subject[mask])
        actual = set(np.unique(subject[mask]).tolist())
        if actual != set(ids) or seen & actual:
            raise AssertionError(f"bad or overlapping subject split: {name}")
        seen |= actual
        if set(np.unique(y[mask]).tolist()) != set(range(CLASS_COUNT)):
            raise ValueError(f"split {name} does not contain all six classes")
    return result


def fit_standardizer(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.mean(x, axis=0)
    scale = np.std(x, axis=0)
    scale = np.where(scale < 1e-12, 1.0, scale)
    return mean, scale


def design(x: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    if x.ndim != 2 or x.shape[1] != mean.shape[0] or mean.shape != scale.shape:
        raise ValueError("incompatible feature/standardizer shapes")
    z = (x - mean) / scale
    return np.column_stack([np.ones(z.shape[0]), z])


def softmax(logits: np.ndarray) -> np.ndarray:
    if logits.ndim != 2 or logits.shape[1] != CLASS_COUNT:
        raise ValueError("logits must have shape (n, 6)")
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def multiclass_nll(logits: np.ndarray, y: np.ndarray, temperature: float = 1.0) -> float:
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be positive and finite")
    if logits.ndim != 2 or logits.shape != (y.size, CLASS_COUNT):
        raise ValueError("logits must have shape (n, 6) and match labels")
    scaled = logits / temperature
    maximum = np.max(scaled, axis=1)
    log_normalizer = maximum + np.log(np.sum(np.exp(scaled - maximum[:, None]), axis=1))
    return float(np.mean(log_normalizer - scaled[np.arange(y.size), y]))


def train_softmax(
    x: np.ndarray,
    y: np.ndarray,
    *,
    l2: float,
    seed: int,
    epochs: int = 36,
    batch_size: int = 512,
    learning_rate: float = 0.012,
) -> np.ndarray:
    """Fit multinomial logistic regression with deterministic mini-batch Adam."""
    if x.ndim != 2 or y.shape != (x.shape[0],):
        raise ValueError("bad design/label shapes")
    if l2 < 0 or epochs <= 0 or batch_size <= 0 or learning_rate <= 0:
        raise ValueError("invalid optimizer parameter")
    rng = np.random.default_rng(seed)
    w = np.zeros((x.shape[1], CLASS_COUNT), dtype=np.float64)
    m = np.zeros_like(w)
    v = np.zeros_like(w)
    step = 0
    for _ in range(epochs):
        permutation = rng.permutation(x.shape[0])
        for start in range(0, x.shape[0], batch_size):
            indices = permutation[start : start + batch_size]
            xb, yb = x[indices], y[indices]
            p = softmax(xb @ w)
            p[np.arange(yb.size), yb] -= 1.0
            grad = xb.T @ p / yb.size
            grad[1:] += l2 * w[1:]
            step += 1
            m = 0.9 * m + 0.1 * grad
            v = 0.999 * v + 0.001 * (grad * grad)
            mhat = m / (1.0 - 0.9**step)
            vhat = v / (1.0 - 0.999**step)
            w -= learning_rate * mhat / (np.sqrt(vhat) + 1e-8)
    return w


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """Minimize calibration NLL over bounded log(T) in [-3, 3]."""
    lo, hi = TEMPERATURE_LOG_BOUNDS
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - ratio * (hi - lo)
    d = lo + ratio * (hi - lo)
    fc = multiclass_nll(logits, y, math.exp(c))
    fd = multiclass_nll(logits, y, math.exp(d))
    for _ in range(80):
        if fc <= fd:
            hi, d, fd = d, c, fc
            c = hi - ratio * (hi - lo)
            fc = multiclass_nll(logits, y, math.exp(c))
        else:
            lo, c, fc = c, d, fd
            d = lo + ratio * (hi - lo)
            fd = multiclass_nll(logits, y, math.exp(d))
    return float(math.exp((lo + hi) / 2.0))


def reliability(probs: np.ndarray, y: np.ndarray, bins: int) -> list[dict]:
    if probs.shape != (y.size, CLASS_COUNT) or bins <= 0:
        raise ValueError("bad probability/label shapes or bin count")
    confidence = np.max(probs, axis=1)
    correct = np.argmax(probs, axis=1) == y
    edges = np.linspace(0.0, 1.0, bins + 1)
    ids = np.minimum(np.searchsorted(edges, confidence, side="right") - 1, bins - 1)
    ids = np.maximum(ids, 0)
    out = []
    for index in range(bins):
        mask = ids == index
        count = int(np.sum(mask))
        out.append(
            {
                "left": float(edges[index]),
                "right": float(edges[index + 1]),
                "count": count,
                "mean_confidence": None if count == 0 else float(np.mean(confidence[mask])),
                "accuracy": None if count == 0 else float(np.mean(correct[mask])),
            }
        )
    return out


def ece_from_reliability(table: list[dict]) -> float:
    total = sum(row["count"] for row in table)
    if total == 0:
        raise ValueError("ECE needs at least one row")
    return float(
        sum(
            row["count"] / total * abs(row["accuracy"] - row["mean_confidence"])
            for row in table
            if row["count"]
        )
    )


def metrics(logits: np.ndarray, y: np.ndarray, temperature: float, bins: int = 10) -> dict:
    probs = softmax(logits / temperature)
    pred = np.argmax(probs, axis=1)
    onehot = np.eye(CLASS_COUNT)[y]
    table = reliability(probs, y, bins)
    return {
        "rows": int(y.size),
        "accuracy": float(np.mean(pred == y)),
        "nll": multiclass_nll(logits, y, temperature),
        "brier": float(np.mean(np.sum((probs - onehot) ** 2, axis=1))),
        "ece": ece_from_reliability(table),
        "bins": bins,
    }


def row_split_indices(y: np.ndarray, seed: int, holdout_fraction: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    """Class-stratified row split used only for a leakage-mechanism diagnostic."""
    if not (0.0 < holdout_fraction < 1.0):
        raise ValueError("holdout_fraction must be in (0, 1)")
    rng = np.random.default_rng(seed)
    train, holdout = [], []
    for label in range(CLASS_COUNT):
        indices = np.flatnonzero(y == label)
        indices = rng.permutation(indices)
        cut = int(round(indices.size * (1.0 - holdout_fraction)))
        train.extend(indices[:cut])
        holdout.extend(indices[cut:])
    return np.array(sorted(train)), np.array(sorted(holdout))


def _rounded(value: float) -> float:
    return round(float(value), 10)


def run_experiment(archive: str | Path, *, seed: int = 20260920) -> tuple[dict, dict]:
    x, y, subject, metadata = load_uci_har_archive(archive)
    split = split_by_subject(x, y, subject)
    x_train, y_train, _ = split["train"]
    mean, scale = fit_standardizer(x_train)
    z_train = design(x_train, mean, scale)
    z_dev = design(split["dev"][0], mean, scale)
    candidates = []
    weights = {}
    for l2 in (1e-5, 1e-4, 1e-3):
        w = train_softmax(z_train, y_train, l2=l2, seed=seed)
        logits = z_dev @ w
        record = {"l2": l2, **metrics(logits, split["dev"][1], 1.0)}
        candidates.append(record)
        weights[l2] = w
    selected = min(candidates, key=lambda row: (row["nll"], row["l2"]))
    selected_l2 = selected["l2"]
    w = weights[selected_l2]
    logits = {name: design(values[0], mean, scale) @ w for name, values in split.items()}
    temperature = fit_temperature(logits["cal"], split["cal"][1])

    before = metrics(logits["test"], split["test"][1], 1.0)
    after = metrics(logits["test"], split["test"][1], temperature)
    bin_sensitivity = {
        str(b): {
            "before": _rounded(metrics(logits["test"], split["test"][1], 1.0, b)["ece"]),
            "after": _rounded(metrics(logits["test"], split["test"][1], temperature, b)["ece"]),
        }
        for b in (5, 10, 15, 30)
    }
    test_subject = split["test"][2]
    subject_metrics = {}
    for sid in SUBJECT_SPLITS["test"]:
        mask = test_subject == sid
        subject_metrics[str(sid)] = metrics(logits["test"][mask], split["test"][1][mask], temperature)

    # Separate diagnostic: it uses only formal train+dev subjects, never cal/test,
    # and none of its outputs feed the formal model or its temperature.
    diagnostic_x = np.vstack([split["train"][0], split["dev"][0]])
    diagnostic_y = np.concatenate([split["train"][1], split["dev"][1]])
    diagnostic_subject = np.concatenate([split["train"][2], split["dev"][2]])
    diagnostic_l2 = 1e-3  # fixed for the diagnostic; never selected by its scores
    entity_w = train_softmax(z_train, y_train, l2=diagnostic_l2, seed=seed + 100)
    entity_logits = z_dev @ entity_w
    row_train, row_holdout = row_split_indices(diagnostic_y, seed + 101)
    row_mean, row_scale = fit_standardizer(diagnostic_x[row_train])
    row_w = train_softmax(
        design(diagnostic_x[row_train], row_mean, row_scale),
        diagnostic_y[row_train],
        l2=diagnostic_l2,
        seed=seed + 102,
    )
    row_logits = design(diagnostic_x[row_holdout], row_mean, row_scale) @ row_w
    row_subject_overlap = sorted(
        set(diagnostic_subject[row_train].tolist()) & set(diagnostic_subject[row_holdout].tolist())
    )
    diagnostic = {
        "formal_test_touched": False,
        "pool": "formal train+dev subjects only",
        "selection": "l2=1e-3 fixed for both diagnostic protocols; no diagnostic score feeds the formal pipeline",
        "entity_holdout": {
            "train_subjects": list(SUBJECT_SPLITS["train"]),
            "holdout_subjects": list(SUBJECT_SPLITS["dev"]),
            "l2": diagnostic_l2,
            **metrics(entity_logits, split["dev"][1], 1.0),
        },
        "row_holdout": {
            "train_rows": int(row_train.size),
            "holdout_rows": int(row_holdout.size),
            "subjects_in_both_sides": row_subject_overlap,
            **metrics(row_logits, diagnostic_y[row_holdout], 1.0),
        },
    }

    report = {
        "schema": "wwl-entity-calibration-v1",
        "split_seed": SPLIT_SEED,
        "optimizer_and_diagnostic_seed": seed,
        "dataset": metadata,
        "protocol": {
            "split_rule": "subject IDs generated once with split_seed=20260920, then hard-coded; CLI seed never changes this split",
            "subject_splits": {k: list(v) for k, v in SUBJECT_SPLITS.items()},
            "rows": {k: int(v[0].shape[0]) for k, v in split.items()},
            "feature_count": FEATURE_COUNT,
            "class_names": list(CLASS_NAMES),
            "hyperparameter_role": "l2 selected by dev NLL only",
            "calibration_role": "temperature selected by cal NLL only",
            "test_role": "one frozen observation; no selection or fitting",
        },
        "dev_candidates": [{k: _rounded(v) if isinstance(v, float) else v for k, v in r.items()} for r in candidates],
        "selected_l2": selected_l2,
        "calibration": {
            "temperature": _rounded(temperature),
            "log_temperature_search_bounds": list(TEMPERATURE_LOG_BOUNDS),
            "temperature_search_bounds": [_rounded(math.exp(v)) for v in TEMPERATURE_LOG_BOUNDS],
            "cal_nll_before": _rounded(multiclass_nll(logits["cal"], split["cal"][1], 1.0)),
            "cal_nll_after": _rounded(multiclass_nll(logits["cal"], split["cal"][1], temperature)),
            "argmax_changes_on_test": int(
                np.sum(np.argmax(logits["test"], axis=1) != np.argmax(logits["test"] / temperature, axis=1))
            ),
        },
        "test": {
            "before_temperature": {k: _rounded(v) if isinstance(v, float) else v for k, v in before.items()},
            "after_temperature": {k: _rounded(v) if isinstance(v, float) else v for k, v in after.items()},
            "ece_bin_sensitivity": bin_sensitivity,
            "by_subject_after_temperature": {
                sid: {k: _rounded(v) if isinstance(v, float) else v for k, v in record.items()}
                for sid, record in subject_metrics.items()
            },
        },
        "row_vs_entity_diagnostic": diagnostic,
    }
    plot_data = {
        "before_reliability": reliability(softmax(logits["test"]), split["test"][1], 10),
        "after_reliability": reliability(softmax(logits["test"] / temperature), split["test"][1], 10),
    }
    return report, plot_data


def save_figures(report: dict, plot_data: dict, output_dir: str | Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update({"svg.hashsalt": "wwl-entity-calibration-v1", "font.size": 9})
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created = []

    fig, ax = plt.subplots(figsize=(6.2, 4.2), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color="0.35", linestyle="--", label="ideal")
    for name, color, marker in (("before_reliability", "#d95f02", "o"), ("after_reliability", "#1b9e77", "s")):
        rows = [r for r in plot_data[name] if r["count"]]
        label = "before T" if name.startswith("before") else "after T"
        ax.plot([r["mean_confidence"] for r in rows], [r["accuracy"] for r in rows], marker=marker, color=color, label=label)
    ax.set(xlabel="mean top-class confidence", ylabel="empirical accuracy", xlim=(0.35, 1.01), ylim=(0.35, 1.01), title="Frozen new-subject test reliability (10 equal-width bins)")
    ax.grid(alpha=0.25); ax.legend()
    path = output_dir / "har-reliability.svg"; fig.savefig(path, metadata={"Date": None}); plt.close(fig); created.append(path)

    diag = report["row_vs_entity_diagnostic"]
    labels = ["entity holdout\n(new subjects)", "row holdout\n(same subjects)"]
    accuracy = [diag["entity_holdout"]["accuracy"], diag["row_holdout"]["accuracy"]]
    fig, ax = plt.subplots(figsize=(6.2, 3.8), constrained_layout=True)
    bars = ax.bar(labels, accuracy, color=["#7570b3", "#e7298a"], width=0.55)
    ax.set(
        ylim=(0.75, 1.0),
        ylabel="accuracy",
        title="Diagnostic pool only: protocols answer different questions\ncal/test excluded; neither score feeds the formal model",
    )
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in accuracy], padding=3)
    ax.grid(axis="y", alpha=0.25)
    path = output_dir / "har-row-vs-entity.svg"; fig.savefig(path, metadata={"Date": None}); plt.close(fig); created.append(path)

    by_subject = report["test"]["by_subject_after_temperature"]
    ids = sorted(by_subject, key=int)
    acc = [by_subject[s]["accuracy"] for s in ids]
    nll = [by_subject[s]["nll"] for s in ids]
    fig, ax1 = plt.subplots(figsize=(7.6, 4.0), constrained_layout=True)
    positions = np.arange(len(ids))
    bars = ax1.bar(positions - 0.18, acc, width=0.36, color="#66c2a5", label="accuracy")
    ax1.set(xticks=positions, xticklabels=[f"subject {s}" for s in ids], ylim=(0.7, 1.0), ylabel="accuracy")
    ax2 = ax1.twinx(); ax2.bar(positions + 0.18, nll, width=0.36, color="#fc8d62", label="NLL"); ax2.set(ylabel="NLL", ylim=(0, max(nll) * 1.25))
    ax1.set_title("Frozen test slices: calibration average can hide subject variation")
    ax1.grid(axis="y", alpha=0.2)
    handles = [bars, ax2.patches[0]]; ax1.legend(handles, ["accuracy", "NLL"], loc="upper center", ncol=2)
    path = output_dir / "har-subject-slices.svg"; fig.savefig(path, metadata={"Date": None}); plt.close(fig); created.append(path)
    return created


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="exact UCI dataset 240 outer ZIP")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--seed",
        type=int,
        default=20260920,
        help="optimizer and row-diagnostic seed; the frozen subject split never changes",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report, plot_data = run_experiment(args.archive, seed=args.seed)
    paths = save_figures(report, plot_data, args.output_dir)
    result_path = args.output_dir / "har-results.json"
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for path in [*paths, result_path]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
