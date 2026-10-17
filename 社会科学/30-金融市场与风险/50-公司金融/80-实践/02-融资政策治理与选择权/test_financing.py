import copy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest
from financing import run

class FinanceTests(unittest.TestCase):
    def setUp(self):self.card=json.loads((Path(__file__).parent/'inputs.json').read_text())
    def test_policy_zero_tax_and_wrong_policy(self):
        self.card['valuation']['tax']='0';x=run(self.card)['results']['valuation']
        self.assertEqual(x['fixed_debt']['APV'],F(2100,11));self.assertEqual(x['constant_ratio']['APV'],F(2100,11))
        self.card['valuation']['tax']='1/4';x=run(self.card)['results']['valuation'];self.assertEqual(x['fixed_debt']['APV'],F(23420,121));self.assertNotEqual(x['fixed_debt_wrong_constant_target_WACC'],x['fixed_debt']['APV'])
    def test_zero_equity_and_risky_yield(self):
        x=run(self.card)['results']['mm']['rows'];self.assertIsNone(x[-1]['r_equity']);self.assertEqual(x[-1]['E'],0)
        self.assertNotEqual(x[2]['r_debt'],x[2]['promised_yield'])
    def test_endogenous_constraint_and_waiting(self):
        x=run(self.card)['results'];self.assertEqual(x['pledge']['maximum_outside_funding'],24);self.assertFalse(x['pledge']['fundable_without_inside_cash_weak_IC']);self.assertTrue(x['pledge']['fundable_weak_IC'])
        self.assertEqual(x['options']['free_wait_value'],25);self.assertEqual(x['options']['delayed_cash_wait_value'],0);self.assertEqual(x['options']['with_abandon_NPV'],-5);self.assertEqual(x['options']['date0_best_invest_or_skip'],0)
    def test_effort_empty_set_is_not_zero_debt(self):
        self.card['pledge']['private_benefit']='60';self.card['pledge']['inside_cash']='50'
        x=run(self.card)['results']['pledge'];self.assertFalse(x['effort_implementable_weak_IC']);self.assertFalse(x['fundable_weak_IC']);self.assertEqual(x['IC_effort_minus_shirk'],-20);self.assertIsNone(x['D_max_weak_IC']);self.assertIsNone(x['minimum_inside_funding_weak_IC'])
        self.card['pledge']['private_benefit']='40';x=run(self.card)['results']['pledge'];self.assertTrue(x['fundable_weak_IC']);self.assertEqual(x['D_max_weak_IC'],0);self.assertEqual(x['IC_effort_minus_shirk'],0)
    def test_reject_domain_before_output(self):
        for field,value in [('r','-1'),('tax','1'),('target_debt_fraction','1'),('debt_after_distribution',['80','40','1'])]:
            c=copy.deepcopy(self.card);c['valuation'][field]=value
            with self.assertRaises(ValueError):run(c)
        c=copy.deepcopy(self.card);c['information']['old_shareholders']='active'
        with self.assertRaises(ValueError):run(c)
        c=copy.deepcopy(self.card);c['mm']['P']=['1/3','1/3']
        with self.assertRaises(ValueError):run(c)
if __name__=='__main__':unittest.main()
