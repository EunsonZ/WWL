"""Independent schema decoder, accepted-snapshot history, SQL temporal join and batch truth."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sqlite3


def encode(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decode(x):
    def string(s):
        if not isinstance(s, str) or not 0 < len(s) <= 80 or s.strip() != s:
            return False
        try:
            s.encode("utf-8")
            return True
        except UnicodeError:
            return False
    def number(n, a, b):
        return isinstance(n, int) and not isinstance(n, bool) and a <= n <= b
    if not isinstance(x, dict):
        return "invalid_envelope", None
    if x.get("kind") == "transport_tombstone":
        return ("transport_tombstone", None) if (sorted(x) == ["key", "kind", "value"] and string(x["key"]) and x["value"] is None) else ("invalid_envelope", None)
    if sorted(x) != ["after", "before", "event_id", "key", "kind", "op", "schema_version", "source_pos", "version"]:
        return "invalid_envelope", None
    if (x["kind"] != "change" or not all(string(x[k]) for k in ("event_id", "key"))
            or not number(x["source_pos"], 1, 1_000_000) or not number(x["version"], 1, 2**63 - 1)
            or x["op"] not in ["c", "u", "d"] or not (x["before"] is None or isinstance(x["before"], dict))):
        return "invalid_envelope", None
    if type(x["schema_version"]) is not int or x["schema_version"] not in [1, 2]:
        return "schema_unsupported", None
    if x["op"] == "d":
        return ("valid", {"version": x["version"], "op": "delete", "after": None}) if x["after"] is None else ("invalid_schema", None)
    a = x["after"]
    if not isinstance(a, dict):
        return "invalid_schema", None
    field = [None, "minutes", "duration_seconds"][x["schema_version"]]
    if field not in a:
        return "missing_measure", None
    if a[field] is None:
        return "null_measure", None
    if not number(a[field], 0, 1_000_000 if field == "minutes" else 60_000_000):
        return "invalid_measure", None
    expected = {"fact_id", "customer_id", "occurred_day", field, "version", "channel", "note", "source_ref"}
    if (set(a) != expected or a["fact_id"] != x["key"] or type(a["version"]) is not int
            or a["version"] != x["version"] or not number(a["occurred_day"], 0, 1_000_000)
            or not all(string(a[k]) for k in ("customer_id", "channel", "note", "source_ref"))):
        return "invalid_schema", None
    normalized = {k: a[k] for k in a if k != field}
    normalized["duration_seconds"] = a[field] if field == "duration_seconds" else 60 * a[field]
    return "valid", {"version": x["version"], "op": "put", "after": normalized}


def sql_as_of(entities, dimensions):
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE facts(id TEXT,c TEXT,t INTEGER,s INTEGER)")
        db.execute("CREATE TABLE dims(sk TEXT,c TEXT,r TEXT,lo INTEGER,hi INTEGER)")
        db.executemany("INSERT INTO facts VALUES(?,?,?,?)", [(key, row["after"]["customer_id"], row["after"]["occurred_day"], row["after"]["duration_seconds"])
                       for key, row in entities.items() if row["op"] == "put"])
        db.executemany("INSERT INTO dims VALUES(?,?,?,?,?)", [(d["sk"], d["customer_id"], d["region"], d["valid_from"], d["valid_to"]) for d in dimensions])
        join = " FROM facts f LEFT JOIN dims d ON f.c=d.c AND d.lo<=f.t AND (d.hi IS NULL OR f.t<d.hi)"
        matches = {}
        for key, sk in db.execute("SELECT f.id,d.sk" + join + " ORDER BY f.id,d.sk"):
            matches.setdefault(key, [])
            if sk is not None:
                matches[key].append(sk)
        grouped = "SELECT f.id,f.s,COUNT(d.sk) AS hits,CASE WHEN COUNT(d.sk)=1 THEN MIN(d.r) END AS region" + join + " GROUP BY f.id,f.s"
        assignments = [[key, matches[key], "matched" if len(matches[key]) == 1 else "unmatched" if not matches[key] else "ambiguous",
                        next(d["region"] for d in dimensions if d["sk"] == matches[key][0]) if len(matches[key]) == 1 else None] for key in sorted(matches)]
        query = ("SELECT CASE hits WHEN 0 THEN 'unmatched' WHEN 1 THEN 'matched' ELSE 'ambiguous' END AS status,region,SUM(s),COUNT(*) FROM ("
                 + grouped + ") GROUP BY status,region ORDER BY status,region")
        return {"assignments": assignments, "groups": [list(row) for row in db.execute(query)]}
    finally:
        db.close()


def rebuild(log, dimensions):
    accepted, seen, claims, quarantine, decisions = [], {}, {}, [], []
    def current():
        rows = {}
        for key, snapshot in accepted:
            if key not in rows or rows[key]["version"] < snapshot["version"]:
                rows[key] = snapshot
        return rows
    for p, event in enumerate(log, 1):
        verdict, row = decode(event)
        if verdict == "transport_tombstone":
            decisions.append(verdict)
            continue
        if verdict != "valid":
            quarantine.append([p, verdict, deepcopy(event)])
            decisions.append(verdict)
            continue
        key, eid, v = event["key"], event["event_id"], row["version"]
        payload = encode(event)
        content = {"op": row["op"], "after": None if row["after"] is None else {k: val for k, val in row["after"].items() if k not in ("fact_id", "version")}}
        content = encode(content)
        if eid in seen:
            verdict = "duplicate" if seen[eid][0] == payload else "id_conflict"
            if verdict == "id_conflict":
                quarantine.append([p, verdict, deepcopy(event)])
        elif (key, v) in claims and claims[key, v] != content:
            verdict = "version_conflict"
            quarantine.append([p, verdict, deepcopy(event)])
        else:
            old = current().get(key)
            if old is None or old["version"] < v:
                verdict = "applied"
                accepted.append((key, deepcopy(row)))
            else:
                verdict = "stale" if old["version"] > v else "same_version"
            seen[eid] = [payload, verdict]
            claims[key, v] = content
        decisions.append(verdict)
    rows = current()
    return decisions, {"entities": [[key, rows[key]] for key in sorted(rows)],
                       "seen": [[key, *seen[key]] for key in sorted(seen)],
                       "claims": [[key, v, claims[key, v]] for key, v in sorted(claims)],
                       "quarantine": quarantine, "as_of": sql_as_of(rows, dimensions)}


def verify(spec, log, actual):
    if actual["protocol"] != "wwl-db19-analysis-v1" or len(actual["trace"]) != len(log):
        raise AssertionError("protocol/trace length")
    dims = spec["dimension_snapshots"][0]["rows"]
    for end in range(1, len(log) + 1):
        decisions, state = rebuild(log[:end], dims)
        if actual["trace"][end-1] != {"position": end, "decision": decisions[-1], "state": state}:
            raise AssertionError(f"prefix {end}: state/identity/as-of/quarantine/decision differs")
    _, state = rebuild(log, dims)
    if actual["final"] != state:
        raise AssertionError("final state")
    rows = dict(state["entities"])
    for d in spec["dimension_snapshots"]:
        if actual["dimension_reports"][d["revision"]] != sql_as_of(rows, d["rows"]):
            raise AssertionError("dimension revision " + d["revision"])
    return {"oracle": "independent-history-sql-asof-v1", "prefixes": len(log),
            "dimension_snapshots": len(spec["dimension_snapshots"]), "groups": state["as_of"]["groups"], "status": "pass"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--deliveries", type=Path, required=True)
    p.add_argument("--actual", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = verify(json.loads(args.input.read_text()), json.loads(args.deliveries.read_text()), json.loads(args.actual.read_text()))
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
