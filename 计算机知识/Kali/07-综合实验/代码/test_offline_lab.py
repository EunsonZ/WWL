"""Small, deterministic, local-only regression tests. No Kali tools required."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import generate_fixtures as gf
import offline_lab as lab

def parse_frames(raw: bytes) -> list[bytes]:
    if len(raw) < 24 or raw[:4] != b"\xd4\xc3\xb2\xa1":
        raise ValueError("wrong PCAP header")
    offset, result = 24, []
    while offset < len(raw):
        if offset + 16 > len(raw):
            raise ValueError("truncated record")
        sec, usec, captured, actual = struct.unpack_from("<IIII", raw, offset)
        if captured != actual or usec >= 1_000_000:
            raise ValueError("unexpected record fields")
        offset += 16
        if offset + captured > len(raw):
            raise ValueError("truncated packet")
        result.append(raw[offset:offset+captured])
        offset += captured
    return result

def ones_sum(raw: bytes) -> int:
    # Independent reference path (not the generator's checksum function).
    total = sum(int.from_bytes(raw[i:i+2].ljust(2, b"\0"), "big") for i in range(0, len(raw), 2))
    return (total & 0xffff) + (total >> 16) if total <= 0xffffffff else _fold(total)

def _fold(total: int) -> int:
    while total > 65535:
        total = (total // 65536) + (total % 65536)
    return total

class AuthorizationTests(unittest.TestCase):
    def test_owner_allowed(self):
        self.assertTrue(lab.can_read("alice", 17))
        self.assertTrue(lab.can_read("bob", 18))
    def test_cross_owner_denied(self):
        self.assertFalse(lab.can_read("bob", 17))
        self.assertFalse(lab.can_read("alice", 18))
    def test_missing_object_and_unknown_user(self):
        self.assertFalse(lab.can_read("alice", 999))
        self.assertFalse(lab.can_read("mallory", 17))
    def test_invalid_types_fail_closed(self):
        for user, ident in [(None,17),("alice","17"),("alice",True),([],17),("alice",17.0)]:
            with self.subTest(user=user, ident=ident):
                self.assertFalse(lab.can_read(user, ident))

class SQLTests(unittest.TestCase):
    def test_normal_query(self):
        self.assertEqual(lab.query_names("alice"), ["alice"])
    def test_injection_demonstrates_difference(self):
        self.assertEqual(lab.query_names(lab.INJECTION, parameterized=False), ["alice","bob"])
        self.assertEqual(lab.query_names(lab.INJECTION), [])
    def test_safe_quote_literal(self):
        self.assertEqual(lab.query_names("O'Reilly"), [])
    def test_bad_sql_not_empty_result(self):
        with self.assertRaises(lab.LabInputError): lab.query_names("'", parameterized=False)
    def test_input_contract(self):
        for value in [None, 7, "x"*257]:
            with self.assertRaises(lab.LabInputError): lab.query_names(value)
        with self.assertRaises(lab.LabInputError): lab.query_names("alice", parameterized="false")
    def test_database_isolated_per_call(self):
        self.assertEqual(lab.query_names("bob"), ["bob"])
        self.assertEqual(lab.query_names("absent"), [])

class LogTests(unittest.TestCase):
    def test_fixture_counts(self):
        result = lab.summarize_logs(gf.contents()["access.jsonl"].decode().splitlines())
        self.assertEqual(result,{"records":6,"statuses":{"200":3,"403":1,"404":1,"500":1}})
    def test_empty_input(self):
        self.assertEqual(lab.summarize_logs([]),{"records":0,"statuses":{}})
    def test_malformed_and_blank(self):
        for line in ["{", "", "null", "[]"]:
            with self.assertRaises(lab.LabInputError): lab.summarize_logs([line])
    def test_invalid_status(self):
        for status in [True,"200",99,600,None,200.0]:
            line=json.dumps({"time":"x","actor":"alice","path":"/","status":status})
            with self.assertRaises(lab.LabInputError): lab.summarize_logs([line])
    def test_missing_required_field(self):
        with self.assertRaises(lab.LabInputError): lab.summarize_logs(['{"status":200}'])
    def test_invalid_second_line_is_not_skipped(self):
        valid='{"time":"x","actor":"alice","path":"/","status":200}'
        with self.assertRaisesRegex(lab.LabInputError,"line 2"):
            lab.summarize_logs([valid,"broken"])

class HashTests(unittest.TestCase):
    def test_known_sha256_vector(self):
        digest="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        self.assertEqual(lab.match_toy_hashes([digest],["abc"]),{digest:"abc"})
    def test_toy_candidates(self):
        files=gf.contents()
        hashes=files["hashes-sha256.txt"].decode().splitlines()
        words=files["candidate-words.txt"].decode().splitlines()
        self.assertEqual(set(lab.match_toy_hashes(hashes,words).values()),{"kali-lab-2026","Cedar-7!"})
        self.assertEqual(len(lab.match_toy_hashes(hashes,[w for w in words if w!="Cedar-7!"])),1)
    def test_empty_and_bad_hash(self):
        self.assertEqual(lab.match_toy_hashes([],[]),{})
        with self.assertRaises(lab.LabInputError): lab.match_toy_hashes(["not-a-hash"],["x"])

class FixtureTests(unittest.TestCase):
    def test_deterministic_and_no_network(self):
        with mock.patch.object(socket,"socket",side_effect=AssertionError("network forbidden")):
            self.assertEqual(gf.contents(),gf.contents())
    def test_manifest_matches(self):
        data=gf.contents(); expected=json.loads(data["expected.json"])
        self.assertEqual(set(expected["sha256"]),set(data)-{"expected.json"})
        for name,digest in expected["sha256"].items():
            self.assertEqual(hashlib.sha256(data[name]).hexdigest(),digest)
    def test_generate_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/"new"; gf.generate(dest)
            with self.assertRaises(FileExistsError): gf.generate(dest)
            self.assertEqual((dest/"http-lab.pcap").read_bytes(),gf.build_pcap())
    def test_generate_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); (base/"real").mkdir(); (base/"link").symlink_to(base/"real",target_is_directory=True)
            with self.assertRaises(ValueError): gf.generate(base/"link"/"new")
    def test_pcap_headers_and_checksums(self):
        packets=parse_frames(gf.build_pcap()); self.assertEqual(len(packets),10)
        for packet in packets:
            self.assertEqual(packet[12:14],b"\x08\x00")
            ip=packet[14:]; size=int.from_bytes(ip[2:4],"big"); ip=ip[:size]
            self.assertEqual(_fold(ones_sum(ip[:20])),65535)
            segment=ip[20:]
            pseudo=ip[12:20]+b"\0\x06"+len(segment).to_bytes(2,"big")
            self.assertEqual(_fold(ones_sum(pseudo+segment)),65535)
    def test_pcap_sequence_and_http(self):
        packets=parse_frames(gf.build_pcap())
        segments=[p[34:14+int.from_bytes(p[16:18],"big")] for p in packets]
        self.assertEqual([x[13] for x in segments],[2,18,16,24,16,24,16,17,17,16])
        request=segments[3][20:]; response=segments[5][20:]
        self.assertTrue(request.startswith(b"GET /health HTTP/1.1\r\n"))
        header,body=response.split(b"\r\n\r\n",1)
        length=int([x for x in header.split(b"\r\n") if x.startswith(b"Content-Length:")][0].split(b":")[1])
        self.assertEqual(length,len(body)); self.assertEqual(json.loads(body),{"status":"ok","synthetic":True})
        def fields(index): return struct.unpack("!II",segments[index][4:12])
        self.assertEqual(fields(4),(5001,1001+len(request)))
        self.assertEqual(fields(6),(1001+len(request),5001+len(response)))
        self.assertEqual(fields(9),(5002+len(response),1002+len(request)))
    def test_pcap_truncation_rejected(self):
        with self.assertRaises(ValueError): parse_frames(gf.build_pcap()[:-1])
    def test_xml_and_marker_fixtures(self):
        data=gf.contents()
        self.assertEqual(ET.fromstring(data["nmap-before.xml"]).find(".//port/state").attrib["state"],"open")
        self.assertEqual(ET.fromstring(data["nmap-after.xml"]).find(".//port/state").attrib["state"],"closed")
        positive,negative=data["files/positive.txt"],data["files/negative.txt"]
        self.assertIn(b"KALI_LAB_MARKER_B",positive); self.assertNotIn(b"KALI_LAB_MARKER_B",negative)
        self.assertLess(len(positive),4096)
    def test_full_demo_from_generated_files(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"fixtures";gf.generate(target)
            result=lab.run_demo(target)
            self.assertEqual(result["toy_hashes"],{"targets":2,"candidates":5,"matches":2})
            self.assertFalse(result["authorization"]["bob_17"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
