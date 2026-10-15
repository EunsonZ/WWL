"""Independent expected minute sets, fault points and persistence contracts."""
import copy
from itertools import product
from pathlib import Path
import sqlite3
import tempfile
import unittest

from reservation import Booking, Conflict, Schedule, validate
from reservation_v2 import (Authority, IntentConflict, InvalidInput,
                            NotificationSink, WriterFenced, fingerprint)


class RefactoredSchedule(Schedule):
    """Executable v1 refactor: only change the conflict predicate representation.

    Keep Booking, input validation, cancellation, id allocation and snapshots.
    This minute-set representation deliberately favors inspection, not speed.
    """
    cleanup = 0

    def reserve(self, actor, start, end):
        validate(actor, start, end)
        requested = set(range(start, end + self.cleanup))
        if any(b.status == "active" and
               requested & set(range(b.start, b.end + self.cleanup))
               for b in self._bookings):
            raise Conflict("requested interval overlaps an active booking")
        booking = Booking(self._next_id, actor, start, end)
        self._bookings += (booking,)
        self._next_id += 1
        return booking


class WrongBufferRefactor(RefactoredSchedule):
    """Counterexample: a policy change mislabeled as a v1 refactor."""
    cleanup = 10


class EvolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwl-v2-test-")
        self.path = Path(self.temp.name) / "authority.sqlite"
        self.authority = Authority(self.path)
        self.sink = NotificationSink(Path(self.temp.name) / "sink.sqlite")

    def tearDown(self):
        self.sink.close()
        self.authority.close()
        self.temp.cleanup()

    def restart(self):
        self.authority.close()
        self.authority = Authority(self.path)

    def test_unsupported_schema_does_not_create_business_tables(self):
        path = Path(self.temp.name) / "future-schema.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE metadata (singleton INTEGER PRIMARY KEY, schema_version INTEGER)")
            db.execute("INSERT INTO metadata VALUES(1,99)")
        with self.assertRaises(InvalidInput):
            Authority(path)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT schema_version FROM metadata").fetchall(), [(99,)])
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(names, {"metadata"})

    def test_foreign_database_is_not_initialized_as_authority(self):
        path = Path(self.temp.name) / "foreign.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE original (value TEXT)")
            db.execute("INSERT INTO original VALUES('preserve')")
        with self.assertRaises(InvalidInput):
            Authority(path)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT value FROM original").fetchall(), [('preserve',)])
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(names, {"original"})

    def test_legacy_exception_and_new_v2_decisions(self):
        a = self.authority
        a.seed_legacy([("A", 540, 600), ("B", 600, 630), ("C", 650, 680)])
        legacy = a.snapshot()
        self.assertEqual([b["policy_version"] for b in legacy], [1, 1, 1])
        self.assertEqual(a.reserve("D", "bad", 630, 660)["status"], "rejected")
        accepted = a.reserve("D", "good", 690, 720)
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(accepted["booking"]["policy_version"], 2)
        self.assertEqual(a.snapshot()[:3], legacy)
        with self.assertRaises(InvalidInput):
            a.seed_legacy([("new-old", 730, 760)])

    def test_v2_oracle_uses_occupied_minutes_not_implementation_formula(self):
        intervals = [(540, 570), (560, 600), (570, 600), (580, 610),
                     (600, 630), (610, 640), (990, 1020)]
        for index, (left, right) in enumerate(product(intervals, repeat=2)):
            with self.subTest(left=left, right=right):
                path = Path(self.temp.name) / f"pair-{index}.sqlite"
                # Include each booking's cleanup occupancy. Half-open sets
                # permit exactly 10 minutes, including cleanup past 17:00.
                blocked = set(range(left[0], left[1] + 10))
                requested = set(range(right[0], right[1] + 10))
                with Authority(path) as a:
                    self.assertEqual(a.reserve("a", "1", *left)["status"], "accepted")
                    result = a.reserve("b", "2", *right)
                    self.assertEqual(result["status"], "rejected" if blocked & requested else "accepted")

    def test_before_commit_fault_has_no_partial_business_state(self):
        with self.assertRaises(ConnectionError):
            self.authority.reserve("a", "1", 540, 600, fail_at="before_commit")
        self.restart()
        self.assertEqual(self.authority.snapshot(), [])
        self.assertEqual(self.authority.pending_events(), [])
        self.assertEqual(self.authority.query("a", "1")["status"], "unknown")
        self.assertEqual(self.authority.reserve("a", "1", 540, 600)["booking"]["id"], 1)

    def test_committed_reply_loss_restart_replay_preserves_identity(self):
        fp = fingerprint("a", 540, 600)
        with self.assertRaises(ConnectionError):
            self.authority.reserve("a", "1", 540, 600, fail_at="after_commit")
        self.restart()
        saved = self.authority.query("a", "1", fp)
        self.assertEqual(saved["status"], "accepted")
        self.assertEqual(self.authority.reserve("a", "1", 540, 600), saved)
        self.assertEqual(len(self.authority.snapshot()), 1)
        self.assertEqual(len(self.authority.pending_events()), 1)

    def test_key_conflict_does_not_rewrite_original_accepted_result(self):
        saved = self.authority.reserve("a", "1", 540, 600)
        with self.assertRaises(IntentConflict):
            self.authority.reserve("a", "1", 610, 640)
        with self.assertRaises(IntentConflict):
            self.authority.query("a", "1", fingerprint("a", 610, 640))
        self.assertEqual(self.authority.query("a", "1"), saved)
        self.assertEqual(len(self.authority.snapshot()), 1)
        self.assertEqual(self.authority.query("other", "1")["status"], "unknown")

    def test_rejected_intent_is_stable_and_new_intent_reconsiders(self):
        self.authority.reserve("a", "busy", 540, 600)
        rejected = self.authority.reserve("b", "conflict", 600, 630)
        self.assertEqual(rejected["reason"], "conflict_with_buffer")
        self.restart()
        self.assertEqual(self.authority.reserve("b", "conflict", 600, 630), rejected)
        with self.assertRaises(IntentConflict):
            self.authority.reserve("b", "conflict", 610, 640)
        self.assertEqual(self.authority.reserve("b", "changed", 610, 640)["status"], "accepted")

    def test_invalid_inputs_not_registered_and_invalid_interval_is_decision(self):
        for start in (True, 540.0, "540"):
            with self.subTest(start=start), self.assertRaises(InvalidInput):
                self.authority.reserve("a", "bad-type", start, 600)
        self.assertEqual(self.authority.query("a", "bad-type")["status"], "unknown")
        result = self.authority.reserve("a", "bad-range", 540, 569)
        self.assertEqual(result["reason"], "invalid_interval")
        self.assertEqual(self.authority.query("a", "bad-range"), result)
        self.assertEqual(self.authority.snapshot(), [])

    def test_fence_blocks_old_new_writes_without_erasing_replay(self):
        saved = self.authority.reserve("a", "1", 540, 600)
        before = self.authority.snapshot()
        self.authority.fence(3)
        self.restart()
        self.assertEqual(self.authority.writer_epoch, 3)
        for epoch, policy in ((2, 2), (3, 1), (4, 2)):
            with self.subTest(epoch=epoch, policy=policy), self.assertRaises(WriterFenced):
                self.authority.reserve("b", "new", 610, 640,
                                       writer_epoch=epoch, policy_version=policy)
        self.assertEqual(self.authority.query("b", "new")["status"], "unknown")
        self.assertEqual(self.authority.reserve("a", "1", 540, 600, writer_epoch=2), saved)
        self.assertEqual(self.authority.snapshot(), before)
        self.assertEqual(self.authority.reserve("b", "new", 610, 640, writer_epoch=3)["status"], "accepted")
        with self.assertRaises(InvalidInput):
            self.authority.fence(2)

    def test_duplicate_effect_after_lost_ack_is_idempotent_in_this_sink(self):
        self.authority.reserve("a", "1", 540, 600)
        event = self.authority.pending_events()[0]
        self.assertTrue(self.sink.deliver(event))
        self.sink.close()
        self.sink = NotificationSink(Path(self.temp.name) / "sink.sqlite")
        # The outbox is still pending because acknowledgement was lost.
        self.assertEqual(self.authority.pending_events(), [event])
        self.assertFalse(self.sink.deliver(event))
        self.assertEqual(self.sink.effects(), [event])
        self.authority.acknowledge(event["event_id"])
        self.authority.acknowledge(event["event_id"])
        self.assertEqual(self.authority.pending_events(), [])
        changed = copy.deepcopy(event)
        changed["booking"]["end"] += 1
        with self.assertRaises(IntentConflict):
            self.sink.deliver(changed)
        self.assertEqual(self.sink.effects(), [event])

    def test_independent_connections_recheck_committed_authority(self):
        with Authority(self.path) as second:
            self.authority.reserve("a", "1", 540, 600)
            self.assertEqual(second.reserve("b", "2", 540, 600)["status"], "rejected")
        # This is sequential dual-connection evidence, not a concurrency run.

    def test_import_rolls_back_if_a_later_legacy_record_overlaps(self):
        with self.assertRaises(InvalidInput):
            self.authority.seed_legacy([("a", 540, 600), ("b", 570, 630)])
        self.assertEqual(self.authority.snapshot(), [])

    def test_v1_refactor_relative_to_v1_contract_and_wrong_change(self):
        def observe(schedule, method, args):
            before, next_id = schedule.snapshot(), schedule._next_id
            try:
                result = ("return", getattr(schedule, method)(*args))
            except Exception as error:
                result = ("raises", type(error), str(error))
                # A failed operation must not change state or consume an id.
                self.assertEqual(schedule.snapshot(), before)
                self.assertEqual(schedule._next_id, next_id)
            return result, schedule.snapshot(), schedule._next_id

        intervals = [(540, 570), (570, 600), (560, 600), (600, 630)]
        for left, right in product(intervals, repeat=2):
            original, refactor = Schedule(), RefactoredSchedule()
            for args in (("a", *left), ("b", *right)):
                observed = observe(original, "reserve", args)
                self.assertEqual(observed, observe(refactor, "reserve", args))
            expected = "raises" if set(range(*left)) & set(range(*right)) else "return"
            # Separate minute-set oracle supplements the full observable trace.
            self.assertEqual(observed[0][0], expected)

        original, refactor = Schedule(), RefactoredSchedule()
        trace = [("reserve", ("a", 540, 600)),
                 ("reserve", ("b", 600, 630)),  # adjacency, id 2
                 ("reserve", ("b", True, 600)),
                 ("reserve", ("", 540, 600)),
                 ("reserve", ("c", 570, 630)),
                 ("cancel", ("other", 1)),
                 ("cancel", ("a", True)),
                 ("cancel", ("a", 999)),
                 ("cancel", ("a", 1)),
                 ("cancel", ("a", 1)),  # repeated cancellation
                 ("reserve", ("c", 540, 600)),  # released slot, id 3
                 ("reserve", ("d", 630, 660))]
        retained = []
        for method, args in trace:
            self.assertEqual(observe(original, method, args),
                             observe(refactor, method, args))
            retained.append((original.snapshot(), refactor.snapshot()))
        self.assertEqual([b.id for b in original.snapshot()], [1, 2, 3, 4])
        self.assertEqual(retained[0][0][0].status, "active")
        self.assertEqual(original.snapshot()[0].status, "cancelled")
        self.assertTrue(all(old == new for old, new in retained))

        original, wrong = Schedule(), WrongBufferRefactor()
        original.reserve("a", 540, 570)
        wrong.reserve("a", 540, 570)
        self.assertEqual(observe(original, "reserve", ("b", 570, 600))[0][0], "return")
        wrong_observation = observe(wrong, "reserve", ("b", 570, 600))
        self.assertEqual(wrong_observation[0][0:2], ("raises", Conflict))
        self.assertEqual(wrong_observation[2], 2)  # rejected change did not consume id


if __name__ == "__main__":
    unittest.main()
