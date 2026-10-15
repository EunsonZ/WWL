"""Narrow teaching-account contracts. Prepared, not executed in this batch."""
import unittest
from fractions import Fraction as F
from everyday_economy import combined_budget, import_payment, two_period_transfer


class AccountContracts(unittest.TestCase):
    def test_transfer_changes_level_balances_not_consolidation(self):
        before = combined_budget(80, 50, 20, 60, 30)
        after = combined_budget(80, 50, 20, 60, 40)
        self.assertEqual((before['central_balance'], before['local_balance']), (0, -10))
        self.assertEqual((after['central_balance'], after['local_balance']), (-10, 0))
        for row in (before, after):
            self.assertEqual((row['combined_tax'], row['combined_services'],
                              row['combined_deficit']), (100, 110, 10))

    def test_deposit_and_credit_are_distinct_counterparts(self):
        cash = import_payment(120, 150)
        credit = import_payment(120, 150, trade_credit=True)
        self.assertEqual((cash['deposit_change'], cash['closing_deposit'],
                          cash['new_trade_credit']), (-120, 30, 0))
        self.assertEqual((credit['deposit_change'], credit['closing_deposit'],
                          credit['new_trade_credit']), (0, 150, 120))
        self.assertEqual(cash['foreign_deposit_liability_change'], -120)
        self.assertEqual(credit['foreign_trade_credit_asset_change'], 120)
        for row in (cash, credit):
            self.assertEqual((row['china_CA'], row['china_FA']), (-120, -120))
            self.assertEqual((row['foreign_CA'], row['foreign_FA']), (120, 120))

    def test_payment_rejects_insufficient_and_invalid_inputs(self):
        for args in ((120, 100), (-1, 100), (True, 100), (120.0, 150)):
            with self.assertRaises(ValueError):
                import_payment(*args)
        with self.assertRaises(ValueError):
            import_payment(120, 0, trade_credit='yes')

    def test_closed_two_period_expected_consumption_and_saving(self):
        for c, expected in ((F(4, 5), (8, F(32, 5))),
                            (F(1, 5), (2, F(2, 5)))):
            rows = two_period_transfer(10, c, 0)
            self.assertEqual(tuple(row['consumption'] for row in rows), expected)
            self.assertEqual(tuple(row['private_saving'] for row in rows), (10, 0))
            self.assertEqual(tuple(row['new_bank_loan_to_government'] for row in rows), (10, 0))

    def test_open_two_period_expected_outputs_and_external_accounts(self):
        rows = two_period_transfer(10, F(4, 5), F(1, 4))
        self.assertEqual(tuple(row['domestic_output'] for row in rows), (6, F(18, 5)))
        self.assertEqual(tuple(row['imports'] for row in rows), (2, F(6, 5)))
        self.assertEqual(tuple(row['private_saving'] for row in rows), (8, F(-6, 5)))
        for row in rows:
            self.assertEqual(row['private_saving'] + row['government_net_lending']
                             + row['foreign_net_lending'], 0)
            self.assertEqual(row['import_accounts']['new_trade_credit'], row['imports'])
            self.assertEqual(row['import_accounts']['deposit_change'], 0)

    def test_share_and_exact_amount_contract(self):
        for c, m in ((F(6, 5), 0), (F(-1, 5), 0), (F(4, 5), F(5, 4)),
                     (0.8, 0), (True, 0)):
            with self.assertRaises(ValueError):
                two_period_transfer(10, c, m)
        rows = two_period_transfer(F(1, 2), F(1, 2), F(1, 2))
        self.assertEqual(rows[0]['imports'], F(1, 8))


if __name__ == '__main__':
    unittest.main()
