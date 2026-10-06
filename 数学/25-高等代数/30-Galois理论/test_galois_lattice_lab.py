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
