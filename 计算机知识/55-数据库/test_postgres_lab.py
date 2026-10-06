"""Oracle 来自串行业务规范/明确可见性预期，所有集成检查运行真实服务。"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import postgres_lab as lab


class PostgresLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = Path(os.environ.get('LAB_EVIDENCE',
                            tempfile.mkdtemp(prefix='wwlpg-evidence-')))
        cls.result = lab.run(cls.evidence / 'suite')

    def test_read_committed_rereads(self):
        self.assertEqual(self.result['rc_snapshots'], [100, 90])

    def test_repeatable_read_snapshot(self):
        self.assertEqual(self.result['rr_snapshots'], [100, 100])

    def test_client_absolute_write_loses_one_debit(self):
        # 串行完成两次 -10 应为 80；故意错误协议实际为 90。
        self.assertEqual(self.result['lost_update'], 90)
        self.assertNotEqual(self.result['lost_update'], 80)

    def test_atomic_two_debits(self):
        self.assertEqual(self.result['atomic_update'], 80)

    def test_repeatable_read_violates_duty(self):
        self.assertEqual(self.result['rr_skew']['reads'], [2, 2])
        self.assertEqual(self.result['rr_skew']['remaining'], 0)
        self.assertIsNone(self.result['rr_skew']['sqlstate'])

    def test_serializable_retries_all_decisions(self):
        r = self.result['serializable']
        self.assertEqual(r['reads'], [2, 2])
        self.assertEqual(r['sqlstate'], '40001')
        self.assertEqual(r['retry_read'], 1)
        self.assertEqual(r['remaining'], 1)

    def test_process_crash_committed_uncommitted(self):
        r = self.result['recovery']
        self.assertEqual(r['uncommitted_session'], '1|99\n2|20')
        self.assertEqual(r['observer_before'], '1|10\n2|0')
        self.assertEqual(r['after_restart'], '1|10\n2|0')
        log = (self.evidence / 'suite' / 'server.log').read_text()
        self.assertIn('database system was interrupted', log)
        self.assertIn('redo starts at', log)
        self.assertIn('redo done at', log)

    def test_socket_only_and_wal_settings(self):
        settings = self.result['settings']
        self.assertEqual(settings['listen_addresses'], '')
        for name in ('fsync', 'synchronous_commit', 'full_page_writes'):
            self.assertEqual(settings[name], 'on')

    def test_success_cleanup(self):
        self.assertTrue(self.result['cleanup']['removed'])
        self.assertFalse(Path(self.result['cleanup']['root']).exists())

    def test_start_failure_cleanup(self):
        c = lab.Cluster(evidence=self.evidence / 'start-failure')
        with patch.object(c, 'start', side_effect=RuntimeError('injected start failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                with c:
                    pass
        self.assertFalse(c.root.exists())

    def test_sql_error_and_invalid_input_cleanup(self):
        c = lab.Cluster(evidence=self.evidence / 'invalid')
        with c:
            s = c.session()
            with self.assertRaises(lab.SqlError) as caught:
                s.sql('SELECT 1/0;')
            self.assertEqual(caught.exception.state, '22012')
            with self.assertRaises(ValueError):
                s.sql('SELECT 1;', timeout=0)
            with self.assertRaises(ValueError):
                lab.snapshots(c, 'READ UNCOMMITED')
            with self.assertRaises(ValueError):
                c.stop('anything')
        self.assertFalse(c.root.exists())

    def test_timeout_finally_cleanup(self):
        c = lab.Cluster(evidence=self.evidence / 'timeout')
        with self.assertRaises(TimeoutError):
            with c:
                c.session().sql('SELECT pg_sleep(2);', timeout=0.05)
        self.assertFalse(c.root.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
