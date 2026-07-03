"""End-to-end tests for the preflight worker readiness check.

Mocks ``subprocess.run`` (for ssh / docker / scp) so the tests run fast
and don't touch the network. The goal is to pin the BEHAVIOUR:

  - All clean → no raise
  - Any reachable worker missing anything → PreflightError listing problems
  - Unreachable worker → logged, NOT a blocker
  - Image-ID digest mismatch → flagged
  - Controller missing local images → digest comparison skipped (warning only)
"""
from __future__ import annotations

import subprocess
import pytest

import scripts.orchestra.preflight as preflight_mod
import scripts.orchestra.prepare_node as prepare_node_mod
from scripts.orchestra.config import (
    ControllerCfg,
    CodexRoleCfg,
    OrchestraConfig,
    SupervisionCfg,
    WorkerCfg,
)


def _stub_cfg(tmp_path, workers):
    """Minimal config wrapping a set of workers."""
    return OrchestraConfig(
        controller=ControllerCfg(host="ctl", data_root=tmp_path, webui_port=9005),
        workers=tuple(workers),
        priorities=(),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="x", model="x"),
            user_simulator=CodexRoleCfg(provider="x", model="x"),
        ),
    )


def _make_completed(stdout: str, rc: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["mocked"], returncode=rc, stdout=stdout, stderr="")


@pytest.fixture
def workers_4(tmp_path):
    return _stub_cfg(tmp_path, [
        WorkerCfg(name="worker1", ssh="worker1", parallel=4),
        WorkerCfg(name="worker2", ssh="worker2", parallel=4),
        WorkerCfg(name="worker3", ssh="worker3", parallel=4),
        WorkerCfg(name="worker4", ssh="worker4", parallel=4),
    ])


def _clean_ssh_response(cmd: str) -> str:
    """Generate a 'clean worker' response for whatever check the cmd is doing."""
    # Image inspection: alternating "tag" / "sha256:..." pairs
    if "docker image inspect" in cmd:
        out_lines = []
        for tag in preflight_mod.REQUIRED_IMAGES:
            out_lines.append(tag)
            out_lines.append(f"sha256:{'a' * 64}")
        return "\n".join(out_lines)
    # apt check: no missing packages → empty stdout
    if "dpkg-query" in cmd:
        return ""
    # pip check: stdout is the freeze list (all packages installed, lower-cased)
    if "list --format=freeze" in cmd:
        return "\n".join(p.lower() for p in prepare_node_mod.WORKER_PIP_PACKAGES)
    # port check: all 9000-9002 listening
    if "ss -tlnp" in cmd:
        return "\n".join("*:9000 *:9001 *:9002".split())
    return ""


@pytest.fixture(autouse=True)
def stub_reachable(monkeypatch):
    """By default, all workers are reachable."""
    monkeypatch.setattr(preflight_mod, "_ssh_probe", lambda host: True)


@pytest.fixture
def stub_clean_ssh(monkeypatch):
    """SSH responses simulate a fully-clean worker."""
    def fake_ssh(host, cmd, timeout=600):
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)


@pytest.fixture
def stub_local_images_match(monkeypatch):
    """Controller has docker images with the same all-a sha256 the workers do."""
    monkeypatch.setattr(
        preflight_mod,
        "_local_image_ids",
        lambda imgs: {tag: f"sha256:{'a' * 64}" for tag in imgs},
    )


# ── test cases ────────────────────────────────────────────────────────


def test_all_workers_clean_passes(workers_4, stub_clean_ssh, stub_local_images_match):
    results = preflight_mod.preflight_check(workers_4)
    assert len(results) == 4
    for r in results:
        assert r.is_clean(), f"{r.worker_name}: {r.summary_line()}"


def test_one_worker_missing_image_raises(workers_4, monkeypatch, stub_local_images_match):
    """worker3 is missing clawbench-codex — preflight must raise listing worker3."""
    def fake_ssh(host, cmd, timeout=600):
        if "docker image inspect" in cmd and host == "worker3":
            # worker3 returns MISSING for clawbench-codex, the rest valid
            lines = []
            for tag in preflight_mod.REQUIRED_IMAGES:
                lines.append(tag)
                lines.append("MISSING" if "codex" in tag else f"sha256:{'a' * 64}")
            return _make_completed("\n".join(lines))
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    with pytest.raises(preflight_mod.PreflightError) as exc_info:
        preflight_mod.preflight_check(workers_4)

    msg = str(exc_info.value)
    assert "worker3" in msg
    assert "clawbench-codex:latest" in msg
    # The 3 other workers must NOT appear in the failure list
    assert "worker1 (worker1)" not in msg.replace("worker10", "")  # worker1 not listed as problem
    # Verify the structured problem list
    problems = exc_info.value.problems
    assert len(problems) == 1
    assert problems[0].worker_name == "worker3"
    assert "clawbench-codex:latest" in problems[0].missing_images


def test_unreachable_worker_logged_not_blocking(workers_4, monkeypatch, stub_clean_ssh, stub_local_images_match):
    """worker2 ssh probe fails — preflight passes with WARNING, worker2 not in raise."""
    def selective_probe(host):
        return host != "worker2"
    monkeypatch.setattr(preflight_mod, "_ssh_probe", selective_probe)

    # No exception raised
    results = preflight_mod.preflight_check(workers_4)
    # worker2 marked unreachable but still in results
    worker2 = next(r for r in results if r.worker_name == "worker2")
    assert not worker2.reachable
    assert worker2.is_clean()  # unreachable workers don't count as "problems"


