"""Exact finite group lattices for two Galois examples.

Permutations are tuples of images; compose(a, b) applies b first.  The
enumeration checks V4 and S3 only.  It does not prove any field theorem.
"""
from itertools import combinations
import json


def compose(a, b):
    if len(a) != len(b) or sorted(a) != list(range(len(a))) or sorted(b) != list(range(len(b))):
        raise ValueError("inputs must be permutations of the same finite set")
    return tuple(a[b[i]] for i in range(len(a)))


def inverse(a):
    if sorted(a) != list(range(len(a))):
        raise ValueError("input must be a permutation")
    return tuple(a.index(i) for i in range(len(a)))


class Group:
    def __init__(self, elements):
        self.elements = frozenset(elements)
        if not self.elements:
            raise ValueError("empty group")
        degrees = {len(g) for g in self.elements}
        if len(degrees) != 1:
            raise ValueError("permutation degrees differ")
        self.identity = tuple(range(len(next(iter(self.elements)))))
        if self.identity not in self.elements:
            raise ValueError("identity missing")
        if any(compose(a, b) not in self.elements for a in self.elements for b in self.elements):
            raise ValueError("not closed")
        if any(inverse(a) not in self.elements for a in self.elements):
            raise ValueError("inverse missing")

    def generated(self, generators):
        h = {self.identity}
        changed = True
        while changed:
            changed = False
            for a in tuple(h) + tuple(generators):
                for b in tuple(h) + tuple(generators):
                    c = compose(a, b)
                    if c not in self.elements:
                        raise ValueError("generator outside group")
                    if c not in h:
                        h.add(c)
                        changed = True
        return frozenset(h)

    def subgroups(self):
        rest = sorted(self.elements - {self.identity})
        answer = []
        for size in range(len(rest) + 1):
            for chosen in combinations(rest, size):
                h = frozenset((self.identity,) + chosen)
                if all(compose(a, b) in h for a in h for b in h):
                    answer.append(h)
        return tuple(answer)

    def is_normal(self, h):
        return all(compose(compose(g, x), inverse(g)) in h for g in self.elements for x in h)


def examples():
    e3 = (0, 1, 2)
    r = (1, 2, 0)                 # alpha -> omega*alpha
    c = (0, 2, 1)                 # complex conjugation
    s3 = Group((e3, r, compose(r, r), c, compose(r, c), compose(compose(r, r), c)))

    e4 = (0, 1, 2, 3)
    s2 = (1, 0, 3, 2)             # flip the sqrt(2) sign bit
    s3sign = (2, 3, 0, 1)         # flip the sqrt(3) sign bit
    v4 = Group((e4, s2, s3sign, compose(s2, s3sign)))
    return s3, (r, c), v4, (s2, s3sign)


def rows(group, correspondence):
    result = []
    for h in sorted(group.subgroups(), key=lambda x: (len(x), sorted(x))):
        if h not in correspondence:
            raise AssertionError("correspondence omitted a subgroup")
        result.append({
            "subgroup_order": len(h),
            "index_or_fixed_field_degree": len(group.elements) // len(h),
            "normal": group.is_normal(h),
            "fixed_field": correspondence[h],
        })
    return result


def demo():
    s3, (r, c), v4, (s2, s3sign) = examples()
    e3, e4 = s3.identity, v4.identity
    r2 = compose(r, r)
    s3_fields = {
        frozenset((e3,)): "Q(alpha, omega)",
        s3.generated((r,)): "Q(omega)",
        s3.generated((c,)): "Q(alpha)",
        s3.generated((compose(r, c),)): "Q(omega^2 alpha)",
        s3.generated((compose(r2, c),)): "Q(omega alpha)",
        s3.elements: "Q",
    }
    v4_fields = {
        frozenset((e4,)): "Q(sqrt2, sqrt3)",
        v4.generated((s2,)): "Q(sqrt3)",
        v4.generated((s3sign,)): "Q(sqrt2)",
        v4.generated((compose(s2, s3sign),)): "Q(sqrt6)",
        v4.elements: "Q",
    }
    return {"V4": rows(v4, v4_fields), "S3": rows(s3, s3_fields)}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
