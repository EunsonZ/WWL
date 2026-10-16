"""Local protocol behavior; the separate parent driver supplies actual SIGKILL evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import recovery_worker as worker
import batch_oracle
import run_experiment

HERE = Path(__file__).resolve().parent


class RecoveryBehavior(unittest.TestCase):
    def test_every_prefix_atomic_state_and_effect(self):
        source, digest = worker.read_source(HERE / "source.json")
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            state = worker.open_resource(base / "state.sqlite", source, digest, "state", "dedupe")
            sink = worker.open_resource(base / "sink.sqlite", source, digest, "sink", "dedupe")
            try:
                for p, event in enumerate(source["events"], 1):
                    with worker.transaction(state):
                        verdict, effect = worker.apply_event(state, event, source["source_id"])
                        if effect:
                            result, _ = worker.deliver(sink, effect, "dedupe")
                            state.execute("INSERT INTO deliveries VALUES(?,?,?)",
                                          (effect["id"], effect["fingerprint"], worker.canonical(result)))
                        state.execute("INSERT INTO positions VALUES(?,?)", (p, verdict))
                        state.execute("UPDATE checkpoint SET p=?", (p,))
                    truth = batch_oracle.rebuild(source, p)
                    self.assertEqual(worker.state_snapshot(state), truth["state"])
                    self.assertEqual([list(r) for r in sink.execute("SELECT g,s,n FROM totals ORDER BY g")], truth["totals"])
            finally:
                state.close()
                sink.close()

    def test_authority_result_reopen_and_parameter_conflict(self):
        source, digest = worker.read_source(HERE / "source.json")
        effect = batch_oracle.rebuild(source, 1)["effects"][0]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            path = base / "sink.sqlite"
            db = worker.open_resource(path, source, digest, "sink", "dedupe")
            result, created = worker.deliver(db, effect, "dedupe")
            db.close()
            db = worker.open_resource(path, source, digest, "sink", "dedupe")
            try:
                repeated, created_again = worker.deliver(db, effect, "dedupe")
                self.assertTrue(created)
                self.assertFalse(created_again)
                self.assertEqual(result, repeated)
                old = run_experiment.inspect(path.resolve(), "sink")
                bad = deepcopy(effect)
                bad["body"]["delta"][0][1] = 999
                bad["fingerprint"] = worker.fingerprint(bad["body"])
                with self.assertRaisesRegex(ValueError, "identity conflict"):
                    worker.deliver(db, bad, "dedupe")
                self.assertEqual(run_experiment.inspect(path.resolve(), "sink"), old)
                bad["fingerprint"] = "0" * 64
                with self.assertRaisesRegex(ValueError, "incorrect fingerprint"):
                    worker.deliver(db, bad, "dedupe")
            finally:
                db.close()

    def test_state_snapshot_and_position_rollback_together(self):
        source, digest = worker.read_source(HERE / "source.json")
        with tempfile.TemporaryDirectory() as temp:
            db = worker.open_resource(Path(temp) / "state.sqlite", source, digest, "state", "dedupe")
            try:
                before = worker.state_snapshot(db)
                with self.assertRaisesRegex(RuntimeError, "controlled"):
                    with worker.transaction(db):
                        worker.apply_event(db, source["events"][0], source["source_id"])
                        db.execute("UPDATE checkpoint SET p=1")
                        raise RuntimeError("controlled application exception, NOT a process kill")
                self.assertEqual(worker.state_snapshot(db), before)
            finally:
                db.close()

    def test_immutable_source_binding_and_role(self):
        source, digest = worker.read_source(HERE / "source.json")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.sqlite"
            worker.open_resource(path, source, digest, "state", "dedupe").close()
            for changed_hash, role, mode in (("0" * 64, "state", "dedupe"),
                                            (digest, "sink", "dedupe"),
                                            (digest, "state", "naive_bad")):
                with self.assertRaisesRegex(ValueError, "identity mismatch"):
                    worker.open_resource(path, source, changed_hash, role, mode)

    def test_file_parse_errors_and_schema_do_not_consume_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.json"
            for raw in ('{"protocol":1,"protocol":2}', '{"x":NaN}', '{"x":Infinity}'):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    worker.read_source(path)
        source, _ = worker.read_source(HERE / "source.json")
        truth = batch_oracle.rebuild(source)
        positions = dict(truth["state"]["positions"])
        self.assertEqual(positions[17], "invalid")
        self.assertEqual(positions[18], "applied")
        self.assertEqual(truth["state"]["totals"], [["A", 7, 2], ["B", 7, 1], ["F", 11, 1]])
        self.assertEqual(len(truth["effects"]), 11)

    def test_oracle_observes_more_than_final_sum(self):
        source, _ = worker.read_source(HERE / "source.json")
        truth = batch_oracle.rebuild(source)
        effects = [[i, e["id"], e["fingerprint"], batch_oracle.encoded(e["body"]), batch_oracle.encoded(e["result"])]
                   for i, e in enumerate(truth["effects"], 1)]
        sink = {"effects": effects, "receipts": truth["receipts"], "totals": truth["totals"]}
        self.assertTrue(batch_oracle.compare(source, truth["state"], sink)["all_match"])
        for field in ("seen", "claims", "positions", "deliveries"):
            corrupt = deepcopy(truth["state"])
            corrupt[field].pop()
            self.assertFalse(batch_oracle.compare(source, corrupt, sink)["all_match"])
        corrupt = deepcopy(sink)
        corrupt["effects"][0][2] = "bad fingerprint"
        self.assertFalse(batch_oracle.compare(source, truth["state"], corrupt)["all_match"])


if __name__ == "__main__":
    unittest.main()
