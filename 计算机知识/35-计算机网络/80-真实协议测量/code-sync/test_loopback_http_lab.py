import http.client
import socket
import threading
import time
import unittest
from loopback_http_lab import (ProtocolError, ScriptedServer, TruncatedMessage, read_response, request)


CL = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello"
CHUNKED = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\n\xe4\xbd\xa0\r\n3\r\n\xe5\xa5\xbd\r\n0\r\n\r\n"


class LoopbackHttpTests(unittest.TestCase):
    def client(self, server):
        s = socket.create_connection(("127.0.0.1", server.port), timeout=0.5)
        self.addCleanup(s.close); return s

    def test_content_length_and_utf8_bytes(self):
        with ScriptedServer([CL]) as server:
            s = self.client(server); request(s)
            self.assertEqual(read_response(s).body, b"hello")
        with ScriptedServer([CHUNKED]) as server:
            s = self.client(server); request(s)
            self.assertEqual(read_response(s).body.decode(), "你好")

    def test_chunked_and_two_requests_one_connection(self):
        with ScriptedServer([CL, CHUNKED]) as server:
            s = self.client(server); request(s, "/one")
            self.assertEqual(read_response(s).body, b"hello")
            request(s, "/two")
            self.assertEqual(read_response(s).body, "你好".encode())

    def test_eof_is_not_complete_body(self):
        with ScriptedServer([b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhe"]) as server:
            s = self.client(server); request(s)
            with self.assertRaises(TruncatedMessage): read_response(s)

    def test_timeout_is_not_eof(self):
        with ScriptedServer([CL], delay=0.15) as server:
            s = self.client(server); s.settimeout(0.02); request(s)
            with self.assertRaises(socket.timeout): read_response(s)

    def test_ambiguous_framing_rejected(self):
        bad = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Length: 5\r\n\r\n0\r\n\r\n"
        with ScriptedServer([bad]) as server:
            s = self.client(server); request(s)
            with self.assertRaises(ProtocolError): read_response(s)

    def test_rejects_plus_signed_lengths(self):
        for bad in (
            b"HTTP/1.1 200 OK\r\nContent-Length: +2\r\n\r\nok",
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n+2\r\nok\r\n0\r\n\r\n",
        ):
            with self.subTest(bad=bad), ScriptedServer([bad]) as server:
                s = self.client(server); request(s)
                with self.assertRaises(ProtocolError): read_response(s)

    def test_rejects_empty_or_extension_framing_fields(self):
        for bad in (
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Length:\r\n\r\n0\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding:\r\nContent-Length: 2\r\n\r\nok",
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2;x=y\r\nok\r\n0\r\n\r\n",
        ):
            with self.subTest(bad=bad), ScriptedServer([bad]) as server:
                s = self.client(server); request(s)
                with self.assertRaises(ProtocolError): read_response(s)

    def test_total_timeout_is_not_refreshed_by_drip(self):
        listener = socket.socket(); listener.bind(("127.0.0.1", 0)); listener.listen(1)
        reply = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello"
        def drip():
            with listener, listener.accept()[0] as conn:
                conn.recv(1024)
                for byte in reply:
                    conn.sendall(bytes([byte])); time.sleep(0.012)
        thread = threading.Thread(target=drip); thread.start()
        s = socket.create_connection(("127.0.0.1", listener.getsockname()[1]), timeout=0.04)
        self.addCleanup(s.close); request(s)
        start = time.monotonic()
        with self.assertRaises(socket.timeout): read_response(s)
        self.assertLess(time.monotonic() - start, 0.12)
        thread.join(timeout=1); self.assertFalse(thread.is_alive())

    def assert_released(self, server):
        self.assertFalse(server.thread.is_alive())
        self.assertEqual(server.listener.fileno(), -1)
        self.assertIsNone(server._connection)

    def test_exit_without_client(self):
        server = ScriptedServer([CL])
        with server: pass
        self.assert_released(server)

    def test_exit_with_held_incomplete_header(self):
        server = ScriptedServer([CL])
        with server:
            client = self.client(server)
            client.sendall(b"GET / HTTP/1.1\r\n")
            self.assertTrue(server._accepted.wait(0.5))
        self.assert_released(server)
        self.assertEqual(client.recv(1), b"")

    def test_exit_interrupts_delay(self):
        server = ScriptedServer([CL], delay=10)
        with server:
            client = self.client(server); request(client)
            self.assertTrue(server._accepted.wait(0.5))
        self.assert_released(server)

    def test_body_exception_is_preserved(self):
        server = ScriptedServer([CL])
        original = ValueError("body failure")
        with self.assertRaises(ValueError) as caught:
            with server: raise original
        self.assertIs(caught.exception, original)
        self.assert_released(server)

    def test_worker_error_is_reported_without_body_error(self):
        # invalid reply exercises an unexpected worker failure, rather than shutdown OSError
        server = ScriptedServer([None])
        with self.assertRaises(TypeError):
            with server:
                client = self.client(server); request(client)
                server.thread.join(timeout=0.5)
        self.assert_released(server)

    def test_body_failure_keeps_worker_diagnostic(self):
        server = ScriptedServer([None])
        original = ValueError("body failure")
        with self.assertRaises(ValueError) as caught:
            with server:
                client = self.client(server); request(client)
                server.thread.join(timeout=0.5)
                raise original
        self.assertIs(caught.exception, original)
        self.assertTrue(any("TypeError" in note for note in original.__notes__))
        self.assert_released(server)

    def test_stdlib_http_client_cross_check(self):
        with ScriptedServer([CL]) as server:
            c = http.client.HTTPConnection("127.0.0.1", server.port, timeout=0.5)
            c.request("GET", "/")
            self.assertEqual(c.getresponse().read(), b"hello")
            c.close()


if __name__ == "__main__": unittest.main(verbosity=2)
