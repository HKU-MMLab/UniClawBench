from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import scripts.orchestra.reap_orphan_containers as reaper


def test_claims_by_worker_missing_inflight_is_empty(tmp_path: Path) -> None:
    assert reaper.claims_by_worker(tmp_path / "missing.jsonl") == {}


def test_reaper_uses_worker_name_for_claims_and_ssh_for_transport(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    (runtime_dir / "inflight.jsonl").write_text(
        json.dumps({"worker": "worker-a", "task": "task_101_01_active"}) + "\n",
        encoding="utf-8",
    )

    worker = SimpleNamespace(name="worker-a", ssh="box-a", skip=False)
    monkeypatch.setattr(
        reaper.cfg_mod,
        "load",
        lambda _path: SimpleNamespace(workers=[worker]),
    )
    monkeypatch.setattr(reaper.cfg_mod, "runtime_dir", lambda: runtime_dir)

    probed_hosts: list[str] = []

    def fake_worker_containers(host: str):
        probed_hosts.append(host)
        return [
            ("cid-active", "3 minutes", "task_101_01_active"),
            ("cid-orphan", "3 minutes", "task_101_02_orphan"),
        ]

    monkeypatch.setattr(reaper, "worker_containers", fake_worker_containers)

    ssh_commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        ssh_commands.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(reaper.subprocess, "run", fake_run)

    rc = reaper.main(["--config", str(tmp_path / "orchestra.yaml"), "--apply"])

    assert rc == 0
    assert probed_hosts == ["box-a"]
    assert ssh_commands == [
        ["ssh", "-n", "-o", "ConnectTimeout=15", "box-a", "docker rm -f cid-orphan"]
    ]


def test_reaper_skips_configured_skip_workers(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    monkeypatch.setattr(
        reaper.cfg_mod,
        "load",
        lambda _path: SimpleNamespace(workers=[SimpleNamespace(name="worker-a", ssh="box-a", skip=True)]),
    )
    monkeypatch.setattr(reaper.cfg_mod, "runtime_dir", lambda: runtime_dir)

    probed_hosts: list[str] = []
    monkeypatch.setattr(reaper, "worker_containers", lambda host: probed_hosts.append(host) or [])

    assert reaper.main(["--config", str(tmp_path / "orchestra.yaml")]) == 0
    assert probed_hosts == []


def test_reaper_age_guard_keeps_second_old_containers(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    worker = SimpleNamespace(name="worker-a", ssh="box-a", skip=False)
    monkeypatch.setattr(reaper.cfg_mod, "load", lambda _path: SimpleNamespace(workers=[worker]))
    monkeypatch.setattr(reaper.cfg_mod, "runtime_dir", lambda: runtime_dir)
    monkeypatch.setattr(
        reaper,
        "worker_containers",
        lambda _host: [("cid-new", "12 seconds", "task_101_02_orphan")],
    )

    removed: list[list[str]] = []
    monkeypatch.setattr(
        reaper.subprocess,
        "run",
        lambda cmd, **kwargs: removed.append(list(cmd)) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )

    assert reaper.main(["--config", str(tmp_path / "orchestra.yaml"), "--apply"]) == 0
    assert removed == []


def test_worker_containers_parses_clawbench_container_names(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):  # noqa: ANN001
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="abc123|3 minutes|clawbench-task_101_01_demo-session-xyz\n",
            stderr="",
        )

    monkeypatch.setattr(reaper.subprocess, "run", fake_run)

    assert reaper.worker_containers("box-a") == [
        ("abc123", "3 minutes", "task_101_01_demo")
    ]
