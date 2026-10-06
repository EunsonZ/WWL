"""Pure TLS result-oracle tests, not substitutes for the real OpenSSL laboratory."""
import importlib
import unittest
from unittest import mock
import tls_verify_lab as lab

class OracleTests(unittest.TestCase):
    def rejected(self, code=62, rc=2, expected=62):
        return lab.assess_verification(rc,'',f'error {code} at 0 depth lookup: reason\nerror leaf.pem: verification failed\n',False,expected)
    def test_positive_requires_ok(self):
        self.assertTrue(lab.assess_verification(0,'leaf.pem: OK\n','',True)['passed'])
    def test_empty_stdout_not_a_positive(self):
        self.assertFalse(lab.assess_verification(0,'','',True)['passed'])
    def test_expected_rejection(self):
        self.assertTrue(self.rejected()['passed'])
    def test_unknown_option_is_not_rejection(self):
        self.assertFalse(lab.assess_verification(2,'','verify: Unknown option: -bad',False,62)['passed'])
    def test_wrong_reason_not_passed(self):
        self.assertFalse(self.rejected(code=20)['passed'])
    def test_missing_expected_reason_not_passed(self):
        self.assertFalse(self.rejected(expected=None)['passed'])
    def test_unexpected_exit_not_passed(self):
        self.assertFalse(self.rejected(rc=1)['passed'])
    def test_success_does_not_pass_negative(self):
        self.assertFalse(lab.assess_verification(0,'leaf.pem: OK','',False,62)['passed'])
    def test_rejection_does_not_pass_positive(self):
        self.assertFalse(lab.assess_verification(2,'','error 62 at 0 depth lookup: mismatch',True)['passed'])
    def test_contradictory_output_rejected(self):
        self.assertFalse(lab.assess_verification(0,'leaf.pem: OK','error 62 at 0 depth lookup: mismatch',True)['passed'])
    def test_additional_error_not_hidden(self):
        result=lab.assess_verification(2,'','error 62 at 0 depth lookup: mismatch\nerror 20 at 1 depth lookup: chain\nverification failed',False,62)
        self.assertFalse(result['passed'])
    def test_depth_is_recorded_in_input_not_assumed_leaf(self):
        self.assertTrue(lab.assess_verification(2,'','error 9 at 2 depth lookup: not yet valid\nverification failed',False,9)['passed'])
    def test_date_epoch(self):
        self.assertEqual(lab._epoch('notBefore=Jan  1 00:00:00 1970 GMT'),0)
    def test_date_timezone_rejected(self):
        with self.assertRaises(ValueError):lab._epoch('notBefore=Jan 1 00:00:00 1970 UTC')
    def test_invalid_day_rejected(self):
        with self.assertRaises(ValueError):lab._epoch('notBefore=Feb 30 00:00:00 2026 GMT')
    def test_import_does_not_spawn_processes(self):
        with mock.patch('subprocess.run',side_effect=AssertionError('process on import')):
            importlib.reload(lab)
    def test_missing_openssl_not_silent_skip(self):
        with mock.patch('shutil.which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'missing'):lab.run()
    def test_unsupported_dialect_is_not_pass(self):
        with mock.patch('shutil.which',return_value='/synthetic/openssl'),mock.patch('subprocess.run',return_value=mock.Mock(stdout='LibreSSL 0.0\n')):
            with self.assertRaisesRegex(RuntimeError,'OpenSSL 3'):lab.run()

if __name__ == '__main__':unittest.main()