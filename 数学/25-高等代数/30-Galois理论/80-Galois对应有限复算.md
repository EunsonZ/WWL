---
type: experiment
stage: 0
aliases:
  - Galois群格复算
  - V4与S3子群枚举
sources: []
prerequisites:
  - "[[数学/25-高等代数/30-Galois理论/05-双二次扩张与S3全部对应]]"
---
# Galois 对应有限复算

先手算 $V_4$ 与 $S_3$ 的子群，再用这个无第三方依赖的脚本核对：子群是否穷尽、哪些正规、指数是否等于正文固定域次数。置换用像元组表示，`compose(a, b)` 约定先作用 `b` 再作用 `a`；因此正文的 $rc$ 在根序列 $(\alpha,\omega\alpha,\omega^2\alpha)$ 上是 `(1, 0, 2)`，固定第三个根。

## 运行与预期

从本目录或库根运行：

```bash
python3 -B 数学/25-高等代数/30-Galois理论/galois_lattice_lab.py
python3 -B -m unittest discover -s 数学/25-高等代数/30-Galois理论 -p 'test_galois_lattice_lab.py' -v
```

应有 4 项测试通过。JSON 中 $V_4$ 有 5 个子群，全部正规，固定域次数排序为 `1,2,2,2,4`；$S_3$ 有 6 个子群，正规子群阶恰为 `1,3,6`，固定域次数排序为 `1,2,3,3,3,6`。`Q(omega)` 对应三阶正规子群，三个三次域对应非正规的二阶子群。

## 它验证什么，不验证什么

程序直接枚举有限置换群的所有含单位子集，并检查乘法封闭；在有限群内，非空有限乘法封闭子集自动含逆元，所以得到全部子群。测试回归地重枚举这些子集，并与已知子群数、正规子群阶、$r^3=c^2=1$、$crc=r^{-1}$ 和复合约定共同核对；这不是一条独立的子群枚举算法。

域名与子群的配对是正文已经证明的输入；程序只检查每个已列子群的阶、指数和正规性。它不构造数域，不证明 $x^3-2$ 不可约，不证明 Artin 定理或有限 Galois 基本定理，更不能从 6 个置换推出无限多个域的结论。

## 源码真源与同版镜像

[galois_lattice_lab.py](galois_lattice_lab.py) 是规范源；下面代码块与它逐字同步。

<!-- code-sync: ./galois_lattice_lab.py -->
```python
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
```

[test_galois_lattice_lab.py](test_galois_lattice_lab.py) 是相关测试真源；下面同版镜像让代码随笔记一起保存。

<!-- code-sync: ./test_galois_lattice_lab.py -->
```python
"""Independent finite checks for galois_lattice_lab."""
from itertools import combinations
import unittest
import galois_lattice_lab as lab


def brute_subgroups(group):
    rest = list(group.elements - {group.identity})
    out = set()
    for k in range(len(rest) + 1):
        for chosen in combinations(rest, k):
            h = frozenset((group.identity,) + chosen)
            if all(lab.compose(a, b) in h for a in h for b in h):
                out.add(h)
    return out


class LatticeChecks(unittest.TestCase):
    def setUp(self):
        self.s3, (self.r, self.c), self.v4, (self.s2, self.s3sign) = lab.examples()

    def test_group_relations_and_composition_convention(self):
        self.assertEqual(lab.compose(self.r, lab.compose(self.r, self.r)), self.s3.identity)
        self.assertEqual(lab.compose(self.c, self.c), self.s3.identity)
        self.assertEqual(lab.compose(self.c, lab.compose(self.r, self.c)), lab.inverse(self.r))
        # rc swaps roots 0 and 1 and fixes root 2 = omega^2 alpha.
        self.assertEqual(lab.compose(self.r, self.c), (1, 0, 2))

    def test_subgroups_are_exhaustive(self):
        for group, count in ((self.v4, 5), (self.s3, 6)):
            self.assertEqual(set(group.subgroups()), brute_subgroups(group))
            self.assertEqual(len(group.subgroups()), count)

    def test_normal_subgroups(self):
        self.assertTrue(all(self.v4.is_normal(h) for h in self.v4.subgroups()))
        normal_s3 = {h for h in self.s3.subgroups() if self.s3.is_normal(h)}
        self.assertEqual({len(h) for h in normal_s3}, {1, 3, 6})
        self.assertEqual(len(normal_s3), 3)

    def test_correspondence_degrees_and_labels(self):
        data = lab.demo()
        self.assertEqual(sorted(row["index_or_fixed_field_degree"] for row in data["V4"]), [1, 2, 2, 2, 4])
        self.assertEqual(sorted(row["index_or_fixed_field_degree"] for row in data["S3"]), [1, 2, 3, 3, 3, 6])
        s3_by_field = {row["fixed_field"]: row for row in data["S3"]}
        self.assertTrue(s3_by_field["Q(omega)"]["normal"])
        self.assertFalse(s3_by_field["Q(alpha)"]["normal"])
        self.assertEqual(s3_by_field["Q(omega^2 alpha)"]["subgroup_order"], 2)


if __name__ == "__main__":
    unittest.main()
```

实际作者运行：4 项测试通过，随后 JSON 输出与两张正文表一致。Obsidian 的 Mermaid 显示、来源语义与人的理解需另行验收。
