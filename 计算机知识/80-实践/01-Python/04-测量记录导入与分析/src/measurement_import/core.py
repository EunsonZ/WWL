"""CSV measurement import: Python 3.11+ standard-library APIs."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from fractions import Fraction
from itertools import islice
import re
import sqlite3
from typing import Callable, Iterable, Iterator, TextIO

COLUMNS = ["sample_id", "tick_ms", "code"]
ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
INT_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\Z")
MAX_TICK = 2**63 - 1


@dataclass(frozen=True)
class Record:
    sample_id: str
    tick_ms: int
    code: int

    def __post_init__(self) -> None:
        if not isinstance(self.sample_id, str) or not ID_PATTERN.fullmatch(self.sample_id):
            raise ValueError("sample_id: expected 1..32 ASCII identifier characters")
        if type(self.tick_ms) is not int or not 0 <= self.tick_ms <= MAX_TICK:
            raise ValueError("tick_ms: expected non-bool integer in 0..2**63-1")
        if type(self.code) is not int or not 0 <= self.code <= 4095:
            raise ValueError("code: expected non-bool integer in 0..4095")


@dataclass(frozen=True)
class Rejected:
    line: int
    reason: str


@dataclass(frozen=True)
class Report:
    read: int = 0
    rejected: int = 0
    inserted: int = 0
    duplicates: int = 0


class ConflictError(ValueError):
    pass


class BatchFailure(RuntimeError):
    def __init__(self, progress: Report, batch_rows: int, cause: Exception):
        self.progress = progress
        self.batch_rows = batch_rows
        self.cause = cause
        super().__init__(f"current batch failed; earlier batches retained: {cause}")


def decimal_integer(text: object, maximum: int) -> int:
    # Limit length before int(), including on interpreters without a digit limit.
    if not isinstance(text, str) or len(text) > 19 or not INT_PATTERN.fullmatch(text):
        raise ValueError("expected canonical ASCII nonnegative decimal integer")
    value = int(text)
    if value > maximum:
        raise ValueError(f"integer exceeds {maximum}")
    return value


def read_records(source: TextIO) -> Iterator[Record | Rejected]:
    # Resource owner passes a live text stream; this generator does not close it.
    reader = csv.DictReader(source, strict=True)
    if reader.fieldnames != COLUMNS:
        raise ValueError("CSV header must be exactly sample_id,tick_ms,code")
    for row in reader:
        try:
            if set(row) != set(COLUMNS) or any(value is None for value in row.values()):
                raise ValueError("record must have exactly three fields")
            yield Record(row["sample_id"], decimal_integer(row["tick_ms"], MAX_TICK),
                         decimal_integer(row["code"], 4095))
        except ValueError as exc:
            yield Rejected(reader.line_num, str(exc))


SCHEMA = """CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY NOT NULL
        CHECK(typeof(sample_id) = 'text' AND length(sample_id) BETWEEN 1 AND 32),
    tick_ms INTEGER NOT NULL
        CHECK(typeof(tick_ms) = 'integer' AND tick_ms BETWEEN 0 AND 9223372036854775807),
    code INTEGER NOT NULL
        CHECK(typeof(code) = 'integer' AND code BETWEEN 0 AND 4095)
)"""


def import_records(connection: sqlite3.Connection, events: Iterable[Record | Rejected],
                   batch_size: int = 2, *,
                   on_insert: Callable[[Record], None] | None = None,
                   on_reject: Callable[[Rejected], None] | None = None) -> Report:
    """Own transactions, not connection; progress counts completed batches."""
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be a non-bool positive integer")
    if connection.isolation_level is not None or connection.in_transaction:
        raise ValueError("requires isolation_level=None and no existing transaction")
    connection.execute(SCHEMA)
    progress = Report()
    iterator = iter(events)
    while True:
        # A decoding/CSV framing error here ends the import before this batch writes.
        batch = list(islice(iterator, batch_size))
        if not batch:
            return progress
        inserted = duplicates = rejected = 0
        connection.execute("BEGIN IMMEDIATE")
        try:
            for event in batch:
                if isinstance(event, Rejected):
                    rejected += 1
                    if on_reject is not None:
                        on_reject(event)
                    continue
                if not isinstance(event, Record):
                    raise TypeError("events must contain Record or Rejected")
                old = connection.execute("SELECT tick_ms, code FROM samples WHERE sample_id = ?",
                                         (event.sample_id,)).fetchone()
                if old is None:
                    connection.execute("INSERT INTO samples(sample_id, tick_ms, code) VALUES (?, ?, ?)",
                                       (event.sample_id, event.tick_ms, event.code))
                    inserted += 1
                    if on_insert is not None:
                        on_insert(event)
                elif old == (event.tick_ms, event.code):
                    duplicates += 1
                else:
                    raise ConflictError(f"sample_id conflict: {event.sample_id}")
            connection.execute("COMMIT")
        except BaseException as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            if isinstance(exc, Exception):
                raise BatchFailure(progress, len(batch), exc) from exc
            raise
        progress = Report(progress.read + len(batch), progress.rejected + rejected,
                          progress.inserted + inserted, progress.duplicates + duplicates)


def summarize(connection: sqlite3.Connection) -> dict[str, int | str | None]:
    # Stream committed rows; exact Python integers avoid SQLite SUM overflow.
    count = total = squares = 0
    for (code,) in connection.execute("SELECT code FROM samples"):
        count += 1
        total += code
        squares += code * code
    if count == 0:
        return {"n": 0, "sum_mV": 0, "mean_mV": None,
                "pvariance_mV2": None, "variance_mV2": None, "rms2_mV2": None}
    centered = Fraction(squares) - Fraction(total * total, count)
    return {"n": count, "sum_mV": total, "mean_mV": str(Fraction(total, count)),
            "pvariance_mV2": str(centered / count),
            "variance_mV2": str(centered / (count - 1)) if count > 1 else None,
            "rms2_mV2": str(Fraction(squares, count))}
