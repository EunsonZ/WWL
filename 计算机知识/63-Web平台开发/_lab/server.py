"""Explicitly started, finite loopback demo. No accounts or persistent writes."""
import argparse
import json
from pathlib import Path
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from urllib.parse import parse_qs, urlsplit

CATALOG = [
    {"id": "web-doc", "title": "Web文档与语义表单", "minutes": 35, "level": "basic"},
    {"id": "web-state", "title": "Web事件与界面状态", "minutes": 50, "level": "core"},
    {"id": "network", "title": "网络请求与取消边界", "minutes": 45, "level": "core"},
    {"id": "layout", "title": "响应式布局与焦点", "minutes": 30, "level": "basic"},
]
STATIC = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
          "/app.js": ("app.js", "text/javascript"), "/model.mjs": ("model.mjs", "text/javascript"),
          "/styles.css": ("styles.css", "text/css")}
ROOT = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, kind="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Expected when client cancels the slow demonstration.

    def do_GET(self):
        if len(self.path) > 4096:
            self.reply(414, b'{"error":"URL too long"}')
            return
        path = urlsplit(self.path)
        if path.path in STATIC:
            file, kind = STATIC[path.path]
            self.reply(200, (ROOT / file).read_bytes(), kind)
            return
        if path.path != "/api/courses":
            self.reply(404, b'{"error":"not found"}')
            return
        params = parse_qs(path.query, keep_blank_values=True)
        q = params.get("q", [""])[0].strip(" \t\n\r\v\f\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff")
        scenario = params.get("scenario", ["success"])[0]
        # HTML maxlength and JS String.length use UTF-16 code units.
        units = len(q.encode("utf-16-le")) // 2
        if not 1 <= units <= 80 or scenario not in {"success", "slow", "http-error", "drop", "bad-json", "bad-data"}:
            self.reply(400, b'{"error":"invalid query or scenario"}')
            return
        if scenario == "slow":
            time.sleep(2)
        if scenario == "drop":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if scenario == "http-error":
            self.reply(503, b'{"error":"teaching outage"}')
            return
        if scenario == "bad-json":
            self.reply(200, b'{')
            return
        if scenario == "bad-data":
            self.reply(200, b'{"courses":[{"id":"x","minutes":-1}]}')
            return
        matches = [c for c in CATALOG if q.casefold() in c["title"].casefold()]
        self.reply(200, json.dumps({"courses": matches}, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # Queries are not recorded by this teaching server.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8763)
    parser.add_argument("--duration", type=int, default=600, help="Stop after 1–3600 seconds")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535 or not 1 <= args.duration <= 3600:
        parser.error("port must be 0–65535; duration must be 1–3600")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    timer = threading.Timer(args.duration, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f"http://127.0.0.1:{server.server_port}/ (stops after {args.duration}s)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        server.server_close()
