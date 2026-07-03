"""Round 9 / A1 regression: privacy/env.env must never leak to public surfaces.

Privacy env values (provider API keys, account credentials, task-level
secrets like cookies) live at
``runs/<...>/codex_sessions/answer_supervisor/workspace/privacy/env.env``
during supervisor evaluation.  This file is supervisor-internal: the
model running inside the supervisor codex container reads it to verify
authenticated artifacts, but the values must not propagate outward.

Round 9 / A1 enforces this at two layers:

1. **worker rsync** (`scripts/orchestra/worker_runner.py:_rsync_to_controller`)
   — `--exclude=codex_sessions/*/workspace/privacy/` prevents the
   long-term run archive on the controller from ever receiving the
   env.env file.
2. **webui server** — defense-in-depth: any GET that resolves under
   raw ``codex_sessions/`` returns 404, even if somehow a Codex home
   transcript or privacy file did land in runs/ on the controller.

This test pins both.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def test_worker_runner_rsync_excludes_privacy_dir():
    """Round 9 / A1 (layer 1): worker's rsync argv carries the privacy
    exclude so the worker→controller transfer never moves env.env."""
    repo = Path(__file__).resolve().parents[2]
    src = _read(repo / "scripts" / "orchestra" / "worker_runner.py")
    assert "--exclude=codex_sessions/*/workspace/privacy/" in src, (
        "worker_runner._rsync_to_controller must pass "
        "--exclude=codex_sessions/*/workspace/privacy/ to rsync"
    )


def test_worker_runner_rsync_excludes_codex_home_caches():
    """2026-05-19 V5 disk audit regression guard.

    The Codex CLI's plugin marketplace pack file (~10 MB) and npm /
    package caches were being mirrored back to the controller per
    supervision cycle, ballooning large matrix runs by tens of GB.
    Pin the three exclude entries that strip that bloat at the
    worker→controller rsync boundary. Raw ``home/sessions/`` transcripts
    can contain supervisor-private context, so the public Trace surface uses
    sanitized ``agent_sessions/`` instead.
    """
    repo = Path(__file__).resolve().parents[2]
    src = _read(repo / "scripts" / "orchestra" / "worker_runner.py")
    for cache_dir in (".tmp", ".cache", ".npm"):
        needle = f"--exclude=codex_sessions/*/home/{cache_dir}/"
        assert needle in src, (
            f"worker_runner._rsync_to_controller must pass {needle} to rsync "
            f"(missing from {repo / 'scripts' / 'orchestra' / 'worker_runner.py'})"
        )
    assert "--exclude=codex_sessions/*/home/sessions/" in src, (
        "worker_runner._rsync_to_controller must not archive raw Codex "
        "home/sessions transcripts; public Trace uses sanitized agent_sessions/"
    )


def test_webui_translate_path_blocks_privacy_url():
    """Round 9 / A1 (layer 3): the webui rewrites any /runs/<...>/codex_sessions/
    <role>/workspace/privacy/* request to a non-existent path so
    SimpleHTTPRequestHandler returns 404.

    Drives `Handler.translate_path` directly with a synthetic request
    path and asserts the returned filesystem path is the sentinel
    'nonexistent' marker — meaning the file lookup will 404 even if
    the real privacy/env.env happens to exist on the controller.
    """
    from webui import server as webui_server

    # Synthesise a minimal Handler enough to call translate_path.
    class _FakeHandler:
        def __init__(self):
            pass
        translate_path = webui_server.Handler.translate_path

    h = _FakeHandler()
    sample_url = (
        "/runs/openclaw/some-model/101_a/task_x/p1-host-abc/"
        "codex_sessions/answer_supervisor/workspace/privacy/env.env"
    )
    resolved = h.translate_path(sample_url)
    assert "__nonexistent_privacy_blocked__" in resolved, (
        f"privacy URL must be rewritten to nonexistent sentinel, got {resolved!r}"
    )


def test_webui_translate_path_blocks_raw_codex_session_files():
    """Raw ``codex_sessions`` trees can include supervisor-private context.
    Public Trace uses sanitized ``agent_sessions`` instead."""
    from webui import server as webui_server

    class _FakeHandler:
        translate_path = webui_server.Handler.translate_path

    h = _FakeHandler()
    sample_url = (
        "/runs/openclaw/m/101_a/task_x/p1-host-abc/"
        "codex_sessions/answer_supervisor/workspace/visible/transcript.jsonl"
    )
    resolved = h.translate_path(sample_url)
    assert "__nonexistent_privacy_blocked__" in resolved, resolved


def test_webui_translate_path_blocks_static_traversal():
    """Static assets must not be able to escape webui/static via ../."""
    from webui import server as webui_server

    class _FakeHandler:
        translate_path = webui_server.Handler.translate_path

    h = _FakeHandler()
    for sample_url in ("/static/../../README.md", "/../../README.md"):
        resolved = h.translate_path(sample_url)
        assert "__nonexistent_static_blocked__" in resolved, resolved


def test_webui_translate_path_blocks_task_and_injection_privacy_assets():
    from webui import server as webui_server

    class _FakeHandler:
        translate_path = webui_server.Handler.translate_path

    h = _FakeHandler()
    blocked = (
        "/injection/101_skill_usage/task_x/privacy/env.env",
        "/injection/101_skill_usage/task_x/.privacy/credentials.env",
        "/tasks/101_skill_usage/.hidden.yaml",
    )
    for sample_url in blocked:
        resolved = h.translate_path(sample_url)
        assert "__nonexistent_privacy_blocked__" in resolved, resolved


def test_privacy_regex_matches_known_paths():
    """Pin the exact regex pattern so future refactors don't accidentally
    narrow / widen what counts as privacy.  The expected pattern is
    ``codex_sessions/<role>/workspace/privacy/...``."""
    from webui import server as webui_server

    matches = [
        "codex_sessions/answer_supervisor/workspace/privacy/env.env",
        "codex_sessions/public_user_simulator/workspace/privacy/something.txt",
        "openclaw/m/101_a/task_x/p1-h-1/codex_sessions/answer_supervisor/workspace/privacy/",
    ]
    nonmatches = [
        "codex_sessions/answer_supervisor/workspace/visible/transcript.jsonl",
        "codex_sessions/answer_supervisor/privacy/env.env",
        "privacy/env.env",
        "codex_sessions//workspace/privacy/env.env",
    ]
    for m in matches:
        assert webui_server._is_privacy_path(m), f"should be privacy: {m}"
    for n in nonmatches:
        assert not webui_server._is_privacy_path(n), f"should NOT be privacy: {n}"


def test_attempt_payload_known_readers_do_not_include_env_env():
    """Round 9 / A1 (defense-in-depth): the structured fields
    ``webui.attempt_payload`` reads (summary, score, transcript,
    supervision_trace, tool_usage, usage_ledger, etc.) do not include
    the raw env.env path — even if a privacy/env.env happened to land
    in the runs tree, the JSON returned to the client wouldn't surface
    it.

    Asserted by inspecting the source: ``attempt_payload`` doesn't read
    any path matching ``privacy/env.env``.
    """
    repo = Path(__file__).resolve().parents[2]
    src = _read(repo / "webui" / "server.py")
    # Find the attempt_payload function body. We don't want a strict
    # regex of the full source; we want to confirm there's no string
    # literal 'privacy/env.env' or 'env.env' (other than in the regex /
    # comments).
    body_start = src.find("def attempt_payload(")
    assert body_start != -1, "attempt_payload function not found"
    body_end = src.find("\ndef ", body_start + 1)
    body = src[body_start:body_end if body_end != -1 else None]
    # Strip comments to avoid false positives.
    code_lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("#")]
    body_code = "\n".join(code_lines)
    assert "env.env" not in body_code, (
        "attempt_payload must not directly read or reference env.env"
    )


def test_attempt_payload_file_listing_excludes_privacy_paths(tmp_path, monkeypatch):
    """Structured attempt payloads should not expose privacy filenames even
    if a stray privacy/env.env file exists under an archived attempt."""
    from webui import server as webui_server

    runs_root = tmp_path / "runs"
    task_dir = runs_root / "openclaw" / "gpt-5.4" / "101_skill_usage" / "task_x"
    attempt_dir = task_dir / "p1-host-primary"
    privacy_file = attempt_dir / "codex_sessions" / "answer_supervisor" / "workspace" / "privacy" / "env.env"
    bare_privacy_file = attempt_dir / "privacy" / "env.env"
    dot_privacy_file = attempt_dir / ".privacy" / "credentials.env"
    visible_file = attempt_dir / "codex_sessions" / "answer_supervisor" / "workspace" / "visible" / "transcript.jsonl"
    privacy_file.parent.mkdir(parents=True)
    bare_privacy_file.parent.mkdir(parents=True)
    dot_privacy_file.parent.mkdir(parents=True)
    visible_file.parent.mkdir(parents=True)
    privacy_file.write_text("SECRET=value\n", encoding="utf-8")
    bare_privacy_file.write_text("SECRET=value\n", encoding="utf-8")
    dot_privacy_file.write_text("SECRET=value\n", encoding="utf-8")
    visible_file.write_text('{"type":"note"}\n', encoding="utf-8")
    (attempt_dir / "score.json").write_text('{"overall_score": 1.0}', encoding="utf-8")
    (attempt_dir / "meta.json").write_text('{"model": "gpt-5.4"}', encoding="utf-8")
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "summary.json").write_text(
        (
            '{"taskId":"task_x","backend":"openclaw","model":"gpt-5.4",'
            '"attempts":[{"attempt":1,"outDir":"p1-host-primary"}],"resolvedAttempt":1}'
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(webui_server, "RUNS", runs_root)
    payload = webui_server.attempt_payload("openclaw/gpt-5.4/101_skill_usage/task_x")

    assert "error" not in payload
    files = payload["attemptFiles"]
    assert "codex_sessions/answer_supervisor/workspace/privacy/env.env" not in files
    assert "privacy/env.env" not in files
    assert ".privacy/credentials.env" not in files
    assert "codex_sessions/answer_supervisor/workspace/visible/transcript.jsonl" not in files


def test_attempt_payload_redacts_public_metadata(tmp_path, monkeypatch):
    """Trace JSON should keep UI/navigation data but not local config paths or
    provider/key-pool model identifiers."""
    from webui import server as webui_server

    runs_root = tmp_path / "runs"
    task_dir = runs_root / "openclaw" / "private-provider-gpt-5-4" / "101_skill_usage" / "task_x"
    attempt_dir = task_dir / "p1-host-primary"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "score.json").write_text('{"overall_score": 1.0}', encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (attempt_dir / "meta.json").write_text(
        json.dumps(
            {
                "model": "private-provider/gpt-5.4",
                "imageModel": "private-provider/gpt-5.4",
                "taskFile": "/root/private/tasks/task_x.yaml",
                "settingRoot": "/root/private/runs/openclaw/private-provider-gpt-5-4",
                "supervision": {
                    "supervisor": {
                        "provider": "private-provider",
                        "model": "private-provider/gpt-5.4",
                        "config": "configs/codex.local.toml",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_x",
                "backend": "openclaw",
                "model": "private-provider/gpt-5.4",
                "imageModel": "private-provider/gpt-5.4",
                "modelSlug": "private-provider-gpt-5-4",
                "taskFile": "/root/private/tasks/task_x.yaml",
                "settingRoot": "/root/private/runs/openclaw/private-provider-gpt-5-4",
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
                "resolvedAttempt": 1,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(webui_server, "RUNS", runs_root)
    payload = webui_server.attempt_payload("openclaw/private-provider-gpt-5-4/101_skill_usage/task_x")
    encoded = json.dumps(payload)

    assert payload["taskSummary"]["model"] == "gpt-5.4"
    assert payload["taskSummary"]["modelSlug"] == "gpt-5.4"
    assert payload["meta"]["model"] == "gpt-5.4"
    assert payload["supervision"]["supervisor"]["model"] == "gpt-5.4"
    assert "/root/private" not in encoded
    assert "codex.local.toml" not in encoded


def test_public_sanitizer_preserves_trace_route_paths_and_urls():
    """Static Trace needs routable paths, but display metadata stays redacted."""
    from webui import server as webui_server

    raw = {
        "relPath": "openclaw/private-provider-gpt-5-4/101_skill_usage/task_x",
        "summaryPath": "openclaw/private-provider-gpt-5-4/101_skill_usage/task_x",
        "selectedAttemptPath": (
            "openclaw/private-provider-gpt-5-4/101_skill_usage/task_x/p1-host"
        ),
        "attemptCards": [
            {
                "attemptPath": (
                    "openclaw/private-provider-gpt-5-4/101_skill_usage/task_x/p1-host"
                )
            }
        ],
        "resultFiles": [
            {
                "url": (
                    "/runs/openclaw/private-provider-gpt-5-4/101_skill_usage/"
                    "task_x/p1-host/result/answer.md"
                )
            }
        ],
        "meta": {
            "model": "private-provider/gpt-5.4",
            "taskFile": "/Users/example/private/tasks/task_x.yaml",
        },
    }

    payload = webui_server.sanitize_public_payload(raw)
    encoded = json.dumps(payload)

    assert payload["relPath"] == raw["relPath"]
    assert payload["summaryPath"] == raw["summaryPath"]
    assert payload["selectedAttemptPath"] == raw["selectedAttemptPath"]
    assert payload["attemptCards"][0]["attemptPath"] == raw["attemptCards"][0]["attemptPath"]
    assert payload["resultFiles"][0]["url"] == raw["resultFiles"][0]["url"]
    assert payload["meta"]["model"] == "gpt-5.4"
    assert "/Users/example" not in encoded
    assert "private/tasks" not in encoded


def test_attempt_payload_rejects_filtered_public_rows(tmp_path, monkeypatch):
    """Knowing a raw run path must not bypass the public WebUI result filter."""
    from webui import server as webui_server

    runs_root = tmp_path / "runs"

    def write_run(backend: str, model_dir: str, category: str, task_id: str) -> str:
        task_dir = runs_root / backend / model_dir / category / task_id
        attempt_dir = task_dir / "p1-host-primary"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "score.json").write_text('{"overall_score": 1.0}', encoding="utf-8")
        (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
        (attempt_dir / "meta.json").write_text(
            json.dumps({"model": model_dir.replace("-", ".")}),
            encoding="utf-8",
        )
        (task_dir / "summary.json").write_text(
            json.dumps(
                {
                    "taskId": task_id,
                    "backend": backend,
                    "model": model_dir,
                    "modelSlug": model_dir,
                    "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
                    "resolvedAttempt": 1,
                }
            ),
            encoding="utf-8",
        )
        return f"{backend}/{model_dir}/{category}/{task_id}"

    filtered_gemini = write_run(
        "nanobot",
        "provider-all-new-gemini-3-1-pro-preview",
        "101_skill_usage",
        "task_filtered_gemini",
    )
    filtered_smoke = write_run(
        "openclaw",
        "proxy-example-gpt-5-4",
        "001_smoketest",
        "task_filtered_smoke",
    )
    public_run = write_run(
        "openclaw",
        "proxy-example-gpt-5-4",
        "101_skill_usage",
        "task_public",
    )

    monkeypatch.setattr(webui_server, "RUNS", runs_root)

    assert webui_server.attempt_payload(filtered_gemini) == {"error": "run path not found"}
    assert webui_server.attempt_payload(filtered_smoke) == {"error": "run path not found"}
    assert "error" not in webui_server.attempt_payload(public_run)


def test_attempt_payload_does_not_publish_debug_supervision_artifacts(tmp_path, monkeypatch):
    from webui import server as webui_server

    runs_root = tmp_path / "runs"
    task_dir = runs_root / "openclaw" / "private-provider-gpt-5-4" / "101_skill_usage" / "task_x"
    attempt_dir = task_dir / "p1-host-primary"
    cycle_dir = attempt_dir / "supervision" / "cycle_00"
    cycle_dir.mkdir(parents=True)
    (attempt_dir / "score.json").write_text('{"overall_score": 1.0}', encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (attempt_dir / "meta.json").write_text('{"model":"private-provider/gpt-5.4"}', encoding="utf-8")
    (cycle_dir / "answer_supervisor_prompt.txt").write_text("hidden prompt", encoding="utf-8")
    (cycle_dir / "answer_supervisor_input_workspace.json").write_text('{"hidden": true}', encoding="utf-8")
    (cycle_dir / "answer_supervisor_response.txt").write_text("hidden response", encoding="utf-8")
    (cycle_dir / "decision.json").write_text('{"verdict":"pass"}', encoding="utf-8")
    (attempt_dir / "supervision_trace.jsonl").write_text(
        '{"evaluation_index":0,"components":{"answer_supervisor":{"prompt":"inline hidden prompt","input_workspace":{"secret":true},"verdict":"pass"}}}\n',
        encoding="utf-8",
    )
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_x",
                "backend": "openclaw",
                "model": "private-provider/gpt-5.4",
                "modelSlug": "private-provider-gpt-5-4",
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
                "resolvedAttempt": 1,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(webui_server, "RUNS", runs_root)
    payload = webui_server.attempt_payload("openclaw/private-provider-gpt-5-4/101_skill_usage/task_x")
    encoded = json.dumps(payload)

    assert "hidden prompt" not in encoded
    assert "hidden response" not in encoded
    assert "input_workspace" not in encoded
    artifact_paths = {item.get("path") for item in payload.get("supervisionArtifacts", [])}
    assert "supervision/cycle_00/decision.json" not in artifact_paths
    assert "supervision/cycle_00/answer_supervisor_prompt.txt" not in artifact_paths
    assert "outDir" not in encoded


def test_task_detail_reports_privacy_count_not_names(tmp_path, monkeypatch):
    from webui import aggregate as webui_aggregate

    tasks_root = tmp_path / "tasks"
    injection_root = tmp_path / "injection"
    category = "101_skill_usage"
    task_id = "task_private"
    task_dir = tasks_root / category
    task_dir.mkdir(parents=True)
    (task_dir / f"{task_id}.yaml").write_text(
        "\n".join(
            [
                f"task_id: {task_id}",
                f"category: {category}",
                "agent_sys: openclaw",
                "agent_id: main",
                "model: gpt-5.4",
                "image_model: gpt-5.4",
                "timeout_seconds: 1200",
                "max_total_seconds: 1800",
                "success_threshold: 0.9",
                "recording: none",
                "headed: auto",
                "task: Demo",
            ]
        ),
        encoding="utf-8",
    )
    privacy_dir = injection_root / category / task_id
    privacy_dir.mkdir(parents=True)
    (privacy_dir / ".privacy").write_text("EMAIL_PASSWORD\nAPI_TOKEN\n", encoding="utf-8")

    monkeypatch.setattr(webui_aggregate, "TASKS", tasks_root)
    monkeypatch.setattr(webui_aggregate, "INJECTION", injection_root)
    payload = webui_aggregate.task_detail(task_id)
    encoded = json.dumps(payload)

    assert payload["assets"]["privacy"] == {"present": True, "count": 2}
    assert "EMAIL_PASSWORD" not in encoded
    assert "API_TOKEN" not in encoded


def test_task_detail_hides_eval_rule_and_references_by_default(tmp_path, monkeypatch):
    from webui import aggregate as webui_aggregate

    tasks_root = tmp_path / "tasks"
    injection_root = tmp_path / "injection"
    category = "101_skill_usage"
    task_id = "task_hidden_refs"
    task_dir = tasks_root / category
    task_dir.mkdir(parents=True)
    (task_dir / f"{task_id}.yaml").write_text(
        "\n".join(
            [
                f"task_id: {task_id}",
                f"category: {category}",
                "agent_sys: openclaw",
                "model: gpt-5.4",
                "references:",
                "  - references/eval_rule.md",
                "task: Demo prompt",
            ]
        ),
        encoding="utf-8",
    )
    refs = injection_root / category / task_id / "references"
    refs.mkdir(parents=True)
    (refs / "eval_rule.md").write_text("PRIVATE RUBRIC", encoding="utf-8")
    (refs / "ground_truth.json").write_text('{"answer":"SECRET"}', encoding="utf-8")

    monkeypatch.setattr(webui_aggregate, "TASKS", tasks_root)
    monkeypatch.setattr(webui_aggregate, "INJECTION", injection_root)
    monkeypatch.delenv("CLAWBENCH_WEBUI_EXPOSE_HIDDEN_REFERENCES", raising=False)

    payload = webui_aggregate.task_detail(task_id)
    encoded = json.dumps(payload)

    assert payload["eval_rule_md"] == ""
    assert payload["assets"]["references"] is None
    assert "references" not in payload["task_yaml"]
    assert "PRIVATE RUBRIC" not in encoded
    assert "ground_truth" not in encoded
    assert "SECRET" not in encoded

    monkeypatch.setenv("CLAWBENCH_WEBUI_EXPOSE_HIDDEN_REFERENCES", "1")
    exposed = webui_aggregate.task_detail(task_id)
    assert exposed["eval_rule_md"] == "PRIVATE RUBRIC"
    assert isinstance(exposed["assets"]["references"], list)
    assert "references" in exposed["task_yaml"]


def test_task_detail_includes_deep_public_assets_but_not_privacy(tmp_path, monkeypatch):
    from webui import aggregate as webui_aggregate

    tasks_root = tmp_path / "tasks"
    injection_root = tmp_path / "injection"
    category = "101_skill_usage"
    task_id = "task_deep_assets"
    task_dir = tasks_root / category
    task_dir.mkdir(parents=True)
    (task_dir / f"{task_id}.yaml").write_text(
        "\n".join(
            [
                f"task_id: {task_id}",
                f"category: {category}",
                "agent_sys: openclaw",
                "model: gpt-5.4",
                "image_model: gpt-5.4",
                "task: Demo",
            ]
        ),
        encoding="utf-8",
    )
    root = injection_root / category / task_id
    deep_file = root / "sources" / "a" / "b" / "c" / "d" / "e" / "visible.txt"
    deep_file.parent.mkdir(parents=True)
    deep_file.write_text("visible", encoding="utf-8")
    privacy_file = root / "sources" / "privacy" / "env.env"
    privacy_file.parent.mkdir(parents=True)
    privacy_file.write_text("SECRET=value", encoding="utf-8")

    monkeypatch.setattr(webui_aggregate, "TASKS", tasks_root)
    monkeypatch.setattr(webui_aggregate, "INJECTION", injection_root)

    payload = webui_aggregate.task_detail(task_id)
    encoded = json.dumps(payload)

    assert "visible.txt" in encoded
    assert "a/b/c/d/e/visible.txt" in encoded
    assert "env.env" not in encoded
    assert "SECRET=value" not in encoded


def test_attempt_file_privacy_filter_matches_static_export_rules():
    from webui import server as webui_server

    for private_rel in (
        "codex_sessions/answer_supervisor/workspace/privacy/env.env",
        "codex_sessions/answer_supervisor/privacy/env.env",
        "privacy/env.env",
        ".privacy/credentials.env",
        "visible/env.env",
    ):
        assert webui_server._is_private_attempt_file_rel(private_rel), private_rel
    assert not webui_server._is_public_run_artifact_rel(
        "codex_sessions/answer_supervisor/workspace/visible/transcript.jsonl"
    )


def test_public_run_artifact_filter_blocks_raw_debug_files():
    from webui import server as webui_server

    assert webui_server._is_public_run_artifact_rel("openclaw/model/cat/task/p1/result/answer.md")
    assert webui_server._is_public_run_artifact_rel("openclaw/model/cat/task/p1/mcp_artifacts/screenshot.png")
    assert webui_server._is_public_run_artifact_rel(
        "openclaw/model/cat/task/p1/result/help_channel_dump_05_25_23.json"
    )
    for private_rel in (
        "openclaw/model/cat/task/p1/meta.json",
        "openclaw/model/cat/task/p1/transcript.jsonl",
        "openclaw/model/cat/task/p1/mcp_artifacts/window_grab_raw.json",
        "openclaw/model/cat/task/p1/mcp_artifacts/dom_snapshot.json",
        "openclaw/model/cat/task/p1/supervision/decision.json",
        "openclaw/model/cat/task/p1/supervision/cycle_00/answer_supervisor_decision.json",
        "openclaw/model/cat/task/p1/supervision/cycle_00/answer_supervisor_summary.md",
        "openclaw/model/cat/task/p1/logs/agent.log",
        "openclaw/model/cat/task/p1/codex_sessions/answer_supervisor/workspace/visible/transcript.jsonl",
        "openclaw/model/cat/task/p1/codex_sessions/answer_supervisor/workspace/privacy/env.env",
    ):
        assert not webui_server._is_public_run_artifact_rel(private_rel), private_rel


def test_supervision_artifacts_hide_raw_text_and_json(tmp_path):
    from webui import server as webui_server

    runs_root = tmp_path / "runs"
    attempt_dir = runs_root / "openclaw" / "gpt-5.4" / "101_demo" / "task_x" / "p1-host"
    cycle = attempt_dir / "supervision" / "cycle_00"
    cycle.mkdir(parents=True)
    (cycle / "answer_supervisor_decision.json").write_text(
        '{"rationale":"references/eval_rule.md"}',
        encoding="utf-8",
    )
    (cycle / "answer_supervisor_summary.md").write_text("hidden rubric quote", encoding="utf-8")
    (cycle / "recording.mp4").write_bytes(b"mp4")
    (cycle / "screenshot.png").write_bytes(b"png")

    old_runs = webui_server.RUNS
    webui_server.RUNS = runs_root
    try:
        items = webui_server.supervision_artifacts(attempt_dir)
    finally:
        webui_server.RUNS = old_runs
    encoded = json.dumps(items)

    assert "answer_supervisor_decision.json" not in encoded
    assert "answer_supervisor_summary.md" not in encoded
    assert "eval_rule.md" not in encoded
    assert "hidden rubric quote" not in encoded
    assert "recording.mp4" in encoded
    assert "screenshot.png" in encoded
