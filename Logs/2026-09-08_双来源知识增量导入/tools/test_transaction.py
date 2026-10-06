import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


TOOL = Path(__file__).with_name("transaction.py")
SPEC = importlib.util.spec_from_file_location("transaction", TOOL)
transaction = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transaction)


class TransactionTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="wwl-transaction-review-")
        root = Path(temp.name)
        vault, stage, work, backup = (
            root / "vault", root / "stage", root / "work", root / "backup"
        )
        for directory in (vault, stage, work):
            directory.mkdir()
        (vault / "a.md").write_text("A0")
        (vault / "b.md").write_text("B0")
        (stage / "a.md").write_text("A1")
        (stage / "b.md").write_text("B1")
        (stage / "added.md").write_text("ADDED")
        baseline = [
            {"path": name, "sha256": transaction.digest(vault / name)}
            for name in ("a.md", "b.md")
        ]
        (work / "baseline.json").write_text(json.dumps(baseline))
        (work / "state.json").write_text(
            json.dumps({"vault": str(vault), "stage": str(stage)})
        )
        return temp, vault, stage, work, backup

    def test_apply_and_rollback_round_trip(self):
        temp, vault, stage, work, backup = self.fixture()
        self.addCleanup(temp.cleanup)
        transaction.plan(work)
        transaction.backup(work, backup)
        transaction.apply(work)
        self.assertEqual((vault / "a.md").read_text(), "A1")
        self.assertEqual((vault / "b.md").read_text(), "B1")
        self.assertEqual((vault / "added.md").read_text(), "ADDED")

        transaction.rollback(backup / "transaction.json", commit=False)
        transaction.rollback(backup / "transaction.json", commit=True)
        self.assertEqual((vault / "a.md").read_text(), "A0")
        self.assertEqual((vault / "b.md").read_text(), "B0")
        self.assertFalse((vault / "added.md").exists())

    def test_stage_change_after_preflight_never_replaces_live_and_partial_apply_recovers(self):
        temp, vault, stage, work, backup = self.fixture()
        self.addCleanup(temp.cleanup)
        transaction.plan(work)
        transaction.backup(work, backup)
        original_atomic_copy = transaction.atomic_copy

        def mutate_next_stage_after_first_copy(src, dst, **kwargs):
            original_atomic_copy(src, dst, **kwargs)
            if Path(dst) == vault / "a.md":
                (stage / "b.md").write_text("B-RACED")

        transaction.atomic_copy = mutate_next_stage_after_first_copy
        self.addCleanup(setattr, transaction, "atomic_copy", original_atomic_copy)
        with self.assertRaisesRegex(ValueError, "Source changed before replacement"):
            transaction.apply(work)

        self.assertEqual((vault / "a.md").read_text(), "A1")
        self.assertEqual((vault / "b.md").read_text(), "B0")
        # Sorted application writes added.md before a.md and b.md. It is part
        # of the installed prefix and therefore must be removed by rollback.
        self.assertEqual((vault / "added.md").read_text(), "ADDED")
        transaction.rollback(backup / "transaction.json", commit=True)
        self.assertEqual((vault / "a.md").read_text(), "A0")
        self.assertEqual((vault / "b.md").read_text(), "B0")
        self.assertFalse((vault / "added.md").exists())

    def test_destination_change_before_replace_is_preserved(self):
        temp, vault, stage, work, backup = self.fixture()
        self.addCleanup(temp.cleanup)
        transaction.plan(work)
        transaction.backup(work, backup)
        original_atomic_copy = transaction.atomic_copy

        def mutate_live_before_copy(src, dst, **kwargs):
            if Path(dst) == vault / "a.md":
                Path(dst).write_text("A-EXTERNAL")
            return original_atomic_copy(src, dst, **kwargs)

        transaction.atomic_copy = mutate_live_before_copy
        self.addCleanup(setattr, transaction, "atomic_copy", original_atomic_copy)
        with self.assertRaisesRegex(ValueError, "Destination changed before replacement"):
            transaction.apply(work)
        self.assertEqual((vault / "a.md").read_text(), "A-EXTERNAL")
        self.assertEqual((vault / "b.md").read_text(), "B0")

    def test_apply_rejects_manifest_changed_after_backup(self):
        temp, vault, stage, work, backup = self.fixture()
        self.addCleanup(temp.cleanup)
        transaction.plan(work)
        transaction.backup(work, backup)

        protected = stage / "TaskNotes" / "escape.md"
        protected.parent.mkdir()
        protected.write_text("must not be written")
        manifest_path = work / "write-plan.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"].append(
            {
                "path": "TaskNotes/escape.md",
                "before": None,
                "after": transaction.digest(protected),
                "size": protected.stat().st_size,
                "action": "add",
            }
        )
        manifest_path.write_text(json.dumps(manifest))

        with self.assertRaisesRegex(ValueError, "[Mm]anifest|transaction"):
            transaction.apply(work)
        self.assertFalse((vault / "TaskNotes" / "escape.md").exists())


if __name__ == "__main__":
    unittest.main()
