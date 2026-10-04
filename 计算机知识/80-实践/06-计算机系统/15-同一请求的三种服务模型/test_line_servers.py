import socket
import threading
import unittest
import re
from pathlib import Path

from line_servers import (
    BUSY,
    GenerationTable,
    LineState,
    MAX_INFLIGHT_LINES,
    MAX_OUTPUT_BYTES,
    READ_CHUNK_BYTES,
    serve_iterative,
    serve_prethreaded,
    serve_selectors,
)


def start(target, **kwargs):
    ready = threading.Event()
    port = []

    def publish(value):
        port.append(value)
        ready.set()

    thread = threading.Thread(target=target, args=(publish,), kwargs=kwargs)
    thread.start()
    if not ready.wait(1):
        raise AssertionError("server never published its loopback port")
    return port[0], thread


def exchange(port, parts):
    with socket.create_connection(("127.0.0.1", port), timeout=1) as client:
        for part in parts:
            client.sendall(part)
        client.shutdown(socket.SHUT_WR)
        result = bytearray()
        while True:
            chunk = client.recv(1024)
            if not chunk:
                return bytes(result)
            result.extend(chunk)


class ProtocolTests(unittest.TestCase):
    def test_fragmented_and_coalesced_lines_share_one_contract(self):
        state = LineState()
        state.receive(b"one")
        state.receive(b"\ntwo\n")
        state.eof()
        self.assertEqual(state.output, b"OK one\nOK two\n")

    def test_half_close_flushes_response_and_partial_line_is_an_error(self):
        state = LineState()
        state.receive(b"answer\nleft")
        state.eof()
        self.assertEqual(state.output, b"OK answer\nERR eof-partial\n")

    def test_overlimit_and_bad_utf8_are_separate_errors(self):
        exact = LineState()
        exact.receive(b"x" * READ_CHUNK_BYTES)
        exact.receive(b"x" * (63 - READ_CHUNK_BYTES) + b"\n")
        self.assertEqual(exact.output, b"OK " + b"x" * 63 + b"\n")
        over = LineState()
        over.receive(b"x" * READ_CHUNK_BYTES)
        over.receive(b"x" * READ_CHUNK_BYTES)
        self.assertEqual(over.output, b"ERR line-too-long\n")
        bad = LineState()
        bad.receive(bytes([0xff, 0x0a]))
        self.assertEqual(bad.output, b"ERR utf8\n")

    def test_slow_reader_backpressures_after_three_inflight_frames(self):
        state = LineState()
        state.receive(b"x\n" * (MAX_INFLIGHT_LINES + 1))
        self.assertTrue(state.read_paused)
        self.assertEqual(len(state.frame_remaining), MAX_INFLIGHT_LINES)
        self.assertLessEqual(len(state.output), MAX_OUTPUT_BYTES)
        with self.assertRaises(RuntimeError):
            state.receive(b"next\n")
        state.written(len(b"OK x\n"))
        self.assertFalse(state.read_paused)
        state.receive(b"")
        self.assertTrue(state.read_paused)
        self.assertLessEqual(len(state.output), MAX_OUTPUT_BYTES)

    def test_generation_model_rejects_a_stale_event_after_fd_reuse(self):
        table = GenerationTable()
        old = table.open(9)
        self.assertTrue(table.close(9, old))
        new = table.open(9)
        self.assertNotEqual(old, new)
        self.assertFalse(table.owns(9, old))
        self.assertTrue(table.owns(9, new))

    def test_source_mirror_matches_both_executable_sources(self):
        directory = Path(__file__).resolve().parent
        mirror = (directory / "源码与测试镜像.md").read_text(encoding="utf-8")
        for name in ("line_servers.py", "test_line_servers.py"):
            match = re.search(
                rf"<!-- code-sync: \./{re.escape(name)} -->\n"
                rf"~~~python\n(.*?)~~~\n",
                mirror,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(match, name)
            self.assertEqual(match.group(1), (directory / name).read_text(encoding="utf-8"))


class ServerTests(unittest.TestCase):
    def _assert_common_io(self, target):
        port, thread = start(target, max_connections=1)
        self.assertEqual(exchange(port, [b"a", b"\nb\n"]), b"OK a\nOK b\n")
        thread.join(2)
        self.assertFalse(thread.is_alive())

    def _assert_packed_half_close_resumes_pending_line(self, target):
        port, thread = start(target, max_connections=1)
        self.assertEqual(exchange(port, [b"x\n" * 4]), b"OK x\n" * 4)
        thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_iterative_common_contract(self):
        self._assert_common_io(serve_iterative)

    def test_iterative_packed_half_close(self):
        self._assert_packed_half_close_resumes_pending_line(serve_iterative)

    def test_prethreaded_common_contract(self):
        self._assert_common_io(serve_prethreaded)

    def test_prethreaded_packed_half_close(self):
        self._assert_packed_half_close_resumes_pending_line(serve_prethreaded)

    def test_selectors_common_contract(self):
        self._assert_common_io(serve_selectors)

    def test_selectors_packed_half_close(self):
        self._assert_packed_half_close_resumes_pending_line(serve_selectors)

    def test_prethreaded_queue_pressure_is_explicit_rejection(self):
        port, thread = start(serve_prethreaded, max_connections=3, workers=1, capacity=1)
        first = socket.create_connection(("127.0.0.1", port), timeout=1)
        second = socket.create_connection(("127.0.0.1", port), timeout=1)
        third = socket.create_connection(("127.0.0.1", port), timeout=1)
        self.assertEqual(third.recv(1024), BUSY)
        third.close()
        first.shutdown(socket.SHUT_WR)
        self.assertEqual(first.recv(1024), b"")
        first.close()
        second.shutdown(socket.SHUT_WR)
        self.assertEqual(second.recv(1024), b"")
        second.close()
        thread.join(3)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
