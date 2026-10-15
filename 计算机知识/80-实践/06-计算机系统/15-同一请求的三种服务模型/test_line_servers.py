import socket
import threading
import unittest
import re
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import line_servers

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


class ServerThread(threading.Thread):
    """Make a server exception visible to the test that started it."""

    error = None

    def run(self):
        try:
            super().run()
        except BaseException as error:
            self.error = error


def finish(thread, timeout=2):
    thread.join(timeout)
    if thread.is_alive():
        raise AssertionError("server did not stop")
    if thread.error is not None:
        raise AssertionError("server raised an exception") from thread.error


def start(target, **kwargs):
    ready = threading.Event()
    port = []

    def publish(value):
        port.append(value)
        ready.set()

    thread = ServerThread(target=target, args=(publish,), kwargs=kwargs)
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
    def test_bad_utf8_stops_coalesced_and_later_requests(self):
        for parts in ([b"\xff\nok\n"], [b"\xff", b"\n", b"ok\n"]):
            with self.subTest(parts=parts):
                state = LineState()
                for part in parts:
                    state.receive(part)
                self.assertEqual(state.output, b"ERR utf8\n")
                self.assertTrue(state.rejected)
                self.assertEqual(state.pending, b"")

    def test_valid_multibyte_utf8_is_echoed_as_utf8(self):
        wire = "中文\n".encode("utf-8")
        state = LineState()
        state.receive(wire[:1])
        state.receive(wire[1:4])
        state.receive(wire[4:])
        self.assertEqual(state.output, b"OK " + wire)
        self.assertFalse(state.rejected)

    def test_complete_overlong_line_also_rejects_following_input(self):
        state = LineState()
        state.receive(b"x" * 32)
        state.receive(b"x" * 31)
        state.receive(b"x\nok\n")
        self.assertEqual(state.output, b"ERR line-too-long\n")
        self.assertTrue(state.rejected)
        self.assertEqual(state.pending, b"")

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
        finish(thread)

    def _assert_packed_half_close_resumes_pending_line(self, target):
        port, thread = start(target, max_connections=1)
        self.assertEqual(exchange(port, [b"x\n" * 4]), b"OK x\n" * 4)
        finish(thread)

    def test_all_models_close_after_bad_utf8_without_waiting_for_peer_eof(self):
        for target in (serve_iterative, serve_prethreaded, serve_selectors):
            with self.subTest(target=target.__name__):
                port, thread = start(target, max_connections=1, timeout=1)
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5) as client:
                        client.sendall(b"\xff\nok\n")
                        result = bytearray()
                        while True:
                            chunk = client.recv(1024)
                            if not chunk:
                                break
                            result.extend(chunk)
                        self.assertEqual(result, b"ERR utf8\n")
                finally:
                    finish(thread)

    def test_all_models_echo_multibyte_utf8(self):
        wire = "中文\n".encode("utf-8")
        for target in (serve_iterative, serve_prethreaded, serve_selectors):
            with self.subTest(target=target.__name__):
                port, thread = start(target, max_connections=1)
                try:
                    self.assertEqual(exchange(port, [wire[:1], wire[1:]]), b"OK " + wire)
                finally:
                    finish(thread)

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
        # A response proves the worker owns this socket before we fill the queue.
        first.sendall(b"ready\n")
        self.assertEqual(first.recv(1024), b"OK ready\n")
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
        finish(thread, 3)


class DeadlineAndShutdownTests(unittest.TestCase):
    def test_blocking_reads_and_writes_recompute_remaining_budget(self):
        for operation in ("recv", "send"):
            with self.subTest(operation=operation):
                clock = [0.0]

                class TimedSocket:
                    def __init__(self):
                        self.budgets = []
                        self.closed = False

                    def settimeout(self, value):
                        self.timeout = value

                    def recv(self, _):
                        self.budgets.append(self.timeout)
                        if len(self.budgets) == 1:
                            clock[0] = 0.9
                            return b"prefix"
                        clock[0] += self.timeout
                        raise socket.timeout()

                    def send(self, data):
                        self.budgets.append(self.timeout)
                        if len(self.budgets) == 1:
                            clock[0] = 0.9
                            return 1
                        clock[0] += self.timeout
                        return len(data)

                    def shutdown(self, _):
                        pass

                    def close(self):
                        self.closed = True

                conn = TimedSocket()
                state = LineState()
                if operation == "send":
                    state.receive(b"ok\n")
                with patch("line_servers.time.monotonic", side_effect=lambda: clock[0]):
                    line_servers._drain(conn, state, 1.0)
                self.assertEqual(len(conn.budgets), 2)
                self.assertAlmostEqual(conn.budgets[0], 1.0)
                self.assertLessEqual(conn.budgets[1], 0.1)
                self.assertLessEqual(clock[0], 1.0)
                self.assertTrue(conn.closed)

    def test_zero_clients_leave_no_live_workers(self):
        before = set(threading.enumerate())
        serve_prethreaded(lambda _: None, max_connections=1, workers=2,
                          capacity=2, timeout=0.05)
        self.assertEqual(set(threading.enumerate()) - before, set())

    def test_nonpositive_worker_and_capacity_counts_are_rejected_before_listen(self):
        for parameters in ({"workers": 0}, {"workers": -1}, {"capacity": 0}, {"capacity": -1}):
            with self.subTest(parameters=parameters), patch("line_servers._listener") as listen:
                with self.assertRaises(ValueError):
                    serve_prethreaded(lambda _: None, max_connections=1, **parameters)
                listen.assert_not_called()

    def test_full_queue_deadline_closes_active_queued_and_rejected_sockets(self):
        before = set(threading.enumerate())
        accepted = []
        second_accepted = threading.Event()
        worker_started = threading.Event()
        real_listener = line_servers._listener()
        real_drain = line_servers._drain

        class RecordingListener:
            def __getattr__(self, name):
                return getattr(real_listener, name)

            def accept(self):
                conn, address = real_listener.accept()
                accepted.append(conn)
                if len(accepted) == 2:
                    second_accepted.set()
                return conn, address

        def observed_drain(*args):
            worker_started.set()
            return real_drain(*args)

        with patch("line_servers._listener", return_value=RecordingListener()), \
                patch("line_servers._drain", side_effect=observed_drain), ExitStack() as clients:
            port, thread = start(serve_prethreaded, max_connections=3,
                                 workers=1, capacity=1, timeout=0.3)
            try:
                clients.enter_context(socket.create_connection(("127.0.0.1", port), timeout=1))
                self.assertTrue(worker_started.wait(1))
                clients.enter_context(socket.create_connection(("127.0.0.1", port), timeout=1))
                self.assertTrue(second_accepted.wait(1))
                third = clients.enter_context(socket.create_connection(("127.0.0.1", port), timeout=1))
                self.assertEqual(third.recv(1024), BUSY)
                finish(thread)
                self.assertEqual(len(accepted), 3)
                self.assertTrue(all(conn.fileno() == -1 for conn in accepted))
            finally:
                real_listener.close()
                finish(thread)
        self.assertEqual(set(threading.enumerate()) - before, set())


if __name__ == "__main__":
    unittest.main()
