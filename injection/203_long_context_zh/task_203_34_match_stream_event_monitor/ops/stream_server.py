#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
VIDEO = Path(os.environ.get("MATCH_STREAM_VIDEO", ROOT / "services" / "match-stream" / "assets" / "stream_asset_103_09.mp4"))
PORT = int(os.environ.get("MATCH_STREAM_PORT", "8129"))
MODE = "mjpeg-live-v2"
SOURCE_FRAME_FPS = float(os.environ.get("MATCH_STREAM_SOURCE_FPS", "3"))
PLAYBACK_RATE = float(os.environ.get("MATCH_STREAM_PLAYBACK_RATE", "4"))
START_OFFSET_SECONDS = float(os.environ.get("MATCH_STREAM_START_OFFSET_SECONDS", "210"))
BOUNDARY = b"clawbench-match-frame"

HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Match Stream</title>
  <style>
    html, body { margin:0; min-height:100%; background:#050505; color:#eee; font-family:Arial, sans-serif; }
    main { min-height:100vh; display:grid; place-items:center; }
    img { width:min(100vw, 1180px); max-height:94vh; object-fit:contain; background:#000; }
  </style>
</head>
<body>
  <main>
    <img id="match-stream" alt="match stream">
  </main>
  <script>
    const stream = document.getElementById("match-stream");
    const sid = Math.random().toString(36).slice(2) + Date.now().toString(36);
    stream.src = "/live?sid=" + encodeURIComponent(sid);
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/stream"}:
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/status":
            exists = VIDEO.exists()
            size = VIDEO.stat().st_size if exists else 0
            ffmpeg = shutil.which("ffmpeg")
            state = "ok" if exists and size > 0 and ffmpeg else "missing"
            ffmpeg_state = "ok" if ffmpeg else "missing"
            body = (
                f"match-stream: {state}\n"
                f"mode: {MODE}\n"
                f"ffmpeg: {ffmpeg_state}\n"
                f"source_fps: {SOURCE_FRAME_FPS:g}\n"
                f"playback_rate: {PLAYBACK_RATE:g}\n"
            ).encode("utf-8")
            self.send_response(HTTPStatus.OK if state == "ok" else HTTPStatus.SERVICE_UNAVAILABLE)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/live":
            self.serve_live()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_HEAD(self) -> None:
        self.send_error(HTTPStatus.NOT_FOUND)

    def serve_live(self) -> None:
        if not VIDEO.exists():
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "stream asset missing")
            return
        if shutil.which("ffmpeg") is None:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "stream transcoder unavailable")
            return
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-ss",
            f"{START_OFFSET_SECONDS:g}",
            "-i",
            str(VIDEO),
            "-an",
            "-vf",
            f"fps={SOURCE_FRAME_FPS:g}",
            "-q:v",
            "5",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-",
        ]
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, f"stream transcoder failed: {exc}")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY.decode('ascii')}")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

        interval = 1.0 / max(SOURCE_FRAME_FPS * PLAYBACK_RATE, 0.1)
        next_frame_at = time.monotonic()
        buffer = b""
        try:
            assert proc.stdout is not None
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                buffer += chunk
                while True:
                    start = buffer.find(b"\xff\xd8")
                    if start < 0:
                        buffer = buffer[-1:]
                        break
                    end = buffer.find(b"\xff\xd9", start + 2)
                    if end < 0:
                        buffer = buffer[start:]
                        break
                    frame = buffer[start : end + 2]
                    buffer = buffer[end + 2 :]
                    now = time.monotonic()
                    if now < next_frame_at:
                        time.sleep(next_frame_at - now)
                    next_frame_at = max(next_frame_at + interval, time.monotonic())
                    header = (
                        b"--"
                        + BOUNDARY
                        + b"\r\nContent-Type: image/jpeg\r\nCache-Control: no-store\r\nContent-Length: "
                        + str(len(frame)).encode("ascii")
                        + b"\r\n\r\n"
                    )
                    self.wfile.write(header)
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def log_message(self, *args) -> None:
        pass


def main() -> None:
    if not VIDEO.exists():
        raise SystemExit(f"missing stream asset: {VIDEO}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
