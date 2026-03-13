#!/usr/bin/env python3
"""Minimal static JSON API server. Serves .json files as API responses.

Usage:
  python server.py [port] [directory] [idle_timeout_seconds]
  python server.py stop

Route resolution:
  /fortunes    -> fortunes.json or fortunes/index.json
  /fortunes/1  -> fortunes/1.json
"""

import os
import signal
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

PIDFILE = Path("/tmp/skivvy_dev_server.pid")
HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_IDLE_TIMEOUT_SECONDS = 60.0


class Handler(BaseHTTPRequestHandler):
    root = None

    def do_POST(self):
        self.do_GET()

    def do_GET(self):
        setattr(self.server, "last_request_ts", time.monotonic())
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        target = (self.root / path.lstrip("/")).resolve()

        if not target.is_relative_to(self.root):
            self.respond(403, {"error": "forbidden"})
            return

        for candidate in [target, target.with_suffix(".json"), target / "index.json"]:
            if candidate.is_file() and candidate.suffix == ".json":
                self.respond(200, candidate.read_bytes())
                return

        self.respond(404, {"error": "not found"})

    def respond(self, status, body):
        if isinstance(body, dict):
            import json
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def stop():
    if not PIDFILE.exists():
        sys.exit("No server running (pid file not found)")
    pid = int(PIDFILE.read_text())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped server (pid {pid})")
    except ProcessLookupError:
        print(f"Server already stopped (stale pid {pid})")
    PIDFILE.unlink(missing_ok=True)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _read_pid() -> Optional[int]:
    if not PIDFILE.exists():
        return None
    try:
        return int(PIDFILE.read_text().strip())
    except (TypeError, ValueError):
        return None


def _acquire_lock_or_exit():
    pid = _read_pid()
    if pid is None:
        PIDFILE.unlink(missing_ok=True)
        return
    if _process_exists(pid):
        sys.exit(f"Server already running (pid {pid}). Stop it with: python server.py stop")
    PIDFILE.unlink(missing_ok=True)


def start(port, root, idle_timeout_seconds):
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    _acquire_lock_or_exit()

    Handler.root = root
    server = HTTPServer((HOST, port), Handler)
    server.timeout = 0.5
    setattr(server, "last_request_ts", time.monotonic())
    PIDFILE.write_text(str(os.getpid()))
    print(
        f"Serving {root} on http://{HOST}:{port} "
        f"(pid {os.getpid()}, idle_timeout={idle_timeout_seconds:.1f}s)"
    )

    def _handle_shutdown(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    try:
        while True:
            server.handle_request()
            idle_for = time.monotonic() - getattr(server, "last_request_ts")
            if idle_for >= idle_timeout_seconds:
                print(f"No requests for {idle_for:.1f}s. Shutting down.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        PIDFILE.unlink(missing_ok=True)


def main():
    if sys.argv[1:2] == ["stop"]:
        stop()
        return

    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    root = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd()
    idle_timeout_seconds = (
        float(sys.argv[3])
        if len(sys.argv) > 3
        else DEFAULT_IDLE_TIMEOUT_SECONDS
    )
    start(port, root, idle_timeout_seconds)


if __name__ == "__main__":
    main()
