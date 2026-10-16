"""Behavior assertions and independent prefix comparisons for short finite histories."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import window_runner as runner
import batch_oracle as oracle

HERE = Path(__file__).resolve().parent


def put(eid, entity, v, t, group="A", minutes=10):
    return dict(event_id=eid, entity_id=entity, version=v, op="put",
                event_time=t, group=group, minutes=minutes)


def delete(eid, entity, v):
    return dict(event_id=eid, entity_id=entity, version=v, op="delete",
                event_time=None, group=None, minutes=None)


class WindowBehavior(unittest.TestCase):
    def test_fixed_every_prefix_and_policy_variants(self):
        log = runner.read_json(HERE / "events.json")
        for width, lateness in ((10, 5), (10, 0), (10, 20), (5, 5), (20, 5)):
            with self.subTest(width=width, lateness=lateness):
                oracle.verify(log, runner.run(log, width, lateness))
        report = runner.run(log)
        trace = report["trace"]
        self.assertEqual(trace[14]["state"]["cells"], [[10, "A", 16, 1], [10, "B", 20, 1]])
        self.assertEqual(trace[15]["decision"], "expired_old")
        self.assertEqual(trace[16]["decision"], "expired_new")
        self.assertEqual(trace[17]["decision"], "duplicate")
        self.assertEqual(trace[18]["decision"], "stale")
        self.assertEqual(trace[19]["decision"], "version_conflict")
        self.assertEqual(trace[39]["decision"], "expired_both")
        self.assertEqual(trace[40]["decision"], "same_version")
        self.assertEqual(report["final"]["cells"], [[40, "B", 5, 1]])
        # Entire replay includes old watermark controls; they regress, not rewind state.
        oracle.verify(log + log, runner.run(log + log))
        self.assertEqual(runner.run(log + log)["final"]["outputs"], report["final"]["outputs"])

    def test_exact_deadline_and_late_is_not_stale(self):
        log = [put("x1", "x", 1, 2), {"watermark": 10}, put("x2", "x", 2, 3, minutes=12),
               {"watermark": 14}, put("x3", "x", 3, 4, minutes=13), {"watermark": 15},
               put("x4", "x", 4, 16), put("old", "x", 1, 2)]
        report = runner.run(log)
        oracle.verify(log, report)
        self.assertEqual([r["decision"] for r in report["trace"]],
                         ["applied", "watermark", "applied", "watermark", "applied",
                          "watermark", "expired_old", "stale"])
        self.assertEqual(report["trace"][2]["state"]["outputs"][-1]["phase"], "late")
        self.assertEqual(report["trace"][5]["state"]["outputs"][-1]["sum_minutes"], 13)
        self.assertEqual(report["trace"][5]["state"]["outputs"][-1]["phase"], "final")
        changed = runner.run(log, lateness=0)
        self.assertEqual(changed["trace"][2]["decision"], "expired_both")

    def test_history_counterexample_needs_old_window(self):
        histories = [[put("x1", "x", 1, 2), put("y1", "y", 1, 12)],
                     [put("x1", "x", 1, 12), put("y1", "y", 1, 2)]]
        # Same unwindowed A:20/2 and even same per-window totals; x's old window differs.
        results = [runner.run(h + [delete("x2", "x", 2)]) for h in histories]
        self.assertEqual(results[0]["final"]["cells"], [[0, "A", 0, 0], [10, "A", 10, 1]])
        self.assertEqual(results[1]["final"]["cells"], [[0, "A", 10, 1], [10, "A", 0, 0]])
        for h, r in zip(histories, results):
            oracle.verify(h + [delete("x2", "x", 2)], r)

    def test_output_versions_and_identity_are_observable(self):
        log = runner.read_json(HERE / "events.json")
        baseline = runner.run(log)
        # A verifier that checked only final sums would miss all three corruptions.
        for field in ("revision", "sum_minutes", "phase"):
            bad = deepcopy(baseline)
            bad["trace"][4]["state"]["outputs"][-1][field] = "corrupt"
            with self.assertRaises(AssertionError):
                oracle.verify(log, bad)
        bad = deepcopy(baseline)
        bad["trace"][15]["state"]["side"][0]["reason"] = "expired_new"
        with self.assertRaises(AssertionError):
            oracle.verify(log, bad)
        bad = deepcopy(baseline)
        bad["trace"][17]["state"]["seen"].pop()
        with self.assertRaises(AssertionError):
            oracle.verify(log, bad)

    def test_no_half_update_and_empty_cell_retraction(self):
        log = [put("x1", "x", 1, 2), {"watermark": 15}, put("x2", "x", 2, 16, "B"),
               put("y1", "y", 1, 16, "B", 0), delete("y2", "y", 2)]
        report = runner.run(log)
        oracle.verify(log, report)
        self.assertEqual(report["trace"][2]["state"]["cells"], [])
        self.assertEqual(report["final"]["cells"], [[10, "B", 0, 0]])
        self.assertEqual(report["final"]["outputs"][-1]["count"], 0)
        self.assertEqual(report["final"]["entities"][0][1]["version"], 1)

    def test_invalid_inputs_do_not_consume_identity(self):
        base = put("fix", "x", 1, 2)
        log = [{**base, "version": True}, {**base, "event_time": -1},
               {**base, "minutes": float("nan")}, {**base, "extra": 1},
               {**base, "group": "\ud800"}, {"watermark": True}, base]
        report = runner.run(log)
        oracle.verify(log, report)
        self.assertEqual([r["decision"] for r in report["trace"]], ["invalid"] * 6 + ["applied"])
        self.assertEqual(len(report["final"]["seen"]), 1)


if __name__ == "__main__":
    unittest.main()
