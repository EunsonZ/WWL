#!/usr/bin/env python3
"""Create deterministic, synthetic teaching fixtures. Never opens a socket.

The destination must be a NEW child of an existing, non-symlink directory.
This is an overwrite guard for trusted local use, not a hostile multi-user sandbox.
"""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import struct

FIXTURE_VERSION = "1.0"
BASE_TS = 1704067200  # Deliberately synthetic: 2024-01-01 00:00:00 UTC.
TOY_PASSWORDS = ("kali-lab-2026", "Cedar-7!")  # Public teaching strings, NOT secrets.
CANDIDATES = ("hello", "kali-lab-2026", "Cedar-7!", "not-the-answer", "example")
REQUEST = b"GET /health HTTP/1.1\r\nHost: web.lab.test:8000\r\nConnection: close\r\n\r\n"
BODY = b'{"status":"ok","synthetic":true}\n'
RESPONSE = (b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
            + str(len(BODY)).encode("ascii") + b"\r\nConnection: close\r\n\r\n" + BODY)

def checksum(data: bytes) -> int:
    """Internet checksum over network-order 16-bit words."""
    if len(data) % 2:
        data += b"\0"
    value = sum(struct.unpack(f"!{len(data)//2}H", data))
    while value >> 16:
        value = (value & 0xffff) + (value >> 16)
    return (~value) & 0xffff

def frame(from_client: bool, seq: int, ack: int, flags: int,
          payload: bytes = b"", ident: int = 1) -> bytes:
    """Ethernet + IPv4 + TCP, no options, no FCS, padded Ethernet minimum."""
    src, dst = ("192.0.2.10", "192.0.2.20") if from_client else ("192.0.2.20", "192.0.2.10")
    sport, dport = (40000, 8000) if from_client else (8000, 40000)
    a, b = ipaddress.ip_address(src).packed, ipaddress.ip_address(dst).packed
    tcp = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, flags, 65535, 0, 0)
    pseudo = a + b + struct.pack("!BBH", 0, 6, len(tcp) + len(payload))
    tcp_sum = checksum(pseudo + tcp + payload)
    tcp = tcp[:16] + struct.pack("!H", tcp_sum) + tcp[18:]
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp) + len(payload),
                     ident, 0x4000, 64, 6, 0, a, b)
    ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
    mac_c, mac_s = bytes.fromhex("020000000010"), bytes.fromhex("020000000020")
    eth = (mac_s + mac_c if from_client else mac_c + mac_s) + b"\x08\x00"
    return (eth + ip + tcp + payload).ljust(60, b"\0")

