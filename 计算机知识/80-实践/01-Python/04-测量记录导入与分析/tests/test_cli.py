"""Installed package integration; independent SQL checks and resource ownership."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from measurement_import.cli import main

CSV = "sample_id,tick_ms,code\na,0,2\nb,1000,4\nc,2000,6\nd,3000,8\n"
ROWS = [("a", 0, 2), ("b", 1000, 4), ("c", 2000, 6), ("d", 3000, 8)]

class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "input.csv"
        self.source.write_text(CSV)
        self.db = self.root / "run.sqlite"

    def command(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", "-m", "measurement_import", *map(str,args)],
                              cwd=self.root, text=True, capture_output=True)

    def rows(self):
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            return db.execute("SELECT sample_id,tick_ms,code FROM samples ORDER BY sample_id").fetchall()

    def test_installed_cli_replay_summary_and_sql(self):
        first = self.command("import", self.source, self.db)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["inserted"], 4)
        replay = self.command("import", self.source, self.db)
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual((json.loads(replay.stdout)["inserted"],json.loads(replay.stdout)["duplicates"]), (0,4))
        self.assertEqual(self.rows(), ROWS)
        report = self.command("summary", self.db)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)["summary"]["variance_mV2"], "20/3")

    def test_dry_run_does_not_create_database(self):
        result = self.command("import", self.source, self.db, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.db.exists())
        report = json.loads(result.stdout)
        self.assertEqual((report["inserted"],report["would_insert"]),(0,4))
        self.assertEqual(report["summary_scope"], "hypothetical database after import")

    def test_dry_run_existing_snapshot_preserves_bytes_and_rows(self):
        self.source.write_text("sample_id,tick_ms,code\na,0,2\nb,1000,4\n")
        self.assertEqual(self.command("import", self.source, self.db).returncode, 0)
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.source.write_text(CSV)
        result = self.command("import", self.source, self.db, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["inserted"],report["would_insert"],report["duplicates"]),(0,2,2))
        self.assertEqual(self.rows(), ROWS[:2])
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_conflict_keeps_completed_batch_but_not_x(self):
        self.source.write_text("sample_id,tick_ms,code\na,0,2\nb,1000,4\nx,4000,10\na,0,9\n")
        result = self.command("import", self.source, self.db)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)["completed_batches"]["inserted"],2)
        self.assertEqual(self.rows(), ROWS[:2])

    def test_bad_encoding_header_and_csv_framing(self):
        for content in (b"sample_id,tick_ms,code\na,0,\xff\n", b"code,tick_ms,sample_id\n2,0,a\n", b'sample_id,tick_ms,code\na,0,"2\n'):
            with self.subTest(content=content):
                self.source.write_bytes(content)
                result = self.command("import",self.source,self.db)
                self.assertEqual(result.returncode,1)
                self.assertIn(json.loads(result.stderr)["error"],("UnicodeDecodeError","ValueError","Error"))
                with contextlib.closing(sqlite3.connect(self.db)) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM samples").fetchone()[0],0)

    def test_file_database_and_output_path_failures(self):
        missing = self.command("import", self.root/"missing.csv", self.db)
        self.assertEqual(missing.returncode,1)
        self.assertFalse(self.db.exists())
        db_failure = self.command("import",self.source,self.root/"no-parent"/"run.sqlite")
        self.assertEqual(db_failure.returncode,1)
        rejects = self.root/"rejects.jsonl"
        rejects.write_text("preserve this\n")
        rejected = self.command("import",self.source,self.db,"--rejects",rejects)
        self.assertEqual(rejected.returncode,1)
        self.assertEqual(rejects.read_text(),"preserve this\n")
        self.assertFalse(self.db.exists())
        alias = self.command("import",self.source,self.source)
        self.assertEqual(alias.returncode,1)
        self.assertEqual(self.source.read_text(),CSV)
        absent_summary = self.command("summary",self.db)
        self.assertEqual(absent_summary.returncode,1)
        self.assertFalse(self.db.exists())

    def test_output_failure_preserves_commits_and_closes_resources(self):
        real_connect, real_open = sqlite3.connect, Path.open
        connections, streams = [], []
        class Connection(sqlite3.Connection):
            closed = False
            def close(self):
                self.closed = True
                super().close()
        def connect(*args,**kwargs):
            obj=real_connect(*args,factory=Connection,**kwargs)
            connections.append(obj)
            return obj
        def open_file(path,*args,**kwargs):
            obj=real_open(path,*args,**kwargs)
            streams.append(obj)
            return obj
        class FailedOutput(io.StringIO):
            def write(self,text):
                raise OSError("injected stdout failure")
        errors=io.StringIO()
        with patch("sqlite3.connect",connect), patch.object(Path,"open",open_file), contextlib.redirect_stdout(FailedOutput()), contextlib.redirect_stderr(errors):
            result=main(["import",str(self.source),str(self.db)])
        self.assertEqual(result,1)
        self.assertEqual(json.loads(errors.getvalue())["error"],"OSError")
        self.assertTrue(connections and all(c.closed for c in connections))
        self.assertTrue(streams and all(s.closed for s in streams))
        self.assertEqual(self.rows(),ROWS)
        self.assertEqual(self.command("summary",self.db).returncode,0)

    def test_import_has_no_io_or_new_files(self):
        script = "import sqlite3,pathlib; from unittest.mock import patch;\nwith patch('sqlite3.connect',side_effect=AssertionError('database at import')), patch.object(pathlib.Path,'open',side_effect=AssertionError('file at import')):\n import measurement_import,measurement_import.cli\n print(measurement_import.__file__)\n"
        before=set(self.root.iterdir())
        result=subprocess.run([sys.executable,"-I","-B","-c",script],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("site-packages",result.stdout)
        self.assertEqual(set(self.root.iterdir()),before)

if __name__ == "__main__":
    unittest.main()
