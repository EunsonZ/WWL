"""Independent finite checks for the lesson's exact examples."""
from itertools import combinations, product
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import abstract_algebra_lab as lab


class AlgebraChecks(unittest.TestCase):
    def setUp(self):
        self.s3, self.d4, self.r, self.s = lab.examples()

    def test_permutation_composition_against_maps(self):
        for a, b in product(self.s3.elements, repeat=2):
            mapping_a, mapping_b = dict(enumerate(a)), dict(enumerate(b))
            expected = tuple(mapping_a[mapping_b[i]] for i in range(3))
            self.assertEqual(lab.compose(a, b), expected)
            self.assertEqual(lab.compose(a, lab.inverse(a)), self.s3.identity)

    def test_d4_semidirect_formula_independent_of_permutations(self):
        # Vertex j is mapped to k+(-1)^epsilon*j modulo 4.
        def image(k, epsilon):
            return tuple((k + (-1)**epsilon*j) % 4 for j in range(4))
        self.assertEqual({image(k, e) for k in range(4) for e in (0, 1)}, self.d4.elements)
        for k, e, ell, f in product(range(4), (0, 1), range(4), (0, 1)):
            expected = image((k + (-1)**e*ell) % 4, (e+f) % 2)
            self.assertEqual(lab.compose(image(k, e), image(ell, f)), expected)

    def test_subgroups_against_exhaustive_subset_enumeration(self):
        for group, expected_count in ((self.s3, 6), (self.d4, 10)):
            brute = set()
            others = sorted(group.elements - {group.identity})
            for size in range(len(others) + 1):
                for selection in combinations(others, size):
                    h = frozenset((group.identity,) + selection)
                    # Independent finite closure criterion, no generated().
                    if all(tuple(a[b[i]] for i in range(len(a))) in h for a in h for b in h):
                        brute.add(h)
            self.assertEqual(set(group.all_subgroups()), brute)
            self.assertEqual(len(brute), expected_count)

    def test_cosets_normality_and_quotient_representatives(self):
        reflection = self.d4.generated((self.s,))
        cosets = self.d4.left_cosets(reflection)
        self.assertEqual(len(cosets), 4)
        self.assertEqual(set().union(*cosets), set(self.d4.elements))
        self.assertEqual(sum(map(len, cosets)), 8)
        self.assertFalse(self.d4.is_normal(reflection))
        self.assertNotIn(lab.compose(lab.compose(self.r, self.s), lab.inverse(self.r)), reflection)
        with self.assertRaises(ValueError):
            self.d4.quotient_table(reflection)
        rotation = self.d4.generated((self.r,))
        cosets = self.d4.left_cosets(rotation)
        table = self.d4.quotient_table(rotation)
        # Check every representative pair, not just chosen minimums.
        for i, a_coset in enumerate(cosets):
            for j, b_coset in enumerate(cosets):
                expected = cosets[table[i][j]]
                for a, b in product(a_coset, b_coset):
                    self.assertIn(lab.compose(a, b), expected)
        self.assertEqual(table, ((0, 1), (1, 0)))
        central = self.d4.generated((lab.compose(self.r, self.r),))
        self.assertTrue(self.d4.is_normal(central))
        ctable = self.d4.quotient_table(central)
        self.assertTrue(all(ctable[i][i] == 0 for i in range(4)))

    def test_sylow_counts_and_conjugates(self):
        for group in (self.s3, self.d4):
            for p in (2, 3, 5):
                subgroups = group.sylow(p)
                n = len(subgroups)
                target = len(subgroups[0])
                self.assertEqual((len(group.elements) // target) % n, 0)
                self.assertEqual(n % p, 1)
                h = subgroups[0]
                conjugates = {frozenset(lab.compose(lab.compose(g, x), lab.inverse(g)) for x in h)
                              for g in group.elements}
                self.assertEqual(conjugates, set(subgroups))
        self.assertEqual((len(self.s3.sylow(2)), len(self.s3.sylow(3))), (3, 1))
        self.assertEqual(len(self.d4.sylow(2)), 1)

    def test_gaussian_division_exhaustive_box_and_large_integers(self):
        box = tuple(product(range(-3, 4), repeat=2))
        for z, w in product(box, repeat=2):
            if w == (0, 0):
                continue
            q, r = lab.gaussian_divmod(z, w)
            qw = lab.gaussian_mul(q, w)
            self.assertEqual((qw[0]+r[0], qw[1]+r[1]), z)
            self.assertLess(lab.gaussian_norm(r), lab.gaussian_norm(w))
        self.assertEqual(lab.gaussian_divmod((7, 5), (3, 2)), ((2, 0), (1, 1)))
        huge = 10**100 + 3
        q, r = lab.gaussian_divmod((huge, huge+1), (3, 2))
        qw = lab.gaussian_mul(q, (3, 2))
        self.assertEqual((qw[0]+r[0], qw[1]+r[1]), (huge, huge+1))
        self.assertLess(lab.gaussian_norm(r), 13)

    def test_minus5_norm_is_exhaustive_and_multiplicative(self):
        for n in range(30):
            brute = {(a, b) for a, b in product(range(-6, 7), repeat=2) if a*a + 5*b*b == n}
            self.assertEqual(set(lab.minus5_norm_solutions(n)), brute)
        self.assertEqual(lab.minus5_norm_solutions(1), ((-1, 0), (1, 0)))
        self.assertEqual(lab.minus5_norm_solutions(2), ())
        self.assertEqual(lab.minus5_norm_solutions(3), ())
        for z, w in product(product(range(-2, 3), repeat=2), repeat=2):
            self.assertEqual(lab.minus5_norm(lab.minus5_mul(z, w)),
                             lab.minus5_norm(z)*lab.minus5_norm(w))
        self.assertEqual(lab.minus5_mul((1, 1), (1, -1)), (6, 0))

    def test_gauss_content_and_evaluation(self):
        polynomials = tuple(product(range(-2, 3), repeat=3))
        def evaluate(f, x):
            return sum(a*x**i for i, a in enumerate(f))
        for f, g in product(polynomials, repeat=2):
            h = lab.poly_mul(f, g)
            self.assertEqual(lab.content(h), lab.content(f)*lab.content(g))
            self.assertEqual(evaluate(h, 2), evaluate(f, 2)*evaluate(g, 2))
        self.assertEqual(lab.content((0,)), 0)
        self.assertEqual(lab.content((-2, -2)), 2)

    def test_invalid_input_and_svg_determinism(self):
        operations = (
            lambda: lab.compose((0, 0), (0, 1)),
            lambda: lab.compose((0,), (0, 1)),
            lambda: lab.permutation((False,)),
            lambda: lab.FiniteGroup([]),
            lambda: lab.FiniteGroup([(1, 0)]),
            lambda: self.d4.subgroup({self.r}),
            lambda: self.s3.generated(((1, 2, 3, 0),)),
            lambda: self.s3.sylow(4),
            lambda: self.s3.sylow(True),
            lambda: self.s3.sylow(10**100 + 7),
            lambda: lab.gaussian_divmod((1, 2), (0, 0)),
            lambda: lab.gaussian_norm((float('nan'), 0)),
            lambda: lab.gaussian_norm((float('inf'), 0)),
            lambda: lab.minus5_norm_solutions(-1),
            lambda: lab.minus5_norm_solutions(10001),
            lambda: lab.content(()),
            lambda: lab.content((True,)),
        )
        for operation in operations:
            with self.assertRaises(ValueError):
                operation()
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/'a.svg', Path(directory)/'b.svg'
            lab.write_d4_svg(a)
            lab.write_d4_svg(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            root = ET.fromstring(a.read_bytes())
            self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
            self.assertIn('r^2s', a.read_text())
            self.assertNotIn('\r', a.read_text())


if __name__ == '__main__':
    unittest.main()