def test_image_id_mismatch_treated_as_failure(workers_4, monkeypatch):
    """Controller has digest X for one tag; worker3 has digest Y → flagged."""
    monkeypatch.setattr(
        preflight_mod,
        "_local_image_ids",
        lambda imgs: {tag: f"sha256:{'a' * 64}" for tag in imgs},
    )

    def fake_ssh(host, cmd, timeout=600):
        if "docker image inspect" in cmd and host == "worker3":
            lines = []
            for tag in preflight_mod.REQUIRED_IMAGES:
                lines.append(tag)
                # worker3's codex tag is a DIFFERENT digest
                if "codex" in tag:
                    lines.append(f"sha256:{'b' * 64}")
                else:
                    lines.append(f"sha256:{'a' * 64}")
            return _make_completed("\n".join(lines))
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    with pytest.raises(preflight_mod.PreflightError) as exc_info:
        preflight_mod.preflight_check(workers_4)
    problems = exc_info.value.problems
    assert len(problems) == 1
    p = problems[0]
    assert p.worker_name == "worker3"
    assert len(p.image_id_mismatches) == 1
    tag, mid, wid = p.image_id_mismatches[0]
    assert "codex" in tag
    assert mid != wid


def test_controller_no_local_images_skips_digest_compare(workers_4, monkeypatch, stub_clean_ssh):
    """When _local_image_ids returns {}, digest comparison is skipped — clean workers still pass."""
    monkeypatch.setattr(preflight_mod, "_local_image_ids", lambda imgs: {})
    # Workers return valid SHA — but controller has no reference, so no comparison happens
    results = preflight_mod.preflight_check(workers_4)
    for r in results:
        assert r.is_clean()


def test_apt_package_missing_raises(workers_4, monkeypatch, stub_local_images_match):
    def fake_ssh(host, cmd, timeout=600):
        if "dpkg-query" in cmd and host == "worker3":
            return _make_completed("ffmpeg\nlibreoffice\n")  # 2 missing
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    with pytest.raises(preflight_mod.PreflightError) as exc_info:
        preflight_mod.preflight_check(workers_4)
    assert "ffmpeg" in str(exc_info.value)


def test_pip_package_missing_raises(workers_4, monkeypatch, stub_local_images_match):
    def fake_ssh(host, cmd, timeout=600):
        if "list --format=freeze" in cmd and host == "worker3":
            # worker3 venv has only a subset
            return _make_completed("pillow\nopenpyxl\n")
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    with pytest.raises(preflight_mod.PreflightError) as exc_info:
        preflight_mod.preflight_check(workers_4)
    p = exc_info.value.problems[0]
    assert "duckduckgo-search" in p.missing_pip  # one of the missing ones


def test_pip_venv_missing_returns_all_packages(workers_4, monkeypatch, stub_local_images_match):
    def fake_ssh(host, cmd, timeout=600):
        if "list --format=freeze" in cmd and host == "worker3":
            return _make_completed("VENV_MISSING\n")
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    with pytest.raises(preflight_mod.PreflightError) as exc_info:
        preflight_mod.preflight_check(workers_4)
    p = exc_info.value.problems[0]
    assert len(p.missing_pip) == len(prepare_node_mod.WORKER_PIP_PACKAGES)


def test_pip_check_uses_configured_worker_python(tmp_path, monkeypatch, stub_local_images_match):
    cfg = _stub_cfg(tmp_path, [
        WorkerCfg(name="worker1", ssh="worker1", parallel=4, python="/srv/custom-venv/bin/python"),
    ])
    seen_cmds: list[str] = []

    def fake_ssh(host, cmd, timeout=600):
        seen_cmds.append(cmd)
        return _make_completed(_clean_ssh_response(cmd))

    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    preflight_mod.preflight_check(cfg)

    pip_cmds = [cmd for cmd in seen_cmds if "list --format=freeze" in cmd]
    assert len(pip_cmds) == 1
    assert "/srv/custom-venv/bin/python -m pip list --format=freeze" in pip_cmds[0]
    assert "/opt/clawbench-venv/bin/python" not in pip_cmds[0]


def test_port_not_listening_raises(workers_4, monkeypatch, stub_local_images_match):
    def fake_ssh(host, cmd, timeout=600):
        if "ss -tlnp" in cmd and host == "worker3":
            return _make_completed("*:9000\n")  # only 9000 listening
        return _make_completed(_clean_ssh_response(cmd))
    monkeypatch.setattr(prepare_node_mod, "_ssh", fake_ssh)

    with pytest.raises(preflight_mod.PreflightError) as exc_info:
        preflight_mod.preflight_check(workers_4)
    p = exc_info.value.problems[0]
    assert 9001 in p.missing_ports
    assert 9002 in p.missing_ports


def test_skip_workers_not_checked(workers_4, monkeypatch, stub_clean_ssh, stub_local_images_match, tmp_path):
    """workers with skip=true are not probed at all."""
    skip_cfg = _stub_cfg(tmp_path, [
        WorkerCfg(name="worker1", ssh="worker1", parallel=4, skip=True),
        WorkerCfg(name="worker2", ssh="worker2", parallel=4),
    ])
    probe_calls = []
    def tracking_probe(host):
        probe_calls.append(host)
        return True
    monkeypatch.setattr(preflight_mod, "_ssh_probe", tracking_probe)
    preflight_mod.preflight_check(skip_cfg)
    assert "worker1" not in probe_calls
    assert "worker2" in probe_calls
