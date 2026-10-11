"""CLI owns streams and connections; importing the package starts no I/O."""
from __future__ import annotations

import argparse
import csv
from contextlib import ExitStack, closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from .core import BatchFailure, import_records, read_records, summarize


def readonly_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro",
                           uri=True, isolation_level=None)


def ensure_distinct(paths: list[Path]) -> None:
    for index, left in enumerate(paths):
        for right in paths[index + 1:]:
            if left.resolve() == right.resolve():
                raise ValueError("input, database and rejects must be distinct paths")
            if left.exists() and right.exists() and left.samefile(right):
                raise ValueError("input, database and rejects must not alias one file")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wwl-measurements")
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import", help="validate CSV and commit by batches")
    importer.add_argument("csv", type=Path)
    importer.add_argument("database", type=Path)
    importer.add_argument("--batch-size", type=int, default=2)
    importer.add_argument("--dry-run", action="store_true")
    importer.add_argument("--rejects", type=Path,
                          help="create a new JSONL file; existing files are refused")
    summary = commands.add_parser("summary", help="summarize existing committed rows")
    summary.add_argument("database", type=Path)
    args = parser.parse_args(argv)
    if args.command == "import" and args.dry_run and args.rejects:
        parser.error("--dry-run cannot create a --rejects file")
    try:
        if args.command == "summary":
            with closing(readonly_connection(args.database)) as database:
                result = {"summary_scope": "committed database", "summary": summarize(database)}
        else:
            if args.batch_size <= 0:
                raise ValueError("--batch-size must be positive")
            paths = [args.csv, args.database]
            if args.rejects is not None:
                paths.append(args.rejects)
            ensure_distinct(paths)
            with ExitStack() as stack:
                source = stack.enter_context(args.csv.open("r", encoding="utf-8", errors="strict", newline=""))
                reject_file = None
                if args.rejects is not None:
                    reject_file = stack.enter_context(args.rejects.open("x", encoding="utf-8", newline=""))
                if args.dry_run:
                    database = stack.enter_context(closing(sqlite3.connect(":memory:", isolation_level=None)))
                    if args.database.exists():
                        original = stack.enter_context(closing(readonly_connection(args.database)))
                        original.backup(database)
                else:
                    database = stack.enter_context(closing(sqlite3.connect(args.database, isolation_level=None)))
                def rejected(event):
                    if reject_file is not None:
                        reject_file.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
                        reject_file.flush()
                report = import_records(database, read_records(source), args.batch_size, on_reject=rejected)
                result = asdict(report)
                result["dry_run"] = args.dry_run
                if args.dry_run:
                    result["would_insert"] = result["inserted"]
                    result["inserted"] = 0
                result["summary_scope"] = ("hypothetical database after import" if args.dry_run else "committed database")
                result["summary"] = summarize(database)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, csv.Error, sqlite3.Error, BatchFailure) as exc:
        error = {"error": type(exc).__name__, "message": str(exc),
                 "recovery": "query existing database, then replay the original input"}
        if isinstance(exc, BatchFailure):
            error["completed_batches"] = asdict(exc.progress)
            error["failed_batch_rows"] = exc.batch_rows
        print(json.dumps(error, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
