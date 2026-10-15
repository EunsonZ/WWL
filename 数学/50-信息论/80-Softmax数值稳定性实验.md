---
type: lab
domain: mathematics
status: ready
difficulty: 入门
stage: 1
estimated_minutes: 35
topics:
  - softmax
  - logsumexp
  - cross-entropy
  - kl-divergence
  - temperature
  - numerical-stability
tags:
  - mathematics/information-theory
  - mathematics/lab
---

# Softmax 数值稳定性实验

## 实验目标

你将只用 Python 标准库观察并验证：

1. 数学上有限的 $e^{1002}$ 在双精度浮点中会溢出；
2. Softmax 先减最大 logit 后仍得到正确概率；
3. 所有 logits 加同一常数不会改变 Softmax；
4. 稳定交叉熵等于 $\operatorname{LSE}(z)-z_y$；
5. $H(P,Q)=H(P)+D_{\mathrm{KL}}(P\Vert Q)$；
6. 温度改变分布尖锐程度；
7. $D_{\mathrm{KL}}(P\Vert Q)$ 与反方向一般不同；
8. 非空、有限、非负且总和为 1 是熵、交叉熵与 KL 的输入契约。
9. NaN、无穷 logit 和无穷温度不属于本课定义的有限实数输入，应明确拒绝。

对应推导：

- [[数学/50-信息论/01-熵交叉熵KL散度与互信息|熵、交叉熵、KL 散度与互信息]]
- [[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]

## 环境与安全边界

- 需要 Python 3.10 或更高版本；
- 不需要安装 NumPy、PyTorch 或任何第三方包；
- 脚本只计算并打印结果，不访问网络、不读取或修改其他文件；
- 伴随文件 `softmax_stability.py` 是规范源，下面带 `code-sync` 标记的代码块必须与它逐字同步。

## 运行方法

在 Vault 根目录执行：

```bash
python3 -B "数学/50-信息论/softmax_stability.py"
```

若环境使用 `python` 指向 Python 3，也可将 `python3` 替换为 `python`。`-B` 阻止生成 `__pycache__`。

## 先预测，再运行

运行前写下你的预测：

1. `[2, 1, 0]` 和 `[1002, 1001, 1000]` 的 Softmax 相同吗？为什么？
2. `T=0.5` 与 `T=2.0` 哪一个分布熵更大？
3. `KL(base || modified)` 会与 `KL(modified || base)` 相同吗？
4. 朴素实现失败时，稳定实现为什么仍能继续？

再预测 `[1e16,1e16]`：数学上应为 `[0.5,0.5]`，真实类别交叉熵为 `log(2)`。若先形成 `LSE(z)` 再减原 logit，小修正会在大公共偏移中丢失。修复后的源码始终在中心化坐标中求概率、log-prob 和交叉熵。有限正温度、非空有限 binary64 输入是必要条件；中心化或缩放超范围也会明确拒绝，不支持无穷掩码。

## 伴随 Python

<!-- code-sync: ./softmax_stability.py -->
```python
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
```

## 读懂输出

你应看到九组结果，最后一行是：

```text
全部断言通过。
```

关键观察：

- 普通 logits 的朴素与稳定实现一致；
- 大 logits 的朴素实现出现预期 `OverflowError`，稳定实现仍返回有限概率；
- `[2,1,0]` 与 `[1002,1001,1000]` 的稳定概率一致，因为两者只差常数；
- `target=2` 的稳定交叉熵等于对应负 log-prob；
- `T=0.5` 的熵低于 `T=1`，`T=2` 的熵高于 `T=1`；
- `KL(base||modified)` 与反方向不同；
- 负概率和总和不为 1 的输入会被明确拒绝，而不是静默产生无意义结果。
- 非有限 logits 和温度也会被拒绝；“减最大值”只稳定有限实数的指数归一化，不负责为 NaN 或 infinity 猜测业务语义。

## 修改练习

### 练习 1：更极端的负数

把 `large_logits` 改成 `[-1000.0, -1001.0, -1002.0]`，预测朴素实现会发生什么。稳定实现是否仍与 `[2,1,0]` 相同？

### 练习 2：支撑不匹配

在 `main()` 中加入：

```python
print(kl_divergence([0.5, 0.5], [1.0, 0.0]))
```

解释为什么结果是 `inf`，并指出是哪个事件满足 $P(i)>0$ 且 $Q(i)=0$。

### 练习 3：方向交换

自行设计两组概率，使 `KL(P||Q)` 与 `KL(Q||P)` 差异更明显。每次都标明谁是基线、谁是修改后模型。

### 练习 4：模拟蒸馏

令教师 $P=[0.7,0.2,0.1]$，设计两组学生分布 $Q_1,Q_2$，计算交叉熵和 KL，验证更接近教师的学生在两项指标上都更小。

## 成功标准

- 原始脚本运行到“全部断言通过”；
- 能解释朴素实现失败不是公式错误，而是有限浮点范围问题；
- 能口头推导减最大值不改变 Softmax；
- 能解释为何交叉熵、KL 函数的参数顺序有数学含义；
- 完成至少两个修改练习，并能预测结果后再运行验证。

## 恢复方法

实验无需修改原文件即可完成。若你编辑了伴随脚本且想恢复，撤销自己对 `数学/50-信息论/softmax_stability.py` 的修改，确保它再次与本页 `code-sync` 代码块逐字一致。不要用会清理整个工作树的命令恢复单个实验。

## 导航

- 上一站：[[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]
- 返回：[[数学/50-信息论/00-信息论-MOC|信息论 MOC]]
- 相关：[[数学/50-信息论/01-熵交叉熵KL散度与互信息|熵、交叉熵、KL 散度与互信息]]
- 相关：[[数学/60-数值计算与量化/00-数值计算与量化-MOC|数值计算与量化 MOC]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/16-数学分析/10-反常积分与含参积分的极限交换|反常积分与含参积分的极限交换]]；[[数学/16-数学分析/15-收敛定理与Fubini-Tonelli|收敛定理与Fubini-Tonelli]]；[[数学/15-微积分/03-中值定理与导数应用单调凸性和优化|中值定理与导数应用单调凸性和优化]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。


## 双来源补充反例

从 WorkWithLLM 的既有测试提取并适配了 [[数学/50-信息论/test_softmax_stability_contracts.py|test_softmax_stability_contracts.py]]：3 个补充反例，覆盖巨大等值 logits、梯度与平移、无效及极端输入。 原实现保持不变，来源与运行结果见 [[Logs/2026-09-08_双来源知识增量导入/artifacts/imported-tests.json|13 个反例映射与验证分层]]。

从 WWL 根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "数学/50-信息论/test_softmax_stability_contracts.py"
```
