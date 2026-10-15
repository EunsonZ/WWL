"""Inject failure after INSERT c, reopen the database, then replay."""
from contextlib import closing
from dataclasses import asdict
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from measurement_import.core import BatchFailure, import_records, read_records

CSV = "sample_id,tick_ms,code\na,0,2\nb,1000,4\nc,2000,6\nd,3000,8\n"

def rows(db):
    return db.execute("SELECT sample_id,tick_ms,code FROM samples ORDER BY sample_id").fetchall()

def fail_after_c(record):
    if record.sample_id == "c":
        raise RuntimeError("injected after INSERT c")

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "recovery.sqlite"
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        try:
            import_records(db, read_records(io.StringIO(CSV)), on_insert=fail_after_c)
        except BatchFailure as error:
            print(json.dumps({"completed_batches": asdict(error.progress), "failed_batch_rows": error.batch_rows}))
        assert rows(db) == [("a", 0, 2), ("b", 1000, 4)]
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        print("after reopen:", rows(db))
        retry = import_records(db, read_records(io.StringIO(CSV)))
        assert (retry.inserted, retry.duplicates) == (2, 2)
        assert rows(db) == [("a", 0, 2), ("b", 1000, 4), ("c", 2000, 6), ("d", 3000, 8)]
        print("retry:", asdict(retry))
        print("final rows:", rows(db))
