"""Tests for the env-var-based privacy injection model.

Each task declares required env-var names in its ``.privacy`` file (one
KEY per line). Values come from ``configs/privacy.local.env`` and are
injected into the executor container via ``docker run -e KEY=VALUE``.
The supervisor workspace mirrors the same KEY=VALUE pairs into
``privacy/env.env``; the public user simulator never sees them.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from lib.privacy import (
    load_privacy_config,
    load_task_privacy_keys,
    parse_privacy_keys_file,
    resolve_privacy_env,
)
from lib.supervision.workspace import _copy_privacy_workspace_files


# ─── .privacy file parsing ───────────────────────────────────────────


def test_parse_privacy_keys_file_accepts_comments_and_blanks(tmp_path: Path) -> None:
    path = tmp_path / ".privacy"
    path.write_text(
        "# Task: demo\n"
        "\n"
        "EMAIL_ADDRESS\n"
        "# API credential\n"
        "API_TOKEN\n"
        "\n",
        encoding="utf-8",
    )
    assert parse_privacy_keys_file(path) == ["EMAIL_ADDRESS", "API_TOKEN"]


def test_parse_privacy_keys_file_tolerates_key_equals_value_lines(tmp_path: Path) -> None:
    """If a user pastes a whole env line by mistake, we keep just the LHS."""
    path = tmp_path / ".privacy"
    path.write_text("EMAIL_PASSWORD=leaked\nAPI_TOKEN\n", encoding="utf-8")
    assert parse_privacy_keys_file(path) == ["EMAIL_PASSWORD", "API_TOKEN"]


def test_parse_privacy_keys_file_rejects_invalid_name(tmp_path: Path) -> None:
    path = tmp_path / ".privacy"
    path.write_text("3BAD_START\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid env-var name"):
        parse_privacy_keys_file(path)


def test_parse_privacy_keys_file_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / ".privacy"
    path.write_text("API_TOKEN\nAPI_TOKEN\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate env-var name"):
        parse_privacy_keys_file(path)


def test_parse_privacy_keys_file_missing_returns_empty(tmp_path: Path) -> None:
    assert parse_privacy_keys_file(tmp_path / "nope") == []


def test_load_task_privacy_keys_reads_injection_file(tmp_path: Path) -> None:
    injection = tmp_path / "injection"
    injection.mkdir()
    (injection / ".privacy").write_text("OUTLOOK_URL\nEMAIL_ADDRESS\n", encoding="utf-8")
    assert load_task_privacy_keys(injection) == ["OUTLOOK_URL", "EMAIL_ADDRESS"]


# ─── configs/privacy.local.env loading + resolution ──────────────────


def test_load_privacy_config_reads_env_file(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("# comment\nFOO=bar\nBAZ=quux\n", encoding="utf-8")
    assert load_privacy_config(cfg) == {"FOO": "bar", "BAZ": "quux"}


def test_resolve_privacy_env_returns_declared_subset(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text(
        "EMAIL_ADDRESS=you@example.com\n"
        "EMAIL_PASSWORD=hunter2\n"
        "UNUSED=leftover\n",
        encoding="utf-8",
    )
    resolved = resolve_privacy_env(["EMAIL_ADDRESS", "EMAIL_PASSWORD"], config_path=cfg)
    assert resolved == {"EMAIL_ADDRESS": "you@example.com", "EMAIL_PASSWORD": "hunter2"}


def test_resolve_privacy_env_raises_on_missing_key(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("EMAIL_ADDRESS=you@example.com\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing keys: EMAIL_PASSWORD"):
        resolve_privacy_env(["EMAIL_ADDRESS", "EMAIL_PASSWORD"], config_path=cfg)


def test_resolve_privacy_env_raises_on_empty_value(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("API_TOKEN=\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty keys: API_TOKEN"):
        resolve_privacy_env(["API_TOKEN"], config_path=cfg)


def test_resolve_privacy_env_rejects_empty_snapshot_mode(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("SNAPSHOT_MODE=\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty keys: SNAPSHOT_MODE"):
        resolve_privacy_env(["SNAPSHOT_MODE"], config_path=cfg)


def test_resolve_privacy_env_snapshot_mode_allows_empty_live_credentials(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text(
        "SNAPSHOT_MODE=1\n"
        "TRELLO_API_KEY=\n"
        "TRELLO_API_TOKEN=REPLACE_ME\n",
        encoding="utf-8",
    )
    assert resolve_privacy_env(
        ["TRELLO_API_KEY", "TRELLO_API_TOKEN", "SNAPSHOT_MODE"],
        config_path=cfg,
    ) == {"SNAPSHOT_MODE": "1"}


def test_resolve_privacy_env_live_mode_requires_declared_credentials(tmp_path: Path) -> None:
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("SNAPSHOT_MODE=0\nTRELLO_API_KEY=\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty keys: TRELLO_API_KEY"):
        resolve_privacy_env(["TRELLO_API_KEY", "SNAPSHOT_MODE"], config_path=cfg)


def test_resolve_privacy_env_no_keys_is_noop() -> None:
    assert resolve_privacy_env([]) == {}


# ─── container-side: start_container injects -e KEY=VALUE ────────────


def test_start_container_injects_privacy_env_args(tmp_path: Path, monkeypatch) -> None:
    """``start_container`` must pass every declared privacy KEY as
    ``docker run -e KEY=VALUE``, sourcing values from the shared local
    config file. Proxy env / browser env must still be forwarded."""
    import lib.runner.container_lifecycle as container_mod

    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("EMAIL_ADDRESS=demo@x\nEMAIL_PASSWORD=pw-secret\n", encoding="utf-8")
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)
    # The env-var injection path uses the default config unless we patch
    # both the imported constant at the usage site (already done via
    # monkeypatch above) and ensure ``resolve_privacy_env`` sees it.
    monkeypatch.setattr(container_mod, "resolve_privacy_env", lambda keys: {
        key: {"EMAIL_ADDRESS": "demo@x", "EMAIL_PASSWORD": "pw-secret"}.get(key, "")
        for key in keys if key in {"EMAIL_ADDRESS", "EMAIL_PASSWORD"}
    })

    captured_args: list[list[str]] = []

    def fake_docker(args: list[str], **_kw):
        captured_args.append(list(args))
        return subprocess.CompletedProcess(args=["docker", *args], returncode=0, stdout="abc", stderr="")

    monkeypatch.setattr("lib.runner.container_lifecycle.docker_mod.docker", fake_docker)
    monkeypatch.setattr("lib.runner.container_lifecycle.docker_mod.docker_rm", lambda *a, **kw: True)

    task = SimpleNamespace(
        task_id="task_demo",
        privacy=["EMAIL_ADDRESS", "EMAIL_PASSWORD"],
    )
    # slugify just returns its input for simple ids; avoid importing
    # task_config just for the sake of the test.
    monkeypatch.setattr("lib.runner.container_lifecycle.task_config.slugify", lambda v: str(v))

    container_mod.start_container("img:latest", task, "a1")

    assert captured_args, "docker run should have been called"
    full_cmd = captured_args[0]
    # The -e pairs for privacy must both appear.
    pairs = [full_cmd[i + 1] for i, tok in enumerate(full_cmd) if tok == "-e"]
    assert "EMAIL_ADDRESS=demo@x" in pairs
    assert "EMAIL_PASSWORD=pw-secret" in pairs


def test_start_container_with_no_privacy_adds_no_privacy_env_args(tmp_path: Path, monkeypatch) -> None:
    """When a task has no privacy keys, no extra ``-e KEY=VALUE`` args
    for credentials should appear — proxy/browser env only."""
    import lib.runner.container_lifecycle as container_mod

    monkeypatch.setattr(container_mod, "resolve_privacy_env", lambda keys: {})

    captured_args: list[list[str]] = []

    def fake_docker(args: list[str], **_kw):
        captured_args.append(list(args))
        return subprocess.CompletedProcess(args=["docker", *args], returncode=0, stdout="abc", stderr="")

    monkeypatch.setattr("lib.runner.container_lifecycle.docker_mod.docker", fake_docker)
    monkeypatch.setattr("lib.runner.container_lifecycle.docker_mod.docker_rm", lambda *a, **kw: True)
    monkeypatch.setattr("lib.runner.container_lifecycle.task_config.slugify", lambda v: str(v))

    task = SimpleNamespace(task_id="task_no_creds", privacy=[])
    container_mod.start_container("img:latest", task, "a1")

    full_cmd = captured_args[0]
    pairs = [full_cmd[i + 1] for i, tok in enumerate(full_cmd) if tok == "-e"]
    # No KEY=VALUE pair unrelated to proxy/browser should appear.
    sensitive_shapes = [p for p in pairs if p.startswith(("EMAIL_", "API_", "TOKEN_", "SECRET_"))]
    assert sensitive_shapes == []


def test_prepare_runtime_no_longer_touches_privacy_directory(tmp_path: Path, monkeypatch) -> None:
    """The old ``.privacy/`` folder copy is gone. ``prepare_runtime``
    must not mkdir/chmod/copy anything under
    /tmp_workspace/clawbench/.privacy/."""
    import lib.runner as runner

    injection_root = tmp_path / "injection"
    (injection_root / "sources").mkdir(parents=True)
    (injection_root / "skills").mkdir()
    # Deliberately leave a stale folder on disk to confirm it's ignored.
    (injection_root / ".privacy").mkdir()
    (injection_root / ".privacy" / "creds.env").write_text("KEY=secret\n", encoding="utf-8")

    task = SimpleNamespace(
        agent_sys="openclaw",
        injection_root=injection_root,
        skills=[],
        services=[],
        privacy=[],
    )

    docker_cmds: list[str] = []

    def fake_docker_exec(container: str, script: str, **_kw):
        docker_cmds.append(script)
        return subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("lib.runner.docker.docker_exec", fake_docker_exec)
    monkeypatch.setattr("lib.runner.docker.copy_tree_contents_to_container", lambda *a, **kw: None)
    monkeypatch.setattr("lib.runner.docker.docker_cp_to_container", lambda *a, **kw: None)
    monkeypatch.setattr("lib.runner.docker.docker_write_text_file", lambda *a, **kw: None)

    runner.prepare_runtime("fake-container", task)

    assert not any(".privacy" in c for c in docker_cmds), (
        "prepare_runtime must not create, chmod, or populate a container-side "
        ".privacy/ directory under the env-var injection model"
    )


# ─── supervisor workspace mirror ─────────────────────────────────────


def _make_ctx_with_privacy(injection_root: Path, *, declared: list[str]):
    """Minimal SupervisorContext sufficient for _copy_privacy_workspace_files."""
    from lib.supervision.common import (
        AttemptSupervisorContext,
        CodexRoleRuntimeContext,
        SupervisorContext,
        TaskSupervisorContext,
    )

    role_ctx = CodexRoleRuntimeContext(
        role="answer_supervisor",
        model="gpt-5.4",
        provider="p",
        config_path=Path("configs/codex.local.toml"),
        reasoning_effort="high",
    )
    task_ctx = TaskSupervisorContext(
        task_id="t",
        task_file=Path("/tmp/x.yaml"),
        injection_root=injection_root,
        run_root=Path("/tmp/run"),
        public_task="do the thing",
        references=[],
        success_threshold=1.0,
        max_user_followups=2,
        user_simulator=role_ctx,
        supervisor=role_ctx,
        privacy=list(declared),
    )
    attempt_ctx = AttemptSupervisorContext(
        attempt=1,
        turn=0,
        out_dir=Path("/tmp/out"),
        result_dir=Path("/tmp/out/result"),
        prompt_file=Path("/tmp/out/prompt.md"),
        transcript_file=Path("/tmp/out/transcript.jsonl"),
        tool_usage_file=Path("/tmp/out/tool_usage.json"),
        runtime_probe_file=Path("/tmp/out/runtime_probe.json"),
    )
    return SupervisorContext(task=task_ctx, attempt=attempt_ctx)


def test_copy_privacy_workspace_files_writes_env_file(tmp_path: Path, monkeypatch) -> None:
    """Supervisor workspace should get a privacy/env.env file with
    exactly the declared KEYs and their values from privacy.local.env."""
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text(
        "EMAIL_ADDRESS=real@x\nEMAIL_PASSWORD=real-pw\nUNUSED=leftover\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    workspace = tmp_path / "ws"
    workspace.mkdir()
    ctx = _make_ctx_with_privacy(tmp_path / "injection", declared=["EMAIL_ADDRESS", "EMAIL_PASSWORD"])

    entries = _copy_privacy_workspace_files(ctx, workspace)

    env_file = workspace / "privacy" / "env.env"
    assert env_file.exists()
    text = env_file.read_text(encoding="utf-8")
    assert "EMAIL_ADDRESS=real@x" in text
    assert "EMAIL_PASSWORD=real-pw" in text
    # The unused value must not leak into the supervisor workspace.
    assert "UNUSED" not in text
    assert any(e.get("purpose", "").startswith("task privacy env vars") for e in entries)


def test_copy_privacy_workspace_files_no_declared_keys_is_noop(tmp_path: Path) -> None:
    """No privacy declaration → no workspace file created."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    ctx = _make_ctx_with_privacy(tmp_path / "injection", declared=[])

    entries = _copy_privacy_workspace_files(ctx, workspace)
    assert entries == []
    assert not (workspace / "privacy").exists()


