import copy
from fractions import Fraction
import json
from pathlib import Path
import unittest
from energy import calculate

class EnergyTests(unittest.TestCase):
    def setUp(self):self.card=json.loads((Path(__file__).parent/'energy.json').read_text())
    def test_hand_unit_and_rebound(self):
        rows=calculate(self.card)['results'];a,b=rows[:2]
        self.assertEqual(Fraction(a['metrics']['dynamic_kWh']['exact']),Fraction(5,9))
        self.assertEqual(Fraction(b['metrics']['dynamic_J']['exact']),2400000)
        self.assertGreater(Fraction(b['metrics']['total_allocated_g']['exact']),Fraction(a['metrics']['total_allocated_g']['exact']))
        self.assertLess(Fraction(b['metrics']['g_per_functional_unit']['exact']),Fraction(a['metrics']['g_per_functional_unit']['exact']))
    def test_quality_not_smaller_denominator(self):self.assertEqual(calculate(self.card)['results'][-1],{'id':'B_bad_quality','status':'not_comparable','reason':'quality_gate'})
    def test_reject_bad_domains(self):
        for key,value in [('successful_requests',True),('successful_requests',0),('success_J','NaN')]:
            c=copy.deepcopy(self.card);c['cases'][0][key]=value
            with self.assertRaises(ValueError):calculate(c)
        for over in [{'reserved_share':'1.1'},{'hardware_life_h':'0'},{'facility_factor':'0.9'}]:
            c=copy.deepcopy(self.card);c['cases'][0]['override']=over
            with self.assertRaises(ValueError):calculate(c)
if __name__=='__main__':unittest.main()
