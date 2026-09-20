"""Tests for the finite covering-space and word calculations."""
import unittest

import covering_vankampen_lab as lab


class CoveringVanKampenLabTests(unittest.TestCase):
    def test_free_reduction(self):
        self.assertEqual(lab.reduce_free_word("abBAcC"), "")
        self.assertEqual(lab.reduce_free_word("abAB"), "abAB")
        self.assertEqual(lab.reduce_free_word("abcCBA"), "")

    def test_reduction_is_idempotent(self):
        for word in ("", "aA", "abAB", "aaBBccCCA"):
            reduced = lab.reduce_free_word(word)
            self.assertEqual(lab.reduce_free_word(reduced), reduced)

    def test_exponent_sums_do_not_detect_free_identity(self):
        self.assertEqual(lab.exponent_sums("abAB"), (0, 0, 0))
        self.assertEqual(lab.reduce_free_word("abAB"), "abAB")

    def test_circle_lift_endpoint_and_closedness(self):
        self.assertEqual(lab.circle_lift_endpoint(7, 5, 1), (3, False))
        self.assertEqual(lab.circle_lift_endpoint(15, 5, 1), (1, True))
        self.assertEqual(lab.circle_lift_endpoint(-2, 5, 1), (4, False))

    def test_torus_endpoints(self):
        self.assertEqual(lab.torus_lift_endpoint("aaaBB"), (3, -2))
        self.assertEqual(lab.torus_lift_endpoint("abAB"), (0, 0))

    def test_rp2_parity(self):
        self.assertEqual(tuple(lab.rp2_class(k) for k in range(-2, 4)), (0, 1, 0, 1, 0, 1))

    def test_invalid_inputs(self):
        cases = [
            lambda: lab.reduce_free_word("ad"),
            lambda: lab.reduce_free_word(3),
            lambda: lab.circle_lift_endpoint(1, 0),
            lambda: lab.circle_lift_endpoint(True, 2),
            lambda: lab.torus_lift_endpoint("ac"),
            lambda: lab.rp2_class(2.0),
        ]
        for case in cases:
            with self.assertRaises((TypeError, ValueError)):
                case()


if __name__ == "__main__":
    unittest.main()
