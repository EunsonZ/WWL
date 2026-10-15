"""Regression definitions only; the current batch did not execute them."""
from pathlib import Path
import importlib.util
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parent

class OutputContractTests(unittest.TestCase):
    def relocated(self, filename):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        outer = Path(tmp.name); vault = outer / "WWL-renamed"
        (vault / "scripts").mkdir(parents=True)
        (vault / "AGENTS.md").write_text("fixture")
        (vault / "scripts/check_vault.py").write_text("# fixture marker")
        folder = vault / "electronics/lab"; folder.mkdir(parents=True)
        for source in SOURCE.glob("*.py"): shutil.copyfile(source, folder / source.name)
        name = "relocated_" + filename.replace(".", "_")
        spec = importlib.util.spec_from_file_location(name, folder / filename)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, "path", [str(folder)] + sys.path):
            sys.modules[name] = module; self.addCleanup(sys.modules.pop, name, None)
            spec.loader.exec_module(module)
        return outer, vault, module

    def test_0_migration_and_reuse(self):
        outer, vault, module = self.relocated('run_hdl.py')
        guard = module._destination
        existing = vault / "existing"; existing.mkdir()
        for target in (vault, vault / "new", existing):
            with self.subTest(target=target), self.assertRaises(ValueError): guard(target)
        self.assertFalse((vault / "new").exists())
        external = outer / "external"
        self.assertEqual(guard(external), external.resolve())
        self.assertFalse(external.exists())
        external.mkdir()
        self.assertEqual(guard(external), external.resolve())
        alias = outer / "alias"
        try: alias.symlink_to(vault, target_is_directory=True)
        except (OSError, NotImplementedError): self.skipTest("symlink unavailable")
        with self.assertRaises(ValueError): guard(alias / "linked-new")
    def test_1_migration_and_reuse(self):
        outer, vault, module = self.relocated('generate.py')
        guard = module._destination
        existing = vault / "existing"; existing.mkdir()
        for target in (vault, vault / "new", existing):
            with self.subTest(target=target), self.assertRaises(ValueError): guard(target)
        self.assertFalse((vault / "new").exists())
        external = outer / "external"
        self.assertEqual(guard(external), external.resolve())
        self.assertFalse(external.exists())
        external.mkdir()
        self.assertEqual(guard(external), external.resolve())
        alias = outer / "alias"
        try: alias.symlink_to(vault, target_is_directory=True)
        except (OSError, NotImplementedError): self.skipTest("symlink unavailable")
        with self.assertRaises(ValueError): guard(alias / "linked-new")
    def test_missing_tools_keep_not_run_external_record(self):
        outer, vault, module = self.relocated("run_hdl.py")
        target = outer / "external"; target.mkdir()
        with patch.object(module.shutil, "which", return_value=None):
            result = module.run(target)
        self.assertEqual(result["status"], "not_run")
        self.assertTrue((target / "execution-status.json").is_file())


if __name__ == "__main__": unittest.main()
