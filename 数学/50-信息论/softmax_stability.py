"""用 Python 标准库演示稳定 Softmax、LogSumExp、交叉熵与 KL。"""

from math import exp, fsum, isclose, isfinite, log


def naive_softmax(logits: list[float]) -> list[float]:
    """教学用朴素实现：大 logit 会令 exp 溢出，不要用于实际计算。"""
    weights = [exp(value) for value in logits]
    total = fsum(weights)
    return [weight / total for weight in weights]


def logsumexp(logits: list[float]) -> float:
    """稳定计算 log(sum(exp(logits)))。"""
    if not logits:
        raise ValueError("logits 不能为空")
    if any(not isfinite(value) for value in logits):
        raise ValueError("logits 必须只包含有限实数")
    maximum = max(logits)
    return maximum + log(fsum(exp(value - maximum) for value in logits))


def centered_logits(logits: list[float], temperature: float = 1.0) -> list[float]:
    """有限 binary64 输入；拒绝不可表示的中心化/缩放，不支持无穷掩码。"""
    if not logits or any(not isfinite(value) for value in logits):
        raise ValueError("logits 必须非空且仅含有限实数")
    if not isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature 必须是大于 0 的有限实数")
    maximum = max(logits)
    shifted = [(value - maximum) / temperature for value in logits]
    if any(not isfinite(value) for value in shifted):
        raise ValueError("中心化或温度缩放超出有限浮点支持域")
    return shifted


def log_softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    """在中心化坐标中计算，不把巨大公共偏移加回再相消。"""
    shifted = centered_logits(logits, temperature)
    normalizer = log(fsum(exp(value) for value in shifted))
    return [value - normalizer for value in shifted]


def stable_softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    """先中心化再缩放温度；exp 下溢为零允许，最大项仍为 1。"""
    shifted = centered_logits(logits, temperature)
    weights = [exp(value) for value in shifted]
    total = fsum(weights)
    return [value / total for value in weights]


def cross_entropy_from_logits(logits: list[float], target: int) -> float:
    """one-hot 交叉熵直接取中心化 log-prob，避免大数相消。"""
    if type(target) is not int or not 0 <= target < len(logits):
        raise IndexError("target 超出 logits 范围")
    return -log_softmax(logits)[target]


