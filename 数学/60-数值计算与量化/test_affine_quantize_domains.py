"""Scale support boundaries; source filename is loaded without executing main."""
import importlib.util
from pathlib import Path
import sys
import math
import unittest
p=Path(__file__).with_name('80-量化误差实验.py')
spec=importlib.util.spec_from_file_location('quantization_domains_source',p)
lab=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lab;spec.loader.exec_module(lab)

class QuantizationDomainsTests(unittest.TestCase):
    def test_zero_and_exact_binary_symmetric_grid(self):
        q=lab.affine_quantize([0.],bits=8,symmetric=False)
        self.assertEqual(q.reconstructed,(0.,));self.assertEqual(q.scale,1.)
        q=lab.affine_quantize([-127.,0.,127.],bits=8,symmetric=True)
        self.assertEqual(q.scale,1.);self.assertEqual(q.codes,(-127,0,127))
        self.assertEqual(q.reconstructed,(-127.,0.,127.))

    def test_underflow_overflow_and_quotient_support(self):
        for symmetric in (False,True):
            with self.assertRaisesRegex(ArithmeticError,'scale'):
                lab.affine_quantize([math.ulp(0.)],bits=8,symmetric=symmetric)
        with self.assertRaisesRegex(ArithmeticError,'scale'):
            lab.affine_quantize([-1e308,1e308],bits=8,symmetric=False)
        # Calibration clips to a tiny percentile but outlier/scale is unrepresentable.
        with self.assertRaisesRegex(ArithmeticError,'code quotient'):
            lab.affine_quantize([1e-300]*100+[1e308],bits=8,symmetric=True,clip_percentile=90)
        for data in ([],[math.inf],[math.nan]):
            with self.assertRaises(ValueError): lab.affine_quantize(data,bits=8,symmetric=False)

if __name__=='__main__':unittest.main()
