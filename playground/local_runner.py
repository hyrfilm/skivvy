from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .runner_core import run_request


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._write_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path != "/health":
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, {"ok": True})

    def do_POST(self):
        if self.path != "/run-skivvy":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"output": "invalid JSON body\n", "exitCode": 2, "durationMs": 0})
            return

        self._send_json(200, run_request(body))

    def log_message(self, _format, *_args):
        return

    def _send_json(self, status: int, payload: dict):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _write_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the skivvy playground endpoint locally")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving skivvy playground runner on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

