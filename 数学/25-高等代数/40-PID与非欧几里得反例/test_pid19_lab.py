"""Exact arithmetic, modular obstruction, and validation tests."""
import math
import unittest

import pid19_lab as lab


class PID19LabTests(unittest.TestCase):
    def test_small_norm_solutions_are_exact(self):
        self.assertEqual(lab.norm19_solutions(1), ((-1, 0), (1, 0)))
        self.assertEqual(lab.norm19_solutions(2), ())
        self.assertEqual(lab.norm19_solutions(3), ())
        self.assertEqual(lab.norm19_solutions(4), ((-2, 0), (2, 0)))
        self.assertEqual(
            set(lab.norm19_solutions(5)),
            {(-1, 1), (0, 1), (0, -1), (1, -1)},
        )

    def test_modular_obstructions(self):
        self.assertEqual(lab.roots_mod_prime(5, 2), ())
        self.assertEqual(lab.roots_mod_prime(5, 3), ())
        self.assertEqual(lab.roots_mod_prime(3, 2), ())

    def test_minkowski_bounds_cross_the_stated_integer_cutoff(self):
        self.assertGreater(lab.minkowski_bound(19), 2.0)
        self.assertLess(lab.minkowski_bound(19), 3.0)
        self.assertGreater(lab.minkowski_bound(11), 2.0)
        self.assertLess(lab.minkowski_bound(11), 3.0)
        self.assertGreater(lab.minkowski_bound(20), 2.0)
        self.assertLess(lab.minkowski_bound(20), 3.0)
        self.assertEqual(math.floor(lab.minkowski_bound(19)), 2)

    def test_displayed_principal_ideal_generators(self):
        self.assertEqual(lab.norm19(0, 1), 5)   # omega
        self.assertEqual(lab.norm19(-1, 1), 5)  # omega-1
        self.assertEqual(lab.norm19(1, 1), 7)   # omega+1

    def test_minus_five_has_no_element_of_norm_two(self):
        candidates = [
            (a, b)
            for a in range(-3, 4)
            for b in range(-3, 4)
            if lab.norm_minus5(a, b) == 2
        ]
        self.assertEqual(candidates, [])

    def test_reject_invalid_inputs(self):
        cases = [
            lambda: lab.norm19(1.0, 0),
            lambda: lab.norm19(True, 0),
            lambda: lab.norm19_solutions(-1),
            lambda: lab.norm19_solutions(True),
            lambda: lab.roots_mod_prime(5, 1),
            lambda: lab.minkowski_bound(0),
            lambda: lab.report(0),
            lambda: lab.report(10_001),
        ]
        for case in cases:
            with self.assertRaises((TypeError, ValueError)):
                case()


if __name__ == "__main__":
    unittest.main()
