"""Meaningful temporal, CDC, layout and count-model boundaries for the fixed workload."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import analytics_runner as runner
import batch_oracle
import capture_source
import layout_workload as layout
import star_model

HERE = Path(__file__).resolve().parent


class AnalyticsBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = runner.read_json(HERE / "spec.json")
        cls.log = runner.read_json(HERE / "capture/delivery_log.json")

    def test_full_prefixes_replay_and_reverse_capture(self):
        actual = runner.run(self.spec, self.log)
        self.assertEqual(batch_oracle.verify(self.spec, self.log, actual)["status"], "pass")
        for log in (self.log + self.log, list(reversed(self.log[:15]))):
            output = runner.run(self.spec, log)
            batch_oracle.verify(self.spec, log, output)
            self.assertEqual(output["final"]["entities"], actual["final"]["entities"])

    def test_actual_capture_migration_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            captured = capture_source.capture(self.spec, Path(temp) / "source.sqlite")
        recorded = runner.read_json(HERE / "capture/capture-observed.json")
        self.assertEqual(captured, recorded)
        self.assertEqual(len(captured["changes"]), 15)
        migration = next(t for t in captured["trace"] if t["op"] == "migrate_to_seconds")
        self.assertEqual((migration["capture_before"], migration["capture_after"]), (8, 8))
        self.assertFalse(captured["trace"][-1]["committed"])
        self.assertEqual(captured["trace"][-1]["capture_after"], 15)
        self.assertFalse(any(r["fact_id"] == "rolled-back" for r in captured["source_live_rows"]))
        output = runner.run(self.spec, captured["changes"])
        live = [e[1]["after"] for e in output["final"]["entities"] if e[1]["op"] == "put"]
        self.assertEqual(live, captured["source_live_rows"])

    def test_temporal_boundaries_unknown_overlap_and_late_dimension(self):
        output = runner.run(self.spec, self.log)
        final = output["dimension_reports"]
        self.assertEqual(final["r1"]["groups"], [["matched", "East", 1200, 3], ["matched", "North", 660, 1],
                          ["matched", "South", 1830, 3], ["unmatched", None, 360, 1]])
        self.assertIn(["matched", "West", 360, 1], final["r2"]["groups"])
        self.assertIn(["ambiguous", None, 1200, 3], final["overlap"]["groups"])
        self.assertIn(["unmatched", None, 1020, 2], final["gap"]["groups"])
        early = output["trace"][4]["state"]["as_of"]["assignments"]
        self.assertIn(["flate", ["c1-old"], "matched", "North"], early)
        self.assertIn(["f2", ["c1-new"], "matched", "South"], early)
        for report in final.values():
            self.assertEqual(sum(g[2] for g in report["groups"]), 4050)
            self.assertEqual(sum(g[3] for g in report["groups"]), 8)

    def test_schema_null_missing_transport_and_business_tombstones(self):
        output = runner.run(self.spec, self.log)
        choices = {t["position"]: t["decision"] for t in output["trace"]}
        self.assertEqual([choices[p] for p in range(21, 31)],
                         ["transport_tombstone", "transport_tombstone", "schema_unsupported", "missing_measure",
                          "same_version", "null_measure", "duplicate", "stale", "same_version", "invalid_measure"])
        rows = dict(output["final"]["entities"])
        self.assertEqual(rows["f2"]["version"], 4)
        self.assertEqual(rows["f2"]["op"], "put")
        self.assertEqual(rows["f4"], {"op": "delete", "version": 2, "after": None})
        self.assertEqual(rows["f8"]["after"]["duration_seconds"], 0)
        identities = {r[0] for r in output["final"]["seen"]}
        self.assertNotIn("unknown-schema", identities)
        self.assertNotIn("null-seconds", identities)
        self.assertIn("repair-schema", identities)
        # before is retained in raw identity/provenance; not a precondition to current-fact apply.
        changed = deepcopy(self.log[0])
        changed["event_id"] = "separate-before-probe"
        changed["before"] = {"untrusted": "not used for contribution"}
        self.assertEqual(runner.run(self.spec, [changed])["trace"][0]["decision"], "applied")

    def test_layout_equal_results_bytes_calls_and_boundaries(self):
        output = runner.run(self.spec, self.log)
        base = layout.build_workload(dict(output["final"]["entities"]), output["final"]["as_of"]["assignments"], 128)
        with tempfile.TemporaryDirectory() as temp:
            result = layout.run(base, Path(temp) / "layout", 10, "web", [1, 16, 64, 2048])
        self.assertEqual(result["N"], 1024)
        self.assertEqual(result["row_scan"]["groups"], [["matched", "East", 0, 128], ["matched", "South", 234240, 384]])
        self.assertEqual(result["row_scan"]["metrics"]["returned_payload_bytes"], 73728)
        self.assertEqual(result["column_scan"]["metrics"]["returned_payload_bytes"], 32768)
        self.assertEqual(result["blocked"]["16"]["metrics"]["operator_calls"], 64)
        self.assertEqual(result["rle_region"]["unsorted"]["encoded_bytes"], 16384)
        self.assertEqual(result["rle_region"]["full_rows_sorted_by_region"]["encoded_bytes"], 64)
        for n in (0, 16, 17):
            small = deepcopy(base)
            small["rows"] = small["rows"][:n]
            with tempfile.TemporaryDirectory() as temp:
                r = layout.run(small, Path(temp) / "layout", 10, "web", [16])
            self.assertEqual(r["blocked"]["16"]["metrics"]["operator_calls"], (n + 15) // 16)
            self.assertEqual(r["row_scan"]["metrics"]["returned_payload_bytes"], 9*n*8)
            self.assertEqual(r["column_scan"]["metrics"]["returned_payload_bytes"], 4*n*8)
            self.assertLessEqual(r["blocked"]["16"]["metrics"]["scratch_slots_peak"], 2*min(n,16))

    def test_actual_star_preserves_grain_and_exposes_wrong_joins(self):
        output = runner.run(self.spec, self.log)
        with tempfile.TemporaryDirectory() as temp:
            reports = {d["revision"]: star_model.materialize(dict(output["final"]["entities"]), d["rows"], output["dimension_reports"][d["revision"]], Path(temp)/(d["revision"]+".sqlite")) for d in self.spec["dimension_snapshots"]}
        r = reports["r1"]
        self.assertEqual(len(r["fact_rows"]), 8)
        self.assertEqual(r["foreign_key_check"], [])
        self.assertEqual(r["wrong_natural_key_join"], {"sum_seconds": 6540, "count": 12})
        self.assertEqual(r["known_only_inner_join"], {"sum_seconds": 3690, "count": 7})
        self.assertEqual(r["wrong_sum_distinct"], {"sum_seconds": 3450, "distinct_measure_values": 7})
        self.assertEqual(r["current_dimension_groups"], [["matched", "East", 1200, 3], ["matched", "South", 2490, 4], ["unmatched", None, 360, 1]])
        for report in reports.values():
            self.assertEqual(sum(g[2] for g in report["star_groups"]), 4050)
            self.assertEqual(sum(g[3] for g in report["star_groups"]), 8)

    def test_cli_reports_escaped_surrogates_without_partial_file(self):
        invalid = deepcopy(self.log[0])
        invalid["after"]["note"] = "\ud800"
        provenance = deepcopy(self.log[0])
        provenance["event_id"] = "before-provenance"
        provenance["before"] = {"nested": ["\ud800"]}
        log = [invalid, provenance]
        with tempfile.TemporaryDirectory() as temp:
            raw, out = Path(temp)/"deliveries.json", Path(temp)/"actual.json"
            raw.write_text(json.dumps(log, ensure_ascii=True))
            process = subprocess.run([sys.executable,"-B",str(HERE/"analytics_runner.py"),"--input",str(HERE/"spec.json"),"--deliveries",str(raw),"--out",str(out)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            actual = json.loads(out.read_text())
            self.assertGreater(out.stat().st_size, 100)
            self.assertIn(b"\\ud800", out.read_bytes())
        self.assertEqual([s["decision"] for s in actual["trace"]], ["invalid_schema","applied"])
        batch_oracle.verify(self.spec, log, actual)

    def test_oracle_detects_wrong_dimension_identity_and_claim(self):
        output = runner.run(self.spec, self.log)
        for field in ("seen", "claims", "quarantine"):
            broken = deepcopy(output)
            broken["trace"][-1]["state"][field].pop()
            with self.assertRaises(AssertionError):
                batch_oracle.verify(self.spec, self.log, broken)
        broken = deepcopy(output)
        broken["dimension_reports"]["r1"]["assignments"][0][3] = "South"
        with self.assertRaises(AssertionError):
            batch_oracle.verify(self.spec, self.log, broken)


if __name__ == "__main__":
    unittest.main()
