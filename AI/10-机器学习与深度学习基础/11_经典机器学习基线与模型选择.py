from __future__ import annotations

import math


def make_samples(start: int, stop: int) -> list[tuple[list[float], int]]:
    """生成可重复的合成二分类数据；不能代表任何真实人群。"""
    samples: list[tuple[list[float], int]] = []
    for i in range(start, stop):
        x0 = ((i * 37) % 101 - 50) / 25.0
        x1 = ((i * 17) % 97 - 48) / 24.0
        noise = ((i * 13) % 11 - 5) / 20.0
        label = int(0.7 * x0 + 1.2 * x1 + noise > 0.0)
        samples.append(([x0, x1], label))
    return samples


def fit_scaler(samples: list[tuple[list[float], int]]) -> tuple[list[float], list[float]]:
    columns = list(zip(*(features for features, _ in samples)))
    means = [sum(column) / len(column) for column in columns]
    scales = [math.sqrt(sum((value - mean) ** 2 for value in column) / len(column))
              for column, mean in zip(columns, means)]
    assert all(scale > 0.0 for scale in scales)
    return means, scales


def scale(features: list[float], means: list[float], scales: list[float]) -> list[float]:
    return [(value - mean) / std for value, mean, std in zip(features, means, scales)]


def sigmoid(score: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, score))))


def fit_logistic(train: list[tuple[list[float], int]], means: list[float], scales: list[float]) -> tuple[list[float], float]:
    weights = [0.0, 0.0]
    bias = 0.0
    learning_rate = 0.18
    for _ in range(900):
        gradient = [0.0, 0.0]
        bias_gradient = 0.0
        for features, label in train:
            scaled = scale(features, means, scales)
            error = sigmoid(sum(weight * value for weight, value in zip(weights, scaled)) + bias) - label
            gradient = [old + error * value for old, value in zip(gradient, scaled)]
            bias_gradient += error
        weights = [weight - learning_rate * value / len(train)
                   for weight, value in zip(weights, gradient)]
        bias -= learning_rate * bias_gradient / len(train)
    return weights, bias


def rule_predict(features: list[float]) -> int:
    return int(features[0] > 0.0)


def logistic_predict(features: list[float], weights: list[float], bias: float,
                     means: list[float], scales: list[float]) -> int:
    scaled = scale(features, means, scales)
    return int(sigmoid(sum(weight * value for weight, value in zip(weights, scaled)) + bias) >= 0.5)


def knn_predict(features: list[float], train: list[tuple[list[float], int]],
                means: list[float], scales: list[float], k: int = 7) -> int:
    point = scale(features, means, scales)
    neighbors = sorted(
        ((sum((left - right) ** 2 for left, right in zip(point, scale(other, means, scales))), label)
         for other, label in train),
        key=lambda item: item[0],
    )[:k]
    return int(sum(label for _, label in neighbors) * 2 >= k)


def accuracy(predict, samples: list[tuple[list[float], int]]) -> float:
    return sum(predict(features) == label for features, label in samples) / len(samples)


def main() -> None:
    train = make_samples(0, 160)
    validation = make_samples(160, 240)
    means, scales = fit_scaler(train)  # 不能用 validation 拟合这些统计量。
    weights, bias = fit_logistic(train, means, scales)

    rule_score = accuracy(rule_predict, validation)
    logistic_score = accuracy(lambda x: logistic_predict(x, weights, bias, means, scales), validation)
    knn_score = accuracy(lambda x: knn_predict(x, train, means, scales), validation)

    print(f"validation accuracy: rule={rule_score:.3f}, logistic={logistic_score:.3f}, knn={knn_score:.3f}")
    assert len(train) == 160 and len(validation) == 80
    assert logistic_score > rule_score + 0.15
    assert knn_score > rule_score + 0.10
    assert logistic_score >= 0.90 and knn_score >= 0.85
    print("检查通过：候选模型在这份合成验证集上胜过简单规则。")
    print("边界：这不证明它们在真实数据、未来时间窗或任何人群上更好。")


if __name__ == "__main__":
    main()
