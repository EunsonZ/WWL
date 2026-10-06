import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from atomic_replace import (
    AtomicWriteAfterReplaceError,
    AtomicWriteResult,
    DirectorySyncStatus,
    atomic_write,
)


class AtomicReplaceTests(unittest.TestCase):
    def test_replaces_existing_file_with_complete_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            directory = Path(directory_name)
            target = directory / "state.txt"
            target.write_bytes(b"old")
            result = atomic_write(target, b"new payload")
            self.assertEqual(target.read_bytes(), b"new payload")
            self.assertIsInstance(result, AtomicWriteResult)
            self.assertTrue(result.replacement_visible)
            self.assertIn(result.directory_sync, set(DirectorySyncStatus))
            self.assertEqual(
                result.durability_claim_allowed,
                result.directory_sync is DirectorySyncStatus.SYNCED,
            )

    def test_repeated_replacement_leaves_only_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            directory = Path(directory_name)
            target = directory / "state.txt"
            atomic_write(target, b"first")
            atomic_write(target, b"second")
            self.assertEqual(target.read_bytes(), b"second")
            self.assertEqual([path.name for path in directory.iterdir()], ["state.txt"])

    def test_reports_unsupported_directory_sync_after_visible_replace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            target = Path(directory_name) / "state.txt"
            target.write_bytes(b"old")
            with patch(
                "atomic_replace.fsync_directory",
                return_value=DirectorySyncStatus.UNSUPPORTED,
            ):
                result = atomic_write(target, b"new payload")
            self.assertEqual(target.read_bytes(), b"new payload")
            self.assertTrue(result.replacement_visible)
            self.assertEqual(result.directory_sync, DirectorySyncStatus.UNSUPPORTED)
            self.assertFalse(result.durability_claim_allowed)

    def test_error_after_replace_preserves_visible_state_in_exception(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            target = Path(directory_name) / "state.txt"
            target.write_bytes(b"old")
            with patch(
                "atomic_replace.fsync_directory",
                side_effect=OSError(errno.EIO, "simulated directory sync failure"),
            ):
                with self.assertRaises(AtomicWriteAfterReplaceError) as raised:
                    atomic_write(target, b"new payload")
            self.assertTrue(raised.exception.replacement_visible)
            self.assertEqual(target.read_bytes(), b"new payload")


if __name__ == "__main__":
    unittest.main()
