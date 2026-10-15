"""Fixed exact course experiments; execute separately from static validation."""
import itertools
import json
from fractions import Fraction
from integer_smith import (matrix, identity, multiply, determinant, smith,
                           kernel_image, homology)


def expect_error(kind, action):
    try:
        action()
    except kind:
        return
    raise AssertionError("expected error was not raised")


def pack_matrix(value):
    return {"shape": value.shape, "rows": value.rows}


def pack_smith(value):
    return {"U": pack_matrix(value.U), "D": pack_matrix(value.D),
            "V": pack_matrix(value.V), "rank": value.rank, "invariants": value.invariants}


def pack_homology(name, a, b, value):
    return {"name": name, "A": pack_matrix(a), "B": pack_matrix(b),
            "K": pack_matrix(value["K"]), "C": pack_matrix(value["C"]),
            "smith_A": pack_smith(value["smith_A"]), "smith_C": pack_smith(value["smith_C"]),
            "torsion": value["torsion"], "free_rank": value["free_rank"],
            "representatives": pack_matrix(value["representatives"])}


def smith_examples():
    cases = [
        ("nontrivial_UV", matrix([[4, 6], [2, 6]]), (2, 6), 0),
        ("chain_repair", matrix([[6, 0], [0, 10]]), (2, 30), 0),
        ("rectangular", matrix([[2, 4, 0], [0, 0, 0]]), (2,), 1),
        ("signed", matrix([[-4, 6], [2, -6]]), (2, 6), 0),
        ("zero", matrix([[0, 0], [0, 0]]), (), 2),
        ("zero_rows", matrix([], 3), (), 0),
        ("zero_cols", matrix([[], []], 0), (), 2),
    ]
    records = []
    for name, b, expected, free in cases:
        result = smith(b)
        assert result.invariants == expected
        assert b.nrows - result.rank == free
        k, im = kernel_image(b, result)
        assert k.shape == (b.ncols, b.ncols - result.rank)
        assert im.shape == (b.nrows, result.rank)
        assert not any(x for row in multiply(b, k).rows for x in row)
        records.append({"name": name, "B": b.rows, "shape": b.shape,
                        "U": result.U.rows, "D": result.D.rows, "V": result.V.rows,
                        "K": k.rows, "image_basis": im.rows,
                        "invariants": result.invariants, "coker_free_rank": free})
    # Independently specified transform and determinantal divisors for the first B.
    b = cases[0][1]
    u = matrix([[0, 1], [-1, 2]])
    v = matrix([[1, -3], [0, 1]])
    assert multiply(multiply(u, b), v) == matrix([[2, 0], [0, 6]])
    assert determinant(u) == determinant(v) == 1
    assert abs(determinant(b)) == 12
    h = homology(matrix([[1, 1]]), matrix([[2], [-2]]))
    assert h["torsion"] == (2,) and h["free_rank"] == 0
    hfree = homology(matrix([[1, 1, 0]]), matrix([[2], [-2], [0]]))
    assert hfree["torsion"] == (2,) and hfree["free_rank"] == 1
    hempty = homology(identity(2), matrix([[], []], 0))
    assert hempty["K"].shape == (2, 0) and hempty["C"].shape == (0, 0)
    assert hempty["torsion"] == () and hempty["free_rank"] == 0
    expect_error(ValueError, lambda: homology(matrix([[1, 1]]), matrix([[1], [0]])))
    expect_error(ValueError, lambda: smith(identity(9)))
    expect_error(TypeError, lambda: matrix([[1.0]]))
    expect_error(TypeError, lambda: matrix([[True]]))
    for wrong_cols in (False, 0.0, ""):
        expect_error(ValueError, lambda wrong_cols=wrong_cols: matrix([], wrong_cols))
    expect_error(RuntimeError, lambda: smith(b, max_ops=1))
    return records, [
        pack_homology("Z2", matrix([[1, 1]]), matrix([[2], [-2]]), h),
        pack_homology("Z_plus_Z2", matrix([[1, 1, 0]]), matrix([[2], [-2], [0]]), hfree),
        pack_homology("zero_kernel", identity(2), matrix([[], []], 0), hempty),
    ]


def permutation(g):
    return matrix([[int(i == g[j]) for j in range(3)] for i in range(3)])


def representation_examples():
    group = list(itertools.permutations(range(3)))
    for g in group:
        for h in group:
            assert multiply(permutation(g), permutation(h)) == permutation(tuple(g[h[j]] for j in range(3)))
    r, s = (1, 2, 0), (1, 0, 2)
    R, S = matrix([[-1, -1], [1, 0]]), matrix([[0, 1], [1, 0]])
    assert multiply(multiply(R, R), R) == identity(2)
    assert multiply(S, S) == identity(2)
    assert multiply(multiply(S, R), S) == multiply(R, R)
    t = matrix([[1, 1, 0], [1, 0, 1], [1, -1, -1]])
    block_r, block_s = matrix([[1, 0, 0], [0, -1, -1], [0, 1, 0]]), matrix([[1, 0, 0], [0, 0, 1], [0, 1, 0]])
    assert determinant(t) == 3
    assert multiply(permutation(r), t) == multiply(t, block_r)
    assert multiply(permutation(s), t) == multiply(t, block_s)
    chars = [(1, 1, 1), (1, -1, 1), (2, 0, -1)]
    weights = (1, 3, 2)
    def inner(a, b):
        return sum(Fraction(w * x * y, 6) for w, x, y in zip(weights, a, b))
    gram = [[inner(a, b) for b in chars] for a in chars]
    assert gram == [[int(i == j) for j in range(3)] for i in range(3)]
    assert [inner((3, 1, 0), c) for c in chars] == [1, 0, 1]
    assert [inner((4, 0, 1), c) for c in chars] == [1, 1, 1]
    assert sum(c[0] ** 2 for c in chars) == 6
    # Q(omega): pair (a,b) denotes a+b*omega, with omega^2=-1-omega.
    def cmul(z, w):
        a, b = z
        c, d = w
        return a * c - b * d, a * d + b * c - b * d
    roots = [(1, 0), (0, 1), (-1, -1)]
    vectors = [[(1, 0), (1, 0), (1, 0)], [(1, 0), (-1, -1), (0, 1)], [(1, 0), (0, 1), (-1, -1)]]
    for lam, vec in zip(roots, vectors):
        assert [vec[-1], vec[0], vec[1]] == [cmul(lam, x) for x in vec]
    # Character 3 makes the Cp Jordan matrix a representation with no complement.
    j = matrix([[1, 1], [0, 1]])
    jp = multiply(multiply(j, j), j)
    assert matrix([[x % 3 for x in row] for row in jp.rows]) == identity(2)
    return {"S3_products_checked": 36, "S3_character_gram": [[int(x) for x in row] for row in gram],
            "permutation_multiplicities": [1, 0, 1], "tensor_multiplicities": [1, 1, 1],
            "n3_fourier_eigenvectors_exact": 3}


def main():
    records, groups = smith_examples()
    print(json.dumps({"integer_smith": records, "homology": groups,
                      "representation": representation_examples()}, indent=2))


if __name__ == "__main__":
    main()
