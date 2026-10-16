import math
import unittest
import target_models as m

class Models(unittest.TestCase):
    def test_axis_and_scale(self):
        self.assertEqual(m.fitts_id(64,64),1)
        self.assertAlmostEqual(m.fitts_id(128,64),math.log2(3))
        self.assertEqual(m.fitts_id(128,64),m.fitts_id(256,128))
        self.assertLess(m.fitts_id(256,128),m.fitts_id(256,64))
        self.assertEqual(m.fitts_id(0,64),0)
    def test_entropy_conventions(self):
        self.assertEqual(m.entropy([1,0]),0)
        self.assertEqual(m.entropy([.25]*4),2)
        self.assertLess(m.entropy([.7,.1,.1,.1]),2)
        self.assertNotEqual(m.entropy([.25]*4),math.log2(5))
        self.assertAlmostEqual(m.entropy([.7,.1,.1,.1]),1.3567796494470397)
    def test_fit_is_descriptive(self):
        r=m.fit([1,2,3],[.3,.5,.7]);self.assertAlmostEqual(r['a_s'],.1);self.assertAlmostEqual(r['b_s_per_bit'],.2)
        self.assertAlmostEqual(r['SSE_s2'],0);self.assertAlmostEqual(r['R2'],1)
        r=m.fit([1,2,3],[.5,.5,.5]);self.assertIsNone(r['R2'])
    def test_contrast_not_round_up(self):
        self.assertEqual(m.contrast([0,0,0],[1,1,1]),21)
        self.assertAlmostEqual(m.contrast([119/255]*3,[1,1,1]),4.478089453577214)
        self.assertLess(m.contrast([119/255]*3,[1,1,1]),4.5)
        self.assertEqual(m.contrast([.4]*3,[.4]*3),1)
    def test_refuse_parameters(self):
        for bad in (True,float('nan'),float('inf'),-1,10**1000,'64'):
            with self.assertRaises(ValueError):m.fitts_id(bad,64)
        for bad in (0,True,float('inf')):
            with self.assertRaises(ValueError):m.fitts_id(64,bad)
        for bad in ([],[.1,.2],[True,0],[float('nan')],[1.1,-.1]):
            with self.assertRaises(ValueError):m.entropy(bad)
        for xs,ys in (([1,1,1],[1,2,3]),([1,2],[1,2]),([1,2,3],[1,2])):
            with self.assertRaises(ValueError):m.fit(xs,ys)
        with self.assertRaises(ValueError):m.channel(2)
        with self.assertRaises(ValueError):m.luminance([0,0])

if __name__=='__main__':unittest.main()
