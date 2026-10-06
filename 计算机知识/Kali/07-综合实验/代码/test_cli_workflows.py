"""Reviewed local jq regression tests and independent arithmetic examples.

No network, installations, listeners, or changes outside in-memory subprocess input.
jq tests require an existing jq CLI; missing it is an explicit error, not a pass.
The tiny bundled jq filter is intentionally a JSON VALUE STREAM schema, not JSONL.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import unicodedata
import unittest

HERE=Path(__file__).resolve().parent

class JqWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jq=shutil.which('jq')
        if cls.jq is None:raise RuntimeError('jq absent: jq regression tests were not run')
        cls.filter=HERE/'validate_status.jq'
        if not cls.filter.is_file():raise RuntimeError('authoritative jq filter missing')
    def run_filter(self,text):
        return subprocess.run([self.jq,'-e','-s','-f',str(self.filter)],input=text,
                              text=True,capture_output=True,timeout=5)
    def test_legacy_exit_code_hides_early_bad_record(self):
        p=subprocess.run([self.jq,'-e','type == "object"'],input='[]\n{"status":200}\n',
                         text=True,capture_output=True,timeout=5)
        self.assertEqual((p.returncode,p.stdout),(0,'false\ntrue\n'))
    def test_valid_records(self):
        p=self.run_filter('{"status":200}\n{"status":403}\n')
        self.assertEqual((p.returncode,p.stdout),(0,'true\n'))
    def test_bad_first_record_rejected(self):
        self.assertEqual(self.run_filter('[]\n{"status":200}\n').returncode,1)
    def test_bad_middle_record_rejected(self):
        self.assertEqual(self.run_filter('{"status":200}\nnull\n{"status":201}').returncode,1)
    def test_bad_last_record_rejected(self):
        self.assertEqual(self.run_filter('{"status":200}\n[]').returncode,1)
    def test_empty_rejected_by_explicit_policy(self):
        self.assertEqual(self.run_filter('').returncode,1)
    def test_missing_status(self):
        self.assertEqual(self.run_filter('{}').returncode,1)
    def test_bool_status(self):
        self.assertEqual(self.run_filter('{"status":true}').returncode,1)
    def test_string_status(self):
        self.assertEqual(self.run_filter('{"status":"200"}').returncode,1)
    def test_fractional_status(self):
        self.assertEqual(self.run_filter('{"status":200.5}').returncode,1)
    def test_range_limits(self):
        for value in [99,600,-1,1000]:
            with self.subTest(value=value):
                self.assertEqual(self.run_filter(json.dumps({'status':value})).returncode,1)
        for value in [100,599,200.0]:
            with self.subTest(value=value):
                self.assertEqual(self.run_filter(json.dumps({'status':value})).returncode,0)
    def test_syntax_error_is_not_schema_false(self):
        p=self.run_filter('{"status":200}\n{"status":')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('parse error',p.stderr.lower())
    def test_blank_lines_are_not_rejected_by_value_stream_contract(self):
        self.assertEqual(self.run_filter('\n{"status":200}\n\n').returncode,0)
    def test_multiple_values_on_one_line_are_allowed(self):
        self.assertEqual(self.run_filter('{"status":200} {"status":201}').returncode,0)
    def test_real_synthetic_fixture(self):
        fixtures=HERE.parent/('fixtures' if (HERE.parent/'fixtures').is_dir() else '夹具')
        p=self.run_filter((fixtures/'access.jsonl').read_text())
        self.assertEqual(p.returncode,0,p.stderr)

class IndependentExamples(unittest.TestCase):
    def test_http_age_intermediates(self):
        request,response,date_header,age_header,now=0,2,0,20,17
        apparent=max(0,response-date_header)
        corrected=max(apparent,age_header+(response-request))
        age=corrected+(now-response)
        self.assertEqual((apparent,corrected,age,60-age),(2,22,37,23))
    def test_tcp_interval_union_not_packet_sum(self):
        a,b=set(range(1,101)),set(range(51,151))
        self.assertEqual((len(a)+len(b),len(a|b),len(a&b)),(200,150,50))
    def test_acl_named_user_mask(self):
        self.assertEqual(0b110 & 0b100,0b100)
    def test_elf_file_backed_and_memory_only(self):
        offset,vaddr,filesz,memsz=0x1000,0x4000,0x600,0x900
        good,zero_fill=0x4210,0x4700
        self.assertTrue(vaddr<=good<vaddr+filesz)
        self.assertEqual(offset+(good-vaddr),0x1210)
        self.assertTrue(vaddr+filesz<=zero_fill<vaddr+memsz)
    def test_sparse_logical_and_elided_lengths(self):
        self.assertEqual((4096*3,4096*2),(12288,8192))
    def test_classifier_metrics(self):
        tp,fp,fn,tn=1,1,1,2
        self.assertEqual(tp+fp+fn+tn,5)
        self.assertEqual((tp/(tp+fp),tp/(tp+fn)),(.5,.5))
    def test_relation_join_multiplicity(self):
        pairs=[(request,alert) for request in ('r1','r2') for alert in ('a1','a2','a3')]
        self.assertEqual(len(pairs),6)
    def test_unicode_bytes_and_nfc(self):
        a,b='Caf\u00e9','Cafe\u0301'
        self.assertNotEqual(a.encode(),b.encode())
        self.assertNotEqual(hashlib.sha256(a.encode()).digest(),hashlib.sha256(b.encode()).digest())
        self.assertEqual(unicodedata.normalize('NFC',a),unicodedata.normalize('NFC',b))
    def test_large_id_lost_after_float_roundtrip(self):
        integer=9007199254740993
        self.assertNotEqual(int(float(integer)),integer)
        self.assertEqual(json.loads(str(integer)),integer)

if __name__=='__main__':unittest.main(verbosity=2)