import csv,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CODE=ROOT/"code"/"rd_case.py"; PREP=ROOT/"code"/"prepare_data.R"
class TestRD(unittest.TestCase):
    def test_fuzzy_hand_calculation(self): self.assertAlmostEqual((56.3-50)/(.70-.25),14)
    def test_real_data_contract(self):
        raw=os.environ.get("LEE2008_DATA")
        proof=os.environ.get("LEE2008_PROOF")
        if not raw or not proof: self.skipTest("set LEE2008_DATA and LEE2008_PROOF")
        with tempfile.TemporaryDirectory() as td:
            o=Path(td)/"g"; a=Path(td)/"a"; subprocess.run([sys.executable,str(CODE),"--data",raw,"--source-proof",proof,"--out",str(o),"--assets",str(a)],check=True)
            r=json.loads((o/"rd_results.json").read_text()); e=r["estimates"]["h10_linear"]
            self.assertEqual((r["provenance"]["rows_use"],r["provenance"]["analysis_rows"]),(6559,6558)); self.assertEqual((e["n_left"],e["n_right"]),(577,632))
            self.assertAlmostEqual(e["tau"],.05936725956002731,12); self.assertAlmostEqual(e["se_hc1"],.012927480309931338,12); self.assertTrue(r["provenance"]["source_proof_verified"]); self.assertFalse(r["estimator"]["rbc"]); self.assertIn("<svg",(a/"01-众议院选举断点图.svg").read_text())
            with open(raw,newline="") as f: rows=list(csv.DictReader(f))
            rows[0]["demsharenext"]=str(float(rows[0]["demsharenext"])+.001); bad_y=Path(td)/"bad-y.csv"
            with bad_y.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
            failed=subprocess.run([sys.executable,str(CODE),"--data",str(bad_y),"--source-proof",proof,"--out",str(o),"--assets",str(a)],capture_output=True)
            self.assertNotEqual(failed.returncode,0); self.assertIn(b"CSV SHA-256 mismatch",failed.stderr)
            with open(raw,newline="") as f: rows=list(csv.DictReader(f))
            rows[0]["right"]=""; bad=Path(td)/"bad-zero.csv"
            with bad.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
            forged=Path(td)/"forged.provenance"
            forged.write_text("dta_sha256=4114a0c1120e6a5cf1e7a2e1f790f04c8d1678bc4e41bd2a901a088affae9db6\ndta_sha256_verified=true\ncsv_sha256="+hashlib.sha256(bad.read_bytes()).hexdigest()+"\nrows_use=6559\n")
            failed=subprocess.run([sys.executable,str(CODE),"--data",str(bad),"--source-proof",str(forged),"--out",str(o),"--assets",str(a)],capture_output=True)
            self.assertNotEqual(failed.returncode,0); self.assertIn(b"unique exact-zero",failed.stderr)

    def test_converter_rejects_wrong_dta_hash(self):
        if not shutil.which("Rscript"): self.skipTest("Rscript unavailable")
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td)/"fake.dta"; fake.write_bytes(b"not the official data")
            p=subprocess.run(["Rscript",str(PREP),str(fake),str(Path(td)/"x.csv")],capture_output=True)
            self.assertNotEqual(p.returncode,0); self.assertIn(b"SHA-256 mismatch",p.stderr)
if __name__=="__main__": unittest.main()
