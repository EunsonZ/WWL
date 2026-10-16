"""Finite, in-memory event-time revision model; no engine or durable sink."""
import argparse
from copy import deepcopy
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_json(path):
    def unique(pairs):
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError("duplicate JSON key")
        return dict(pairs)
    def finite(_):
        raise ValueError("nonfinite JSON constant")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=finite)


def valid(item):
    def text(s):
        if type(s) is not str or not 1 <= len(s) <= 80 or s != s.strip():
            return False
        try:
            s.encode("utf-8")
        except UnicodeError:
            return False
        return True
    def integer(n, low, high):
        return type(n) is int and low <= n <= high
    if type(item) is not dict:
        return False
    if set(item) == {"watermark"}:
        return integer(item["watermark"], 0, 1_000_000)
    if set(item) != {"event_id", "entity_id", "version", "op", "group", "minutes", "event_time"}:
        return False
    if not text(item["event_id"]) or not text(item["entity_id"]):
        return False
    if not integer(item["version"], 1, 2**63 - 1):
        return False
    if item["op"] == "delete":
        return all(item[k] is None for k in ("group", "minutes", "event_time"))
    return (item["op"] == "put" and text(item["group"])
            and integer(item["minutes"], 0, 1_000_000)
            and integer(item["event_time"], 0, 1_000_000))


class Windows:
    def __init__(self, width=10, lateness=5):
        if type(width) is not int or not 1 <= width <= 1000:
            raise ValueError("width must be integer 1..1000")
        if type(lateness) is not int or not 0 <= lateness <= 1000:
            raise ValueError("lateness must be integer 0..1000")
        self.width, self.lateness, self.watermark = width, lateness, -1
        self.entities, self.seen, self.claims, self.cells = {}, {}, {}, {}
        self.revisions, self.outputs, self.side = {}, [], []

    def key(self, event):
        if event is None or event["op"] == "delete":
            return None
        return (event["event_time"] // self.width * self.width, event["group"])

    def expired(self, key):
        return key is not None and self.watermark >= key[0] + self.width + self.lateness

    def emit(self, key, phase, position):
        self.revisions[key] = self.revisions.get(key, 0) + 1
        total, count = self.cells[key]
        self.outputs.append({"window_start": key[0], "window_end": key[0] + self.width,
                             "group": key[1], "revision": self.revisions[key],
                             "sum_minutes": total, "count": count, "phase": phase,
                             "position": position, "watermark": self.watermark})

    def apply(self, item, position):
        if not valid(item):
            return "invalid"
        if "watermark" in item:
            mark = item["watermark"]
            if mark < self.watermark:
                return "watermark_regression"
            previous, self.watermark = self.watermark, mark
            for key in sorted(list(self.cells)):
                end = key[0] + self.width
                if self.expired(key):
                    self.emit(key, "final", position)
                    del self.cells[key]
                elif previous < end <= mark:
                    self.emit(key, "on_time", position)
            return "watermark"
        message = canonical(item)
        eid, entity, version = item["event_id"], item["entity_id"], item["version"]
        if eid in self.seen:
            return "duplicate" if self.seen[eid][0] == message else "id_conflict"
        claim = canonical({k: item[k] for k in ("op", "group", "minutes", "event_time")})
        identity = (entity, version)
        if identity in self.claims and self.claims[identity] != claim:
            return "version_conflict"
        old = self.entities.get(entity)
        if old is not None and version <= old["version"]:
            decision = "stale" if version < old["version"] else "same_version"
        else:
            old_key, new_key = self.key(old), self.key(item)
            old_closed, new_closed = self.expired(old_key), self.expired(new_key)
            if old_closed or new_closed:
                decision = ("expired_both" if old_closed and new_closed else
                            "expired_old" if old_closed else "expired_new")
                self.side.append({"position": position, "reason": decision,
                                  "watermark": self.watermark, "event": deepcopy(item)})
            else:
                decision = "applied"
                for key, event, sign in ((old_key, old, -1), (new_key, item, 1)):
                    if key is not None:
                        total, count = self.cells.get(key, [0, 0])
                        self.cells[key] = [total + sign * event["minutes"], count + sign]
                self.entities[entity] = deepcopy(item)
                for key in sorted({k for k in (old_key, new_key) if k is not None}):
                    phase = "late" if self.watermark >= key[0] + self.width else "early"
                    self.emit(key, phase, position)
        self.seen[eid] = [message, decision]
        self.claims[identity] = claim
        return decision

    def snapshot(self):
        return {"watermark": self.watermark,
                "entities": [[key, self.entities[key]] for key in sorted(self.entities)],
                "seen": [[key, *self.seen[key]] for key in sorted(self.seen)],
                "claims": [[e, v, self.claims[e, v]] for e, v in sorted(self.claims)],
                "cells": [[w, g, *self.cells[w, g]] for w, g in sorted(self.cells)],
                "revisions": [[w, g, self.revisions[w, g]] for w, g in sorted(self.revisions)],
                "outputs": deepcopy(self.outputs), "side": deepcopy(self.side)}


def run(log, width=10, lateness=5):
    if type(log) is not list or len(log) > 1000:
        raise ValueError("finite teaching log: list of at most 1000 items")
    engine = Windows(width, lateness)
    trace = []
    for position, item in enumerate(log, 1):
        decision = engine.apply(item, position)
        trace.append({"position": position, "decision": decision, "state": engine.snapshot()})
    return {"protocol": "event-time-windows-v1", "width": width, "lateness": lateness,
            "trace": trace, "final": engine.snapshot()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=10)
    parser.add_argument("--lateness", type=int, default=5)
    args = parser.parse_args()
    if args.input.stat().st_size > 1_000_000:
        parser.error("finite teaching input exceeds 1 MB")
    result = run(read_json(args.input), args.width, args.lateness)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
