"""Generator guards and Android resource identity; no service/device is launched."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent / 'fixtures/generate-fixtures.sh'

class FixtureGenerationTests(unittest.TestCase):
    def run_generator(self, *args):
        return subprocess.run(['sh', str(SCRIPT), *map(str, args)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_missing_relative_and_existing_outputs_are_rejected(self):
        self.assertNotEqual(self.run_generator().returncode, 0)
        self.assertNotEqual(self.run_generator('relative-directory').returncode, 0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'keep.txt'
            marker.write_text('preserved')
            self.assertNotEqual(self.run_generator(root).returncode, 0)
            self.assertEqual(marker.read_text(), 'preserved')
            link = root / 'existing-link'
            link.symlink_to(root, target_is_directory=True)
            self.assertNotEqual(self.run_generator(link).returncode, 0)
            self.assertEqual(set(p.name for p in root.iterdir()), {'keep.txt', 'existing-link'})

    def test_generated_debug_ca_matches_server_trust_material_and_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new-tls'
            result = self.run_generator(output)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            self.assertEqual((output/'ca.pem').read_bytes(),
                             (output/'android-res/raw/wwl_public_ca.pem').read_bytes())
            for name in ['ca-public-fixture.key', 'server-public-fixture.key']:
                self.assertEqual((output/name).stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            original = (output/'ca.pem').read_bytes()
            self.assertNotEqual(self.run_generator(output).returncode, 0)
            self.assertEqual((output/'ca.pem').read_bytes(), original)

if __name__ == '__main__':
    unittest.main()
