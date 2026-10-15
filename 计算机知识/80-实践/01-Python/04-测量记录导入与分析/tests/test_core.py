"""Independent finite row sets and SQL expectations."""
import io
import sqlite3
import unittest
from measurement_import.core import (BatchFailure, ConflictError, Record, Rejected,
                                     import_records, read_records, summarize)

CSV = "sample_id,tick_ms,code\na,0,2\nb,1000,4\nc,2000,6\nd,3000,8\n"
ROWS = [("a", 0, 2), ("b", 1000, 4), ("c", 2000, 6), ("d", 3000, 8)]

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None)
        self.addCleanup(self.db.close)

    def rows(self):
        return self.db.execute("SELECT sample_id, tick_ms, code FROM samples ORDER BY sample_id").fetchall()

    def import_csv(self, text=CSV, **options):
        return import_records(self.db, read_records(io.StringIO(text)), **options)

    def test_finite_rows_replay_and_independent_sql(self):
        first = self.import_csv()
        self.assertEqual((first.read, first.rejected, first.inserted, first.duplicates), (4, 0, 4, 0))
        self.assertEqual(self.rows(), ROWS)
        self.assertEqual(self.db.execute("SELECT COUNT(*), SUM(code), AVG(code), SUM(code * code) FROM samples").fetchone(), (4, 20, 5.0, 120))
        # A second independent SQL expression checks both variance denominators.
        self.assertEqual(self.db.execute("SELECT AVG((code-5.0)*(code-5.0)), SUM((code-5.0)*(code-5.0))/3.0, AVG(code*code) FROM samples").fetchone(), (5.0, 20/3, 30.0))
        self.assertEqual(summarize(self.db), {"n": 4, "sum_mV": 20, "mean_mV": "5", "pvariance_mV2": "5", "variance_mV2": "20/3", "rms2_mV2": "30"})
        again = self.import_csv()
        self.assertEqual((again.inserted, again.duplicates), (0, 4))
        self.assertEqual(self.rows(), ROWS)

    def test_fault_after_c_rolls_back_batch_then_recovers(self):
        def fail_after_c(record):
            if record.sample_id == "c":
                raise RuntimeError("injected after insert c")
        with self.assertRaises(BatchFailure) as raised:
            self.import_csv(on_insert=fail_after_c)
        self.assertEqual(raised.exception.progress.inserted, 2)
        self.assertEqual(raised.exception.batch_rows, 2)
        self.assertEqual(self.rows(), ROWS[:2])
        self.assertFalse(self.db.in_transaction)
        retry = self.import_csv()
        self.assertEqual((retry.inserted, retry.duplicates), (2, 2))
        self.assertEqual(self.rows(), ROWS)

    def test_conflict_rolls_back_new_row_in_same_batch(self):
        self.import_csv()
        with self.assertRaises(BatchFailure) as raised:
            self.import_csv("sample_id,tick_ms,code\nx,5000,10\na,0,9\n")
        self.assertIsInstance(raised.exception.cause, ConflictError)
        self.assertEqual(self.rows(), ROWS)

    def test_identical_duplicate_within_one_batch(self):
        result = self.import_csv("sample_id,tick_ms,code\na,0,2\na,0,2\n")
        self.assertEqual((result.inserted, result.duplicates), (1, 1))
        self.assertEqual(self.rows(), [ROWS[0]])

    def test_rejects_not_zero_and_valid_records_survive(self):
        rejects = []
        result = self.import_csv("sample_id,tick_ms,code\na,0,2\nb,1000,\nc,2000,6\nd,3000,NaN\n", on_reject=rejects.append)
        self.assertEqual((result.read, result.rejected, result.inserted), (4, 2, 2))
        self.assertEqual(self.rows(), [ROWS[0], ROWS[2]])
        self.assertEqual([r.line for r in rejects], [3, 5])
        self.assertEqual(summarize(self.db)["mean_mV"], "4")

    def test_numeric_and_shape_boundaries(self):
        for bad in ("", "True", "NaN", "Infinity", "-1", "+2", "02", "２", "4096", "9"*10000, "2.0", " 2"):
            with self.subTest(bad=bad[:20]):
                self.assertIsInstance(list(read_records(io.StringIO(f"sample_id,tick_ms,code\na,0,{bad}\n")))[0], Rejected)
        for bad in (True, False, 2.0, float("nan"), float("inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Record("a", 0, bad)
        for text in ("sample_id,tick_ms,code\na,0,2,extra\n", "sample_id,tick_ms,code\na,0\n"):
            self.assertIsInstance(list(read_records(io.StringIO(text)))[0], Rejected)
        with self.assertRaises(ValueError):
            list(read_records(io.StringIO("code,tick_ms,sample_id\n2,0,a\n")))
        for tick in (-1, 2**63, True):
            with self.assertRaises(ValueError):
                Record("a", tick, 2)

    def test_reject_sink_error_rolls_back_current_batch(self):
        def failed_sink(event):
            raise OSError("reject output failed")
        with self.assertRaises(BatchFailure):
            self.import_csv("sample_id,tick_ms,code\na,0,2\nb,1000,NaN\n", on_reject=failed_sink)
        self.assertEqual(self.rows(), [])
        self.assertFalse(self.db.in_transaction)

    def test_empty_single_and_batch_size_contract(self):
        self.import_csv("sample_id,tick_ms,code\n")
        self.assertIsNone(summarize(self.db)["mean_mV"])
        self.import_csv("sample_id,tick_ms,code\na,0,2\n")
        self.assertIsNone(summarize(self.db)["variance_mV2"])
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.import_csv(batch_size=bad)

if __name__ == "__main__":
    unittest.main()
