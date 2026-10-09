"""Single-room/day teaching authority; SQLite, no network or real authentication.

Commit booking, intent outcome and outbox together. A second SQLite sink models
an explicitly idempotent external consumer; it is not an email provider.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile


PROTOCOL = "wwl-reservation-v2/1"


class InvalidInput(ValueError):
    """Malformed input: no registered business decision."""


class IntentConflict(ValueError):
    """An existing intent has different parameters; its decision is unchanged."""


class WriterFenced(PermissionError):
    """This attempt is not permitted to make a new business decision."""


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def text(value, name):
    if type(value) is not str or not value.strip() or len(value) > 128:
        raise InvalidInput(f"{name}: nonblank string, at most 128 characters")
    return value


def integer(value, name):
    if type(value) is not int:
        raise InvalidInput(f"{name}: integer, excluding bool")
    return value


def fingerprint(actor: str, start: int, end: int, policy_version: int = 2) -> str:
    """SHA-256 of UTF-8 canonical business fields; neither MAC nor authorization.

    Intent id and writer epoch are excluded: retrying the same business request
    after restart/epoch change must still match. Policy version is included.
    """
    text(actor, "actor")
    integer(start, "start")
    integer(end, "end")
    integer(policy_version, "policy_version")
    request = {"actor": actor, "end": end, "op": "reserve",
               "policy_version": policy_version, "start": start}
    return hashlib.sha256(canonical(request).encode("utf-8")).hexdigest()


def valid_interval(start, end):
    return 540 <= start < end <= 1020 and 30 <= end - start <= 120


def compatible_v2(start, end, old_start, old_end):
    # New requests apply the 10-minute rule even against preserved v1 records.
    return end + 10 <= old_start or old_end + 10 <= start


class Authority:
    """Every mutating transaction obtains BEGIN IMMEDIATE before reading state.

    Only this implementation may write the database. A legacy process with raw
    filesystem/SQL access can bypass the epoch check: not a security sandbox.
    """

    def __init__(self, database):
        self.path = Path(database)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA synchronous = FULL")
        existing_metadata = self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone()
        if existing_metadata is None and self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone():
            self.db.close()
            raise InvalidInput("existing database is not an authority schema")
        if existing_metadata is not None:
            version = self.db.execute(
                "SELECT schema_version FROM metadata WHERE singleton=1").fetchone()
            if version is None or version[0] != 1:
                self.db.close()
                raise InvalidInput("unsupported authority schema; do not initialize")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                schema_version INTEGER NOT NULL,
                writer_epoch INTEGER NOT NULL CHECK(writer_epoch>=2));
            INSERT OR IGNORE INTO metadata VALUES(1,1,2);
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL,
                policy_version INTEGER NOT NULL CHECK(policy_version IN (1,2)),
                CHECK(540<=start AND start<end AND end<=1020),
                CHECK(30<=end-start AND end-start<=120));
            CREATE TABLE IF NOT EXISTS intents (
                actor TEXT NOT NULL, intent_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, outcome TEXT NOT NULL,
                PRIMARY KEY(actor,intent_id));
            CREATE TABLE IF NOT EXISTS outbox (
                event_id TEXT PRIMARY KEY, booking_id INTEGER NOT NULL UNIQUE,
                payload TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(booking_id) REFERENCES bookings(id));
        """)
        if self.db.execute("SELECT schema_version FROM metadata").fetchone()[0] != 1:
            self.db.close()
            raise InvalidInput("unsupported authority schema; do not overwrite")

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    @property
    def writer_epoch(self):
        return self.db.execute("SELECT writer_epoch FROM metadata").fetchone()[0]

    def _check_writer(self, writer_epoch, policy_version=2):
        integer(writer_epoch, "writer_epoch")
        integer(policy_version, "policy_version")
        if writer_epoch != self.writer_epoch or policy_version != 2:
            raise WriterFenced("new decisions require current epoch and v2 policy")

    def fence(self, new_epoch):
        """Simulated operator action: advance epoch, retain all business state."""
        integer(new_epoch, "new_epoch")
        with self.transaction():
            if new_epoch <= self.writer_epoch:
                raise InvalidInput("epoch must strictly increase")
            self.db.execute("UPDATE metadata SET writer_epoch=?", (new_epoch,))

    def seed_legacy(self, records):
        """One-time import into an empty authority, not an online write API.

        records = [(owner,start,end),...]. Preserve v1 adjacency; reject overlaps.
        Identity/consent of historical data is outside this synthetic fixture.
        """
        rows = list(records)
        for owner, start, end in rows:
            text(owner, "actor"); integer(start, "start"); integer(end, "end")
            if not valid_interval(start, end):
                raise InvalidInput("invalid legacy interval")
        with self.transaction():
            if self.db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] or self.db.execute("SELECT COUNT(*) FROM intents").fetchone()[0]:
                raise InvalidInput("legacy import requires an empty authority")
            for owner, start, end in rows:
                old = self.db.execute("SELECT start,end FROM bookings").fetchall()
                if any(start < b["end"] and b["start"] < end for b in old):
                    raise InvalidInput("overlapping legacy records")
                self.db.execute("INSERT INTO bookings(owner,start,end,policy_version) VALUES(?,?,?,1)",
                                (owner, start, end))

    def snapshot(self):
        return [dict(row) for row in self.db.execute("SELECT * FROM bookings ORDER BY id")]

    def query(self, actor, intent_id, expected_fingerprint=None):
        """Absent record = unknown, not proof that a delayed request cannot commit."""
        text(actor, "actor"); text(intent_id, "intent_id")
        row = self.db.execute("SELECT fingerprint,outcome FROM intents WHERE actor=? AND intent_id=?",
                              (actor, intent_id)).fetchone()
        if row is None:
            return {"protocol": PROTOCOL, "actor": actor, "intent_id": intent_id,
                    "status": "unknown", "reason": "not_registered"}
        if expected_fingerprint is not None and expected_fingerprint != row["fingerprint"]:
            raise IntentConflict("query fingerprint differs; original decision retained")
        return json.loads(row["outcome"])

    def reserve(self, actor, intent_id, start, end, *, writer_epoch=2, policy_version=2,
                fail_at=None):
        """Return the durable business result, or raise an attempt/transport error.

        fail_at is a lab-only fault switch: before_commit rolls everything back;
        after_commit loses the reply but retains the decision. Never a public API.
        """
        text(actor, "actor"); text(intent_id, "intent_id")
        fp = fingerprint(actor, start, end, policy_version)
        if fail_at not in (None, "before_commit", "after_commit"):
            raise InvalidInput("unknown fault switch")
        with self.transaction():
            saved = self.query(actor, intent_id, fp)
            if saved["status"] != "unknown":
                # Replay is a read of an existing decision, even after fencing.
                return saved
            self._check_writer(writer_epoch, policy_version)
            outcome = {"protocol": PROTOCOL, "actor": actor, "intent_id": intent_id,
                       "fingerprint": fp, "policy_version": 2,
                       "writer_epoch": writer_epoch, "status": "rejected"}
            old = self.db.execute("SELECT start,end FROM bookings").fetchall()
            if not valid_interval(start, end):
                outcome["reason"] = "invalid_interval"
            elif any(not compatible_v2(start, end, b["start"], b["end"]) for b in old):
                outcome["reason"] = "conflict_with_buffer"
            else:
                cursor = self.db.execute("INSERT INTO bookings(owner,start,end,policy_version) VALUES(?,?,?,2)",
                                         (actor, start, end))
                booking_id = cursor.lastrowid
                event_id = f"booking:{booking_id}:created"
                booking = {"id": booking_id, "owner": actor, "start": start,
                           "end": end, "policy_version": 2}
                outcome.update(status="accepted", reason="created", booking=booking,
                               event_id=event_id)
                event = {"protocol": PROTOCOL, "event_id": event_id,
                         "kind": "booking_created", "booking": booking,
                         "actor": actor, "intent_id": intent_id, "fingerprint": fp}
                self.db.execute("INSERT INTO outbox(event_id,booking_id,payload) VALUES(?,?,?)",
                                (event_id, booking_id, canonical(event)))
            self.db.execute("INSERT INTO intents VALUES(?,?,?,?)",
                            (actor, intent_id, fp, canonical(outcome)))
            if fail_at == "before_commit":
                raise ConnectionError("lab fault: transaction not committed")
        if fail_at == "after_commit":
            raise ConnectionError("lab fault: committed reply lost")
        return outcome

    def pending_events(self):
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT payload FROM outbox WHERE acknowledged=0 ORDER BY booking_id")]

    def acknowledge(self, event_id):
        """Lab worker calls only after sink confirmation; this is not user receipt."""
        text(event_id, "event_id")
        with self.transaction():
            row = self.db.execute("SELECT 1 FROM outbox WHERE event_id=?", (event_id,)).fetchone()
            if row is None:
                raise InvalidInput("unknown event")
            self.db.execute("UPDATE outbox SET acknowledged=1 WHERE event_id=?", (event_id,))


