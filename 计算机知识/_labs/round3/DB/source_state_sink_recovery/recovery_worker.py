"""Two-resource SQLite recovery model; deliberately bad modes are counterexamples."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

PROTOCOL = "wwl-db18-recovery-v1"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_source(path):
    def unique(pairs):
        if len({k for k, _ in pairs}) != len(pairs):
            raise ValueError("duplicate JSON key")
        return dict(pairs)
    def finite(_):
        raise ValueError("nonfinite JSON constant")
    data = path.read_bytes()
    if len(data) > 1_000_000:
        raise ValueError("finite source exceeds 1 MB")
    source = json.loads(data, object_pairs_hook=unique, parse_constant=finite)
    if (type(source) is not dict or set(source) != {"protocol", "source_id", "events"}
            or source["protocol"] != "wwl-db18-source-v1"
            or not text(source["source_id"]) or type(source["events"]) is not list
            or len(source["events"]) > 1000):
        raise ValueError("source envelope")
    return source, hashlib.sha256(data).hexdigest()


def text(value):
    if type(value) is not str or not 1 <= len(value) <= 80 or value != value.strip():
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def valid(event):
    if type(event) is not dict or set(event) != {"event_id", "entity_id", "version", "op", "group", "minutes"}:
        return False
    if not text(event["event_id"]) or not text(event["entity_id"]):
        return False
    if type(event["version"]) is not int or not 1 <= event["version"] < 2**63:
        return False
    if event["op"] == "delete":
        return event["group"] is None and event["minutes"] is None
    return (event["op"] == "put" and text(event["group"])
            and type(event["minutes"]) is int and 0 <= event["minutes"] <= 1_000_000)


@contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise


def open_resource(path, source, source_hash, role, sink_mode):
    db = sqlite3.connect(path, isolation_level=None, timeout=2)
    try:
        actual = db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if actual.lower() != "wal":
            raise RuntimeError("WAL unavailable")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA fullfsync=ON")
        db.execute("PRAGMA wal_autocheckpoint=0")
        metadata = {"protocol": PROTOCOL, "source_id": source["source_id"],
                    "source_sha256": source_hash, "role": role, "sink_mode": sink_mode}
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables:
            if "metadata" not in tables or dict(db.execute("SELECT k,v FROM metadata")) != metadata:
                raise ValueError("resource/source/protocol identity mismatch; no migration")
            return db
        with transaction(db):
            db.execute("CREATE TABLE metadata(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            db.executemany("INSERT INTO metadata VALUES(?,?)", sorted(metadata.items()))
            if role == "state":
                statements = ["CREATE TABLE checkpoint(singleton INTEGER PRIMARY KEY CHECK(singleton=1),p INTEGER NOT NULL)",
                              "CREATE TABLE entities(id TEXT PRIMARY KEY,payload TEXT NOT NULL)",
                              "CREATE TABLE seen(id TEXT PRIMARY KEY,payload TEXT NOT NULL,decision TEXT NOT NULL)",
                              "CREATE TABLE claims(entity TEXT,v INTEGER,content TEXT NOT NULL,PRIMARY KEY(entity,v))",
                              "CREATE TABLE totals(g TEXT PRIMARY KEY,s INTEGER NOT NULL,n INTEGER NOT NULL)",
                              "CREATE TABLE positions(p INTEGER PRIMARY KEY,decision TEXT NOT NULL)",
                              "CREATE TABLE deliveries(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,result TEXT NOT NULL)"]
                for statement in statements:
                    db.execute(statement)
                db.execute("INSERT INTO checkpoint VALUES(1,0)")
            else:
                db.execute("CREATE TABLE effects(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL,fingerprint TEXT NOT NULL,body TEXT NOT NULL,result TEXT NOT NULL)")
                db.execute("CREATE TABLE receipts(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,result TEXT NOT NULL)")
                db.execute("CREATE TABLE totals(g TEXT PRIMARY KEY,s INTEGER NOT NULL,n INTEGER NOT NULL)")
        return db
    except BaseException:
        db.close()
        raise


def add_totals(db, delta):
    for group, ds, dn in delta:
        row = db.execute("SELECT s,n FROM totals WHERE g=?", (group,)).fetchone() or (0, 0)
        total, count = row[0] + ds, row[1] + dn
        if count < 0 or total < 0 or (count == 0 and total != 0):
            raise ValueError("inconsistent aggregate")
        if count == 0:
            db.execute("DELETE FROM totals WHERE g=?", (group,))
        else:
            db.execute("INSERT OR REPLACE INTO totals VALUES(?,?,?)", (group, total, count))


def apply_event(db, event, source_id):
    if not valid(event):
        return "invalid", None
    eid, entity, version = event["event_id"], event["entity_id"], event["version"]
    payload = canonical(event)
    seen = db.execute("SELECT payload FROM seen WHERE id=?", (eid,)).fetchone()
    if seen:
        return ("duplicate" if seen[0] == payload else "id_conflict"), None
    content = canonical({k: event[k] for k in ("op", "group", "minutes")})
    claim = db.execute("SELECT content FROM claims WHERE entity=? AND v=?", (entity, version)).fetchone()
    if claim and claim[0] != content:
        return "version_conflict", None
    row = db.execute("SELECT payload FROM entities WHERE id=?", (entity,)).fetchone()
    old = json.loads(row[0]) if row else None
    if old and version <= old["version"]:
        decision = "stale" if version < old["version"] else "same_version"
        effect = None
    else:
        decision, delta = "applied", {}
        for item, sign in ((old, -1), (event, 1)):
            if item and item["op"] == "put":
                ds, dn = delta.get(item["group"], (0, 0))
                delta[item["group"]] = (ds + sign * item["minutes"], dn + sign)
        delta = [[g, *delta[g]] for g in sorted(delta) if delta[g] != (0, 0)]
        add_totals(db, delta)
        db.execute("INSERT OR REPLACE INTO entities VALUES(?,?)", (entity, payload))
        body = {"protocol": PROTOCOL, "event": event, "delta": delta}
        effect = {"id": canonical([source_id, eid]), "fingerprint": fingerprint(body), "body": body}
    db.execute("INSERT INTO seen VALUES(?,?,?)", (eid, payload, decision))
    db.execute("INSERT OR IGNORE INTO claims VALUES(?,?,?)", (entity, version, content))
    return decision, effect


def deliver(sink, effect, sink_mode):
    """The receipt and the teaching effect share THIS sink transaction."""
    if effect["fingerprint"] != fingerprint(effect["body"]):
        raise ValueError("incorrect fingerprint")
    with transaction(sink):
        prior = sink.execute("SELECT fingerprint,result FROM receipts WHERE id=?", (effect["id"],)).fetchone()
        if prior:
            if prior[0] != effect["fingerprint"]:
                raise ValueError("effect identity conflict")
            return json.loads(prior[1]), False
        add_totals(sink, effect["body"]["delta"])
        seq = sink.execute("SELECT COALESCE(MAX(seq),0)+1 FROM effects").fetchone()[0]
        result = {"status": "committed", "effect_id": effect["id"], "effect_seq": seq,
                  "fingerprint": effect["fingerprint"]}
        encoded = canonical(result)
        sink.execute("INSERT INTO effects VALUES(?,?,?,?,?)",
                     (seq, effect["id"], effect["fingerprint"], canonical(effect["body"]), encoded))
        if sink_mode == "dedupe":
            sink.execute("INSERT INTO receipts VALUES(?,?,?)", (effect["id"], effect["fingerprint"], encoded))
    return result, True


def state_snapshot(db):
    return {"checkpoint": db.execute("SELECT p FROM checkpoint").fetchone()[0],
            "entities": [list(r) for r in db.execute("SELECT id,payload FROM entities ORDER BY id")],
            "seen": [list(r) for r in db.execute("SELECT id,payload,decision FROM seen ORDER BY id")],
            "claims": [list(r) for r in db.execute("SELECT entity,v,content FROM claims ORDER BY entity,v")],
            "totals": [list(r) for r in db.execute("SELECT g,s,n FROM totals ORDER BY g")],
            "positions": [list(r) for r in db.execute("SELECT p,decision FROM positions ORDER BY p")],
            "deliveries": [list(r) for r in db.execute("SELECT id,fingerprint,result FROM deliveries ORDER BY id")]}


def record(value):
    print(canonical(value), flush=True)


def barrier(args, kind, position, extra=None):
    if args.fault == kind and args.at == position:
        record({"phase": "barrier", "kind": kind, "position": position,
                "pid": os.getpid(), "token": args.token, **(extra or {})})
        # Parent must observe the exact structured barrier before killing its child.
        if sys.stdin.readline() != "continue\n":
            raise RuntimeError("barrier closed without continuation")


def consume(args):
    source, source_hash = read_source(args.source)
    if not 1 <= args.batch_size <= 100 or args.at < 0:
        raise ValueError("batch size 1..100 and nonnegative fault position required")
    if args.fault == "after_offset" and args.checkpoint_mode != "offset_first_bad":
        raise ValueError("after_offset is exclusively the bad-order cut")
    if args.state.resolve() == args.sink.resolve():
        raise ValueError("state and sink must be distinct resources")
    state = open_resource(args.state, source, source_hash, "state", args.sink_mode)
    sink = None
    try:
        sink = open_resource(args.sink, source, source_hash, "sink", args.sink_mode)
        start = state.execute("SELECT p FROM checkpoint").fetchone()[0]
        if not 0 <= start <= len(source["events"]):
            raise ValueError("checkpoint outside source")
        record({"phase": "start", "position": start, "pid": os.getpid(),
                "source_sha256": source_hash, "journal_mode": state.execute("PRAGMA journal_mode").fetchone()[0],
                "synchronous": state.execute("PRAGMA synchronous").fetchone()[0],
                "fullfsync": state.execute("PRAGMA fullfsync").fetchone()[0],
                "wal_autocheckpoint": state.execute("PRAGMA wal_autocheckpoint").fetchone()[0],
                "sink_settings": {key: sink.execute("PRAGMA " + key).fetchone()[0]
                                  for key in ("journal_mode", "synchronous", "fullfsync", "wal_autocheckpoint")}})
        for low in range(start, len(source["events"]), args.batch_size):
            end = min(low + args.batch_size, len(source["events"]))
            if args.checkpoint_mode == "offset_first_bad":
                with transaction(state):
                    state.execute("UPDATE checkpoint SET p=?", (end,))
                barrier(args, "after_offset", end)
            with transaction(state):
                for index in range(low, end):
                    event = source["events"][index]
                    decision, effect = apply_event(state, event, source["source_id"])
                    if effect:
                        result, created = deliver(sink, effect, args.sink_mode)
                        state.execute("INSERT INTO deliveries VALUES(?,?,?)",
                                      (effect["id"], effect["fingerprint"], canonical(result)))
                        record({"phase": "sink_committed", "position": index + 1,
                                "effect": effect, "result": result, "new_effect": created})
                        barrier(args, "after_sink", index + 1, {"result": result})
                    state.execute("INSERT INTO positions VALUES(?,?)", (index + 1, decision))
                    record({"phase": "evaluated_uncommitted", "position": index + 1, "decision": decision})
                if args.checkpoint_mode == "atomic":
                    state.execute("UPDATE checkpoint SET p=?", (end,))
                barrier(args, "before_state_commit", end)
            record({"phase": "state_committed", "position": end, "state": state_snapshot(state)})
            barrier(args, "after_state_commit", end)
        record({"phase": "finished", "position": len(source["events"])})
    finally:
        if sink is not None:
            sink.close()
        state.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--sink", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--sink-mode", choices=("dedupe", "naive_bad"), default="dedupe")
    parser.add_argument("--checkpoint-mode", choices=("atomic", "offset_first_bad"), default="atomic")
    parser.add_argument("--fault", choices=("none", "after_sink", "after_offset", "before_state_commit", "after_state_commit"), default="none")
    parser.add_argument("--at", type=int, default=0)
    parser.add_argument("--token", default="")
    consume(parser.parse_args())


if __name__ == "__main__":
    main()
