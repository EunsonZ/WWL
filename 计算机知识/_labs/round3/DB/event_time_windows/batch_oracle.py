"""Independent prefix interpreter: rebuild accepted facts, SQL aggregate; no reducer import."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sqlite3


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def admissible(x):
    if not isinstance(x, dict):
        return False
    if list(sorted(x)) == ["watermark"]:
        return type(x["watermark"]) is int and 0 <= x["watermark"] <= 1_000_000
    fields = ["entity_id", "event_id", "event_time", "group", "minutes", "op", "version"]
    if sorted(x) != fields:
        return False
    strings = [x["entity_id"], x["event_id"]]
    if x["op"] == "put":
        strings.append(x["group"])
    for s in strings:
        if not isinstance(s, str) or not 0 < len(s) <= 80 or s.strip() != s:
            return False
        try:
            s.encode("utf-8")
        except UnicodeError:
            return False
    if type(x["version"]) is not int or not 0 < x["version"] < 2**63:
        return False
    if x["op"] == "delete":
        return (x["event_time"], x["group"], x["minutes"]) == (None, None, None)
    return (x["op"] == "put" and type(x["minutes"]) is int
            and 0 <= x["minutes"] <= 1_000_000 and type(x["event_time"]) is int
            and 0 <= x["event_time"] <= 1_000_000)


def rebuild(log, width, lateness):
    """All windows use full accepted history and SQL, never subtract old contributions."""
    accepted, receipts, claims, touched, versions, outputs, side, decisions = [], {}, {}, set(), {}, [], [], []
    mark = -1

    def facts():
        # The input contract is full after-images, so greatest accepted version wins.
        result = {}
        for event in accepted:
            entity = event["entity_id"]
            if entity not in result or result[entity]["version"] < event["version"]:
                result[entity] = event
        return result

    def location(event):
        if event is None or event["op"] != "put":
            return None
        return (width * (event["event_time"] // width), event["group"])

    def closed(key):
        return key is not None and mark >= key[0] + width + lateness

    def batch():
        db = sqlite3.connect(":memory:")
        try:
            db.execute("CREATE TABLE live(w INTEGER,g TEXT,m INTEGER)")
            db.executemany("INSERT INTO live VALUES(?,?,?)", [
                (*location(e), e["minutes"]) for e in facts().values()
                if location(e) is not None and not closed(location(e))])
            result = {(w, g): [s, n] for w, g, s, n in db.execute(
                "SELECT w,g,SUM(m),COUNT(*) FROM live GROUP BY w,g")}
            return {key: result.get(key, [0, 0]) for key in touched if not closed(key)}
        finally:
            db.close()

    def publish(key, phase, pos, values):
        versions[key] = versions.get(key, 0) + 1
        outputs.append({"window_start": key[0], "window_end": key[0] + width,
                        "group": key[1], "revision": versions[key],
                        "sum_minutes": values[0], "count": values[1], "phase": phase,
                        "position": pos, "watermark": mark})

    for pos, x in enumerate(log, 1):
        if not admissible(x):
            decisions.append("invalid")
            continue
        if "watermark" in x:
            if x["watermark"] < mark:
                decisions.append("watermark_regression")
                continue
            old_values = batch()
            previous, mark = mark, x["watermark"]
            for key in sorted(old_values):
                if closed(key):
                    publish(key, "final", pos, old_values[key])
                elif previous < key[0] + width <= mark:
                    publish(key, "on_time", pos, old_values[key])
            touched = {k for k in touched if not closed(k)}
            decisions.append("watermark")
            continue
        eid, entity, v = x["event_id"], x["entity_id"], x["version"]
        payload = encode(x)
        content = encode({k: x[k] for k in ("op", "group", "minutes", "event_time")})
        if eid in receipts:
            decisions.append("duplicate" if receipts[eid][0] == payload else "id_conflict")
            continue
        if (entity, v) in claims and claims[entity, v] != content:
            decisions.append("version_conflict")
            continue
        current = facts().get(entity)
        if current is not None and v < current["version"]:
            result = "stale"
        elif current is not None and v == current["version"]:
            result = "same_version"
        else:
            old, new = location(current), location(x)
            if closed(old) or closed(new):
                result = "expired_both" if closed(old) and closed(new) else (
                    "expired_old" if closed(old) else "expired_new")
                side.append({"position": pos, "reason": result,
                             "watermark": mark, "event": deepcopy(x)})
            else:
                result = "applied"
                accepted.append(deepcopy(x))
                affected = {k for k in (old, new) if k is not None}
                touched |= affected
                values = batch()
                for key in sorted(affected):
                    publish(key, "late" if mark >= key[0] + width else "early", pos, values[key])
        receipts[eid] = [payload, result]
        claims[entity, v] = content
        decisions.append(result)
    rows, values = facts(), batch()
    return decisions, {"watermark": mark,
                       "entities": [[k, rows[k]] for k in sorted(rows)],
                       "seen": [[k, *receipts[k]] for k in sorted(receipts)],
                       "claims": [[e, v, claims[e, v]] for e, v in sorted(claims)],
                       "cells": [[w, g, *values[w, g]] for w, g in sorted(values)],
                       "revisions": [[w, g, versions[w, g]] for w, g in sorted(versions)],
                       "outputs": outputs, "side": side}


def verify(log, actual):
    if actual["protocol"] != "event-time-windows-v1" or len(actual["trace"]) != len(log):
        raise AssertionError("protocol or trace length")
    width, lateness = actual["width"], actual["lateness"]
    for end in range(1, len(log) + 1):
        choices, state = rebuild(log[:end], width, lateness)
        expected = {"position": end, "decision": choices[-1], "state": state}
        if actual["trace"][end - 1] != expected:
            raise AssertionError(f"prefix {end}: decisions/identity/state/revision/output/side differ")
    _, final = rebuild(log, width, lateness)
    if actual["final"] != final:
        raise AssertionError("final")
    return {"oracle": "independent-history-sql-v1", "prefixes_checked": len(log),
            "width": width, "lateness": lateness, "outputs": len(final["outputs"]),
            "side": [[s["position"], s["reason"], s["event"]["event_id"]] for s in final["side"]],
            "status": "pass"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(json.loads(args.input.read_text(encoding="utf-8")),
                    json.loads(args.actual.read_text(encoding="utf-8")))
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