class NotificationSink:
    """Separate durable, idempotent teaching sink. No actual email or payment.

    Effect record and deduplication identity are the same SQLite row. Providers
    without this contract do not inherit this model's effect guarantee.
    """

    def __init__(self, database):
        self.db = sqlite3.connect(Path(database), isolation_level=None, timeout=5)
        self.db.execute("PRAGMA synchronous = FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS effects(event_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def close(self):
        self.db.close()

    def deliver(self, event):
        event_id = text(event.get("event_id"), "event_id")
        payload = canonical(event)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT payload FROM effects WHERE event_id=?", (event_id,)).fetchone()
            if old is not None and old[0] != payload:
                raise IntentConflict("same event id has different payload")
            created = old is None
            if created:
                self.db.execute("INSERT INTO effects VALUES(?,?)", (event_id, payload))
            self.db.execute("COMMIT")
            return created
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def effects(self):
        return [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM effects ORDER BY event_id")]


def demo():
    """Temporary databases only; emit the committed-loss/restart/replay trace."""
    with tempfile.TemporaryDirectory(prefix="wwl-v2-demo-") as directory:
        authority_path = Path(directory) / "authority.sqlite"
        with Authority(authority_path) as authority:
            authority.seed_legacy([("A", 540, 600), ("B", 600, 630), ("C", 650, 680)])
            print(canonical({"legacy": authority.snapshot()}))
            try:
                authority.reserve("D", "intent-D", 690, 720, fail_at="after_commit")
            except ConnectionError:
                print(canonical({"client": "unknown", "reason": "reply_lost"}))
        with Authority(authority_path) as authority:
            print(canonical({"query_after_restart": authority.query("D", "intent-D")}))
            replay = authority.reserve("D", "intent-D", 690, 720)
            sink = NotificationSink(Path(directory) / "notifications.sqlite")
            try:
                event = authority.pending_events()[0]
                print(canonical({"first_effect": sink.deliver(event), "duplicate_effect": sink.deliver(event)}))
                authority.acknowledge(event["event_id"])
            finally:
                sink.close()
            authority.fence(3)
            try:
                authority.reserve("old", "new-intent", 730, 760, writer_epoch=2)
            except WriterFenced:
                print(canonical({"old_writer": "fenced", "bookings": authority.snapshot(),
                                 "saved_outcome": replay}))


if __name__ == "__main__":
    demo()
