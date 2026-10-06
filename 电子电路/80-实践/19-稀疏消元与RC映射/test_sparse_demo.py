import itertools
from fractions import Fraction as F
import unittest

import sparse_demo as m


class ExactStar(unittest.TestCase):
    def test_independent_branch_formula_all_orders(self):
        for rhs in ((1,0,0,0), (0,1,0,0), (F(1,7), -3, F(2,5), 4)):
            direct = m.physical_star(rhs)
            for order in itertools.permutations(range(4)):
                solved, _ = m.solve_order(rhs, order)
                self.assertEqual(solved, direct)
                kcl, src, diss = m.kcl_and_power(solved, list(map(F,rhs)))
                self.assertEqual(kcl, list(map(F,rhs)))
                self.assertEqual(src, diss)

    def test_first_schur_and_rhs(self):
        volts, stages = m.solve_order((1,0,0,0), (0,1,2,3))
        self.assertEqual(stages[0]["matrix_S"], [[F(5,3) if i==j else F(-1,3) for j in range(3)] for i in range(3)])
        self.assertEqual(stages[0]["rhs_A"], [F(1,3)]*3)
        self.assertEqual(stages[0]["fill_pairs"], [(1,2),(1,3),(2,3)])
        self.assertEqual(volts,[F(2,3),F(1,3),F(1,3),F(1,3)])

    def test_leaf_order_and_changed_injection(self):
        volts, stages = m.solve_order((0,1,0,0),(1,2,3,0))
        self.assertTrue(all(not s["fill_pairs"] for s in stages))
        self.assertEqual([s["pivot_S"] for s in stages], [F(2),F(2),F(2),F(3,2)])
        self.assertEqual(volts, [F(1,3),F(2,3),F(1,6),F(1,6)])

    def test_contract_rejects_not_rational_or_not_permutation(self):
        for rhs, order in (((True,0,0,0),(0,1,2,3)), ((1.,0,0,0),(0,1,2,3)), ((1,0,0),(0,1,2,3)), ((1,0,0,0),(0,0,2,3)), ((1,0,0,0),(False,1,2,3))):
            with self.assertRaises(ValueError):
                m.solve_order(rhs,order)

if __name__ == "__main__":
    unittest.main()
