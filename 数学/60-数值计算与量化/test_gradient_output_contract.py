"""Path-only regression definitions, stop before numerical case/render work."""
from pathlib import Path
import importlib.util
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

class StopBeforeCase(Exception): pass

class GradientOutputContract(unittest.TestCase):
    def test_source_descendants_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'vault/math'; source.mkdir(parents=True)
            origin=Path(__file__).with_name('gradient_flow_precision_lab.py')
            target=source/origin.name; shutil.copyfile(origin,target)
            spec=importlib.util.spec_from_file_location('relocated_gradient',target)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
            self.addCleanup(sys.modules.pop,spec.name,None);spec.loader.exec_module(module)
            existing=source/'existing';existing.mkdir()
            with patch.object(module,'case',side_effect=StopBeforeCase) as case:
                for output in (source,source/'new',existing):
                    with self.assertRaises(ValueError): module.generate(output)
                self.assertFalse((source/'new').exists());case.assert_not_called()
                external=root/'vault/other-lab'
                with self.assertRaises(StopBeforeCase): module.generate(external)
                self.assertTrue(external.is_dir())
                alias=root/'alias'
                try: alias.symlink_to(source,target_is_directory=True)
                except (OSError,NotImplementedError): self.skipTest('symlink unavailable')
                with self.assertRaises(ValueError): module.generate(alias/'new')

if __name__=='__main__': unittest.main()
