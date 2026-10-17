"""Real TLS/socket tests; SE82 is imported, not reimplemented. Only temporary databases."""
import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
from http_authority import LabServer, load_contract, strict_json, PROTOCOL

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get('SE82_SOURCE', HERE.parents[2] / '75-软件工程与人机交互/reservation_v2.py'))
C = load_contract(SOURCE)

class HttpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        supplied = os.environ.get('WWL_TLS_FIXTURE_DIR')
        cls.fixture_temp = None
        if supplied:
            cls.fixtures = Path(supplied).resolve(strict=True)
        else:
            cls.fixture_temp = tempfile.TemporaryDirectory()
            cls.fixtures = Path(cls.fixture_temp.name) / 'tls'
            try:
                subprocess.run(['sh', str(HERE/'fixtures/generate-fixtures.sh'), str(cls.fixtures)],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            except BaseException:
                cls.fixture_temp.cleanup()
                raise

    @classmethod
    def tearDownClass(cls):
        if cls.fixture_temp is not None:
            cls.fixture_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = LabServer(('127.0.0.1', 0), C, self.root/'authority.db', self.root/'events.jsonl', allow_drop=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.fixtures/'server.pem', self.fixtures/'server-public-fixture.key')
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()
        self.tls = ssl.create_default_context(cafile=str(self.fixtures/'ca.pem'))
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()
    def request(self, path='/v2/snapshot', *, actor='D', body=None, drop=False, token=None, tls=None):
        connection = http.client.HTTPSConnection('127.0.0.1', self.server.server_port, context=tls or self.tls, timeout=3)
        headers = {'Authorization': 'Bearer '+(token or 'wwl175-public-'+actor)}
        if body is not None: headers['Content-Type'] = 'application/json'
        if drop: headers['X-WWL-Lab-Drop-Reply'] = 'true'
        try:
            connection.request('GET' if body is None else 'POST', path,
                               None if body is None else json.dumps(body).encode(), headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally: connection.close()
    def body(self, actor='D', identity='same-id', start=690, end=720):
        return dict(protocol=PROTOCOL, actor=actor, intent_id=identity, start=start, end=end,
                    fingerprint=C.fingerprint(actor,start,end), policy_version=2)
    def test_trust_and_hostname(self):
        self.assertEqual(self.request()[0],200)
        with self.assertRaises(ssl.SSLCertVerificationError): self.request(tls=ssl.create_default_context())
        # An unrelated peer name must fail with the same trusted CA (no trust-all).
        sock=__import__('socket').create_connection(('127.0.0.1',self.server.server_port),timeout=3)
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.tls.wrap_socket(sock,server_hostname='not-the-lab.example')
        sock.close()
    def test_authenticated_subject_and_no_business_result_on_auth_failure(self):
        self.assertEqual(self.request(token='bad')[0],401)
        self.assertEqual(self.request('/v2/reserve', actor='E',body=self.body('D')),(403,{'error':'actor_mismatch'}))
        with C.Authority(str(self.server.database)) as a:
            self.assertEqual(len(a.snapshot()),3);self.assertEqual(a.query('D','same-id')['status'],'unknown')
    def test_original_result_and_cross_actor_key(self):
        code,original=self.request('/v2/reserve',body=self.body())
        self.assertEqual((code,original['status']),(200,'accepted'))
        self.assertEqual(self.request('/v2/reserve',body=self.body()),(200,original))
        conflict=self.request('/v2/reserve',body=self.body(start=810,end=840))
        self.assertEqual(conflict[0],409)
        code,other=self.request('/v2/reserve',actor='E',body=self.body('E'))
        self.assertEqual((code,other['status'],other['reason']),(200,'rejected','conflict_with_buffer'))
        self.assertEqual(self.request('/v2/intent?intent_id=same-id&fingerprint='+self.body()['fingerprint']),(200,original))
    def test_commit_then_real_wire_close(self):
        with self.assertRaises(http.client.RemoteDisconnected):
            self.request('/v2/reserve',body=self.body(),drop=True)
        with C.Authority(str(self.server.database)) as a:
            original=a.query('D','same-id');self.assertEqual(original['status'],'accepted')
            self.assertEqual(len(a.snapshot()),4);self.assertEqual(len(a.pending_events()),1)
        self.assertEqual(self.request('/v2/reserve',body=self.body()),(200,original))
        self.assertIn('committed_then_wire_closed',(self.root/'events.jsonl').read_text())
    def test_two_concurrent_tls_clients_one_capacity(self):
        barrier=threading.Barrier(2)
        def submit(actor):
            barrier.wait()
            return self.request('/v2/reserve',actor=actor,body=self.body(actor))[1]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,['D','E']))
        self.assertEqual(sorted(x['status'] for x in results),['accepted','rejected'])
        with C.Authority(str(self.server.database)) as a:
            self.assertEqual(len(a.snapshot()),4);self.assertEqual(len(a.pending_events()),1)
            for result in results:self.assertEqual(a.query(result['actor'],'same-id'),result)
    def test_strict_payload_and_unknown(self):
        for raw in [b'{"x":1,"x":2}',b'{"x":NaN}',b'[]']:
            with self.assertRaises(ValueError):strict_json(raw)
        for change in [{'start':True},{'start':2**31},{'policy_version':2.0},{'fingerprint':'bad'},{'writer_epoch':2}]:
            body=self.body();body.update(change)
            self.assertEqual(self.request('/v2/reserve',body=body)[0],400)
        code,value=self.request('/v2/intent?intent_id=unused&fingerprint='+self.body()['fingerprint'])
        self.assertEqual((code,value['status'],value['reason']),(200,'unknown','not_registered'))

if __name__=='__main__':unittest.main()
