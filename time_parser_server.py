"""Local verification server for the Chinese time parser."""

from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from time_parser import parse_chinese_time


HOST = "127.0.0.1"
PORT = 8766
PAGE = Path(__file__).with_name("time-parser-demo.html")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/time-parser-demo.html"}:
            self.send_error(404)
            return

        body = PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/parse":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            parsed = parse_chinese_time(str(payload.get("text", "")))
            response = {
                **parsed,
                "trigger_at": (
                    parsed["trigger_at"].isoformat(sep=" ")
                    if isinstance(parsed["trigger_at"], datetime)
                    else None
                ),
            }
            body = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error(400, str(error))

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    print(f"Time parser demo: http://{HOST}:{PORT}/")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
