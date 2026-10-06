import unittest,math
import models
class Board(unittest.TestCase):
 def test_rotated_pad(self):self.assertEqual(models.coordinate(2,3,10,20,'R90'),(7.,22.))
 def test_rotation_roundtrip(self):
  x,y=models.coordinate(2,3,0,0,'R90');self.assertEqual(models.coordinate(x,y,0,0,'R270'),(2.,3.))
 def test_invalid(self):
  for v in (True,float('nan'),float('inf'),10**400,1j):
   with self.assertRaises(ValueError):models.coordinate(v,0,0,0)
  with self.assertRaises(ValueError):models.coordinate(0,0,0,0,'MR0')
 def test_pin_net_identity(self):
  d=models.load();p={(v['ref'],v['pad']):v for v in d['points']}
  self.assertEqual(p['TP_A0','X']['net'],'AD0');self.assertEqual(p['AD','1']['net'],'AD0');self.assertEqual(p['ZU4','23']['net'],'AD0')
  self.assertEqual(p['POWER','5']['net'],'+5V');self.assertEqual(p['POWER','6']['net'],'GND')
 def test_local_pad_coordinate(self):
  p={(v['ref'],v['pad']):v for v in models.load()['points']};self.assertAlmostEqual(p['AD','1']['x_mm'],50.8);self.assertAlmostEqual(p['POWER','5']['x_mm'],38.1)
 def test_trace_endpoints(self):
  d=models.load();w=[v for v in d['wires'] if v['net']=='AD0'];self.assertTrue(w)
  endpoints={(round(float(v[a]),4),round(float(v[b]),4)) for v in w for a,b in [('x1','y1'),('x2','y2')]};self.assertIn((50.8,2.54),endpoints)
