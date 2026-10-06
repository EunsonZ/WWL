import unittest
from dataclasses import FrozenInstanceError
from itertools import product

from reservation import Conflict, Forbidden, Invalid, Schedule


class ReservationTests(unittest.TestCase):
    def test_invalid_inputs_leave_state_and_id_unchanged(self):
        cases = (("a", True, 600), ("a", 540, False), ("a", 540.0, 600),
                 ("a", "540", 600), ("a", 539, 600), ("a", 990, 1021),
                 ("a", 600, 600), ("a", 601, 600), ("a", 540, 569),
                 ("a", 540, 661), ("", 540, 600), ("  ", 540, 600))
        for args in cases:
            with self.subTest(args=args):
                s = Schedule()
                with self.assertRaises(Invalid):
                    s.reserve(*args)
                self.assertEqual(s.snapshot(), ())
                self.assertEqual(s.reserve("ok", 540, 570).id, 1)

    def test_duration_and_opening_boundaries(self):
        for start, end in ((540, 570), (540, 660), (990, 1020)):
            with self.subTest(interval=(start, end)):
                self.assertEqual(Schedule().reserve("a", start, end).end, end)

    def test_adjacent_allowed_overlap_rejected_without_change(self):
        s = Schedule()
        s.reserve("a", 540, 600)
        before = s.snapshot()
        with self.assertRaises(Conflict):
            s.reserve("b", 599, 629)
        self.assertEqual(s.snapshot(), before)
        self.assertEqual(s.reserve("b", 600, 630).id, 2)

    def test_cancel_authority_release_and_idempotence(self):
        s = Schedule()
        b = s.reserve("a", 540, 600)
        before = s.snapshot()
        with self.assertRaises(Forbidden):
            s.cancel("b", b.id)
        self.assertEqual(s.snapshot(), before)
        cancelled = s.cancel("a", b.id)
        once = s.snapshot()
        self.assertEqual(s.cancel("a", b.id), cancelled)
        self.assertEqual(s.snapshot(), once)
        self.assertEqual(s.reserve("b", 540, 600).id, 2)

    def test_invalid_and_unknown_cancel_do_not_change_state(self):
        s = Schedule()
        b = s.reserve("a", 540, 600)
        before = s.snapshot()
        for actor, key in (("a", True), ("a", 0), ("a", "1"), ("", b.id)):
            with self.subTest(key=key, actor=actor):
                with self.assertRaises(Invalid):
                    s.cancel(actor, key)
        with self.assertRaises(KeyError):
            s.cancel("a", 999)
        self.assertEqual(s.snapshot(), before)

    def test_snapshot_and_records_are_immutable(self):
        s = Schedule()
        b = s.reserve("a", 540, 600)
        old = s.snapshot()
        with self.assertRaises(FrozenInstanceError):
            b.status = "cancelled"
        s.cancel("a", b.id)
        self.assertEqual(old[0].status, "active")
        self.assertEqual(s.snapshot()[0].status, "cancelled")

    def test_finite_minute_occupancy_oracle(self):
        # Four valid intervals, 16 ordered pairs. Independent of endpoint formula.
        intervals = ((540, 570), (540, 600), (570, 600), (570, 630))
        for left, right in product(intervals, repeat=2):
            with self.subTest(left=left, right=right):
                shared_minutes = set(range(*left)) & set(range(*right))
                s = Schedule()
                s.reserve("a", *left)
                before = s.snapshot()
                if shared_minutes:
                    with self.assertRaises(Conflict):
                        s.reserve("b", *right)
                    self.assertEqual(s.snapshot(), before)
                else:
                    s.reserve("b", *right)
                    self.assertEqual(len(s.snapshot()), 2)


if __name__ == "__main__":
    unittest.main()
