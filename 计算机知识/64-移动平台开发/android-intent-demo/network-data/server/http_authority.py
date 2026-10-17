#!/usr/bin/env python3
"""Loopback HTTPS adapter. All booking decisions come from the given SE82 source.
The bundled CA/private keys and bearer strings are deliberately PUBLIC lab fixtures.
No OAuth issuance, account management, production hosting or TLS implementation here.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import socketserver
import sqlite3
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PROTOCOL = 'wwl-reservation-v2/1'
TOKENS = {'wwl175-public-D': 'D', 'wwl175-public-E': 'E'}
SEEDS = [('A', 540, 600), ('B', 600, 630), ('C', 650, 680)]


def load_contract(path):
    spec = importlib.util.spec_from_file_location('se82_network_contract', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite JSON')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError('object required')
    return value


class LabServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, contract, database, events, *, allow_drop=False):
        self.contract, self.database = contract, Path(database)
        self.allow_drop, self.events = allow_drop, Path(events)
        self.lock = threading.Lock()
        self.sequence = 0
        existed = self.database.exists()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.events.parent.mkdir(parents=True, exist_ok=True)
        with contract.Authority(str(self.database)) as authority:
            if not existed:
                authority.seed_legacy(SEEDS)
            if authority.writer_epoch != 2:
                raise ValueError('this adapter supports fixed epoch 2 only')
        super().__init__(address, Handler)

    def server_bind(self):
        # Fixed loopback fixture: do not block startup on machine reverse DNS.
        socketserver.TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.socket.getsockname()[1]

    def event(self, **fields):
        with self.lock:
            self.sequence += 1
            row = dict(sequence=self.sequence, **fields)
            with self.events.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'WWLTeachingAdapter/1'
    def log_message(self, *_):
        pass  # Never log Authorization or query strings via default access log.

    def reply(self, code, value):
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Connection', 'close')
        self.send_header('Cache-Control', 'no-store')
        if code == 401:
            self.send_header('WWW-Authenticate', 'Bearer realm="wwl-public-lab", error="invalid_token"')
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True

    def handle_request(self, method):
        subject = None
        identity = None
        path = urlsplit(self.path)
        try:
            auth = self.headers.get_all('Authorization', [])
            if len(auth) != 1 or not auth[0].startswith('Bearer '):
                code, value = 401, {'error': 'invalid_token'}
            else:
                subject = TOKENS.get(auth[0][7:])
                if subject is None:
                    code, value = 401, {'error': 'invalid_token'}
                else:
                    code, value, identity = self.authorized(method, path, subject)
            self.server.event(method=method, path=path.path, subject=subject,
                              intent_id=identity, http_status=code,
                              outcome=value.get('status'), error=value.get('error'),
                              tls=self.connection.version())
            if code == 200 and path.path == '/v2/reserve' and self.headers.get('X-WWL-Lab-Drop-Reply') == 'true':
                # reserve() has returned after COMMIT. Close the actual TLS/TCP
                # connection BEFORE HTTP headers, including every automatic retry.
                self.server.event(kind='committed_then_wire_closed', subject=subject,
                                  intent_id=identity, outcome=value['status'])
                self.close_connection = True
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.connection.close()
                return
            self.reply(code, value)
        except self.server.contract.IntentConflict:
            self.server.event(method=method, path=path.path, subject=subject, http_status=409,
                              error='intent_conflict')
            self.reply(409, {'error': 'intent_conflict'})
        except (ValueError, UnicodeError, self.server.contract.InvalidInput) as exc:
            self.server.event(method=method, path=path.path, subject=subject, http_status=400,
                              error=type(exc).__name__)
            self.reply(400, {'error': 'invalid_request'})
        except (sqlite3.OperationalError, self.server.contract.WriterFenced):
            self.server.event(method=method, path=path.path, subject=subject, http_status=503,
                              error='authority_unavailable')
            self.reply(503, {'error': 'authority_unavailable'})

    def authorized(self, method, path, subject):
        c = self.server.contract
        if method == 'GET' and path.path == '/v2/snapshot' and not path.query:
            with c.Authority(str(self.server.database)) as a:
                return 200, {'protocol': PROTOCOL, 'bookings': a.snapshot()}, None
        if method == 'GET' and path.path == '/v2/intent':
            params = parse_qs(path.query, keep_blank_values=True, strict_parsing=True)
            if set(params) != {'intent_id', 'fingerprint'} or any(len(v) != 1 for v in params.values()):
                raise ValueError('query shape')
            identity, fp = params['intent_id'][0], params['fingerprint'][0]
            c.text(identity, 'intent_id')
            if len(fp) != 64 or any(x not in '0123456789abcdef' for x in fp):
                raise ValueError('fingerprint')
            with c.Authority(str(self.server.database)) as a:
                return 200, a.query(subject, identity, fp), identity
        if method != 'POST' or path.path != '/v2/reserve' or path.query:
            return 404, {'error': 'not_found'}, None
        if self.headers.get('X-WWL-Lab-Drop-Reply') is not None and (
                not self.server.allow_drop or self.headers['X-WWL-Lab-Drop-Reply'] != 'true'):
            return 400, {'error': 'lab_fault_disabled'}, None
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal():
            raise ValueError('length required')
        size = int(lengths[0])
        if not 0 < size <= 4096 or self.headers.get_content_type() != 'application/json':
            raise ValueError('body contract')
        value = strict_json(self.rfile.read(size))
        if set(value) != {'protocol', 'actor', 'intent_id', 'start', 'end', 'fingerprint', 'policy_version'}:
            raise ValueError('request fields')
        if value['actor'] != subject:
            return 403, {'error': 'actor_mismatch'}, None
        if value['protocol'] != PROTOCOL or type(value['policy_version']) is not int or value['policy_version'] != 2:
            raise ValueError('version')
        identity = c.text(value['intent_id'], 'intent_id')
        for k in ('start', 'end'):
            if type(value[k]) is not int or not -(2**31) <= value[k] < 2**31:
                raise ValueError('Android Int range')
        fp = c.fingerprint(subject, value['start'], value['end'])
        if value['fingerprint'] != fp:
            raise ValueError('fingerprint mismatch')
        with c.Authority(str(self.server.database)) as a:
            return 200, a.reserve(subject, identity, value['start'], value['end'], writer_epoch=2), identity

    def do_GET(self):
        self.handle_request('GET')

    def do_POST(self):
        self.handle_request('POST')


def main():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, default=here.parents[2] / '75-软件工程与人机交互/reservation_v2.py')
    p.add_argument('--database', type=Path, required=True)
    p.add_argument('--events', type=Path, required=True)
    p.add_argument('--ready', type=Path, required=True)
    p.add_argument('--port', type=int, default=18751)
    p.add_argument('--cert', type=Path, default=here / 'fixtures/server.pem')
    p.add_argument('--key', type=Path, default=here / 'fixtures/server-public-fixture.key')
    p.add_argument('--allow-lab-faults', action='store_true')
    args = p.parse_args()
    c = load_contract(args.contract)
    server = LabServer(('127.0.0.1', args.port), c, args.database, args.events, allow_drop=args.allow_lab_faults)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.cert, args.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    args.ready.parent.mkdir(parents=True, exist_ok=True)
    args.ready.write_text(json.dumps({'host': '127.0.0.1', 'port': server.server_port,
        'contract_sha256': hashlib.sha256(args.contract.read_bytes()).hexdigest(),
        'fixture_only': True, 'allow_lab_faults': args.allow_lab_faults}, indent=2) + '\n')
    try:
        server.serve_forever(poll_interval=.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
