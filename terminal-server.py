#!/usr/bin/env python3
"""Persistent zsh PTY backend for Übersicht terminal widget.

Creates a pseudo-terminal running zsh -l (login shell) and exposes
an HTTP API for the widget to send commands and read output.

Usage:
    python3 terminal-server.py [--port PORT] [--pidfile PATH]

Endpoints:
    POST /send   { "input": "ls -la\\n" }  → send text to PTY
    GET  /read                              → get queued output
    GET  /health                            → server status
    POST /resize { "cols": 80, "rows": 24 } → resize terminal
    POST /kill                              → shutdown server
"""

import pty
import os
import select
import sys
import json
import struct
import fcntl
import termios
import signal
import time
import threading
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Configuration ---
HOST = '127.0.0.1'
DEFAULT_PORT = 18765
SHELL = os.environ.get('SHELL', '/bin/zsh')
CWD_MARKER = '__TW_CWD__'

# --- Global State ---
output_queue = []
output_lock = threading.Lock()
input_queue = []
input_lock = threading.Lock()
pty_fd = None
running = True
ready_event = threading.Event()


def pty_reader(fd):
    """Read PTY output continuously into a queue."""
    global running
    incomplete = b''
    while running and fd >= 0:
        try:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                data = os.read(fd, 8192)
                if not data:
                    break
                incomplete += data
                # Try to decode UTF-8 with replacement for incomplete sequences
                try:
                    decoded = incomplete.decode('utf-8')
                    incomplete = b''
                except UnicodeDecodeError:
                    if len(incomplete) > 10:  # Force decode if buffer gets large
                        decoded = incomplete.decode('utf-8', errors='replace')
                        incomplete = b''
                    else:
                        continue
                
                with output_lock:
                    output_queue.append(decoded)
        except (OSError, ValueError):
            break
    
    with output_lock:
        output_queue.append('\r\n[Terminal session ended]\r\n')
    ready_event.set()


def pty_writer(fd):
    """Write queued input to PTY."""
    global running
    while running and fd >= 0:
        with input_lock:
            if input_queue:
                data = input_queue.pop(0)
                try:
                    os.write(fd, data.encode('utf-8'))
                except OSError:
                    break
        time.sleep(0.01)


def get_output():
    """Get and clear all queued output."""
    with output_lock:
        result = ''.join(output_queue)
        output_queue.clear()
    return result


def send_input(text):
    """Queue text to send to PTY."""
    with input_lock:
        input_queue.append(text)


def normalize_command_input(text):
    """Convert command-bar input into shell input plus a hidden cwd marker."""
    if not text or not text.endswith('\n'):
        return text

    command = text[:-1]
    if not command.strip():
        return f"printf '\\n{CWD_MARKER}%s\\n' \"$PWD\"\n"

    escaped_marker = CWD_MARKER.replace("'", "'\\''")
    return f"{command}\nprintf '\\n{escaped_marker}%s\\n' \"$PWD\"\n"


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler."""
    
    def log_message(self, fmt, *args):
        pass  # Suppress HTTP log spam
    
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        
        if parsed.path == '/read':
            output = get_output()
            self._send_json({'output': output})
        elif parsed.path == '/health':
            alive = pty_fd is not None and running
            self._send_json({'status': 'ok' if alive else 'dead', 'alive': alive})
        else:
            self._send_json({'error': 'not found'}, 404)
    
    def do_POST(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else '{}'
        data = json.loads(body) if body else {}
        
        if parsed.path == '/send':
            cmd = data.get('input', '')
            send_input(normalize_command_input(cmd))
            self._send_json({'status': 'ok'})
        
        elif parsed.path == '/resize':
            cols = data.get('cols', 80)
            rows = data.get('rows', 24)
            if pty_fd:
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(pty_fd, termios.TIOCSWINSZ, winsize)
            self._send_json({'status': 'ok'})
        
        elif parsed.path == '/kill':
            self._send_json({'status': 'ok', 'message': 'shutting down'})
            threading.Thread(target=do_shutdown, daemon=True).start()
        
        else:
            self._send_json({'error': 'not found'}, 404)


def do_shutdown():
    """Graceful shutdown in a separate thread to allow HTTP response to be sent."""
    global running
    time.sleep(0.5)
    running = False
    os._exit(0)


def main():
    global pty_fd, running
    
    parser = argparse.ArgumentParser(description='Terminal PTY server')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--pidfile', type=str, default='')
    args = parser.parse_args()
    
    port = args.port
    pidfile = args.pidfile
    
    # Kill any existing server on this port
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((HOST, port))
    if result == 0:
        # Port in use - try to kill existing server
        try:
            import urllib.request
            req = urllib.request.Request(f'http://{HOST}:{port}/kill', method='POST')
            urllib.request.urlopen(req, timeout=3)
            time.sleep(0.5)
        except:
            pass
    sock.close()
    
    # Fork PTY (must be before threads!)
    try:
        pid, fd = pty.fork()
    except OSError as e:
        print(f"Failed to fork PTY: {e}", file=sys.stderr)
        sys.exit(1)
    
    pty_fd = fd
    
    if pid == 0:
        # Child process: start login shell
        # Set proper terminal settings
        os.chdir(os.path.expanduser('~'))
        os.environ['TERM'] = 'xterm-256color'
        os.environ['PROMPT'] = ''
        os.environ['PS1'] = ''
        os.environ['RPROMPT'] = ''
        os.environ['PROMPT_EOL_MARK'] = ''
        shell_name = os.path.basename(SHELL)
        if shell_name == 'zsh':
            os.execvp(SHELL, [SHELL, '-f', '-s'])
        if shell_name == 'bash':
            os.execvp(SHELL, [SHELL, '--noprofile', '--norc', '-s'])
        os.execvp(SHELL, [SHELL])
        sys.exit(0)
     
    # Parent process
    attrs = termios.tcgetattr(fd)
    attrs[3] = attrs[3] & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, attrs)

    # Set terminal size
    winsize = struct.pack('HHHH', 24, 80, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    
    # Start I/O threads
    reader = threading.Thread(target=pty_reader, args=(fd,), daemon=True)
    writer = threading.Thread(target=pty_writer, args=(fd,), daemon=True)
    reader.start()
    writer.start()
    
    # Write PID file if requested
    if pidfile:
        with open(pidfile, 'w') as f:
            f.write(str(os.getpid()))
    
    # Wait for initial shell prompt
    time.sleep(0.5)
    ready_event.set()
    
    # Start HTTP server
    server = HTTPServer((HOST, port), Handler)
    server.timeout = 0.5
    
    try:
        while running:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        if pty_fd:
            try:
                os.close(pty_fd)
            except:
                pass
        if pidfile and os.path.exists(pidfile):
            os.remove(pidfile)


if __name__ == '__main__':
    main()