def test_copy_privacy_workspace_files_incomplete_config_fails_open(tmp_path: Path, monkeypatch) -> None:
    """If resolve_privacy_env can't find all keys, the supervisor path
    must not crash — load-time validation would already have raised on
    a real run. Return an empty list and skip the workspace mirror."""
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("EMAIL_ADDRESS=real@x\n", encoding="utf-8")  # missing EMAIL_PASSWORD
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    workspace = tmp_path / "ws"
    workspace.mkdir()
    ctx = _make_ctx_with_privacy(tmp_path / "injection", declared=["EMAIL_ADDRESS", "EMAIL_PASSWORD"])

    entries = _copy_privacy_workspace_files(ctx, workspace)
    assert entries == []
    assert not (workspace / "privacy").exists()


# ─── privacy leakage cap (values sourced from config now) ────────────


def test_apply_privacy_leakage_cap_is_disabled_by_default(tmp_path: Path, monkeypatch) -> None:
    """With ENABLE_PRIVACY_LEAKAGE_CAP=False (default), a score is
    passed through unchanged even if a credential value appears in the
    transcript."""
    import lib.runner as runner

    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("EMAIL_PASSWORD=super-secret-password\n", encoding="utf-8")
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    out_dir = tmp_path / "attempt"
    out_dir.mkdir()
    (out_dir / "result").mkdir()
    (out_dir / "transcript.jsonl").write_text(
        '{"type":"message","text":"password was super-secret-password"}\n',
        encoding="utf-8",
    )
    task = SimpleNamespace(injection_root=tmp_path, privacy=["EMAIL_PASSWORD"])
    score = {
        "overall_score": 1.0,
        "score_cap": 1.0,
        "capped_score": 1.0,
        "verdict": "pass",
        "attempt_state": "complete_and_passed",
        "recoverable": False,
        "safe_user_feedback": "done",
        "guidance_tags": ["credential_hygiene"],
        "public_feedback_points": ["keep going"],
    }

    result = runner.apply_privacy_leakage_cap(task, out_dir, score)

    assert result["privacy_leakage_detected"] is False
    assert result["overall_score"] == 1.0
    assert result["verdict"] == "pass"
    assert "super-secret-password" not in json.dumps(result, ensure_ascii=False)


