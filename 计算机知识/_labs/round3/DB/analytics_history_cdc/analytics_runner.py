"""Schema-aware current facts and temporal dimension attribution; finite in-memory model."""
import argparse
from copy import deepcopy
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_json(path):
    def unique(pairs):
        if len({k for k, _ in pairs}) != len(pairs):
            raise ValueError("duplicate JSON key")
        return dict(pairs)
    def finite(_):
        raise ValueError("nonfinite JSON constant")
    if path.stat().st_size > 1_000_000:
        raise ValueError("finite input exceeds 1 MB")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=finite)


def text(value):
    if type(value) is not str or not 1 <= len(value) <= 80 or value != value.strip():
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def integer(value, lo=0, hi=1_000_000):
    return type(value) is int and lo <= value <= hi


def normalize(event):
    if type(event) is not dict:
        return "invalid_envelope", None
    if event.get("kind") == "transport_tombstone":
        if set(event) == {"kind", "key", "value"} and text(event["key"]) and event["value"] is None:
            return "transport_tombstone", None
        return "invalid_envelope", None
    if set(event) != {"kind", "event_id", "source_pos", "schema_version", "op", "key", "version", "before", "after"}:
        return "invalid_envelope", None
    if (event["kind"] != "change" or not text(event["event_id"]) or not text(event["key"])
            or not integer(event["source_pos"], 1) or not integer(event["version"], 1, 2**63 - 1)
            or event["op"] not in ("c", "u", "d")
            or (event["before"] is not None and type(event["before"]) is not dict)):
        return "invalid_envelope", None
    schema = event["schema_version"]
    if type(schema) is not int or schema not in (1, 2):
        return "schema_unsupported", None
    if event["op"] == "d":
        if event["after"] is not None:
            return "invalid_schema", None
        return "valid", {"op": "delete", "version": event["version"], "after": None}
    after = event["after"]
    if type(after) is not dict:
        return "invalid_schema", None
    measure = "minutes" if schema == 1 else "duration_seconds"
    if measure not in after:
        return "missing_measure", None
    if after[measure] is None:
        return "null_measure", None
    if not integer(after[measure], 0, 1_000_000 if schema == 1 else 60_000_000):
        return "invalid_measure", None
    required = {"fact_id", "customer_id", "occurred_day", measure, "version", "channel", "note", "source_ref"}
    if (set(after) != required or after["fact_id"] != event["key"]
            or type(after["version"]) is not int or after["version"] != event["version"]
            or not integer(after["occurred_day"])
            or any(not text(after[k]) for k in ("customer_id", "channel", "note", "source_ref"))):
        return "invalid_schema", None
    normalized = {k: v for k, v in after.items() if k != measure}
    normalized["duration_seconds"] = after[measure] * (60 if schema == 1 else 1)
    return "valid", {"op": "put", "version": event["version"], "after": normalized}


def attribute(entities, dimensions):
    identities = set()
    for dim in dimensions:
        if (set(dim) != {"sk", "customer_id", "region", "valid_from", "valid_to"}
                or any(not text(dim[k]) for k in ("sk", "customer_id", "region"))
                or dim["sk"] in identities or not integer(dim["valid_from"])
                or (dim["valid_to"] is not None and not integer(dim["valid_to"], dim["valid_from"] + 1))):
            raise ValueError("dimension row schema or duplicate surrogate key")
        identities.add(dim["sk"])
    assignments, totals = [], {}
    for key in sorted(entities):
        entity = entities[key]
        if entity["op"] != "put":
            continue
        fact = entity["after"]
        matches = sorted([dim for dim in dimensions if dim["customer_id"] == fact["customer_id"]
                          and dim["valid_from"] <= fact["occurred_day"]
                          and (dim["valid_to"] is None or fact["occurred_day"] < dim["valid_to"])], key=lambda d: d["sk"])
        status = "matched" if len(matches) == 1 else "unmatched" if not matches else "ambiguous"
        region = matches[0]["region"] if len(matches) == 1 else None
        assignments.append([key, [d["sk"] for d in matches], status, region])
        group = (status, region)
        total, count = totals.get(group, (0, 0))
        totals[group] = (total + fact["duration_seconds"], count + 1)
    return {"assignments": assignments,
            "groups": [[s, r, *totals[s, r]] for s, r in sorted(totals, key=lambda k: (k[0], k[1] or ""))]}


class Model:
    def __init__(self):
        self.entities, self.seen, self.claims, self.quarantine = {}, {}, {}, []

    def apply(self, event, position):
        reason, row = normalize(event)
        if reason == "transport_tombstone":
            return reason
        if reason != "valid":
            self.quarantine.append([position, reason, deepcopy(event)])
            return reason
        eid, key, version = event["event_id"], event["key"], row["version"]
        payload = canonical(event)
        if eid in self.seen:
            reason = "duplicate" if self.seen[eid][0] == payload else "id_conflict"
            if reason == "id_conflict":
                self.quarantine.append([position, reason, deepcopy(event)])
            return reason
        normalized_content = deepcopy(row)
        del normalized_content["version"]
        if normalized_content["after"] is not None:
            del normalized_content["after"]["version"]
            del normalized_content["after"]["fact_id"]
        content = canonical(normalized_content)
        if (key, version) in self.claims and self.claims[key, version] != content:
            self.quarantine.append([position, "version_conflict", deepcopy(event)])
            return "version_conflict"
        old = self.entities.get(key)
        if old is None or old["version"] < version:
            reason = "applied"
            self.entities[key] = deepcopy(row)
        else:
            reason = "stale" if old["version"] > version else "same_version"
        self.seen[eid] = [payload, reason]
        self.claims[key, version] = content
        return reason

    def snapshot(self, dimensions):
        return {"entities": [[key, self.entities[key]] for key in sorted(self.entities)],
                "seen": [[key, *self.seen[key]] for key in sorted(self.seen)],
                "claims": [[key, v, self.claims[key, v]] for key, v in sorted(self.claims)],
                "quarantine": deepcopy(self.quarantine), "as_of": attribute(self.entities, dimensions)}


def run(spec, deliveries):
    if type(deliveries) is not list or len(deliveries) > 1000:
        raise ValueError("finite delivery list of at most 1000 items")
    model, trace = Model(), []
    for p, item in enumerate(deliveries, 1):
        decision = model.apply(item, p)
        trace.append({"position": p, "decision": decision,
                      "state": deepcopy(model.snapshot(spec["dimension_snapshots"][0]["rows"]))})
    return {"protocol": "wwl-db19-analysis-v1", "dimension_revision": spec["dimension_snapshots"][0]["revision"],
            "trace": trace, "final": deepcopy(model.snapshot(spec["dimension_snapshots"][0]["rows"])),
            "dimension_reports": {d["revision"]: attribute(model.entities, d["rows"])
                                  for d in spec["dimension_snapshots"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--deliveries", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(read_json(args.input), read_json(args.deliveries))
    args.out.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
