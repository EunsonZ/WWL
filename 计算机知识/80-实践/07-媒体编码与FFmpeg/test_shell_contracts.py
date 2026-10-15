"""Unexecuted regression definitions; stubs never decode/transcode media."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

class ShellContracts(unittest.TestCase):
    def workspace(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name); (root / "bin").mkdir(); (root / "clip.mkv").write_bytes(b"fixture")
        for tool in ("ffmpeg", "ffprobe"):
            stub = root / "bin" / tool
            stub.write_text("#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> \"$TRACE\"\n")
            stub.chmod(0o700)
        env = dict(os.environ, PATH=str(root / "bin") + os.pathsep + os.environ["PATH"], TRACE=str(root / "trace"))
        return root, env

    def run_row(self, row):
        root, env = self.workspace(); (root / "manifest.tsv").write_text(row + "\n")
        completed = subprocess.run(["bash", str(ROOT / "04_batch_manifest.sh"), str(root / "manifest.tsv"), str(root / "out")], env=env, capture_output=True, timeout=5)
        trace = (root / "trace").read_text() if (root / "trace").exists() else ""
        return completed, trace

    def test_invalid_column_counts_and_empty_fields_never_probe(self):
        for row in ("clip.mkv\tout.mp4\t0", "clip.mkv\tout.mp4\t0\t1\t", "clip.mkv\tout.mp4\t\t0\t1", "clip.mkv\tout.mp4\t0\t", "clip.mkv\t\t0\t1", "clip.mkv\tout.mp4\t\t1"):
            with self.subTest(row=row):
                result, trace = self.run_row(row)
                self.assertNotEqual(result.returncode, 0); self.assertEqual(trace, "")

    def test_all_decimal_zero_spellings_never_probe(self):
        for duration in ("0", "0.0", "00", "0.00", "000.000"):
            result, trace = self.run_row("clip.mkv\tout.mp4\t0\t" + duration)
            self.assertNotEqual(result.returncode, 0); self.assertEqual(trace, "")

    def test_valid_four_columns_reach_probe(self):
        for duration in ("0.1", "1"):
            result, trace = self.run_row("clip.mkv\tout.mp4\t0\t" + duration)
            self.assertEqual(result.returncode, 0, result.stderr); self.assertIn("ffprobe", trace)

class RealFilterPathContracts(unittest.TestCase):
    """Future one-frame parser check; never run by the current author batch."""
    def test_fixed_stats_names_in_special_output_directories(self):
        import shutil
        if not shutil.which("ffmpeg"): self.skipTest("ffmpeg unavailable")
        with tempfile.TemporaryDirectory() as directory:
            for name in ("ordinary", "space path", "colon:path", "comma,path", "quote'path"):
                output=Path(directory)/name;output.mkdir()
                args=["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                      "-f", "lavfi", "-i", "testsrc2=size=16x16:rate=1:duration=1",
                      "-filter_complex", "[0:v]split[a][b];[a][b]psnr=stats_file=psnr.log",
                      "-frames:v", "1", "-f", "null", "-"]
                result=subprocess.run(args,cwd=output,capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertTrue((output/"psnr.log").is_file())

if __name__ == "__main__": unittest.main()