def test_apply_privacy_leakage_cap_caps_score_when_enabled(tmp_path: Path, monkeypatch) -> None:
    """With the cap enabled, a leaked credential value caps the score to 0."""
    import lib.runner as runner

    monkeypatch.setattr("lib.runner.evaluation.ENABLE_PRIVACY_LEAKAGE_CAP", True)

    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("EMAIL_PASSWORD=super-secret-password\n", encoding="utf-8")
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    out_dir = tmp_path / "attempt"
    out_dir.mkdir()
    (out_dir / "result").mkdir()
    (out_dir / "transcript.jsonl").write_text(
        '{"type":"message","text":"password was super-secret-password"}\n',
        encoding="utf-8",
    )
    task = SimpleNamespace(injection_root=tmp_path, privacy=["EMAIL_PASSWORD"])
    score = {
        "overall_score": 1.0,
        "score_cap": 1.0,
        "capped_score": 1.0,
        "verdict": "pass",
        "attempt_state": "complete_and_passed",
        "recoverable": False,
        "safe_user_feedback": "done",
        "guidance_tags": ["credential_hygiene"],
        "public_feedback_points": ["keep going"],
    }

    result = runner.apply_privacy_leakage_cap(task, out_dir, score)

    assert result["privacy_leakage_detected"] is True
    assert result["overall_score"] == 0.0
    assert result["verdict"] == "fail"
    assert result["attempt_state"] == "terminal_failure"
    assert result["privacy_leakage_hits"] == [
        {"key": "EMAIL_PASSWORD", "file": "transcript.jsonl", "lines": [1]}
    ]
    assert "super-secret-password" not in json.dumps(result, ensure_ascii=False)
