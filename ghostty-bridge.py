#!/usr/bin/env python3
"""HTTP bridge for the Übersicht terminal widget.

The Übersicht widget renders a flat text stream (no embedded terminal
emulator), so a PTY-based interactive shell does not display correctly.
Instead, this bridge runs each submitted command as a one-shot
``bash -c`` invocation and queues the combined stdout/stderr for the
widget to read on its next /read poll. ``cd`` is intercepted so the
current working directory persists across commands.

Endpoints:
    GET  /health  → {status, cwd}
    GET  /read    → {output: [str, ...], cwd}
    GET  /cwd     → {cwd}
    POST /send    body: {"input": "<command>\\n"}
    POST /kill    shutdown
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
DEFAULT_PORT = 18766
COMMAND_TIMEOUT = 30  # seconds


class Shell:
    def __init__(self) -> None:
        self.cwd = os.environ.get("HOME", "/Users/scottchen")
        self._queue: list[str] = []
        self._lock = threading.Lock()

    # ── public API ──────────────────────────────────────────────────────────
    def submit(self, raw: str) -> None:
        """Queue & execute a command line on a worker thread."""
        cmd = raw.rstrip("\r\n")
        if not cmd.strip():
            return
        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def drain(self) -> list[str]:
        with self._lock:
            out = self._queue[:]
            self._queue.clear()
        return out

    # ── internals ───────────────────────────────────────────────────────────
    def _push(self, text: str) -> None:
        if not text:
            return
        # Split on newlines but keep them; widget expects ["line\n", ...].
        parts = text.splitlines(keepends=True)
        with self._lock:
            self._queue.extend(parts)

    CWD_MARKER = "___TWCWD___"

    def _run(self, cmd: str) -> None:
        # Always echo the prompt+command so the user sees what they ran.
        self._push(f"{self._prompt()} {cmd}\n")

        # Local-only builtin: clear screen.
        try:
            tokens = shlex.split(cmd, posix=True)
        except ValueError:
            tokens = []
        if tokens and tokens[0] == "clear":
            with self._lock:
                self._queue.clear()
            return

        # Wrap so the post-command CWD is reported back, letting `cd`
        # (and any compound command containing it) persist across submissions.
        wrapped = f"{{ {cmd}\n}}; __rc=$?; printf '\\n{self.CWD_MARKER}%s\\n' \"$PWD\"; exit $__rc"
        try:
            proc = subprocess.run(
                ["/bin/bash", "-c", wrapped],
                cwd=self.cwd,
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            self._push(f"[timeout after {COMMAND_TIMEOUT}s]\n")
            return
        except Exception as e:  # pragma: no cover
            self._push(f"[error: {e}]\n")
            return

        stdout = self._extract_cwd(proc.stdout)
        if stdout:
            self._push(stdout if stdout.endswith("\n") else stdout + "\n")
        if proc.stderr:
            self._push(proc.stderr if proc.stderr.endswith("\n") else proc.stderr + "\n")
        if proc.returncode != 0 and not proc.stderr:
            self._push(f"[exit {proc.returncode}]\n")

    def _extract_cwd(self, stdout: str) -> str:
        """Strip the trailing CWD marker line and update self.cwd."""
        marker = self.CWD_MARKER
        idx = stdout.rfind(marker)
        if idx < 0:
            return stdout
        new_cwd = stdout[idx + len(marker):].strip()
        if new_cwd and os.path.isdir(new_cwd):
            self.cwd = new_cwd
        # Trim "\n<MARKER>...\n" from the visible output.
        prefix = stdout[:idx]
        return prefix.rstrip("\n")

    def _prompt(self) -> str:
        home = os.environ.get("HOME", "")
        p = self.cwd
        if home and (p == home or p.startswith(home + "/")):
            p = "~" + p[len(home):]
        return f"{p} ❯"


shell = Shell()


# ── HTTP layer ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt: str, *args) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        sys.stdout.write(f"[{ts}] {fmt % args}\n")
        sys.stdout.flush()

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # CORS preflight (defensive)
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "ok", "cwd": shell.cwd})
        elif self.path == "/read":
            self._send_json({"output": shell.drain(), "cwd": shell.cwd})
        elif self.path == "/cwd":
            self._send_json({"cwd": shell.cwd})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            data = json.loads(body or b"{}")
        except json.JSONDecodeError:
            data = {}

        if self.path == "/send":
            shell.submit(str(data.get("input", "")))
            self._send_json({"ok": True})
        elif self.path == "/kill":
            self._send_json({"ok": True})
            threading.Timer(0.2, lambda: os._exit(0)).start()
        else:
            self._send_json({"error": "not found"}, 404)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    server = HTTPServer((HOST, args.port), Handler)
    sys.stdout.write(
        f"[bridge] listening on http://{HOST}:{args.port}  cwd={shell.cwd}\n"
    )
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
