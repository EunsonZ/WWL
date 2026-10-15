#!/usr/bin/env python3
"""Offline SQLite authorization/transaction model, version transactions-v3.1.

No listener, network, dependencies, or import-time writes. CLI uses a private temporary
SQLite database and deletes it on exit. This is NOT an authentication server, ORM,
production idempotency service, or model of every DBMS isolation level.
Python >= 3.11 (SQLite diagnostic attributes and constants). Callers supply trusted connections to their own disposable databases.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sqlite3
import tempfile

class InputError(ValueError):
    """Malformed call, different from denied authorization or a stale state."""

class ConflictError(RuntimeError):
    """A valid call conflicts with version, lifecycle, or an existing request key."""

# Same initial identities and report states as reasoning-v2.0, a separate mutable copy.
_PRINCIPALS = {
    'alice': ('red', 'author'),
    'bob': ('red', 'reviewer'),
    'carol': ('blue', 'reviewer'),
}
_INITIAL = (
    (17, 'red', 'alice', 'draft', 0),
    (18, 'red', 'alice', 'submitted', 0),
    (19, 'blue', 'carol', 'submitted', 0),
    (20, 'red', 'bob', 'submitted', 0),
    (21, 'red', 'alice', 'approved', 0),
)
_SCHEMA = """
CREATE TABLE reports (
 id INTEGER PRIMARY KEY,
 tenant TEXT NOT NULL,
 owner TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('draft','submitted','approved')),
 version INTEGER NOT NULL CHECK(version >= 0)
);
CREATE TABLE requests (
 tenant TEXT NOT NULL, actor TEXT NOT NULL, request_key TEXT NOT NULL,
 report_id INTEGER NOT NULL REFERENCES reports(id), action TEXT NOT NULL,
 expected_version INTEGER NOT NULL,
 result_status TEXT NOT NULL, result_version INTEGER NOT NULL,
 PRIMARY KEY(tenant, actor, request_key)
);
CREATE TABLE events (
 event_id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL REFERENCES reports(id),
 actor TEXT NOT NULL, action TEXT NOT NULL, version INTEGER NOT NULL
);
"""

@dataclass(frozen=True)
class Outcome:
    report_id: int
    status: str
    version: int
    replayed: bool


def connect(path: str | Path) -> sqlite3.Connection:
    """A trusted owned path, not a sandbox for hostile paths. Never called on import."""
    conn = sqlite3.connect(path, isolation_level=None, timeout=0.0)
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    """Initialize an empty teaching DB. Existing tables cause an error, not replacement."""
    if conn.in_transaction:
        raise InputError('initialization requires a connection without an open transaction')
    conn.executescript(_SCHEMA)
    conn.executemany('INSERT INTO reports VALUES (?,?,?,?,?)', _INITIAL)


def transition(conn: sqlite3.Connection, identity: str, report_id: int, action: str,
               expected_version: int, request_key: str) -> Outcome:
    """Atomically bind authorization, state/version check, update, event and replay result.

    identity is already authenticated by the TRUSTED caller. Keys are scoped by tenant
    and actor, and bound to (report_id, action, expected_version). Exact retries return
    the original small result; they do not reapply the transition. No TTL/role revocation
    store, external side effect, automatic busy retry or distributed exactly-once claim.
    SQLite busy/IO errors remain sqlite3 errors, not 'permission denied' or success.
    """
    if not isinstance(conn, sqlite3.Connection) or conn.in_transaction:
        raise InputError('an idle SQLite connection is required; caller transactions are untouched')
    if not isinstance(identity, str) or identity not in _PRINCIPALS:
        raise PermissionError('unknown trusted identity')
    if type(report_id) is not int or not 1 <= report_id <= 2**31-1:
        raise InputError('report_id must be an integer in 1..2**31-1, not bool')
    if type(expected_version) is not int or not 0 <= expected_version <= 2**31-1:
        raise InputError('expected_version must be an integer in 0..2**31-1, not bool')
    if not isinstance(action, str) or action not in {'submit', 'approve'}:
        raise InputError('supported actions: submit, approve')
    if not isinstance(request_key, str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', request_key) is None:
        raise InputError('request_key must be 1..64 supported ASCII characters')
    tenant, role = _PRINCIPALS[identity]
    # This may raise SQLITE_BUSY before the transaction starts. Do not call it denial.
    conn.execute('BEGIN IMMEDIATE')
    try:
        row = conn.execute('SELECT tenant, owner, status, version FROM reports WHERE id=?',
                           (report_id,)).fetchone()
        if row is None or row[0] != tenant:
            raise PermissionError('object unavailable in this tenant')
        _, owner, state, version = row
        # Authorization is checked on retries too; a key is not an access token.
        if action == 'submit':
            if identity != owner:
                raise PermissionError('only the owner may submit')
            source, target = 'draft', 'submitted'
        else:
            if role != 'reviewer' or identity == owner:
                raise PermissionError('approval requires a same-tenant non-owner reviewer')
            source, target = 'submitted', 'approved'
        previous = conn.execute(
            'SELECT report_id, action, expected_version, result_status, result_version '
            'FROM requests WHERE tenant=? AND actor=? AND request_key=?',
            (tenant, identity, request_key)).fetchone()
        if previous is not None:
            if previous[:3] != (report_id, action, expected_version):
                raise ConflictError('same request key has different operation content')
            result = Outcome(report_id, previous[3], previous[4], True)
        else:
            if state != source or version != expected_version:
                raise ConflictError('lifecycle or expected version does not match')
            cursor = conn.execute(
                'UPDATE reports SET status=?, version=version+1 '
                'WHERE id=? AND tenant=? AND status=? AND version=?',
                (target, report_id, tenant, source, expected_version))
            if cursor.rowcount != 1:
                raise ConflictError('conditional update did not affect exactly one row')
            result = Outcome(report_id, target, expected_version+1, False)
            conn.execute('INSERT INTO events(report_id,actor,action,version) VALUES (?,?,?,?)',
                         (report_id, identity, action, result.version))
            conn.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)',
                         (tenant, identity, request_key, report_id, action, expected_version,
                          result.status, result.version))
        conn.execute('COMMIT')
        return result
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise


def demo() -> dict:
    with tempfile.TemporaryDirectory(prefix='kali-sqlite-lab-') as folder:
        path = Path(folder)/'synthetic.sqlite'
        conn, other = connect(path), None
        try:
            initialize(conn)
            results = [asdict(transition(conn, 'alice', 17, 'submit', 0, 'submit-17')),
                       asdict(transition(conn, 'alice', 17, 'submit', 0, 'submit-17')),
                       asdict(transition(conn, 'bob', 17, 'approve', 1, 'approve-17'))]
            errors = {}
            for label, args in [
                ('cross_tenant', ('carol', 17, 'approve', 2, 'carol-17')),
                ('stale_state', ('bob', 17, 'approve', 1, 'new-approve-17')),
                ('key_content_conflict', ('alice', 17, 'submit', 1, 'submit-17')),
            ]:
                try:
                    transition(conn, *args)
                except (PermissionError, ConflictError) as exc:
                    errors[label] = type(exc).__name__
                else:
                    raise AssertionError('negative case unexpectedly succeeded')
            other = connect(path)
            conn.execute('BEGIN IMMEDIATE')
            try:
                transition(other, 'alice', 17, 'submit', 0, 'submit-17')
            except sqlite3.OperationalError as exc:
                # A different operational error is not evidence of the intended lock case.
                if getattr(exc, 'sqlite_errorcode', None) != sqlite3.SQLITE_BUSY:
                    raise RuntimeError('expected SQLITE_BUSY; unrelated SQL error is not a passed contention case') from exc
                errors['writer_contention'] = {'class': type(exc).__name__,
                    'sqlite_errorcode': exc.sqlite_errorcode,
                    'sqlite_errorname': exc.sqlite_errorname}
            else:
                raise AssertionError('second writer unexpectedly succeeded')
            finally:
                conn.execute('ROLLBACK')
            return {'model': 'transactions-v3.1', 'sqlite_version': sqlite3.sqlite_version,
                    'synthetic': True, 'network_io': False, 'operations': results,
                    'negative_cases': errors,
                    'event_count': conn.execute('SELECT COUNT(*) FROM events').fetchone()[0],
                    'final_report_17': conn.execute('SELECT status,version FROM reports WHERE id=17').fetchone()}
        finally:
            if other is not None: other.close()
            conn.close()

if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
