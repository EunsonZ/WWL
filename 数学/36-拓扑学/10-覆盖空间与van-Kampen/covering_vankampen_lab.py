"""Finite checks for covering endpoints and group-word examples.

These functions verify particular symbolic calculations.  Finite computation
does not prove path lifting, van Kampen's theorem, or a group presentation.
"""
from __future__ import annotations

import argparse


INVERSE = {"a": "A", "A": "a", "b": "B", "B": "b", "c": "C", "C": "c"}


def _validate_word(word: str) -> None:
    if not isinstance(word, str):
        raise TypeError("word must be a string")
    invalid = sorted(set(word) - set(INVERSE))
    if invalid:
        raise ValueError(f"invalid letters: {''.join(invalid)}")


def reduce_free_word(word: str) -> str:
    """Cancel adjacent inverse pairs in a word on a,b,c."""
    _validate_word(word)
    stack: list[str] = []
    for letter in word:
        if stack and INVERSE[letter] == stack[-1]:
            stack.pop()
        else:
            stack.append(letter)
    return "".join(stack)


def exponent_sums(word: str) -> tuple[int, int, int]:
    """Return exponent sums of a,b,c, as used after abelianization."""
    _validate_word(word)
    return (
        word.count("a") - word.count("A"),
        word.count("b") - word.count("B"),
        word.count("c") - word.count("C"),
    )


def circle_lift_endpoint(winding: int, sheets: int, start: int = 0) -> tuple[int, bool]:
    """Endpoint sheet and closedness for z -> z**sheets."""
    values = (winding, sheets, start)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise TypeError("winding, sheets, and start must be integers")
    if sheets <= 0:
        raise ValueError("sheets must be positive")
    endpoint = (start + winding) % sheets
    return endpoint, endpoint == start % sheets


def torus_lift_endpoint(word: str) -> tuple[int, int]:
    """Integer-lattice endpoint of a torus word lifted from (0,0)."""
    a_sum, b_sum, _ = exponent_sums(word)
    if "c" in word or "C" in word:
        raise ValueError("torus words may only use a,A,b,B")
    return a_sum, b_sum


def rp2_class(exponent: int) -> int:
    """Class of a**exponent in <a | a**2=1>."""
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise TypeError("exponent must be an integer")
    return exponent % 2


def report(word: str, winding: int, sheets: int) -> None:
    endpoint, closed = circle_lift_endpoint(winding, sheets)
    print(f"free reduction: {word!r} -> {reduce_free_word(word)!r}")
    print(f"exponent sums: {exponent_sums(word)}")
    print(f"{sheets}-sheet lift of winding {winding}: endpoint={endpoint}, closed={closed}")
    print(f"torus commutator endpoint: {torus_lift_endpoint('abAB')}")
    print(f"RP2 classes of a^0..a^5: {tuple(rp2_class(k) for k in range(6))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", default="abBAcC")
    parser.add_argument("--winding", type=int, default=7)
    parser.add_argument("--sheets", type=int, default=5)
    arguments = parser.parse_args()
    report(arguments.word, arguments.winding, arguments.sheets)
