#!/usr/bin/env python3
"""Purely local teaching exercises. No sockets, installs, or credential access."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable

OWNERS = {17: "alice", 18: "bob"}
USERS = frozenset({"alice", "bob"})
INJECTION = "' OR '1'='1"

class LabInputError(ValueError):
    """An invalid input, not an empty or negative result."""

def can_read(user: object, report_id: object) -> bool:
    """Toy authorization ONLY. Caller identity is assumed, not authenticated.

    Deny unknown users, nonexistent objects and wrong types (including bool).
    Never use this in a real service as an authentication implementation.
    """
    if not isinstance(user, str) or type(report_id) is not int:
        return False
    return user in USERS and OWNERS.get(report_id) == user

def query_names(name: str, *, parameterized: bool = True) -> list[str]:
    """Compare safe parameter binding to intentionally unsafe concatenation.

    This database is ephemeral, synthetic and never exposed over a network.
    """
    if not isinstance(name, str) or len(name) > 256:
        raise LabInputError("name must be a string of at most 256 characters")
    if type(parameterized) is not bool:
        raise LabInputError("parameterized must be a bool")
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE users (name TEXT NOT NULL)")
        connection.executemany("INSERT INTO users VALUES (?)", [("alice",), ("bob",)])
        if parameterized:
            cursor = connection.execute("SELECT name FROM users WHERE name = ?", (name,))
        else:
            # Intentionally unsafe fixture. Never copy this branch into applications.
            cursor = connection.execute("SELECT name FROM users WHERE name = '" + name + "'")
        return sorted(row[0] for row in cursor.fetchall())
    except sqlite3.Error as exc:
        raise LabInputError(f"SQL demonstration rejected input: {exc}") from exc
    finally:
        connection.close()

def summarize_logs(lines: Iterable[str]) -> dict[str, object]:
    """Validate every JSONL record. Fail on the first bad line; never skip it.

    Empty input is valid: zero records and empty counts. Blank lines are invalid.
    A bad status type/range is an error, distinct from a legitimate HTTP failure.
    """
    counts: Counter[int] = Counter()
    total = 0
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LabInputError(f"line {number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise LabInputError(f"line {number}: record must be an object")
        status = row.get("status")
        if type(status) is not int or not 100 <= status <= 599:
            raise LabInputError(f"line {number}: status must be integer 100..599")
        if any(not isinstance(row.get(k), str) or not row[k] for k in ("time", "actor", "path")):
            raise LabInputError(f"line {number}: time/actor/path must be nonempty strings")
        # Timestamp text is retained, not claimed to have been temporally validated.
        total += 1
        counts[status] += 1
    return {"records": total, "statuses": {str(k): v for k, v in sorted(counts.items())}}

def match_toy_hashes(hashes: Iterable[str], candidates: Iterable[str]) -> dict[str, str]:
    """SHA-256 teaching comparison, NOT a KDF implementation or hash identifier."""
    targets = list(hashes)
    words = list(candidates)
    if any(not isinstance(h, str) or re.fullmatch(r"[0-9a-f]{64}", h) is None for h in targets):
        raise LabInputError("hashes must be lowercase 64-character hexadecimal strings")
    if any(not isinstance(word, str) for word in words):
        raise LabInputError("candidate words must be strings")
    wanted = set(targets)
    found = {}
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).hexdigest()
        if digest in wanted and digest not in found:
            found[digest] = word
    return found

def run_demo(fixtures: Path) -> dict[str, object]:
    with (fixtures / "access.jsonl").open(encoding="utf-8") as stream:
        logs = summarize_logs(stream)
    hashes = (fixtures / "hashes-sha256.txt").read_text(encoding="utf-8").splitlines()
    words = (fixtures / "candidate-words.txt").read_text(encoding="utf-8").splitlines()
    return {
        "provenance":"SYNTHETIC OFFLINE DEMO; not a security scan",
        "authorization":{"alice_17":can_read("alice", 17),"bob_17":can_read("bob", 17),
                         "bob_18":can_read("bob", 18),"unknown_17":can_read("mallory", 17)},
        "sql":{"normal_safe":query_names("alice"),
               "injection_unsafe":query_names(INJECTION, parameterized=False),
               "injection_safe":query_names(INJECTION)},
        "logs":logs,
        "toy_hashes":{"targets":len(hashes),"candidates":len(words),
                      "matches":len(match_toy_hashes(hashes, words))},
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_demo(args.fixtures)
    except (OSError, LabInputError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
