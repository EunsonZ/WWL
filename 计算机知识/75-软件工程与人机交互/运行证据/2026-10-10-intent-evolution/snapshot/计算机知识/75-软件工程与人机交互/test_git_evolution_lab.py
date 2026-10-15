"""Only fresh isolated repos. Requires installed Git; no remote connection."""
from pathlib import Path
import shutil
import tempfile
import unittest

from git_evolution_lab import run_lab


@unittest.skipUnless(shutil.which("git"), "installed Git required")
class GitEvolutionTests(unittest.TestCase):
    def test_real_dag_text_conflict_and_semantic_witness(self):
        with tempfile.TemporaryDirectory(prefix="wwl-git-test-") as parent:
            sentinel = Path(parent) / "existing.txt"
            sentinel.write_text("keep existing parent files\n")
            result = run_lab(parent)
            self.assertEqual(sentinel.read_text(), "keep existing parent files\n")
            self.assertTrue(Path(result["root"]).is_relative_to(Path(parent).resolve()))
            self.assertEqual(len(result["merge_parents"]), 2)
            self.assertEqual(set(result["merge_parents"]),
                             {result["commits"]["policy"], result["commits"]["refactor"]})
            self.assertTrue(result["merged_accepts_1021_incorrectly"])
            self.assertFalse(result["repaired_accepts_1021"])
            self.assertIn("<<<<<<<", result["text_conflict"])
            self.assertTrue((Path(result["root"]) / "exercise-result.json").is_file())


if __name__ == "__main__":
    unittest.main()
