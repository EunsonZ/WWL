"""Enumerate fixed finite populations; all outputs are teaching likelihoods."""

from fractions import Fraction
from itertools import combinations, permutations
from math import comb


def count_probability(bad_count, sample_size, observed_count):
    """Independent enumeration oracle over unordered subsets of ten labels."""
    samples = list(combinations(range(10), sample_size))
    matches = sum(
        sum(label < bad_count for label in sample) == observed_count
        for sample in samples
    )
    return Fraction(matches, len(samples))


def hypergeometric(bad_count, sample_size, observed_count):
    lower = max(0, sample_size - (10 - bad_count))
    upper = min(sample_size, bad_count)
    if not lower <= observed_count <= upper:
        return Fraction(0)
    return Fraction(
        comb(bad_count, observed_count)
        * comb(10 - bad_count, sample_size - observed_count),
        comb(10, sample_size),
    )


def main():
    # Check every K and sample size, including the empty and whole samples.
    for bad_count in range(11):
        for sample_size in range(11):
            probabilities = [
                count_probability(bad_count, sample_size, x)
                for x in range(sample_size + 1)
            ]
            assert sum(probabilities) == 1
            for x, probability in enumerate(probabilities):
                assert probability == hypergeometric(bad_count, sample_size, x)

    print("K\tone_bad_n1\texactly_one_bad_n2\tbad_then_good\tat_least_one_bad_n2")
    ordered_pairs = list(permutations(range(10), 2))
    assert len(ordered_pairs) == 90
    for bad_count in range(11):
        one_bad = count_probability(bad_count, 1, 1)
        exactly_one = count_probability(bad_count, 2, 1)
        ordered = Fraction(
            sum(a < bad_count and b >= bad_count for a, b in ordered_pairs), 90
        )
        at_least_one = 1 - count_probability(bad_count, 2, 0)
        assert one_bad == Fraction(bad_count, 10)
        assert exactly_one == Fraction(bad_count * (10 - bad_count), 45)
        assert ordered * 2 == exactly_one
        assert at_least_one == 1 - Fraction(comb(10 - bad_count, 2), 45)
        if bad_count in (1, 5, 10):
            expected = {
                1: (Fraction(1, 10), Fraction(1, 5), Fraction(1, 5)),
                5: (Fraction(1, 2), Fraction(5, 9), Fraction(7, 9)),
                10: (Fraction(1), Fraction(0), Fraction(1)),
            }[bad_count]
            assert (one_bad, exactly_one, at_least_one) == expected
        print(f"{bad_count}\t{one_bad}\t{exactly_one}\t{ordered}\t{at_least_one}")
    assert sum(Fraction(k, 10) for k in range(11)) == Fraction(11, 2)
    print("PASS: exact enumeration agrees for all K=0..10 and n=0..10.")


if __name__ == "__main__":
    main()