def build_pcap() -> bytes:
    c, s = 1001 + len(REQUEST), 5001 + len(RESPONSE)
    packets = [
        frame(True, 1000, 0, 0x02, ident=1),
        frame(False, 5000, 1001, 0x12, ident=2),
        frame(True, 1001, 5001, 0x10, ident=3),
        frame(True, 1001, 5001, 0x18, REQUEST, 4),
        frame(False, 5001, c, 0x10, ident=5),
        frame(False, 5001, c, 0x18, RESPONSE, 6),
        frame(True, c, s, 0x10, ident=7),
        frame(False, s, c, 0x11, ident=8),
        frame(True, c, s + 1, 0x11, ident=9),
        frame(False, s + 1, c + 1, 0x10, ident=10),
    ]
    output = bytearray(struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
    for index, packet in enumerate(packets):
        output += struct.pack("<IIII", BASE_TS, index * 100000, len(packet), len(packet))
        output += packet
    return bytes(output)

def scan_xml(open_port: bool) -> str:
    state = "open" if open_port else "closed"
    reason = "syn-ack" if open_port else "conn-refused"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- SYNTHETIC fixture; not a captured Nmap execution. -->
<nmaprun scanner="nmap" args="SYNTHETIC-NOT-EXECUTED" start="{BASE_TS}" version="SYNTHETIC" xmloutputversion="1.05">
<scaninfo type="connect" protocol="tcp" numservices="1" services="8000"/>
<host><status state="up" reason="user-set"/>
<address addr="127.0.0.1" addrtype="ipv4"/><hostnames/>
<ports><port protocol="tcp" portid="8000"><state state="{state}" reason="{reason}" reason_ttl="0"/></port></ports>
</host><runstats><finished time="{BASE_TS + 1}" elapsed="1.00" exit="success"/><hosts up="1" down="0" total="1"/></runstats></nmaprun>
'''

def contents() -> dict[str, bytes]:
    events = [
        {"time":"2024-01-01T00:00:00Z","actor":"alice","path":"/health","status":200},
        {"time":"2024-01-01T00:00:01Z","actor":"alice","path":"/reports/17","status":200},
        {"time":"2024-01-01T00:00:02Z","actor":"bob","path":"/reports/17","status":403},
        {"time":"2024-01-01T00:00:03Z","actor":"alice","path":"/missing","status":404},
        {"time":"2024-01-01T00:00:04Z","actor":"bob","path":"/reports/18","status":200},
        {"time":"2024-01-01T00:00:05Z","actor":"alice","path":"/toy-error","status":500},
    ]
    text = {
        "web/index.html": '<!doctype html><html lang="en"><meta charset="utf-8"><title>Kali Local Lab</title><h1>PUBLIC SYNTHETIC LAB</h1><p>No login, no database, no private content.</p></html>\n',
        "web/health": BODY.decode(),
        "web/api/status.json": BODY.decode(),
        "web/robots.txt": "User-agent: *\nDisallow: /missing\n# Synthetic; robots.txt is not an access control.\n",
        "paths.txt": "health\napi/status.json\nrobots.txt\nindex.html\nmissing\n",
        "access.jsonl": "".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in events),
        "hashes-sha256.txt": "".join(hashlib.sha256(x.encode()).hexdigest() + "\n" for x in TOY_PASSWORDS),
        "candidate-words.txt": "\n".join(CANDIDATES) + "\n",
        "files/positive.txt": "SYNTHETIC BENIGN FILE\nKALI_LAB_MARKER_A\nKALI_LAB_MARKER_B\n",
        "files/negative.txt": "SYNTHETIC BENIGN FILE\nKALI_LAB_MARKER_A\nThe second marker is deliberately absent.\n",
        "iac/pod.yaml": '# SYNTHETIC CONFIGURATION ONLY: never deploy. Image is deliberately nonexistent.\napiVersion: v1\nkind: Pod\nmetadata:\n  name: kali-lab-synthetic\nspec:\n  containers:\n    - name: demo\n      image: example.invalid/kali-lab/no-image:synthetic\n',
        "nmap-before.xml": scan_xml(True),
        "nmap-after.xml": scan_xml(False),
    }
    result = {k: v.encode("utf-8") for k, v in text.items()}
    result["http-lab.pcap"] = build_pcap()
    expected = {
        "fixture_version": FIXTURE_VERSION,
        "provenance": "All data synthetic. Fixed timestamps are NOT collection times.",
        "pcap": {"frames":10,"connections":1,"requests":1,"method":"GET","uri":"/health",
                 "status":200,"client":"192.0.2.10","server":"192.0.2.20","server_port":8000,
                 "request_bytes":len(REQUEST),"response_bytes":len(RESPONSE),"body_bytes":len(BODY),
                 "base_timestamp_utc":"2024-01-01T00:00:00Z"},
        "logs": {"records":6,"statuses":{"200":3,"403":1,"404":1,"500":1}},
        "sha256": {name: hashlib.sha256(blob).hexdigest() for name, blob in sorted(result.items())},
        "notes": ["Static web server is optional and must bind to 127.0.0.1.",
                  "The PCAP is synthetic, not a capture of the supplied static server.",
                  "Static HTTP headers can differ from the synthetic PCAP headers.",
                  "Authentication demo and SQL demo run in memory, not on the HTTP server."]
    }
    result["expected.json"] = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode()
    return result

def generate(destination: Path) -> None:
    path = Path(os.path.abspath(destination))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Destination and ancestors must not be symlinks")
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing destination: {path}")
    if not path.parent.is_dir():
        raise ValueError("Parent directory must already exist")
    path.mkdir(mode=0o700, exist_ok=False)
    # Paths below are fixed internal names, not user-controlled archive entries.
    for relative, blob in contents().items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(blob)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        generate(args.destination)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Synthetic fixtures v{FIXTURE_VERSION} created: {args.destination}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
