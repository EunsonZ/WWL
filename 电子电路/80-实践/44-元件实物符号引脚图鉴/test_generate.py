import unittest,xml.etree.ElementTree as ET
import generate
class Atlas(unittest.TestCase):
 def test_seven_licensed_sources(self):
  rows=generate.catalog();self.assertEqual(len(rows),7)
  for r in rows:self.assertTrue(r['license']);self.assertTrue(r['page'].startswith('https://commons.wikimedia.org/'))
 def test_named_model_pin_labels(self):
  for k in ('R','C','L','D','MOS','BJT','OP'):ET.fromstring('<svg>'+generate.symbol(k)+'</svg>')
  self.assertIn('C(1)',generate.symbol('BJT'));self.assertIn('E(3)',generate.symbol('BJT'));self.assertIn('8 V+',generate.symbol('OP'));self.assertIn('4 V-',generate.symbol('OP'))
 def test_diode_polarity(self):
  s=generate.symbol('D');self.assertIn('>A<',s);self.assertIn('>K<',s);self.assertIn('M230 380L230 430',s)
 def test_output_guard(self):
  from pathlib import Path
  for p in (Path(__file__).parent,Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')):
   with self.assertRaises(ValueError):generate.generate(p)