def validate_distribution(probabilities: list[float], name: str) -> None:
    """Validate a finite, non-negative probability vector with unit mass."""
    if not probabilities:
        raise ValueError(f"{name} 不能为空")
    if any(not isfinite(value) for value in probabilities):
        raise ValueError(f"{name} 必须只包含有限值")
    if any(value < 0.0 for value in probabilities):
        raise ValueError(f"{name} 不能包含负概率")
    if not isclose(fsum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{name} 的概率总和必须为 1")


def entropy(probabilities: list[float]) -> float:
    """H(P)，使用自然对数；0 log 0 按极限记为 0。"""
    validate_distribution(probabilities, "P")
    return -fsum(p * log(p) for p in probabilities if p > 0)


def cross_entropy(p: list[float], q: list[float]) -> float:
    """H(P, Q)：按 P 加权、对 Q 取对数。"""
    if len(p) != len(q):
        raise ValueError("P 与 Q 的长度必须相同")
    validate_distribution(p, "P")
    validate_distribution(q, "Q")
    if any(p_i > 0 and q_i == 0 for p_i, q_i in zip(p, q)):
        return float("inf")
    return -fsum(p_i * log(q_i) for p_i, q_i in zip(p, q) if p_i > 0)


def kl_divergence(p: list[float], q: list[float]) -> float:
    """D_KL(P || Q)：方向是第一个参数 P 到第二个参数 Q。"""
    if len(p) != len(q):
        raise ValueError("P 与 Q 的长度必须相同")
    validate_distribution(p, "P")
    validate_distribution(q, "Q")
    if any(p_i > 0 and q_i == 0 for p_i, q_i in zip(p, q)):
        return float("inf")
    return fsum(
        p_i * (log(p_i) - log(q_i))
        for p_i, q_i in zip(p, q)
        if p_i > 0
    )


def format_values(values: list[float]) -> str:
    return "[" + ", ".join(f"{value:.6f}" for value in values) + "]"


def main() -> None:
    ordinary_logits = [2.0, 1.0, 0.0]
    large_logits = [1002.0, 1001.0, 1000.0]

    print("1) 普通 logits：朴素与稳定 Softmax 应一致")
    naive = naive_softmax(ordinary_logits)
    stable = stable_softmax(ordinary_logits)
    print("   朴素：", format_values(naive))
    print("   稳定：", format_values(stable))
    assert all(isclose(a, b, rel_tol=1e-12) for a, b in zip(naive, stable))
    assert isclose(fsum(stable), 1.0, rel_tol=1e-12)

    print("\n2) 大 logits：朴素实现溢出，稳定实现仍有效")
    try:
        naive_softmax(large_logits)
    except OverflowError as error:
        print("   预期中的朴素实现失败：", type(error).__name__)
    else:
        raise AssertionError("当前平台未触发预期的 exp 溢出")
    stable_large = stable_softmax(large_logits)
    print("   稳定：", format_values(stable_large))
    assert all(isclose(a, b, rel_tol=1e-12) for a, b in zip(stable, stable_large))

    print("\n3) 平移不变：所有 logits 加 12345 后概率不变")
    shifted = stable_softmax([value + 12345.0 for value in ordinary_logits])
    print("   平移后：", format_values(shifted))
    assert all(isclose(a, b, rel_tol=1e-12) for a, b in zip(stable, shifted))

    print("\n4) 稳定 log-softmax 与 one-hot 交叉熵")
    target = 2
    log_probs = log_softmax(large_logits)
    loss_from_logits = cross_entropy_from_logits(large_logits, target)
    loss_from_log_prob = -log_probs[target]
    print("   log-prob：", format_values(log_probs))
    print(f"   target={target} 的损失：{loss_from_logits:.6f}")
    assert isclose(loss_from_logits, loss_from_log_prob, rel_tol=1e-12)

    print("\n5) H(P,Q) = H(P) + D_KL(P || Q)")
    p = [0.70, 0.20, 0.10]
    q = stable_softmax([1.5, 0.5, -0.5])
    h_p = entropy(p)
    h_pq = cross_entropy(p, q)
    kl_pq = kl_divergence(p, q)
    print(f"   H(P)={h_p:.6f}, H(P,Q)={h_pq:.6f}, KL(P||Q)={kl_pq:.6f}")
    assert isclose(h_pq, h_p + kl_pq, rel_tol=1e-12, abs_tol=1e-12)

    print("\n6) 温度：低温更尖锐，高温更平坦")
    for temperature in (0.5, 1.0, 2.0):
        probabilities = stable_softmax(ordinary_logits, temperature)
        print(
            f"   T={temperature:.1f}: {format_values(probabilities)}, "
            f"H={entropy(probabilities):.6f}"
        )

    print("\n7) KL 方向审计：基线 P 到修改后 Q 不等于反方向")
    baseline = [0.80, 0.15, 0.05]
    modified = [0.60, 0.25, 0.15]
    forward = kl_divergence(baseline, modified)
    reverse = kl_divergence(modified, baseline)
    print(f"   KL(base||modified)={forward:.6f}")
    print(f"   KL(modified||base)={reverse:.6f}")
    assert not isclose(forward, reverse, rel_tol=1e-6)

    print("\n8) 非法分布输入必须被拒绝")
    invalid_distributions = ([0.60, 0.50], [1.10, -0.10])
    for invalid in invalid_distributions:
        try:
            entropy(invalid)
        except ValueError as error:
            print(f"   拒绝 {invalid}: {error}")
        else:
            raise AssertionError(f"非法分布未被拒绝：{invalid}")

    print("\n9) 非有限 logits 与温度必须被拒绝")
    invalid_calls = (
        ("无穷 logit", lambda: stable_softmax([0.0, float("inf")])),
        ("NaN logit", lambda: stable_softmax([0.0, float("nan")])),
        ("无穷温度", lambda: stable_softmax([2.0, 1.0], float("inf"))),
    )
    for name, call in invalid_calls:
        try:
            call()
        except ValueError as error:
            print(f"   拒绝{name}: {error}")
        else:
            raise AssertionError(f"非法输入未被拒绝：{name}")

    print("\n全部断言通过。")


if __name__ == "__main__":
    main()
