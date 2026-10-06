"""Independent rational oracles, bank cash rollforward and amount identities."""
import unittest
from fractions import Fraction as F
from itertools import combinations
from f1_reporting_lab import (Potential, weighted_shares, treasury_increment, diluted_eps,
                              lease_schedule, pension_rollforward, tax_bridge, disposal,
                              pro_forma, ratio)


class ReportingTests(unittest.TestCase):
    def test_timeline_rational(self):
        self.assertEqual(weighted_shares([(200,.5),(220,.25),(210,.25)]), float(F(415,2)))
    def test_treasury_rational(self):
        self.assertAlmostEqual(treasury_increment(40,6,10), float(F(16)))
        self.assertEqual(treasury_increment(40,12,10), 0)
        self.assertEqual(treasury_increment(40,6,10,.5), 8)
    def test_eps_enumeration_oracle(self):
        inputs = [('options',0,16),('A',3,10),('preferred',12,30),('B',12,25)]
        result = diluted_eps(108,207.5,[Potential(*x) for x in reversed(inputs)])
        # Enumerate all 16 subsets with exact rational arithmetic, without sequential algorithm.
        alternatives = []
        for size in range(5):
            for subset in combinations(inputs,size):
                alternatives.append((F(108)+sum(F(x[1]) for x in subset))/(F(415,2)+sum(F(x[2]) for x in subset)))
        self.assertAlmostEqual(result['eps'], float(min(alternatives)))
        self.assertEqual([x['included'] for x in result['steps']],[True,True,True,False])
        self.assertAlmostEqual(result['eps'],float(F(246,527)))
    def test_loss_antidilution(self):
        r=diluted_eps(-10,100,[Potential('options',0,20),Potential('bond',3,10)])
        self.assertEqual(r['eps'],-.1)
        self.assertFalse(any(x['included'] for x in r['steps']))
    def test_sequence_counterexample(self):
        b=diluted_eps(108,207.5,[Potential('B',12,25)])
        self.assertTrue(b['steps'][0]['included'])
        full=diluted_eps(108,207.5,[Potential('opt',0,16),Potential('A',3,10),Potential('pref',12,30),Potential('B',12,25)])
        self.assertFalse(full['steps'][-1]['included'])
    def test_lease_closed_form_and_cash(self):
        r=lease_schedule([60,55],.1)
        self.assertAlmostEqual(r['pv'],100)
        self.assertAlmostEqual(sum(x['principal'] for x in r['rows']),100)
        self.assertAlmostEqual(sum(x['interest'] for x in r['rows']),15)
        self.assertAlmostEqual(r['rows'][0]['operating_rou'],52.5)
        for row in r['rows']:
            self.assertAlmostEqual(row['payment'],row['principal']+row['interest'])
        for key in ['liability','finance_rou','operating_rou']:
            self.assertAlmostEqual(r['rows'][-1][key],0)
    def test_lease_zero_rate(self):
        r=lease_schedule([10,10],0)
        self.assertEqual(r['pv'],20)
        self.assertEqual(r['rows'][0]['interest'],0)
    def test_db_cash_profit_oci_identity(self):
        r=pension_rollforward()
        self.assertEqual((r['obligation'],r['assets'],r['net_liability']),(115,89,26))
        self.assertEqual(r['profit_cost'],9)
        self.assertEqual(r['oci_loss'],7)
        self.assertEqual(20+r['profit_cost']+r['oci_loss']-r['contribution'],26)
    def test_tax_exact_oracle(self):
        r=tax_bridge(65,4,6,20,.25,12)
        self.assertEqual((r['taxable'],r['current'],r['deferred'],r['expense']),(43,10.75,5,15.75))
        self.assertAlmostEqual(r['effective'],float(F(63,260)))
        self.assertEqual(r['expense'],65*.25+4*.25-6*.25)
        self.assertEqual(r['ending_net_payable'],-1.25)
    def test_tax_payment_timing(self):
        a=tax_bridge(65,4,6,20,.25,12)
        b=tax_bridge(65,4,6,20,.25,20)
        self.assertEqual(a['expense'],b['expense'])
        self.assertNotEqual(a['cash_rate'],b['cash_rate'])
    def test_disposal_amount_identity(self):
        r=disposal(30,38,20,.25)
        self.assertEqual((r['gain'],r['current_tax'],r['dtl_reversal'],r['total_tax'],r['ni']),(8,4.5,2.5,2,6))
        self.assertEqual(r['net_cash']-30, r['ni']-r['dtl_reversal'])
    def test_forecast_rational_bank_oracle(self):
        r=pro_forma()
        # Bank receipts544, suppliers310, salaries110, interest15, taxes22.5.
        bank_cfo=F(544)-F(310)-F(110)-F(15)-F(45,2)
        self.assertAlmostEqual(r['cfo'],float(bank_cfo))
        self.assertAlmostEqual(r['direct_cfo'],float(bank_cfo))
        self.assertAlmostEqual(r['borrowing'],float(F(81,2)))
        self.assertAlmostEqual(r['assets'],530)
        self.assertAlmostEqual(r['assets'],r['liabilities']+r['equity'])
        self.assertAlmostEqual(r['cash'],113+r['cfo']+r['cfi']+r['cff'])
    def test_forecast_scenarios_identities(self):
        for sales in [500,550,600,700]:
            for floor in [0,100,130]:
                r=pro_forma(sales,floor)
                self.assertAlmostEqual(r['assets'],r['liabilities']+r['equity'])
                self.assertAlmostEqual(r['cfo'],r['direct_cfo'])
                self.assertGreaterEqual(r['cash'],floor)
                self.assertGreaterEqual(r['borrowing'],0)
    def test_invalid_inputs(self):
        calls=[lambda:weighted_shares([]),lambda:weighted_shares([(100,.5)]),
               lambda:weighted_shares([(0,1)]),lambda:treasury_increment(40,6,0),
               lambda:treasury_increment(40,6,10,2),lambda:diluted_eps(10,0,[]),
               lambda:diluted_eps(10,100,[Potential('x',0,0)]),
               lambda:diluted_eps(10,100,[Potential('x',0,2),Potential('x',0,3)]),
               lambda:lease_schedule([],0),lambda:lease_schedule([1],-.1),
               lambda:tax_bridge(0,0,0,0,.25,0),lambda:tax_bridge(1,0,10,0,.25,0),
               lambda:tax_bridge(10,0,0,0,2,0),lambda:disposal(30,38,20,2),
               lambda:disposal(10,38,20,.25),lambda:pro_forma(100),lambda:pro_forma(float('nan')),
               lambda:ratio(1,0),lambda:ratio(True,1),lambda:ratio(1,float('inf'))]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):call()
    def test_cash_cover_exact(self):
        self.assertEqual(ratio(63+15,15),float(F(26,5)))
        self.assertAlmostEqual(ratio(63+15,20+15),float(F(78,35)))


if __name__=='__main__':
    unittest.main()
