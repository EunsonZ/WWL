"""Behavioral tests for exact finite certificates; not topology theorem proofs."""
import unittest

from homology_lab import cup_on_fundamental, finite_chain, fixed_report, one_relation_integer, rank_q


class FiniteCertificates(unittest.TestCase):
    def test_triangle_changes_only_two_chain(self):
        models = {r["name"]: r for r in fixed_report()["models"]}
        edge, filled = models["triangle_boundary"], models["triangle_filled"]
        self.assertEqual(edge["d1"], filled["d1"])
        self.assertEqual(edge["betti_Q"], [1, 1, 0])
        self.assertEqual(filled["betti_Q"], [1, 0, 0])
        self.assertEqual((edge["chi"], filled["chi"]), (0, 1))

    def test_chain_law_rejects_bad_face(self):
        with self.assertRaises(ValueError):
            finite_chain("bad", [2, 1, 1], [[-1], [1]], [[1]])

    def test_declared_shapes_and_integer_contract(self):
        with self.assertRaises(ValueError):
            finite_chain("bad", [1, 2, 0], [[0]], [[], []])
        with self.assertRaises(TypeError):
            finite_chain("bad", [1, 1, 0], [[True]], [[]])
        with self.assertRaises(TypeError):
            finite_chain("bad", [1, 1, 0], [[0.0]], [[]])

    def test_exact_rank_with_large_near_dependent_integers(self):
        n = 10**30
        self.assertEqual(rank_q([[n, n + 1], [n + 1, n + 2]], 2), 2)
        self.assertEqual(rank_q([[], []], 0), 0)

    def test_cup_determinant_and_orientation(self):
        x, y = (1, 0, 1), (0, 1, 1)
        self.assertEqual(cup_on_fundamental(x, y), 1)
        self.assertEqual(cup_on_fundamental(y, x), -1)
        self.assertEqual(cup_on_fundamental(x, x), 0)
        self.assertEqual(cup_on_fundamental((2, -1, 1), (1, 3, 4)), 7)
        self.assertEqual(cup_on_fundamental(x, y, -1), -1)
        with self.assertRaises(ValueError):
            cup_on_fundamental((1, 0, 0), y)

    def test_integer_torsion_survives_rank_zero(self):
        result = one_relation_integer(2)
        self.assertEqual(result["H1_free_rank"], 0)
        self.assertEqual(result["H1_torsion_factors"], [2])
        self.assertEqual(result["H2_free_rank"], 0)
        self.assertEqual(one_relation_integer(-2)["H1_torsion_factors"], [2])
        self.assertEqual(one_relation_integer(0)["H2_free_rank"], 1)
        self.assertEqual(one_relation_integer(1)["H1_torsion_factors"], [])

    def test_same_additive_groups_need_extra_cup_data(self):
        report = fixed_report()
        models = {r["name"]: r for r in report["models"]}
        self.assertEqual(models["T2_minimal"]["d2"], models["wedge_S1_S1_S2"]["d2"])
        self.assertEqual(report["torus_cup"]["xy_on_z"], 1)
        # W's zero product is proven by restrictions in lesson05, not inferred here.


if __name__ == "__main__":
    unittest.main()
