"""Independent finite source interpreter; full-snapshot SQL recomputation, no worker import."""
import hashlib
import json
import sqlite3


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def admissible(x):
    if not isinstance(x, dict) or sorted(x) != ["entity_id", "event_id", "group", "minutes", "op", "version"]:
        return False
    strings = [x["entity_id"], x["event_id"]] + ([x["group"]] if x["op"] == "put" else [])
    for value in strings:
        if not isinstance(value, str) or not 0 < len(value) <= 80 or value.strip() != value:
            return False
        try:
            value.encode("utf-8")
        except UnicodeError:
            return False
    if type(x["version"]) is not int or not 0 < x["version"] < 2**63:
        return False
    if x["op"] == "delete":
        return x["group"] is None and x["minutes"] is None
    return x["op"] == "put" and type(x["minutes"]) is int and 0 <= x["minutes"] <= 1_000_000


def rebuild(source, end=None):
    """Choose accepted snapshots, not deltas; independently GROUP BY every prefix."""
    events = source["events"][:end]
    history, seen, claims, decisions, effects = [], {}, {}, [], []

    def current():
        selected = {}
        for snapshot in history:
            entity = snapshot["entity_id"]
            if entity not in selected or snapshot["version"] > selected[entity]["version"]:
                selected[entity] = snapshot
        return selected

    def totals():
        db = sqlite3.connect(":memory:")
        try:
            db.execute("CREATE TABLE live(g TEXT,m INTEGER)")
            db.executemany("INSERT INTO live VALUES(?,?)", [
                (x["group"], x["minutes"]) for x in current().values() if x["op"] == "put"])
            return {g: (s, n) for g, s, n in db.execute("SELECT g,SUM(m),COUNT(*) FROM live GROUP BY g")}
        finally:
            db.close()

    for position, item in enumerate(events, 1):
        effect = None
        if not admissible(item):
            verdict = "invalid"
        else:
            eid, entity, version = item["event_id"], item["entity_id"], item["version"]
            message = encoded(item)
            content = encoded({k: item[k] for k in ("op", "group", "minutes")})
            if eid in seen:
                verdict = "duplicate" if seen[eid][0] == message else "id_conflict"
            elif (entity, version) in claims and claims[entity, version] != content:
                verdict = "version_conflict"
            else:
                old = current().get(entity)
                if old is not None and version < old["version"]:
                    verdict = "stale"
                elif old is not None and version == old["version"]:
                    verdict = "same_version"
                else:
                    verdict = "applied"
                    before = totals()
                    history.append(item)
                    after = totals()
                    delta = []
                    for group in sorted(before.keys() | after.keys()):
                        b, a = before.get(group, (0, 0)), after.get(group, (0, 0))
                        if b != a:
                            delta.append([group, a[0] - b[0], a[1] - b[1]])
                    body = {"protocol": "wwl-db18-recovery-v1", "event": item, "delta": delta}
                    digest = hashlib.sha256(encoded(body).encode("utf-8")).hexdigest()
                    identity = encoded([source["source_id"], eid])
                    result = {"status": "committed", "effect_id": identity,
                              "effect_seq": len(effects) + 1, "fingerprint": digest}
                    effect = {"id": identity, "fingerprint": digest, "body": body, "result": result}
                    effects.append(effect)
                seen[eid] = [message, verdict]
                claims[entity, version] = content
        decisions.append([position, verdict])
    rows, sums = current(), totals()
    state = {"checkpoint": len(events),
             "entities": [[k, encoded(rows[k])] for k in sorted(rows)],
             "seen": [[k, *seen[k]] for k in sorted(seen)],
             "claims": [[e, v, claims[e, v]] for e, v in sorted(claims)],
             "totals": [[g, *sums[g]] for g in sorted(sums)], "positions": decisions,
             "deliveries": sorted([[e["id"], e["fingerprint"], encoded(e["result"])] for e in effects])}
    return {"state": state, "effects": effects,
            "receipts": sorted([[e["id"], e["fingerprint"], encoded(e["result"])] for e in effects]),
            "totals": state["totals"]}


def compare(source, state, sink):
    truth = rebuild(source)
    expected_effects = [[i, e["id"], e["fingerprint"], encoded(e["body"]), encoded(e["result"])]
                        for i, e in enumerate(truth["effects"], 1)]
    checks = {"state": state == truth["state"], "sink_effects": sink["effects"] == expected_effects,
              "sink_receipts": sink["receipts"] == truth["receipts"],
              "sink_totals": sink["totals"] == truth["totals"]}
    return {"checks": checks, "all_match": all(checks.values()),
            "expected_totals": truth["totals"], "actual_totals": sink["totals"],
            "expected_effects": len(expected_effects), "actual_effects": len(sink["effects"])}
