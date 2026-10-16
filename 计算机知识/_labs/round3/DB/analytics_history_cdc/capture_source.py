"""Actual local trigger capture with a transactional schema/unit migration; no connector."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sqlite3


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def columns(schema):
    return ["fact_id", "customer_id", "occurred_day", "minutes" if schema == 1 else "duration_seconds",
            "version", "channel", "note", "source_ref"]


def install_triggers(db, schema):
    def image(prefix):
        return "json_object(" + ",".join("'" + key + "'," + prefix + "." + key for key in columns(schema)) + ")"
    for kind, action in (("c", "INSERT"), ("u", "UPDATE"), ("d", "DELETE")):
        before = image("OLD") if kind != "c" else "NULL"
        after = image("NEW") if kind != "d" else "NULL"
        key = "OLD.fact_id" if kind == "d" else "NEW.fact_id"
        version = "(SELECT v FROM versions WHERE id=" + key + ")"
        db.execute("CREATE TRIGGER capture_" + kind + " AFTER " + action + " ON facts BEGIN "
                   "INSERT INTO changes(schema_v,op,key,v,before_json,after_json) VALUES("
                   + str(schema) + ",'" + kind + "'," + key + "," + version + "," + before + "," + after + "); END")


def create_facts(db, schema, triggers=True):
    db.execute("CREATE TABLE facts(fact_id TEXT PRIMARY KEY,customer_id TEXT NOT NULL,occurred_day INTEGER NOT NULL,"
               + columns(schema)[3] + " INTEGER NOT NULL,version INTEGER NOT NULL,channel TEXT NOT NULL,note TEXT NOT NULL,source_ref TEXT NOT NULL)")
    if triggers:
        install_triggers(db, schema)


def capture(spec, db_path):
    if db_path.exists():
        raise ValueError("capture requires a NEW source database path")
    db = sqlite3.connect(db_path, isolation_level=None)
    trace, schema = [], 1
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE versions(id TEXT PRIMARY KEY,v INTEGER NOT NULL)")
        db.execute("CREATE TABLE changes(p INTEGER PRIMARY KEY AUTOINCREMENT,schema_v INTEGER,op TEXT,key TEXT,v INTEGER,before_json TEXT,after_json TEXT)")
        create_facts(db, schema)
        for index, operation in enumerate(spec["source_operations"], 1):
            start_count = db.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
            db.execute("BEGIN IMMEDIATE")
            try:
                if operation["op"] == "migrate_to_seconds":
                    if schema != 1:
                        raise ValueError("only the declared v1-to-v2 migration is supported")
                    for kind in ("c", "u", "d"):
                        db.execute("DROP TRIGGER capture_" + kind)
                    db.execute("ALTER TABLE facts RENAME TO old_facts")
                    create_facts(db, 2, triggers=False)
                    # Layout/unit migration preserves facts; it is not a new business change.
                    db.execute("INSERT INTO facts SELECT fact_id,customer_id,occurred_day,minutes*60,version,channel,note,source_ref FROM old_facts")
                    db.execute("DROP TABLE old_facts")
                    install_triggers(db, 2)
                    schema = 2
                else:
                    row = operation.get("row")
                    key = row["fact_id"] if row else operation["key"]
                    v = row["version"] if row else operation["version"]
                    prior = db.execute("SELECT v FROM versions WHERE id=?", (key,)).fetchone()
                    if v != (prior[0] + 1 if prior else 1):
                        raise ValueError("source authority version must advance exactly once")
                    db.execute("INSERT OR REPLACE INTO versions VALUES(?,?)", (key, v))
                    if operation["op"] == "delete":
                        if db.execute("DELETE FROM facts WHERE fact_id=?", (key,)).rowcount != 1:
                            raise ValueError("source delete missing fact")
                    elif operation["op"] == "update":
                        names = columns(schema)
                        if db.execute("UPDATE facts SET "+",".join(k+"=?" for k in names[1:])+" WHERE fact_id=?",
                                      [row[k] for k in names[1:]]+[key]).rowcount != 1:
                            raise ValueError("source update missing fact")
                    else:
                        db.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?)", [row[k] for k in columns(schema)])
                if operation["op"] == "rollback_probe":
                    db.execute("ROLLBACK")
                    committed = False
                else:
                    db.execute("COMMIT")
                    committed = True
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
            end_count = db.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
            trace.append({"operation": index, "op": operation["op"], "committed": committed,
                          "schema_version": schema, "capture_before": start_count, "capture_after": end_count})
        changes = []
        for p, sv, op, key, v, before, after in db.execute("SELECT * FROM changes ORDER BY p"):
            changes.append({"kind": "change", "event_id": spec["source_id"]+":"+str(p), "source_pos": p,
                            "schema_version": sv, "op": op, "key": key, "version": v,
                            "before": json.loads(before) if before else None,
                            "after": json.loads(after) if after else None})
        live = [dict(zip(columns(schema), row)) for row in db.execute("SELECT * FROM facts ORDER BY fact_id")]
        return {"changes": changes, "trace": trace, "source_live_rows": live,
                "versions": [list(r) for r in db.execute("SELECT id,v FROM versions ORDER BY id")],
                "integrity": db.execute("PRAGMA integrity_check").fetchone()[0]}
    finally:
        db.close()


def deliveries(spec, captured):
    result = []
    for instruction in spec["delivery_plan"]:
        if "literal" in instruction:
            result.append(deepcopy(instruction["literal"]))
            continue
        event = deepcopy(captured[instruction["capture"] - 1])
        event.update(instruction.get("patch", {}))
        for key in instruction.get("after_remove", []):
            del event["after"][key]
        if "after_patch" in instruction:
            event["after"].update(instruction["after_patch"])
        result.append(event)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    spec = json.loads(args.input.read_text(encoding="utf-8"))
    result = capture(spec, args.db)
    write(args.out / "captured_changes.json", result["changes"])
    write(args.out / "capture-observed.json", result)
    write(args.out / "delivery_log.json", deliveries(spec, result["changes"]))


if __name__ == "__main__":
    main()
