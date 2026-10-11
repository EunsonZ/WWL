"""Independent subprocess oracles; C assertions/injection tests live separately."""
from pathlib import Path
from fractions import Fraction
import math
import random
import struct
import subprocess
import sys
import tempfile
import unittest

BUILD = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else Path("build").resolve()
class CLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
    def run_tool(self, name, payload, *args, output=None):
        path = self.base / "input"
        path.write_bytes(payload)
        argv = [str(BUILD/name), *args, str(path)] if name == "wordfreq" else [str(BUILD/name), args[0], str(path), *args[1:]]
        return subprocess.run(argv, stdout=output or subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    def test_first_input(self):
        for payload,expected_status,expected_output in [
            (b"2\n4\n6\n8\n",0,b"n=4\nmean_mv=5\n"),
            (b"2\n4",0,b"n=2\nmean_mv=3\n"),
            (b"2\nword\n",1,b""),(b"",1,b""),(b"4096\n",1,b""),
            (b"1\n2\n3\n4\n5\n",1,b""),(b"+2\n",1,b"")]:
            r = subprocess.run([str(BUILD/"first_input")],input=payload,capture_output=True,check=False)
            self.assertEqual(r.returncode,expected_status)
            self.assertEqual(r.stdout,expected_output)
    def test_fixed_fixtures(self):
        expected = (Path("fixtures")/"expected.txt").read_bytes()
        self.assertEqual(self.run_tool("measure",b"4\n2 4 6 8\n","text").stdout,expected)
        r = self.run_tool("measure",bytes.fromhex((Path("fixtures")/"samples.hex").read_text()),"binary")
        self.assertEqual(r.returncode,0); self.assertEqual(r.stdout,expected)
        self.assertEqual((Path("fixtures")/"samples.bin").read_bytes(),bytes.fromhex((Path("fixtures")/"samples.hex").read_text()))
    def test_statistics_and_fir_independent_oracle(self):
        rng = random.Random(242)
        for size in [1,2,4,17,100]:
            codes = [rng.randrange(4096) for _ in range(size)]
            for scale,offset in [(1,0),(0.5,-3),(2,7)]:
                data = struct.pack(">I",size)+b"".join(struct.pack(">H",q) for q in codes)
                r = self.run_tool("measure",data,"binary",str(scale),str(offset),"0.25")
                self.assertEqual(r.returncode,0,r.stderr)
                fields = dict(line.split("=",1) for line in r.stdout.decode().splitlines())
                values = [Fraction(str(scale))*q+offset for q in codes]
                mean = sum(values)/size
                variance = sum((x-mean)**2 for x in values)/size
                rms2 = sum(x*x for x in values)/size
                for field,expected in [("sum_mv",sum(values)),("mean_mv",mean),
                    ("descriptive_variance_mv2",variance),("rms2_mv2",rms2)]:
                    self.assertTrue(math.isclose(float(fields[field]),float(expected),rel_tol=1e-12,abs_tol=1e-10),(field,fields))
                previous = Fraction(0)
                for i,x in enumerate(values):
                    self.assertEqual(float(fields[f"fir_mv[{i}]"]),float((previous+x)/2)); previous=x
                self.assertNotIn(f"fir_mv[{size}]",fields)
    def test_input_failure_classes(self):
        for payload,error in [(b"",b"truncated"),(b"0",b"empty"),(b"4 2 4 6",b"truncated"),
                              (b"1 4096",b"invalid"),(b"1000001",b"limit"),(b"1 2\x00",b"invalid"),
                              (b"1 2 3",b"invalid"),(b"1 99999999999",b"limit")]:
            r=self.run_tool("measure",payload,"text")
            self.assertEqual(r.returncode,1); self.assertEqual(r.stdout,b""); self.assertIn(b"error="+error,r.stderr)
        frame=struct.pack(">I4H",4,2,4,6,8)
        for end in range(len(frame)):
            r=self.run_tool("measure",frame[:end],"binary")
            self.assertEqual(r.returncode,1); self.assertIn(b"truncated",r.stderr); self.assertEqual(r.stdout,b"")
        for payload,error in [(frame+b"\x00",b"invalid"),(struct.pack(">IH",1,4096),b"invalid"),
                              (struct.pack(">I",1000001),b"limit"),(b"\0\0\0\0",b"empty")]:
            r=self.run_tool("measure",payload,"binary")
            self.assertEqual(r.returncode,1); self.assertIn(error,r.stderr)
        r=self.run_tool("measure",b"0"+b" "*16777216,"text")
        self.assertEqual(r.returncode,1);self.assertIn(b"limit",r.stderr)
    def test_invalid_calibration(self):
        for params in [("nan","0","1"),("inf","0","1"),("0","0","1"),
                       ("1","1000000001","1"),("1","0","0"),("1x","0","1")]:
            r=self.run_tool("measure",b"1 2","text",*params)
            self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b"");self.assertIn(b"invalid",r.stderr)
    def test_wordfreq(self):
        for payload,expected in [(b"Red blue RED. blue green red",b"red 3\nblue 2\ngreen 1\n"),
                                 (b"",b""),(b"b A",b"a 1\nb 1\n"),(b"tu anr bmd tv tu",b"tu 2\nanr 1\nbmd 1\ntv 1\n"),(b"a"*63,b"a"*63+b" 1\n")]:
            r=self.run_tool("wordfreq",payload)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,expected)
        def key(i):
            return bytes([97+i//26,97+i%26])
        for payload,error in [(b"a"*64,b"limit"),("café".encode(),b"invalid"),
                              (b" ".join(key(i) for i in range(257)),b"limit"),
                              (b" "*1048577,b"limit")]:
            r=self.run_tool("wordfreq",payload)
            self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b"");self.assertIn(error,r.stderr)
        r=self.run_tool("wordfreq",b" ".join(key(i) for i in range(256)))
        self.assertEqual(r.returncode,0);self.assertEqual(len(r.stdout.splitlines()),256)
        self.assertEqual(self.run_tool("wordfreq",b" "*1048576).returncode,0)
    def test_actual_stdout_failure(self):
        # Host fixture: a read-only descriptor passed as stdout induces EBADF.
        readonly=self.base/"readonly";readonly.write_bytes(b"existing")
        with readonly.open("rb") as output:
            for name,payload,args in [("measure",b"4 2 4 6 8",("text",)),("wordfreq",b"red red",())]:
                r=self.run_tool(name,payload,*args,output=output)
                self.assertEqual(r.returncode,1);self.assertIn(b"error=io",r.stderr)
        self.assertEqual(readonly.read_bytes(),b"existing")
if __name__ == "__main__": unittest.main(verbosity=2)
