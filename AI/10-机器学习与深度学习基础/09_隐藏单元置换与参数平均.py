"""Fixed-input, standard-library demonstration; prints JSON, writes no files.

Row-vector convention: W1 has shape (1, 2), W2 has shape (2, 1).
No training or randomness. Closed-form expected results are stated in the lesson;
a separate reviewer should compare these with this implementation's JSON output.
"""

from fractions import Fraction
import json


INPUTS = (-2, 0, 1)
W1 = ((1, -1),)
W2 = ((1,), (-1,))
SWAP = ((0, 1), (1, 0))  # Its inverse is itself.


def matmul(a, b):
    return tuple(
        tuple(sum(a[i][t] * b[t][j] for t in range(len(b)))
              for j in range(len(b[0])))
        for i in range(len(a))
    )


def average(a, b):
    return tuple(tuple(Fraction(x + y, 2) for x, y in zip(ar, br))
                 for ar, br in zip(a, b))


def network(x, w1, w2):
    z = matmul(((x,),), w1)
    hidden = tuple(tuple(max(0, v) for v in row) for row in z)
    return hidden, matmul(hidden, w2)[0][0]


def encode(value):
    """Keep exact fractions readable; this example's outputs are all integers."""
    if isinstance(value, Fraction):
        return int(value) if value.denominator == 1 else str(value)
    raise TypeError(type(value).__name__)


def main():
    w1_swapped = matmul(W1, SWAP)
    w2_swapped = matmul(SWAP, W2)
    w1_mean = average(W1, w1_swapped)
    w2_mean = average(W2, w2_swapped)
    w1_aligned = matmul(w1_swapped, SWAP)
    w2_aligned = matmul(SWAP, w2_swapped)
    rows = []
    for x in INPUTS:
        h, original = network(x, W1, W2)
        hp, permuted = network(x, w1_swapped, w2_swapped)
        _, parameter_mean = network(x, w1_mean, w2_mean)
        _, aligned_mean = network(
            x, average(W1, w1_aligned), average(W2, w2_aligned))
        _, only_first = network(x, w1_swapped, W2)
        _, only_first_parameter_mean = network(x, w1_mean, W2)
        rows.append({
            "x": x,
            "hidden_original": h[0],
            "hidden_permuted": hp[0],
            "original": original,
            "permuted": permuted,
            "parameter_mean": parameter_mean,
            "output_mean": Fraction(original + permuted, 2),
            "aligned_parameter_mean": aligned_mean,
            "only_first_swapped": only_first,
            "only_first_parameter_mean": only_first_parameter_mean,
            "only_first_output_mean": Fraction(original + only_first, 2),
            "scalar_relu": max(0, x),
            "scalar_post_activation_recode": (-max(0, x)) * (-1),
            "scalar_wrong_pre_activation_change": -max(0, -x),
        })
    print(json.dumps({"rows": rows}, default=encode, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
