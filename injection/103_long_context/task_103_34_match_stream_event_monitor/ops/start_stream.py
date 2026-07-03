#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback for local dev
    fcntl = None


ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("MATCH_STREAM_PORT", "8129"))
URL = f"http://127.0.0.1:{PORT}/status"
SERVER = ROOT / "ops" / "stream_server.py"
VIDEO = ROOT / "services" / "match-stream" / "assets" / "stream_asset_103_09.mp4"
MODE = "mjpeg-live-v2"
PID_FILE = Path(f"/tmp/clawbench_match_stream_{PORT}.pid")
LOG_FILE = Path(f"/tmp/clawbench_match_stream_{PORT}.log")
LOCK_FILE = Path(f"/tmp/clawbench_match_stream_{PORT}.lock")


@contextmanager
def host_lock():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def healthy() -> bool:
    try:
        with urllib.request.urlopen(URL, timeout=1.5) as response:
            body = response.read(1000)
            return (
                b"match-stream: ok" in body
                and f"mode: {MODE}".encode("utf-8") in body
                and b"ffmpeg: ok" in body
            )
    except Exception:
        return False


def stop_existing() -> None:
    if not PID_FILE.exists():
        return
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return
    try:
        os.kill(pid, 15)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return
    except PermissionError:
        return
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            PID_FILE.unlink(missing_ok=True)
            return
        time.sleep(0.1)


def main() -> None:
    with host_lock():
        if healthy():
            print(f"match stream already running on port {PORT}")
            return
        if not VIDEO.exists():
            raise SystemExit(f"missing stream asset: {VIDEO}")
        stop_existing()
        env = dict(os.environ)
        env["MATCH_STREAM_PORT"] = str(PORT)
        env["MATCH_STREAM_VIDEO"] = str(VIDEO)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log = LOG_FILE.open("ab")
        proc = subprocess.Popen(
            [sys.executable, str(SERVER)],
            cwd=str(ROOT),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        PID_FILE.write_text(str(proc.pid), encoding="utf-8")
        for _ in range(40):
            if proc.poll() is not None:
                raise SystemExit(f"match stream exited early; see {LOG_FILE}")
            if healthy():
                print(f"match stream started on port {PORT}; pid={proc.pid}")
                return
            time.sleep(0.25)
        proc.terminate()
        raise SystemExit(f"match stream did not become healthy; see {LOG_FILE}")


if __name__ == "__main__":
    main()
