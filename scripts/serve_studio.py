#!/usr/bin/env python3
"""
Zero-dependency HTTP static server with full RFC 9110 Byte-Range support
(Accept-Ranges: bytes, 206 Partial Content, 416 Range Not Satisfiable)
so browser <audio> scrubbing and live A/B switching work smoothly.

Usage:
  python3 scripts/serve_studio.py [port]
"""

from __future__ import annotations

import os
import re
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
CHUNK_SIZE = 64 * 1024


def parse_byte_range(header: str, file_size: int) -> Optional[Tuple[int, int]]:
    """Parse a single HTTP byte-range spec into inclusive (start, end), or None if invalid."""
    spec = header.strip()
    if "," in spec:
        # Handle first range cleanly for single-part media requests
        spec = spec.split(",", 1)[0].strip()
    m = RANGE_RE.match(spec)
    if not m or file_size <= 0:
        return None
    start_s, end_s = m.groups()
    if not start_s and not end_s:
        return None
    if start_s == "":
        # Suffix byte range: bytes=-N
        suffix = int(end_s)
        if suffix <= 0:
            return None
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        start = int(start_s)
        if start >= file_size:
            return None
        end = file_size - 1 if end_s == "" else min(int(end_s), file_size - 1)
        if end < start:
            return None
    return (start, end)


class RangeRequestHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler with full HTTP Range (206 Partial Content) support."""

    protocol_version = "HTTP/1.1"

    def __init__(self, *args, directory: Optional[str] = None, **kwargs):
        repo_root = str(Path(__file__).resolve().parent.parent)
        super().__init__(*args, directory=directory or repo_root, **kwargs)

    def _open_for_range(self, send_body: bool) -> None:
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            # Fall back to standard directory/index.html handling
            f = self.send_head()
            if f:
                try:
                    if send_body:
                        self.copyfile(f, self.wfile)
                finally:
                    f.close()
            return

        if not os.path.isfile(path):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        try:
            fs = os.fstat(f.fileno())
            file_size = fs.st_size
            ctype = self.guess_type(path)
            last_mod = self.date_time_string(fs.st_mtime)
            range_hdr = self.headers.get("Range")

            if range_hdr:
                parsed = parse_byte_range(range_hdr, file_size)
                if parsed is None:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                start, end = parsed
                length = end - start + 1
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Last-Modified", last_mod)
                self.end_headers()

                if send_body:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(CHUNK_SIZE, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            else:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Last-Modified", last_mod)
                self.end_headers()

                if send_body:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # Normal when browsers cancel range requests during rapid scrubbing
            pass
        finally:
            f.close()

    def do_GET(self) -> None:
        self._open_for_range(send_body=True)

    def do_HEAD(self) -> None:
        self._open_for_range(send_body=False)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    host = "127.0.0.1"
    repo_root = Path(__file__).resolve().parent.parent
    server = ReusableThreadingHTTPServer((host, port), RangeRequestHandler)
    print(f"Serving {repo_root} on http://{host}:{port}/ (HTTP Range/206 enabled)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
