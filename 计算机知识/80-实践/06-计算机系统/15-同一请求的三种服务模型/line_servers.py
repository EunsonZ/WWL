"""Three deliberately small loopback line servers with one shared contract.

This is teaching code, not a framework.  It never listens outside 127.0.0.1,
uses no external service, and each runner has a deadline and a finite accept
budget.  ``serve_*`` returns after that budget or deadline and closes every
socket it owns.
"""

from __future__ import annotations

import queue
import selectors
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


HOST = "127.0.0.1"
MAX_LINE_BYTES = 64  # Includes the terminating LF; the payload is at most 63 B.
READ_CHUNK_BYTES = 32
MAX_INFLIGHT_LINES = 3
MAX_OUTPUT_BYTES = MAX_INFLIGHT_LINES * (MAX_LINE_BYTES + 3)
BUSY = b"ERR busy\n"


def decode_line(wire: bytes) -> bytes:
    """Return the one response for a complete, LF-terminated wire line.

    A line is valid only when its complete UTF-8 wire representation is at
    most 64 bytes including LF.  Newlines delimit requests; ``CR`` remains an
    ordinary payload byte.  Successful replies echo valid UTF-8; error codes
    are ASCII.  A bad input never makes the server's reply undecodable.
    """
    assert wire.endswith(b"\n")
    if len(wire) > MAX_LINE_BYTES:
        return b"ERR line-too-long\n"
    try:
        text = wire[:-1].decode("utf-8", "strict")
    except UnicodeDecodeError:
        return b"ERR utf8\n"
    return b"OK " + text.encode("utf-8") + b"\n"


@dataclass
class LineState:
    pending: bytearray = field(default_factory=bytearray)
    output: bytearray = field(default_factory=bytearray)
    frame_remaining: deque[int] = field(default_factory=deque)
    read_eof: bool = False
    rejected: bool = False

    @property
    def read_paused(self) -> bool:
        return len(self.frame_remaining) >= MAX_INFLIGHT_LINES

    def _queue(self, response: bytes) -> None:
        assert len(self.output) + len(response) <= MAX_OUTPUT_BYTES
        self.output.extend(response)
        self.frame_remaining.append(len(response))

    def written(self, count: int) -> None:
        """Record a prefix sent by the socket and reopen reads after a frame."""
        del self.output[:count]
        while count:
            remaining = self.frame_remaining[0]
            used = min(count, remaining)
            count -= used
            if used == remaining:
                self.frame_remaining.popleft()
            else:
                self.frame_remaining[0] -= used

    def receive(self, data: bytes) -> None:
        """Consume lines until backpressure or a terminal protocol error."""
        if self.read_eof or self.rejected:
            return
        if len(data) > READ_CHUNK_BYTES:
            raise ValueError("caller must retain unread bytes when the read budget is exhausted")
        if self.read_paused:
            raise RuntimeError("read attempted while this connection is backpressured")
        self.pending.extend(data)
        while True:
            if self.read_paused:
                return
            newline = self.pending.find(b"\n")
            if newline < 0:
                if len(self.pending) >= MAX_LINE_BYTES:
                    self._queue(b"ERR line-too-long\n")
                    self.pending.clear()
                    self.rejected = True
                return
            wire = bytes(self.pending[: newline + 1])
            del self.pending[: newline + 1]
            response = decode_line(wire)
            self._queue(response)
            if response.startswith(b"ERR "):
                self.pending.clear()
                self.rejected = True
                return

    def eof(self) -> None:
        self.read_eof = True
        if self.pending and not self.rejected:
            self._queue(b"ERR eof-partial\n")
            self.pending.clear()


def _set_remaining_timeout(conn: socket.socket, deadline: float) -> bool:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return False
    conn.settimeout(remaining)
    return True


def _drain(conn: socket.socket, state: LineState, deadline: float) -> None:
    """Own reads, writes and close; every blocking call shares one deadline."""
    try:
        while True:
            if state.output:
                if not _set_remaining_timeout(conn, deadline):
                    break
                sent = conn.send(state.output)
                if sent == 0:
                    break
                state.written(sent)
                if not state.output and not state.read_paused:
                    state.receive(b"")
                continue
            if state.read_eof or state.rejected:
                break
            if state.pending and not state.read_paused:
                state.receive(b"")
                if state.output:
                    continue
            if not _set_remaining_timeout(conn, deadline):
                break
            data = conn.recv(READ_CHUNK_BYTES)
            if not data:
                state.eof()
            else:
                state.receive(data)
    except OSError:
        # Timeout, reset or failed write ends this connection, not its owner pool.
        pass
    finally:
        try:
            conn.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        conn.close()


def _listener() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST, 0))
    listener.listen()
    listener.settimeout(0.02)
    return listener


def serve_iterative(
    publish: Callable[[int], None], *, max_connections: int, timeout: float = 2.0
) -> None:
    """One connection owner at a time.  A slow connection delays the next one."""
    deadline = time.monotonic() + timeout
    listener = _listener()
    accepted = 0
    try:
        publish(listener.getsockname()[1])
        while accepted < max_connections:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            listener.settimeout(min(0.02, remaining))
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                continue
            accepted += 1
            _drain(conn, LineState(), deadline)
    finally:
        listener.close()


