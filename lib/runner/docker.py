"""Docker / subprocess primitives used by the rest of the runner package.

These wrappers keep every ``docker <subcommand>`` shell call in one place so
tests can stub them via ``monkeypatch.setattr("lib.runner.docker.<name>",
fake)`` (or the legacy ``lib.runner.<name>`` re-export).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from ..proxy import write_local


def run(
    cmd: list[str],
    *,
    input_text: str | None = None,
    cwd: Path | None = None,
    timeout_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        timeout=timeout_seconds,
    )


def docker(
    args: list[str],
    *,
    input_text: str | None = None,
    timeout_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return run(["docker", *args], input_text=input_text, timeout_seconds=timeout_seconds)


def container_exists(container: str) -> bool:
    result = docker(["inspect", container])
    return result.returncode == 0


def docker_rm(container: str, *, timeout_seconds: float = 20.0) -> bool:
    if not container:
        return True
    start = time.time()
    result = docker(["rm", "-f", container])
    if result.returncode != 0 and "No such container" not in ((result.stderr or "") + (result.stdout or "")):
        return False
    while time.time() - start < timeout_seconds:
        if not container_exists(container):
            return True
        time.sleep(0.2)
    return not container_exists(container)


def docker_exec(
    container: str,
    command: str,
    *,
    detach: bool = False,
    timeout_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    args = ["exec"]
    if detach:
        args.append("-d")
    args.extend([container, "bash", "-lc", command])
    return docker(args, timeout_seconds=timeout_seconds)


def docker_cp_to_container(src: Path, container: str, dest: str) -> None:
    result = docker(["cp", str(src), f"{container}:{dest}"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"docker cp failed: {src} -> {dest}")


def docker_cp_from_container(container: str, src: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = docker(["cp", f"{container}:{src}", str(dest)])
    return result.returncode == 0


def copy_tree_contents_to_container(src: Path, container: str, dest: str) -> None:
    if not src.exists():
        return
    for child in sorted(src.iterdir()):
        docker_cp_to_container(child, container, f"{dest}/")


def docker_write_text_file(
    container: str,
    dest: str,
    content: str,
    *,
    prefix: str = "clawbench-text-",
    suffix: str = ".txt",
) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        write_local(temp_path, content)
        docker_cp_to_container(temp_path, container, dest)
    finally:
        temp_path.unlink(missing_ok=True)
