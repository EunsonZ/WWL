"""可复现的 LLM 采样与评测数学小实验，仅使用 Python 标准库。"""

from math import exp, isfinite, log, sqrt
from random import Random
from statistics import mean


TOKENS = ["A", "B", "C", "D"]


def softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    """用减最大值技巧计算带温度的稳定 softmax。"""
    if not logits:
        raise ValueError("logits 不能为空")
    if not isfinite(temperature) or temperature <= 0:
        raise ValueError("数学上的 temperature 必须是有限正数")
    if any(not isfinite(value) for value in logits):
        raise ValueError("logits 必须全是有限数")
    maximum = max(logits)
    weights = [exp((value - maximum) / temperature) for value in logits]
    total = sum(weights)
    return [weight / total for weight in weights]


def renormalize(probabilities: list[float], kept: set[int]) -> list[float]:
    """把 kept 外的概率置零，再让剩余概率和回到 1。"""
    mass = sum(probabilities[index] for index in kept)
    if mass <= 0:
        raise ValueError("保留集合的总概率必须大于 0")
    return [
        probability / mass if index in kept else 0.0
        for index, probability in enumerate(probabilities)
    ]


def truncate(
    probabilities: list[float],
    top_k: int | None = None,
    top_p: float | None = None,
) -> list[float]:
    """明确采用 Top-k 后 Top-p 的顺序，并在每一步重新归一化。"""
    if not probabilities or any(
        not isfinite(value) or value < 0 for value in probabilities
    ):
        raise ValueError("probabilities 必须是非空、有限的非负列表")
    if abs(sum(probabilities) - 1.0) > 1e-9:
        raise ValueError("probabilities 的总和必须为 1")

    current = list(probabilities)
    order = sorted(range(len(current)), key=lambda i: (-current[i], i))

    if top_k is not None:
        if not 1 <= top_k <= len(current):
            raise ValueError("top_k 必须在 1 到词表大小之间")
        current = renormalize(current, set(order[:top_k]))

    if top_p is not None:
        if not 0 < top_p <= 1:
            raise ValueError("top_p 必须在 (0, 1] 内")
        order = sorted(range(len(current)), key=lambda i: (-current[i], i))
        kept: set[int] = set()
        cumulative = 0.0
        for index in order:
            if current[index] == 0:
                continue
            kept.add(index)
            cumulative += current[index]
            if cumulative >= top_p:
                break
        current = renormalize(current, kept)

    return current


def sample_counts(
    probabilities: list[float], draws: int, seed: int
) -> dict[str, int]:
    """按给定分布抽样；固定 seed 只用于复现实验。"""
    if len(probabilities) != len(TOKENS):
        raise ValueError("probabilities 必须与 TOKENS 一一对应")
    if draws <= 0:
        raise ValueError("draws 必须大于 0")
    if any(not isfinite(value) or value < 0 for value in probabilities) or abs(
        sum(probabilities) - 1.0
    ) > 1e-9:
        raise ValueError("probabilities 必须是和为 1、元素有限的非负分布")
    rng = Random(seed)
    samples = rng.choices(TOKENS, weights=probabilities, k=draws)
    return {token: samples.count(token) for token in TOKENS}


def nll_and_perplexity(target_probabilities: list[float]) -> tuple[float, float]:
    """计算序列 NLL 与按 token 归一化的 perplexity。"""
    if not target_probabilities or any(
        not isfinite(probability) or probability <= 0 or probability > 1
        for probability in target_probabilities
    ):
        raise ValueError("每个目标 token 概率必须在 (0, 1] 内")
    nll = -sum(log(probability) for probability in target_probabilities)
    perplexity = exp(nll / len(target_probabilities))
    return nll, perplexity


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """返回二项比例的 Wilson 分数区间。"""
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("需满足 total > 0 且 0 <= successes <= total")
    if not isfinite(z) or z <= 0:
        raise ValueError("z 必须是有限正数")
    estimate = successes / total
    denominator = 1 + z * z / total
    center = (estimate + z * z / (2 * total)) / denominator
    radius = (
        z
        * sqrt(estimate * (1 - estimate) / total + z * z / (4 * total * total))
        / denominator
    )
    return center - radius, center + radius


def linear_quantile(sorted_values: list[float], probability: float) -> float:
    """Return an explicitly linearly interpolated quantile of sorted values."""
    if not sorted_values:
        raise ValueError("分位数输入不能为空")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("分位点必须在 [0, 1] 内")
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def paired_bootstrap_difference(
    scores_a: list[int],
    scores_b: list[int],
    repetitions: int = 5000,
    seed: int = 20260901,
) -> tuple[float, float, float]:
    """按题目对重采样，估计平均配对差的 percentile 区间。"""
    if len(scores_a) != len(scores_b) or not scores_a:
        raise ValueError("两模型必须在同一批非空题目上评测")
    if any(value not in (0, 1) for value in scores_a + scores_b):
        raise ValueError("本实验只接受 0/1 分数")
    if repetitions <= 0:
        raise ValueError("repetitions 必须大于 0")

    differences = [a - b for a, b in zip(scores_a, scores_b)]
    rng = Random(seed)
    boot_means = []
    for _ in range(repetitions):
        resample = [rng.choice(differences) for _ in differences]
        boot_means.append(mean(resample))
    boot_means.sort()
    lower = linear_quantile(boot_means, 0.025)
    upper = linear_quantile(boot_means, 0.975)
    return mean(differences), lower, upper


def show_distribution(label: str, probabilities: list[float]) -> None:
    assert abs(sum(probabilities) - 1.0) <= 1e-12
    rendered = ", ".join(
        f"{token}={probability:.4f}"
        for token, probability in zip(TOKENS, probabilities)
    )
    counts = sample_counts(probabilities, draws=20_000, seed=7)
    assert sum(counts.values()) == 20_000
    frequencies = ", ".join(
        f"{token}={counts[token] / 20_000:.4f}" for token in TOKENS
    )
    print(f"{label} 理论解码概率: {rendered}")
    print(f"{label} 经验采样频率: {frequencies}")


def main() -> None:
    logits = [log(0.50), log(0.30), log(0.15), log(0.05)]
    original = softmax(logits, temperature=1.0)
    cold_top_k = truncate(softmax(logits, temperature=0.7), top_k=2)
    nucleus = truncate(original, top_p=0.81)

    print("一、概率事实与经验采样频率")
    show_distribution("原始", original)
    show_distribution("低温后 Top-k=2", cold_top_k)
    show_distribution("Top-p=0.81", nucleus)

    print("\n二、负对数似然与困惑度")
    nll, perplexity = nll_and_perplexity([0.50, 0.25])
    print(f"NLL={nll:.4f}, 每 token perplexity={perplexity:.4f}")

    print("\n三、经验准确率与区间")
    accuracy = 160 / 200
    lower, upper = wilson_interval(160, 200)
    print(f"经验准确率={accuracy:.3f}, Wilson 95% 区间=[{lower:.3f}, {upper:.3f}]")

    print("\n四、同题配对模型差异")
    scores_a = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0]
    scores_b = [1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0]
    difference, diff_lower, diff_upper = paired_bootstrap_difference(scores_a, scores_b)
    print(
        f"A-B 经验准确率差={difference:+.3f}, "
        f"配对 bootstrap 95% 区间=[{diff_lower:+.3f}, {diff_upper:+.3f}]"
    )
    print("区间较宽是在提醒：20 道题不足以支撑精细排名。")


if __name__ == "__main__":
    main()
