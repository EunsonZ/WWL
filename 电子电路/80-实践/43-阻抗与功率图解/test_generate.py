import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest


class OutputContract(unittest.TestCase):
    def test_import_and_missing_output(self):
        source=Path(__file__).parent
        with tempfile.TemporaryDirectory() as td:
            cwd=Path(td)
            env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1')
            script='import sys;sys.argv=["generate.py","--nonsense"];import generate'
            p=subprocess.run([sys.executable,'-B','-c',script],cwd=cwd,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(list(cwd.iterdir()),[])
            p=subprocess.run([sys.executable,'-B',str(source/'generate.py')],cwd=cwd,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,2)
            self.assertEqual(list(cwd.iterdir()),[])

    def test_explicit_output_and_occupied_path(self):
        import generate
        before=dict(os.environ),random.getstate(),Path.cwd()
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'new'
            generate.generate(target)
            self.assertEqual(len(list(target.iterdir())),14)
            for n in target.glob('*.svg'):
                self.assertIn('viewBox=',n.read_text())
            sent=(target/'cases.json').read_bytes()
            with self.assertRaises(FileExistsError):generate.generate(target)
            self.assertEqual((target/'cases.json').read_bytes(),sent)
            with self.assertRaises(ValueError):generate.generate(None)
        self.assertEqual(before,(dict(os.environ),random.getstate(),Path.cwd()))


if __name__=='__main__':unittest.main()
