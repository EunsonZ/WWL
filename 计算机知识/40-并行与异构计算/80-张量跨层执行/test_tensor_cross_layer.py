import unittest
from tensor_cross_layer import CompileContract, kv_bytes, offset, thread_for

class CrossLayerTests(unittest.TestCase):
    def test_contiguous_and_transpose_share_offset(self):
        self.assertEqual(offset((2,3), (5,1)), 13)
        self.assertEqual(offset((3,2), (1,5)), 13)
    def test_bytes_thread_and_tail(self):
        self.assertEqual(13*4, 52); self.assertEqual(thread_for(13), (1,5))
        self.assertEqual(thread_for(15), (1,7))
    def test_kv_formula(self): self.assertEqual(kv_bytes(), 49152)
    def test_contract_change_is_visible(self):
        old=CompileContract((3,5),'fp32',(5,1),False,'causal',1,False)
        new=CompileContract((5,3),'fp32',(1,5),True,'causal',2,True)
        self.assertNotEqual(old,new)
if __name__ == '__main__': unittest.main()
