#!/usr/bin/env python3
"""Tiny Termux notification bridge for proot/Ubuntu -> Termux API.

This script exposes a small HTTP server on localhost:8787 and translates
/pro toast and /notify requests into Termux commands.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
TOKEN_ENV = "TT_BRIDGE_TOKEN"
DEFAULT_TOKEN = "super-secret-change-me"


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "TTBridge/1.0"

    def _reply(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._reply(200, {"ok": True, "token": os.environ.get(TOKEN_ENV, DEFAULT_TOKEN)})
            return
        self._reply(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        token = self.headers.get("X-TT-Token") or ""
        expected = os.environ.get(TOKEN_ENV, DEFAULT_TOKEN)
        if token != expected:
            self._reply(401, {"ok": False, "error": "invalid token"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            self._reply(400, {"ok": False, "error": "invalid json"})
            return

        path = self.path
        if path == "/toast":
            text = str(payload.get("text", "")).strip()
            ok = run_termux(["termux-toast", text]) if text else False
            self._reply(200 if ok else 500, {"ok": ok, "path": path, "text": text})
            return

        if path == "/notify":
            ok = run_notify(payload)
            self._reply(200 if ok else 500, {"ok": ok, "path": path, "title": payload.get("title", "")})
            return

        self._reply(404, {"ok": False, "error": "unknown path"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("[tt_notify_bridge] %s\n" % (format % args))


def run_termux(command: list[str]) -> bool:
    try:
        subprocess.run(command, check=False, capture_output=True, text=True)
        return True
    except Exception:
        return False


def run_notify(payload: dict[str, Any]) -> bool:
    title = str(payload.get("title", "")).strip() or "Notification"
    content = str(payload.get("content", "")).strip() or ""
    priority = str(payload.get("priority", "default")).strip() or "default"
    sticky = bool(payload.get("sticky", False))

    command = ["termux-notification", "--title", title, "--content", content, "--priority", priority]
    if sticky:
        command.append("--sticky")

    # Optional extra buttons (if provided by the caller)
    for key in ("button1", "button2", "button3"):
        if payload.get(key):
            command.extend(["--button", f"{key}:{payload[key]}"])
    if payload.get("button1_action"):
        command.extend(["--button-action", payload["button1_action"]])

    return run_termux(command)


def serve(host: str, port: int) -> None:
    httpd = ThreadingHTTPServer((host, port), BridgeHandler)
    print(f"[tt_notify_bridge] listening on http://{host}:{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Termux notification bridge server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default=os.environ.get(TOKEN_ENV, DEFAULT_TOKEN))
    args = parser.parse_args()

    os.environ[TOKEN_ENV] = args.token
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
