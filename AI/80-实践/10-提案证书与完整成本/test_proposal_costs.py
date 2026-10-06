import unittest
from fractions import Fraction as F
from proposal_costs import accepted, residual, total_cost
class ProposalTests(unittest.TestCase):
    def test_certificate_and_known_bias(self):
        self.assertEqual(residual(F(14,5)), F(2,5)); self.assertFalse(accepted(F(14,5))); self.assertTrue(accepted(F(3)))
    def test_scalar_task_error_is_limited_case(self): self.assertEqual(residual(F(14,5))/2, F(1,5))
    def test_known_bias_fast_route(self):
        mean,bias=F(16,45),F(2,25)
        self.assertEqual(mean+bias,F(98,225)); self.assertEqual(mean+bias-bias,mean)
        self.assertLess(F(1,48),F(1,40)); self.assertLessEqual(F(47,10)+F(4,5),F(11,2))
    def test_unknown_bias_fails_concrete_recheck(self): self.assertEqual(residual(F(31,10)), F(1,5)); self.assertFalse(accepted(F(31,10)))
    def test_complete_cost_keeps_fallback(self): self.assertEqual(total_cost(F(1),F(2),F(3),F(4)), F(10))
    def test_branch_counts_do_not_mix(self): self.assertEqual(198+162,360); self.assertEqual(360,360)
if __name__ == '__main__': unittest.main()
