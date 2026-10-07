"""Finite machine support checks with independent probability identities."""
import math
import unittest
from sampling_evaluation_lab import nll_and_perplexity

class SamplingDomainsTests(unittest.TestCase):
    def test_ordinary_probability_identity(self):
        nll,ppl=nll_and_perplexity([0.5,0.25])
        self.assertAlmostEqual(nll,3*math.log(2))
        self.assertAlmostEqual(ppl,math.sqrt(8))
        nll,ppl=nll_and_perplexity([2.0**-1022])
        self.assertAlmostEqual(nll,1022*math.log(2))
        self.assertTrue(math.isfinite(ppl))
        self.assertAlmostEqual(ppl/(2.0**1022),1,places=12)

    def test_subnormal_probability_has_finite_log_but_unrepresentable_ppl(self):
        p=math.ulp(0.)  # p=2^-1074; reciprocal 2^1074 cannot fit binary64.
        self.assertAlmostEqual(-math.log(p),1074*math.log(2))
        with self.assertRaisesRegex(ArithmeticError,"finite NLL but perplexity"):
            nll_and_perplexity([p])
        for p in (0.,-1.,math.inf,math.nan):
            with self.assertRaises(ValueError): nll_and_perplexity([p])

if __name__=='__main__':unittest.main()
