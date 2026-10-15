"""Tests the new input adapter; does not rerun the three complete physics labs."""
import importlib.util
from pathlib import Path
import unittest
import subprocess
import sys

path=Path(__file__).resolve().parents[1]/"examples/physics_readouts.py"
spec=importlib.util.spec_from_file_location("readouts",path)
readouts=importlib.util.module_from_spec(spec)
spec.loader.exec_module(readouts)

class EncodingTests(unittest.TestCase):
    def test_ties_and_domain(self):
        self.assertEqual([readouts.encode_mv(v) for v in (0,.5,1.5,2.5,4095)],
                         [0,0,2,2,4095])
        for value in (-.001,4095.001,float("nan"),float("inf")):
            with self.assertRaises(ValueError): readouts.encode_mv(value)
        for value in (True,1j,"1",[1]):
            with self.assertRaises(TypeError): readouts.encode_mv(value)

    def test_fraction_summary(self):
        s=readouts.summarize([2,4,6,8])
        self.assertEqual(s,{"n":4,"sum_mv":20,"mean_mv":"5",
                            "variance_mv2":"5","rms2_mv2":"30"})

    def test_source_output_rejected_before_loading(self):
        # A bogus vault still yields the explicit output-boundary refusal first.
        result=subprocess.run([sys.executable,"-B",str(path),"--vault",
            str(path.parent),"--output",str(path.parent/"forbidden-output")],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertIn("--output must be outside",result.stderr)
        self.assertFalse((path.parent/"forbidden-output").exists())

if __name__ == "__main__": unittest.main()
