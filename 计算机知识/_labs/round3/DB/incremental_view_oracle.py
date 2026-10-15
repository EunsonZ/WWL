"""Independent log interpreter and SQL batch oracle; never imports the runner."""
import argparse
import json
from pathlib import Path
import sqlite3


def encode(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def admissible(x):
    if not isinstance(x, dict):
        return False
    if sorted(x) != ["entity_id", "event_id", "group", "minutes", "op", "version"]:
        return False
    text = (x["entity_id"], x["event_id"])
    if any(not isinstance(s, str) or not s or len(s) > 80 or s != s.strip() for s in text):
        return False
    try:
        for value in text:
            value.encode("utf-8")
        if isinstance(x["group"], str):
            x["group"].encode("utf-8")
    except UnicodeError:
        return False
    if isinstance(x["version"], bool) or not isinstance(x["version"], int):
        return False
    if x["version"] < 1 or x["version"] >= 2**63:
        return False
    if x["op"] == "delete":
        return (x["group"], x["minutes"]) == (None, None)
    if x["op"] != "put":
        return False
    g, m = x["group"], x["minutes"]
    return (isinstance(g, str) and 0 < len(g) <= 80 and g == g.strip()
            and isinstance(m, int) and not isinstance(m, bool) and 0 <= m <= 1_000_000)


def rebuild(log):
    """Replace full entity snapshots, then use SQL SUM/COUNT over all live rows."""
    identities, claims, rows, decisions = {}, {}, {}, []
    for event in log:
        if not admissible(event):
            decisions.append("invalid")
            continue
        message = encode(event)
        key, entity, v = event["event_id"], event["entity_id"], event["version"]
        content = encode({"op": event["op"], "group": event["group"], "minutes": event["minutes"]})
        if key in identities:
            decisions.append("duplicate" if identities[key][0] == message else "id_conflict")
            continue
        if (entity, v) in claims and claims[entity, v] != content:
            decisions.append("version_conflict")
            continue
        if entity not in rows and len(rows) >= 100_000:
            decisions.append("capacity_rejected")
            continue
        current = rows.get(entity)
        if current is None or current[0] < v:
            rows[entity] = (v, event["group"], event["minutes"])
            result = "applied"
        elif current[0] == v:
            result = "same_version"
        else:
            result = "stale"
        identities[key] = (message, result)
        claims[entity, v] = content
        decisions.append(result)
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE live(entity TEXT PRIMARY KEY, g TEXT, minutes INTEGER NOT NULL)")
        db.executemany("INSERT INTO live VALUES(?,?,?)",
                       [(id, row[1], row[2]) for id, row in rows.items() if row[1] is not None])
        view = [list(r) for r in db.execute(
            "SELECT g,SUM(minutes),COUNT(*) FROM live GROUP BY g ORDER BY g")]
        global_sum, n = db.execute("SELECT SUM(minutes),COUNT(*) FROM live").fetchone()
    finally:
        db.close()
    state = {
        "entities": [[id, *rows[id]] for id in sorted(rows)],
        "seen": [[id, *identities[id]] for id in sorted(identities)],
        "claims": [[id, v, claims[id, v]] for id, v in sorted(claims)],
        "view": view,
    }
    return decisions, state, {"sum_minutes": global_sum, "count": n}


def verify(events, actual):
    empty = {k: [] for k in ("entities", "view", "seen", "claims")}
    if actual["protocol"] != "incremental-view-v1" or actual["initial"] != empty:
        raise ValueError("oracle requires a fresh empty initial database")
    if len(actual["trace"]) != len(events):
        raise AssertionError("trace length")
    counts, checks = {}, []
    for end in range(1, len(events) + 1):
        decisions, truth, global_metric = rebuild(events[:end])
        step = actual["trace"][end - 1]
        if step != {"step": end, "decision": decisions[-1], "state": truth}:
            raise AssertionError(f"prefix {end}: decision or full state differs")
        counts[decisions[-1]] = counts.get(decisions[-1], 0) + 1
        checks.append({"step": end, "decision": decisions[-1], "view": truth["view"],
                       "global_batch": global_metric})
    _, truth, global_metric = rebuild(events)
    if actual["final"] != truth or actual["counts"] != counts:
        raise AssertionError("final state or decision counts differ")
    return {"oracle": "independent-snapshot-and-sql-v1", "prefixes": checks,
            "final": truth, "counts": counts, "global_batch": global_metric}


def read_json(path):
    def unique_object(pairs):
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError("JSON object has repeated keys")
        return dict(pairs)

    def reject_constant(token):
        raise ValueError("nonfinite JSON token: " + token)

    return json.loads(path.read_text(), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.input.stat().st_size > 30_000_000:
        parser.error("input exceeds 30 MB finite teaching budget")
    events = read_json(args.input)
    if type(events) is not list or len(events) > 1000:
        parser.error("at most 1000 events in the finite prefix check")
    result = verify(events, read_json(args.actual))
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
