import mmap
import unittest

from mmap_observer import Faults, observe_anonymous, touch_each_page


class MmapObserverTests(unittest.TestCase):
    def test_fault_delta(self) -> None:
        self.assertEqual(Faults(9, 4) - Faults(3, 1), Faults(6, 3))

    def test_page_touch_changes_one_byte_per_page(self) -> None:
        page_size = mmap.PAGESIZE
        with mmap.mmap(-1, page_size * 3, access=mmap.ACCESS_WRITE) as mapping:
            self.assertEqual(touch_each_page(mapping, page_size, write=True), 3)
            self.assertEqual(touch_each_page(mapping, page_size, write=False), 3)

    def test_observation_returns_nonnegative_process_deltas(self) -> None:
        first, second = observe_anonymous(mmap.PAGESIZE * 4, mmap.PAGESIZE)
        self.assertGreaterEqual(first.minor, 0)
        self.assertGreaterEqual(first.major, 0)
        self.assertGreaterEqual(second.minor, 0)
        self.assertGreaterEqual(second.major, 0)


if __name__ == "__main__":
    unittest.main()
