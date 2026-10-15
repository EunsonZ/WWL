"""A deliberately small HTTP/1.1 framing lab.  It only talks to loopback."""
from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass


class ProtocolError(ValueError):
    pass


class TruncatedMessage(EOFError):
    pass


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


def _headers(block: bytes) -> tuple[int, dict[str, str]]:
    lines = block.split(b"\r\n")
    try:
        status = int(lines[0].split()[1])
    except (IndexError, ValueError) as exc:
        raise ProtocolError("bad status line") from exc
    out: dict[str, str] = {}
    for line in lines[1:]:
        if b":" not in line:
            raise ProtocolError("bad header")
        k, v = line.split(b":", 1)
        key = k.decode("ascii").lower()
        if key in out:
            raise ProtocolError("duplicate header unsupported by this lab")
        out[key] = v.strip().decode("ascii")
    return status, out


def _recv_into(sock: socket.socket, buf: bytearray, need: int, deadline: float | None) -> None:
    while len(buf) < need:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("total response deadline expired")
            sock.settimeout(remaining)
        data = sock.recv(3)  # deliberately tiny: recv is observable, not framing
        if not data:
            raise TruncatedMessage(f"EOF after {len(buf)} bytes; need {need}")
        buf.extend(data)


def read_response(sock: socket.socket, *, total_timeout: float | None = None) -> Response:
    """Read one response. A finite socket timeout is a total budget unless overridden."""
    old_timeout = sock.gettimeout()
    budget = old_timeout if total_timeout is None else total_timeout
    deadline = None if budget is None else time.monotonic() + budget
    buf = bytearray()
    try:
        while b"\r\n\r\n" not in buf:
            _recv_into(sock, buf, len(buf) + 1, deadline)
        marker = buf.index(b"\r\n\r\n")
        status, headers = _headers(bytes(buf[:marker]))
        del buf[: marker + 4]
        te, cl = headers.get("transfer-encoding"), headers.get("content-length")
        if te is not None and cl is not None:
            raise ProtocolError("reject ambiguous Transfer-Encoding plus Content-Length")
        if te:
            if te.lower() != "chunked":
                raise ProtocolError("this teaching parser supports only chunked")
            body = bytearray()
            while True:
                while b"\r\n" not in buf:
                    _recv_into(sock, buf, len(buf) + 1, deadline)
                line_end = buf.index(b"\r\n")
                raw_size = bytes(buf[:line_end])
                if b";" in raw_size:
                    raise ProtocolError("chunk extensions unsupported by this lab")
                size = raw_size
                if not size or any(c not in b"0123456789abcdefABCDEF" for c in size):
                    raise ProtocolError("bad chunk size")
                n = int(size, 16)
                del buf[: line_end + 2]
                _recv_into(sock, buf, n + 2, deadline)
                if bytes(buf[n:n + 2]) != b"\r\n":
                    raise ProtocolError("chunk lacks CRLF")
                body.extend(buf[:n]); del buf[:n + 2]
                if n == 0:
                    return Response(status, headers, bytes(body))
        if cl is None:
            raise ProtocolError("lab requires a body delimiter")
        if not cl or not cl.isascii() or not cl.isdecimal():
            raise ProtocolError("invalid Content-Length")
        n = int(cl)
        _recv_into(sock, buf, n, deadline)
        return Response(status, headers, bytes(buf[:n]))
    finally:
        sock.settimeout(old_timeout)


class ScriptedServer:
    """Own one temporary loopback listener, accepted peer and non-daemon worker."""
    def __init__(self, replies: list[bytes], delay: float = 0.0):
        self.replies, self.delay = replies, delay
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0)); self.listener.listen(1)
        self.listener.settimeout(0.1)  # accept periodically observes stop on every platform
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self._run)
        self.error: Exception | None = None
        self._stopping = threading.Event()
        self._accepted = threading.Event()
        self._connection_lock = threading.Lock()
        self._connection: socket.socket | None = None

    def __enter__(self): self.thread.start(); return self

    def __exit__(self, exc_type, body_error, traceback):
        self._stopping.set()
        self.listener.close()
        with self._connection_lock:
            conn = self._connection
            if conn is not None:
                try: conn.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                conn.close()
        self.thread.join(timeout=1)
        cleanup_error = (RuntimeError("loopback worker did not stop during context exit")
                         if self.thread.is_alive() else None)
        errors = [error for error in (cleanup_error, self.error) if error is not None]
        if body_error is not None:
            # Preserve the body exception; retain cleanup/worker diagnostics as notes.
            for error in errors: body_error.add_note(f"loopback cleanup/worker: {error!r}")
            return False
        if cleanup_error is not None: raise cleanup_error
        if self.error is not None: raise self.error
        return False

    def _run(self):
        try:
            while not self._stopping.is_set():
                try: conn, _ = self.listener.accept()
                except socket.timeout: continue
                with self._connection_lock:
                    if self._stopping.is_set():
                        conn.close(); return
                    self._connection = conn
                    self._accepted.set()
                break
            else: return
            with conn:
                pending = bytearray()
                for reply in self.replies:
                    while b"\r\n\r\n" not in pending:
                        part = conn.recv(1024)
                        if not part or self._stopping.is_set(): return
                        pending.extend(part)
                    end = pending.index(b"\r\n\r\n") + 4
                    del pending[:end]
                    if self.delay and self._stopping.wait(self.delay): return
                    for i in range(0, len(reply), 2):
                        if self._stopping.is_set(): return
                        conn.sendall(reply[i:i + 2])
        except Exception as error:
            if not (isinstance(error, OSError) and self._stopping.is_set()):
                self.error = error
        finally:
            with self._connection_lock: self._connection = None


def request(sock: socket.socket, target: str = "/") -> None:
    sock.sendall(f"GET {target} HTTP/1.1\r\nHost: loopback\r\n\r\n".encode())
