"""Independent examples and failure-path tests for the offline transaction model."""
import importlib
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import transaction_lab as lab

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'lab.sqlite'
        self.conn = lab.connect(self.path)
        lab.initialize(self.conn)
    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()
    def call(self, who='alice', ident=17, action='submit', version=0, key='request-1'):
        return lab.transition(self.conn, who, ident, action, version, key)
    def state(self, ident=17):
        return self.conn.execute('SELECT status,version FROM reports WHERE id=?',(ident,)).fetchone()
    def counts(self):
        return tuple(self.conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                     for table in ('events','requests'))
    def test_submit_commits_all_records(self):
        out=self.call()
        self.assertEqual((out.status,out.version,out.replayed),('submitted',1,False))
        self.assertEqual(self.state(),('submitted',1)); self.assertEqual(self.counts(),(1,1))
    def test_approve_after_submit(self):
        self.call(); out=self.call('bob',17,'approve',1,'approve-1')
        self.assertEqual((out.status,out.version),('approved',2));self.assertEqual(self.counts(),(2,2))
    def test_exact_replay_does_not_repeat_side_effect(self):
        self.call(); out=self.call()
        self.assertTrue(out.replayed);self.assertEqual(self.counts(),(1,1))
    def test_replay_returns_original_result_not_current_state(self):
        self.call();self.call('bob',17,'approve',1,'approve-1')
        out=self.call();self.assertEqual((out.status,out.version),('submitted',1))
        self.assertEqual(self.state(),('approved',2))
    def test_same_key_different_content_conflicts(self):
        self.call()
        with self.assertRaises(lab.ConflictError):self.call(version=1)
        self.assertEqual(self.counts(),(1,1))
    def test_different_actors_may_use_same_key(self):
        self.call();self.call('bob',17,'approve',1,'request-1')
        self.assertEqual(self.counts(),(2,2))
    def test_cross_tenant_is_denied_without_writes(self):
        with self.assertRaises(PermissionError):self.call('carol',18,'approve')
        self.assertEqual(self.state(18),('submitted',0));self.assertEqual(self.counts(),(0,0))
    def test_unknown_identity_denied(self):
        with self.assertRaises(PermissionError):self.call('nobody')
    def test_missing_report_denied(self):
        with self.assertRaises(PermissionError):self.call(ident=900)
    def test_reviewer_cannot_edit_owners_state(self):
        with self.assertRaises(PermissionError):self.call('bob')
    def test_self_approval_denied(self):
        with self.assertRaises(PermissionError):self.call('bob',20,'approve')
        self.assertEqual(self.state(20),('submitted',0))
    def test_author_cannot_approve(self):
        with self.assertRaises(PermissionError):self.call('alice',18,'approve')
    def test_stale_version_is_conflict(self):
        with self.assertRaises(lab.ConflictError):self.call(version=1)
        self.assertEqual(self.state(),('draft',0))
    def test_wrong_lifecycle_is_conflict(self):
        with self.assertRaises(lab.ConflictError):self.call('bob',17,'approve')
    def test_new_key_does_not_reapply_completed_transition(self):
        self.call()
        with self.assertRaises(lab.ConflictError):self.call(version=1,key='new-key')
        self.assertEqual(self.counts(),(1,1))
    def test_bool_is_not_an_integer_identifier(self):
        with self.assertRaises(lab.InputError):self.call(ident=True)
    def test_invalid_version_rejected_before_sql(self):
        for value in [True,-1,1.5,2**63,'0']:
            with self.subTest(value=value), self.assertRaises(lab.InputError):self.call(version=value)
        self.assertFalse(self.conn.in_transaction)
    def test_invalid_keys_rejected(self):
        for key in ['', 'x'*65, 'a b', 'a\nb', None, 42]:
            with self.subTest(key=key),self.assertRaises(lab.InputError):self.call(key=key)
    def test_unknown_action_is_input_error(self):
        with self.assertRaises(lab.InputError):self.call(action='delete')
    def test_event_failure_rolls_back_state_and_replay_record(self):
        self.conn.execute("CREATE TEMP TRIGGER stop_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.call()
        self.assertEqual(self.state(),('draft',0));self.assertEqual(self.counts(),(0,0))
        self.assertFalse(self.conn.in_transaction)
        self.conn.execute('DROP TRIGGER stop_event');self.call();self.assertEqual(self.counts(),(1,1))
    def test_ledger_failure_also_rolls_back_event(self):
        self.conn.execute("CREATE TEMP TRIGGER stop_request BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.call()
        self.assertEqual(self.state(),('draft',0));self.assertEqual(self.counts(),(0,0))
    def test_caller_transaction_is_not_rolled_back(self):
        self.conn.execute('BEGIN');self.conn.execute('UPDATE reports SET version=3 WHERE id=17')
        with self.assertRaises(lab.InputError):self.call()
        self.assertTrue(self.conn.in_transaction);self.assertEqual(self.state(),('draft',3))
        self.conn.execute('ROLLBACK')
    def test_writer_contention_is_runtime_error_not_denial(self):
        other=lab.connect(self.path)
        try:
            self.conn.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError) as ctx:
                lab.transition(other,'alice',17,'submit',0,'key')
            self.assertEqual(getattr(ctx.exception,'sqlite_errorcode',None),sqlite3.SQLITE_BUSY)
            self.assertFalse(other.in_transaction);self.assertEqual(self.state(),('draft',0))
        finally:
            self.conn.execute('ROLLBACK');other.close()
    def test_reopening_keeps_committed_idempotency(self):
        self.call();other=lab.connect(self.path)
        try:
            out=lab.transition(other,'alice',17,'submit',0,'request-1')
            self.assertTrue(out.replayed);self.assertEqual(self.counts(),(1,1))
        finally:other.close()
    def test_initialization_does_not_replace_existing_data(self):
        self.call()
        with self.assertRaises(sqlite3.OperationalError):lab.initialize(self.conn)
        self.assertEqual(self.state(),('submitted',1))

class IsolationTests(unittest.TestCase):
    def test_import_does_not_open_database_or_socket(self):
        with patch.object(sqlite3,'connect',side_effect=AssertionError('no import IO')), \
             patch.object(socket,'socket',side_effect=AssertionError('no sockets')):
            importlib.reload(lab)
    def test_demo_does_not_relabel_unrelated_sql_error_as_contention(self):
        original = lab.transition
        calls = 0
        def injected(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 7:
                error = sqlite3.OperationalError('synthetic unrelated IO failure')
                error.sqlite_errorcode = sqlite3.SQLITE_IOERR
                error.sqlite_errorname = 'SQLITE_IOERR'
                raise error
            return original(*args, **kwargs)
        with patch.object(lab, 'transition', side_effect=injected):
            with self.assertRaisesRegex(RuntimeError, 'expected SQLITE_BUSY'):
                lab.demo()

    def test_demo_without_network(self):
        with patch.object(socket,'socket',side_effect=AssertionError('no sockets')):
            result=lab.demo()
        self.assertEqual(result['event_count'],2)
        self.assertEqual(result['final_report_17'],('approved',2))
        self.assertEqual(result['negative_cases']['cross_tenant'],'PermissionError')

if __name__=='__main__':unittest.main(verbosity=2)
