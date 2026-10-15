"""Finite after-image log -> transactional SQLite incremental view (Python 3.11+)."""
import argparse
import json
from pathlib import Path
import sqlite3

FIELDS = {"event_id", "entity_id", "version", "op", "group", "minutes"}
LIMIT = 100_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def utf8_text(value):
    if type(value) is not str or not 1 <= len(value) <= 80 or value.strip() != value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def validate(event):
    if type(event) is not dict or set(event) != FIELDS:
        return False
    for key in ("event_id", "entity_id"):
        x = event[key]
        if not utf8_text(x):
            return False
    v = event["version"]
    if type(v) is not int or not 1 <= v <= 2**63 - 1:
        return False
    if event["op"] == "delete":
        return event["group"] is None and event["minutes"] is None
    if event["op"] != "put":
        return False
    g, m = event["group"], event["minutes"]
    return (utf8_text(g)
            and type(m) is int and 0 <= m <= 1_000_000)


def snapshot(event):
    return canonical({k: event[k] for k in ("op", "group", "minutes")})


class InjectedFailure(RuntimeError):
    pass


class ViewStore:
    """One owner per connection; no source offset or external sink is implemented."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS seen(
          event_id TEXT PRIMARY KEY, payload TEXT NOT NULL, outcome TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS claims(
          entity_id TEXT NOT NULL, version INTEGER NOT NULL, snapshot TEXT NOT NULL,
          PRIMARY KEY(entity_id, version));
        CREATE TABLE IF NOT EXISTS entities(
          entity_id TEXT PRIMARY KEY, version INTEGER NOT NULL,
          group_name TEXT, minutes INTEGER,
          CHECK((group_name IS NULL AND minutes IS NULL) OR
                (group_name IS NOT NULL AND minutes IS NOT NULL)));
        CREATE TABLE IF NOT EXISTS view_totals(
          group_name TEXT PRIMARY KEY, sum_minutes INTEGER NOT NULL,
          n INTEGER NOT NULL CHECK(n > 0), CHECK(sum_minutes >= 0));
        """)

    def close(self):
        self.db.close()

    def dump(self):
        """Stable logical state, including the identities needed for replay."""
        self.db.execute("BEGIN")
        try:
            result = {
                "entities": [list(r) for r in self.db.execute(
                    "SELECT * FROM entities ORDER BY entity_id")],
                "view": [list(r) for r in self.db.execute(
                    "SELECT group_name,sum_minutes,n FROM view_totals ORDER BY group_name")],
                "seen": [list(r) for r in self.db.execute(
                    "SELECT * FROM seen ORDER BY event_id")],
                "claims": [list(r) for r in self.db.execute(
                    "SELECT * FROM claims ORDER BY entity_id,version")],
            }
            self.db.execute("COMMIT")
            return result
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def _contribute(self, group, minutes, sign):
        if group is None:
            return
        old = self.db.execute(
            "SELECT sum_minutes,n FROM view_totals WHERE group_name=?", (group,)).fetchone()
        total, count = old if old else (0, 0)
        total, count = total + sign * minutes, count + sign
        if count < 0 or total < 0 or total > 2**63 - 1:
            raise RuntimeError("view invariant violated")
        if count == 0:
            if total != 0:
                raise RuntimeError("empty group has nonzero sum")
            self.db.execute("DELETE FROM view_totals WHERE group_name=?", (group,))
        else:
            self.db.execute("INSERT INTO view_totals VALUES(?,?,?) "
                            "ON CONFLICT(group_name) DO UPDATE SET "
                            "sum_minutes=excluded.sum_minutes,n=excluded.n",
                            (group, total, count))

    def apply(self, event, fail_at=None):
        """Return a decision; injected/runtime failure raises and preserves commit boundary."""
        if fail_at not in (None, "after_identity", "after_entity", "before_commit", "after_commit"):
            raise ValueError("unknown failure point")
        if not validate(event):
            return "invalid"
        payload, content = canonical(event), snapshot(event)
        eid, version = event["entity_id"], event["version"]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            seen = self.db.execute("SELECT payload FROM seen WHERE event_id=?",
                                   (event["event_id"],)).fetchone()
            if seen:
                decision = "duplicate" if seen[0] == payload else "id_conflict"
                self.db.execute("ROLLBACK")
                return decision
            claim = self.db.execute("SELECT snapshot FROM claims WHERE entity_id=? AND version=?",
                                    (eid, version)).fetchone()
            if claim and claim[0] != content:
                self.db.execute("ROLLBACK")
                return "version_conflict"
            old = self.db.execute("SELECT version,group_name,minutes FROM entities WHERE entity_id=?",
                                  (eid,)).fetchone()
            decision = ("stale" if old and version < old[0] else
                        "same_version" if old and version == old[0] else "applied")
            if decision == "applied" and old is None:
                size = self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
                if size >= LIMIT:
                    self.db.execute("ROLLBACK")
                    return "capacity_rejected"
            self.db.execute("INSERT INTO seen VALUES(?,?,?)", (event["event_id"], payload, decision))
            self.db.execute("INSERT OR IGNORE INTO claims VALUES(?,?,?)", (eid, version, content))
            if fail_at == "after_identity":
                raise InjectedFailure(fail_at)
            if decision == "applied":
                if old:
                    self._contribute(old[1], old[2], -1)
                self._contribute(event["group"], event["minutes"], 1)
                self.db.execute("INSERT INTO entities VALUES(?,?,?,?) "
                                "ON CONFLICT(entity_id) DO UPDATE SET version=excluded.version,"
                                "group_name=excluded.group_name,minutes=excluded.minutes",
                                (eid, version, event["group"], event["minutes"]))
            if fail_at in ("after_entity", "before_commit"):
                raise InjectedFailure(fail_at)
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise
        if fail_at == "after_commit":
            raise InjectedFailure(fail_at)
        return decision


def no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--db", required=True, help="new teaching database path or :memory:")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.input.stat().st_size > 30_000_000:
        p.error("input exceeds 30 MB finite teaching budget")
    events = json.loads(args.input.read_text(), object_pairs_hook=no_duplicate_keys,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    if type(events) is not list or len(events) > 1000:
        p.error("input must be a list with at most 1000 events")
    store = ViewStore(args.db)
    try:
        initial = store.dump()
        trace, counts = [], {}
        for index, event in enumerate(events, 1):
            decision = store.apply(event)
            counts[decision] = counts.get(decision, 0) + 1
            trace.append({"step": index, "decision": decision, "state": store.dump()})
        report = {"protocol": "incremental-view-v1", "initial": initial,
                  "counts": counts, "trace": trace, "final": store.dump()}
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