def serve_prethreaded(
    publish: Callable[[int], None], *, max_connections: int, workers: int = 2,
    capacity: int = 2, timeout: float = 2.0
) -> None:
    """A finite admission queue.  Full means a visible `ERR busy`, never growth."""
    if workers <= 0 or capacity <= 0:
        raise ValueError("workers and capacity must be positive")
    deadline = time.monotonic() + timeout
    listener = _listener()
    jobs: queue.Queue[socket.socket] = queue.Queue(maxsize=capacity)
    done = threading.Event()
    errors: queue.SimpleQueue[Exception] = queue.SimpleQueue()

    def worker() -> None:
        while True:
            try:
                item = jobs.get(timeout=0.02)
            except queue.Empty:
                if done.is_set():
                    return
                continue
            try:
                _drain(item, LineState(), deadline)
            except Exception as error:
                errors.put(error)
            finally:
                jobs.task_done()

    threads = [threading.Thread(target=worker, name=f"wwl-line-worker-{index}")
               for index in range(workers)]
    for thread in threads:
        thread.start()
    accepted = 0
    try:
        publish(listener.getsockname()[1])
        while accepted < max_connections:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            listener.settimeout(min(0.02, remaining))
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                continue
            accepted += 1
            try:
                jobs.put_nowait(conn)
            except queue.Full:
                try:
                    if _set_remaining_timeout(conn, deadline):
                        conn.sendall(BUSY)
                        conn.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                conn.close()
    finally:
        listener.close()
        # No producer remains. Drain admitted jobs, then leave a timed get on
        # an empty queue; shutdown needs no free slot for a sentinel.
        done.set()
        join_deadline = max(deadline, time.monotonic()) + 0.1
        for thread in threads:
            thread.join(timeout=max(0.0, join_deadline - time.monotonic()))
        # Recover any socket still owned by the admission queue on failure.
        while True:
            try:
                pending = jobs.get_nowait()
            except queue.Empty:
                break
            try:
                pending.close()
            finally:
                jobs.task_done()
        if any(thread.is_alive() for thread in threads):
            raise RuntimeError("worker did not stop before the service deadline")
        if not errors.empty():
            raise RuntimeError("connection worker failed") from errors.get_nowait()


@dataclass
class EventConnection:
    sock: socket.socket
    generation: int
    state: LineState = field(default_factory=LineState)


class GenerationTable:
    """A deterministic ownership model for stale readiness after FD-number reuse."""

    def __init__(self) -> None:
        self._next = 0
        self._live: dict[int, int] = {}

    def open(self, fd: int) -> int:
        self._next += 1
        self._live[fd] = self._next
        return self._next

    def owns(self, fd: int, generation: int) -> bool:
        return self._live.get(fd) == generation

    def close(self, fd: int, generation: int) -> bool:
        if not self.owns(fd, generation):
            return False
        del self._live[fd]
        return True


def serve_selectors(
    publish: Callable[[int], None], *, max_connections: int, timeout: float = 2.0
) -> None:
    """One-thread nonblocking model with per-connection state and a read budget.

    ``selectors`` chooses the OS mechanism (kqueue on many macOS builds,
    epoll on Linux, etc.).  It is not a claim that every readiness API shares
    identical edge-trigger or cancellation semantics.
    """
    deadline = time.monotonic() + timeout
    selector = selectors.DefaultSelector()
    listener = _listener()
    listener.setblocking(False)
    generations = GenerationTable()
    accepted = 0

    def close(event: EventConnection) -> None:
        fd = event.sock.fileno()
        if not generations.close(fd, event.generation):
            return
        try:
            selector.unregister(event.sock)
        except Exception:
            pass
        event.sock.close()

    selector.register(listener, selectors.EVENT_READ, data=None)
    try:
        publish(listener.getsockname()[1])
        while time.monotonic() < deadline:
            if accepted >= max_connections and len(selector.get_map()) == 1:
                return
            for key, mask in selector.select(timeout=min(0.02, max(0.0, deadline - time.monotonic()))):
                if key.data is None:
                    if accepted >= max_connections:
                        continue
                    conn, _ = listener.accept()
                    conn.setblocking(False)
                    event = EventConnection(conn, generations.open(conn.fileno()))
                    selector.register(conn, selectors.EVENT_READ, data=event)
                    accepted += 1
                    continue
                event: EventConnection = key.data
                if not generations.owns(event.sock.fileno(), event.generation):
                    continue
                if mask & selectors.EVENT_READ:
                    # One recv per readiness turn is an explicit fairness budget.
                    try:
                        data = event.sock.recv(READ_CHUNK_BYTES)
                    except BlockingIOError:
                        data = None
                    if data == b"":
                        event.state.eof()
                    elif data:
                        event.state.receive(data)
                    if event.state.output:
                        selector.modify(event.sock, selectors.EVENT_WRITE, event)
                if mask & selectors.EVENT_WRITE and event.state.output:
                    try:
                        sent = event.sock.send(event.state.output)
                    except BlockingIOError:
                        sent = 0
                    event.state.written(sent)
                    if not event.state.output and not (event.state.read_eof or event.state.rejected):
                        event.state.receive(b"")
                        if event.state.output:
                            selector.modify(event.sock, selectors.EVENT_WRITE, event)
                        else:
                            selector.modify(event.sock, selectors.EVENT_READ, event)
                if (event.state.read_eof or event.state.rejected) and not event.state.output:
                    close(event)
    finally:
        for key in list(selector.get_map().values()):
            try:
                selector.unregister(key.fileobj)
            except Exception:
                pass
            try:
                key.fileobj.close()
            except OSError:
                pass
        selector.close()
