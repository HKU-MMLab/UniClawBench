from __future__ import annotations

import json
from pathlib import Path

from webui import aggregate, server
from webui.export_static import (
    EXPORT_MARKER,
    STATIC_EXPORT_SCHEMA,
    _filter_payload_to_selected_attempt,
    _build_index_html,
    _attempt_detail_path,
    _packed_runs_payload,
    _public_run_path,
    _public_trace_path,
    export,
    _rewrite_static_urls,
    _prepare_output_dir,
    _slim_aggregate,
    _static_asset_rel_for_url,
)


def test_slim_aggregate_ships_results_only_schema() -> None:
    slim = _slim_aggregate(
        {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "proxy-example-gpt-5-4",
                    "model_label": "proxy-example/gpt-5.4",
                    "category": "101_skill_usage",
                    "task_id": "task_101_01_demo",
                    "score": 1.0,
                }
            ],
            "models": [{"key": "should-not-ship"}],
            "backends": [{"key": "should-not-ship"}],
            "model_backend_pairs": [{"key": "should-not-ship"}],
            "task_backends": {"101_skill_usage::task_101_01_demo": ["openclaw"]},
            "categories": ["101_skill_usage", "102_exploration"],
        }
    )

    assert slim["schema"] == STATIC_EXPORT_SCHEMA
    assert slim["task_count"] == 1
    assert slim["all_backends"] == ["openclaw"]
    assert slim["categories"] == ["101_skill_usage", "102_exploration"]
    assert slim["model_labels"] == {"openclaw::gpt-5.4": "gpt-5.4"}
    assert slim["rows"] == [
        {
            "backend": "openclaw",
            "model_slug": "gpt-5.4",
            "category": "101_skill_usage",
            "task_id": "task_101_01_demo",
            "score": 1.0,
        }
    ]
    assert "models" not in slim
    assert "backends" not in slim
    assert "model_backend_pairs" not in slim
    assert "task_backends" not in slim


def test_slim_aggregate_scopes_labels_by_backend() -> None:
    slim = _slim_aggregate(
        {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "shared-model",
                    "model_label": "provider-a/shared.model",
                    "category": "101_skill_usage",
                    "task_id": "task_101_01_demo",
                },
                {
                    "backend": "nanobot",
                    "model_slug": "shared-model",
                    "model_label": "provider-b/shared.model",
                    "category": "101_skill_usage",
                    "task_id": "task_101_01_demo",
                },
            ],
        }
    )

    assert slim["model_labels"] == {
        "openclaw::shared.model": "shared.model",
        "nanobot::shared.model": "shared.model",
    }


def test_packed_runs_payload_uses_trace_sidebar_fields() -> None:
    payload = _packed_runs_payload(
        [
            {
                "category": "101_skill_usage",
                "taskId": "task_101_01_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "provider-model-a",
                "settingKey": "not-needed",
                "summaryPath": "openclaw/provider-model-a/101_skill_usage/task_101_01_demo",
                "selectedAttemptPath": "not-needed",
                "finalScore": 1.0,
                "rawFinalScore": 1.0,
                "passed": True,
                "finalStatus": "pass",
                "resolvedAttempt": 1,
                "checkpointCounts": {"total": 3},
                "continuationCount": 2,
                "supervisionCycleCount": 4,
                "supervisionVerdict": "pass",
                "createdAt": 123,
                "runtimeMs": 456,
            }
        ]
    )

    assert payload["schema"] == STATIC_EXPORT_SCHEMA
    assert payload["kind"] == "runs_packed"
    assert "summaryPath" in payload["fields"]
    assert "selectedAttemptPath" in payload["fields"]
    assert "checkpointCounts" in payload["fields"]
    row = dict(zip(payload["fields"], payload["runs"][0]))
    assert row["taskId"] == "task_101_01_demo"
    assert row["summaryPath"] == "openclaw/provider-model-a/101_skill_usage/task_101_01_demo"
    assert row["runtimeMs"] == 456
    assert row["selectedAttemptPath"] == "not-needed"
    assert row["checkpointCounts"] == {"total": 3}


def test_static_index_exposes_all_pages() -> None:
    html = _build_index_html()
    assert "UniClawBench" in html
    assert "window.CLAWBENCH_STATIC_DATA" in html
    assert "window.CLAWBENCH_STATIC_TASKS" in html
    assert "window.CLAWBENCH_STATIC_RUNS" in html
    assert "window.CLAWBENCH_STATIC_ATTEMPTS_BASE" in html
    assert 'href="#/home"' in html
    assert 'href="#/demo"' not in html
    assert 'href="#/leaderboard/model"' in html
    assert 'href="#/tasks"' in html
    assert 'href="#/trace"' in html
    assert 'window.location.hash = "#/home"' not in html
    assert 'src="static/main.js' in html


def test_static_frontend_does_not_enable_same_origin_scripts_in_iframes() -> None:
    root = Path("webui/static")
    joined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.rglob("*.js")
        if "vendor" not in path.parts
    )
    assert "allow-scripts allow-same-origin" not in joined


def test_static_url_rewrite_makes_export_relative() -> None:
    payload = {
        "resultFiles": [{"url": "/runs/openclaw/model/101/task/result.txt"}],
        "assets": {"references": [{"url": "/injection/101/task/references/eval_rule.md"}]},
        "plain": "/api/runs",
    }

    rewritten = _rewrite_static_urls(payload)

    assert rewritten["resultFiles"][0]["url"].startswith("artifacts/")
    assert rewritten["resultFiles"][0]["url"].endswith("/result.txt")
    assert rewritten["assets"] == {"references": [{"url": "injection/101/task/references/eval_rule.md"}]}
    assert rewritten["plain"] == "/api/runs"


def test_static_url_rewrite_can_target_remote_asset_base() -> None:
    payload = {
        "resultFiles": [{"url": "/runs/openclaw/model/101/task/result.txt"}],
        "assets": {"references": [{"url": "/injection/101/task/references/eval_rule.md"}]},
        "task": "/tasks/101/task.yaml",
    }

    rewritten = _rewrite_static_urls(payload, asset_base_url="https://assets.example/u", asset_mode="full")

    assert rewritten["resultFiles"][0]["url"].startswith("https://assets.example/u/artifacts/")
    assert rewritten["assets"] == {"references": [{"url": "https://assets.example/u/injection/101/task/references/eval_rule.md"}]}
    assert rewritten["task"] == "tasks/101/task.yaml"


def test_export_can_split_large_static_assets_for_r2(tmp_path, monkeypatch) -> None:
    import webui.export_static as export_static

    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "passed": True,
                "finalScore": 1.0,
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "runtimeMs": 10}],
            }
        ),
        encoding="utf-8",
    )
    injection_file = tmp_path / "injection" / "101_demo" / "task_demo" / "sources" / "brief.txt"
    injection_file.parent.mkdir(parents=True)
    injection_file.write_text("brief", encoding="utf-8")

    monkeypatch.setattr(export_static, "ROOT", tmp_path)
    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "model-a",
                    "model_label": "provider/model.a",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "passed": True,
                }
            ],
            "models": [{"model_slug": "model-a"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [{"task_id": "task_demo", "category": "101_demo"}])
    monkeypatch.setattr(
        aggregate,
        "task_detail",
        lambda task_id, **_: {
            "task_id": task_id,
            "category": "101_demo",
            "prompt": "demo",
            "assets": {"sources": [{"url": "/injection/101_demo/task_demo/sources/brief.txt"}]},
        },
    )

    out = tmp_path / "site"
    asset_out = tmp_path / "r2"
    summary = export(
        runs,
        out,
        asset_out=asset_out,
        asset_base_url="https://assets.example/u",
        asset_mode="lite",
    )

    assert summary["asset_out"] == asset_out
    assert not (out / "attempts").exists()
    assert (asset_out / _attempt_detail_path("openclaw/model-a/101_demo/task_demo")).exists()
    assert (asset_out / "injection" / "101_demo" / "task_demo" / "sources" / "brief.txt").exists()
    index_html = (out / "index.html").read_text(encoding="utf-8")
    assert 'window.CLAWBENCH_STATIC_ATTEMPTS_BASE = "https://assets.example/u/attempts"' in index_html
    detail = json.loads((out / "task-details" / "task_demo.json").read_text(encoding="utf-8"))
    assert detail["assets"]["sources"][0]["url"] == "https://assets.example/u/injection/101_demo/task_demo/sources/brief.txt"
    manifest = json.loads((out / "asset-manifest.json").read_text(encoding="utf-8"))
    assert manifest["asset_split"] is True
    assert manifest["asset_base_url"] == "https://assets.example/u"
    assert "asset_out" not in manifest
    assert str(asset_out) not in json.dumps(manifest)


def test_static_run_artifact_url_uses_safe_public_filename() -> None:
    rel = _static_asset_rel_for_url('/runs/model/task/result/weird "x<y>.html?download=1')
    assert rel.startswith("artifacts/")
    assert rel.endswith(".html")
    assert " " not in rel
    assert '"' not in rel
    assert "<" not in rel
    assert ">" not in rel


def test_dynamic_run_url_percent_encodes_path_segments(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "RUNS", tmp_path)
    artifact = tmp_path / "model name" / 'result "quote".txt'
    artifact.parent.mkdir(parents=True)
    artifact.write_text("ok", encoding="utf-8")

    assert server.run_url(artifact) == "/runs/model%20name/result%20%22quote%22.txt"


def test_prepare_output_refuses_unmarked_nonempty_directory(tmp_path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    out = tmp_path / "site"
    out.mkdir()
    (out / "keep.txt").write_text("not an export", encoding="utf-8")

    try:
        _prepare_output_dir(runs, out)
    except ValueError as exc:
        assert "refusing to delete non-export directory" in str(exc)
    else:  # pragma: no cover - defensive assertion shape
        raise AssertionError("expected ValueError")


def test_prepare_output_allows_marked_export_directory(tmp_path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    out = tmp_path / "site"
    out.mkdir()
    (out / EXPORT_MARKER).write_text("old export", encoding="utf-8")
    (out / "old.txt").write_text("remove me", encoding="utf-8")

    _prepare_output_dir(runs, out)

    assert (out / EXPORT_MARKER).exists()
    assert not (out / "old.txt").exists()


def test_prepare_output_resume_keeps_marked_export_directory(tmp_path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    out = tmp_path / "site"
    out.mkdir()
    (out / EXPORT_MARKER).write_text("old export", encoding="utf-8")
    keep = out / "keep.txt"
    keep.write_text("reuse me", encoding="utf-8")

    _prepare_output_dir(runs, out, resume=True)

    assert (out / EXPORT_MARKER).exists()
    assert keep.read_text(encoding="utf-8") == "reuse me"


def test_export_writes_task_and_attempt_trace_payloads(tmp_path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    p1 = task_dir / "p1-host-a"
    p2 = task_dir / "p2-host-a"
    for attempt_dir in (p1, p2):
        (attempt_dir / "result").mkdir(parents=True)
        (attempt_dir / "result" / "answer.md").write_text("# answer\n", encoding="utf-8")
        (attempt_dir / "result" / "help_channel_dump_05_25_23.json").write_text(
            json.dumps({"ok": True}),
            encoding="utf-8",
        )
        (attempt_dir / "result" / "venv_fig2" / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
        (
            attempt_dir
            / "result"
            / "venv_fig2"
            / "lib"
            / "python3.12"
            / "site-packages"
            / "bulk.py"
        ).write_text("not a benchmark artifact\n", encoding="utf-8")
        (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
        (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
        (attempt_dir / "transcript.jsonl").write_text(
            json.dumps({"type": "message", "role": "assistant", "content": "ok"}) + "\n",
            encoding="utf-8",
        )
    (p1 / "runtime_probe_desktop.png").write_bytes(b"png")
    (p1 / "recording.mp4").write_bytes(b"mp4")
    (p1 / "mcp_artifacts").mkdir()
    (p1 / "mcp_artifacts" / "screenshot.png").write_bytes(b"png")
    (p1 / "mcp_artifacts" / "window_grab_raw.json").write_text(
        json.dumps({"provider": "private_provider_secret", "path": "/Users/example/private"}),
        encoding="utf-8",
    )
    (p1 / "timeline.json").write_text("", encoding="utf-8")
    (p1 / "supervision" / "cycle_00").mkdir(parents=True)
    (p1 / "supervision" / "cycle_00" / "recording.mp4").write_bytes(b"cycle-mp4")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "finalScore": 1.0,
                "passed": True,
                "resolvedAttempt": 2,
                "attempts": [
                    {"attempt": 1, "outDir": str(p1), "runtimeMs": 10},
                    {"attempt": 2, "outDir": str(p2), "runtimeMs": 20},
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "model-a",
                    "model_label": "provider/model.a",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "model-a"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [{"task_id": "task_demo", "category": "101_demo"}])
    monkeypatch.setattr(
        aggregate,
        "task_detail",
        lambda task_id, **_: {
            "task_id": task_id,
            "category": "101_demo",
            "prompt": "demo",
            "eval_rule_md": "ok",
            "assets": {},
        },
    )

    out = tmp_path / "site"
    summary = export(runs, out, trace_detail_policy="all-attempts")

    assert summary["rows"] == 1
    assert (out / "results.json").exists()
    assert (out / "tasks.json").exists()
    assert (out / "task-details" / "task_demo.json").exists()
    assert (out / "runs.json").exists()

    task_rel = "openclaw/model-a/101_demo/task_demo"
    p1_rel = f"{task_rel}/p1-host-a"
    p2_rel = f"{task_rel}/p2-host-a"
    public_task_rel = _public_trace_path(task_rel)
    public_p1_rel = _public_trace_path(p1_rel)
    public_p2_rel = _public_trace_path(p2_rel)
    runs_index = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    runs_row = dict(zip(runs_index["fields"], runs_index["runs"][0]))
    assert runs_row["summaryPath"] == _public_run_path(task_rel)
    assert runs_row["selectedAttemptPath"] == public_p2_rel
    assert "provider/" not in json.dumps(runs_index)
    assert (out / _attempt_detail_path(task_rel)).exists()
    assert (out / _attempt_detail_path(p1_rel)).exists()
    assert (out / _attempt_detail_path(p2_rel)).exists()

    p1_payload = json.loads((out / _attempt_detail_path(p1_rel)).read_text(encoding="utf-8"))
    p2_payload = json.loads((out / _attempt_detail_path(p2_rel)).read_text(encoding="utf-8"))
    task_payload = json.loads((out / _attempt_detail_path(task_rel)).read_text(encoding="utf-8"))
    assert len(task_payload["attemptDetails"]) == 2
    assert len(p1_payload["attemptDetails"]) == 1
    assert p1_payload["relPath"] == public_task_rel
    assert p1_payload["attemptDetails"][0]["attemptPath"] == public_p1_rel
    assert "transcript" not in p1_payload
    assert "logs" not in p1_payload
    assert p1_payload["selectedAttemptPath"] == public_p1_rel
    assert p2_payload["selectedAttemptPath"] == public_p2_rel
    assert all("outDir" not in detail for detail in p1_payload["attemptDetails"])
    assert [item["path"] for item in p1_payload["resultFiles"]] == [
        "answer.md",
        "help_channel_dump_05_25_23.json",
    ]
    assert all("text" not in item for item in p1_payload["resultFiles"])
    assert [item["path"] for item in p1_payload["mcpArtifacts"]] == ["mcp_artifacts/screenshot.png"]
    assert "window_grab_raw" not in json.dumps(p1_payload)
    assert "private_provider_secret" not in json.dumps(p1_payload)
    assert "/Users/example" not in json.dumps(p1_payload)
    assert p1_payload["recording"]["url"].startswith("artifacts/")
    assert p1_payload["recording"]["url"].endswith("/recording.mp4")
    assert p1_payload["recording"]["poster"].startswith("artifacts/")
    assert p1_payload["recording"]["poster"].endswith("/runtime_probe_desktop.png")

    assert (out / p1_payload["resultFiles"][0]["url"]).exists()
    assert (out / p1_payload["resultFiles"][1]["url"]).exists()
    assert not any(path.name == "bulk.py" for path in (out / "artifacts").rglob("*"))
    assert not any(path.name == "window_grab_raw.json" for path in (out / "artifacts").rglob("*"))
    assert any(path.name == "screenshot.png" for path in (out / "artifacts").rglob("*"))
    assert (out / p1_payload["recording"]["url"]).exists()
    assert (out / p1_payload["recording"]["poster"]).exists()
    cycle_recording = p1_payload["recordingsByCycle"]["0"]["url"]
    assert cycle_recording.startswith("artifacts/")
    assert (out / cycle_recording).exists()


def test_export_defaults_to_selected_attempt_only(tmp_path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    p1 = task_dir / "p1-host-a"
    p2 = task_dir / "p2-host-a"
    for attempt_dir, score in ((p1, 0.1), (p2, 1.0)):
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
        (attempt_dir / "score.json").write_text(json.dumps({"overall_score": score}), encoding="utf-8")
        (attempt_dir / "transcript.jsonl").write_text(
            json.dumps({"type": "message", "role": "assistant", "content": attempt_dir.name}) + "\n",
            encoding="utf-8",
        )
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "finalScore": 1.0,
                "resolvedAttempt": 2,
                "attempts": [
                    {"attempt": 1, "outDir": str(p1), "runtimeMs": 10},
                    {"attempt": 2, "outDir": str(p2), "runtimeMs": 20},
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "model-a",
                    "model_label": "provider/model.a",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "model-a"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [])

    out = tmp_path / "site"
    summary = export(runs, out)

    assert summary["trace_detail_policy"] == "selected"
    task_rel = "openclaw/model-a/101_demo/task_demo"
    p1_rel = f"{task_rel}/p1-host-a"
    p2_rel = f"{task_rel}/p2-host-a"
    payload = json.loads((out / _attempt_detail_path(task_rel)).read_text(encoding="utf-8"))
    assert (out / _attempt_detail_path(task_rel)).exists()
    assert not (out / _attempt_detail_path(p1_rel)).exists()
    assert not (out / _attempt_detail_path(p2_rel)).exists()
    assert payload["staticTracePolicy"] == "selected"
    assert payload["omittedAttemptCount"] == 1
    assert payload["selectedAttemptPath"] == _public_trace_path(p2_rel)
    assert [card["attemptPath"] for card in payload["attemptCards"]] == [_public_trace_path(p2_rel)]
    assert [detail["attemptPath"] for detail in payload["attemptDetails"]] == [_public_trace_path(p2_rel)]


def test_filter_payload_to_selected_attempt_keeps_only_selected_card_and_detail() -> None:
    payload = {
        "selectedAttemptPath": "run/p2-host",
        "attemptCards": [
            {"attemptPath": "run/p1-host", "attempt": 1},
            {"attemptPath": "run/p2-host", "attempt": 2},
        ],
        "attemptDetails": [
            {"attemptPath": "run/p1-host", "attempt": 1},
            {"attemptPath": "run/p2-host", "attempt": 2},
        ],
    }

    _filter_payload_to_selected_attempt(payload)

    assert payload["staticTracePolicy"] == "selected"
    assert payload["omittedAttemptCount"] == 1
    assert payload["attemptCards"] == [{"attemptPath": "run/p2-host", "attempt": 2}]
    assert payload["attemptDetails"] == [{"attemptPath": "run/p2-host", "attempt": 2}]


def test_lite_export_keeps_trace_text_without_run_artifact_links(tmp_path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    result_dir = attempt_dir / "result"
    result_dir.mkdir(parents=True)
    (result_dir / "answer.md").write_text("# answer\n", encoding="utf-8")
    (result_dir / "chart.png").write_bytes(b"png")
    (attempt_dir / "runtime_probe_desktop.png").write_bytes(b"poster")
    (attempt_dir / "recording.mp4").write_bytes(b"mp4")
    (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text(
        json.dumps({"type": "message", "role": "assistant", "content": "ok"}) + "\n",
        encoding="utf-8",
    )
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "finalScore": 1.0,
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "runtimeMs": 10}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "model-a",
                    "model_label": "provider/model.a",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "model-a"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [])

    out = tmp_path / "site"
    summary = export(runs, out, asset_mode="lite")

    assert summary["asset_mode"] == "lite"
    assert summary["asset_count"] == 0
    assert not (out / "artifacts").exists()

    rel = "openclaw/model-a/101_demo/task_demo"
    payload = json.loads((out / _attempt_detail_path(rel)).read_text(encoding="utf-8"))
    assert payload["staticAssetMode"] == "lite"
    answer = next(item for item in payload["resultFiles"] if item["path"] == "answer.md")
    chart = next(item for item in payload["resultFiles"] if item["path"] == "chart.png")
    assert answer["text"] == "# answer\n"
    assert "url" not in answer
    assert answer["assetSkipped"] is True
    assert "url" not in chart
    assert chart["assetSkipped"] is True
    assert "url" not in payload["recording"]
    assert "poster" not in payload["recording"]
    assert payload["recording"]["assetSkipped"] is True


def test_lite_resume_removes_stale_full_export_artifacts(tmp_path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "model-a",
                    "model_label": "provider/model.a",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "model-a"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [])

    out = tmp_path / "site"
    stale = out / "artifacts" / "old" / "recording.mp4"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old full export")
    (out / EXPORT_MARKER).write_text("old export", encoding="utf-8")

    export(runs, out, resume=True, asset_mode="lite")

    assert not (out / "artifacts").exists()


def test_attempt_payload_accepts_symlinked_runs_view(tmp_path) -> None:
    real_runs = tmp_path / "real-runs"
    task_dir = real_runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
            }
        ),
        encoding="utf-8",
    )

    view_runs = tmp_path / "view-runs"
    view_parent = view_runs / "openclaw" / "model-a" / "101_demo"
    view_parent.mkdir(parents=True)
    (view_parent / "task_demo").symlink_to(task_dir, target_is_directory=True)

    old_runs = server.RUNS
    try:
        server.RUNS = view_runs
        payload = server.attempt_payload("openclaw/model-a/101_demo/task_demo")
    finally:
        server.RUNS = old_runs

    assert payload["relPath"] == "openclaw/model-a/101_demo/task_demo"
    assert payload["selectedAttemptPath"] == "openclaw/model-a/101_demo/task_demo/p1-host-a"
    assert payload["attemptCards"][0]["attemptPath"] == "openclaw/model-a/101_demo/task_demo/p1-host-a"


def test_symlinked_runs_view_rejects_artifact_escape(tmp_path, monkeypatch) -> None:
    real_runs = tmp_path / "real-runs"
    task_dir = real_runs / "openclaw" / "model-a" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    result_dir = attempt_dir / "result"
    result_dir.mkdir(parents=True)
    (result_dir / "answer.md").write_text("safe answer\n", encoding="utf-8")
    outside_secret = tmp_path / "outside-secret.txt"
    outside_secret.write_text("do not publish\n", encoding="utf-8")
    (result_dir / "leak.txt").symlink_to(outside_secret)
    (attempt_dir / "meta.json").write_text(json.dumps({"model": "provider/model.a"}), encoding="utf-8")
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "provider/model.a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
            }
        ),
        encoding="utf-8",
    )

    view_runs = tmp_path / "view-runs"
    view_model = view_runs / "openclaw"
    view_model.mkdir(parents=True)
    (view_model / "model-a").symlink_to(real_runs / "openclaw" / "model-a", target_is_directory=True)

    old_runs = server.RUNS
    try:
        server.RUNS = view_runs
        rel = "openclaw/model-a/101_demo/task_demo"
        payload = server.attempt_payload(rel)
        assert server.safe_rel_path(f"{rel}/p1-host-a/result/answer.md", view_runs) is not None
        assert server.safe_rel_path(f"{rel}/p1-host-a/result/leak.txt", view_runs) is None
    finally:
        server.RUNS = old_runs

    assert [item["path"] for item in payload["resultFiles"]] == ["answer.md"]
    assert "do not publish" not in json.dumps(payload)

    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "model-a",
                    "model_label": "provider/model.a",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "model-a"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [])

    out = tmp_path / "site"
    export(view_runs, out)
    assert (out / "404.html").read_text(encoding="utf-8") == (out / "index.html").read_text(encoding="utf-8")

    static_payload = json.loads((out / _attempt_detail_path(rel)).read_text(encoding="utf-8"))
    answer_url = static_payload["resultFiles"][0]["url"]
    assert answer_url.startswith("artifacts/")
    assert (out / answer_url).exists()
    assert not any(path.name == "leak.txt" for path in (out / "artifacts").rglob("*"))


def test_static_export_redacts_trace_metadata(tmp_path, monkeypatch) -> None:
    runs_root = tmp_path / "runs"
    task_dir = runs_root / "openclaw" / "private-provider-gpt-5-4" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "meta.json").write_text(
        json.dumps(
            {
                "model": "private-provider/gpt-5.4",
                "imageModel": "private-provider/gpt-5.4",
                "taskFile": "/root/private/tasks/task_demo.yaml",
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
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "private-provider/gpt-5.4",
                "imageModel": "private-provider/gpt-5.4",
                "modelSlug": "private-provider-gpt-5-4",
                "taskFile": "/root/private/tasks/task_demo.yaml",
                "settingRoot": "/root/private/runs/openclaw/private-provider-gpt-5-4",
                "finalStatus": "pass",
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "private-provider-gpt-5-4",
                    "model_label": "gpt-5.4",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "private-provider-gpt-5-4"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [])

    out = tmp_path / "site"
    export(runs_root, out)

    payload_path = out / _attempt_detail_path("openclaw/private-provider-gpt-5-4/101_demo/task_demo")
    encoded = payload_path.read_text(encoding="utf-8")
    payload = json.loads(encoded)
    assert payload["taskSummary"]["model"] == "gpt-5.4"
    assert payload["meta"]["model"] == "gpt-5.4"
    assert payload["supervision"]["supervisor"]["model"] == "gpt-5.4"
    assert "/root/private" not in encoded
    assert "private-provider" not in encoded
    assert "codex.local.toml" not in encoded
    assert "outDir" not in encoded


def test_public_task_run_drops_raw_score_payload() -> None:
    row = server.public_task_run(
        {
            "backend": "openclaw",
            "model": "private-provider/gpt-5.4",
            "modelSlug": "private-provider-gpt-5-4",
            "category": "101_demo",
            "taskId": "task_demo",
            "summaryPath": "openclaw/private-provider-gpt-5-4/101_demo/task_demo",
            "finalScore": 1.0,
            "rawFinalScore": 1.0,
            "score": {
                "overall_score": 1.0,
                "config": "configs/codex.local.toml",
                "debug_path": "/Users/example/private",
            },
        }
    )
    encoded = json.dumps(row)

    assert row["model"] == "gpt-5.4"
    assert row["modelSlug"] == "gpt-5.4"
    assert "score" not in row
    assert "codex.local.toml" not in encoded


def test_static_export_resume_rewrites_attempt_details(tmp_path, monkeypatch) -> None:
    runs_root = tmp_path / "runs"
    task_dir = runs_root / "openclaw" / "private-provider-gpt-5-4" / "101_demo" / "task_demo"
    attempt_dir = task_dir / "p1-host-a"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "meta.json").write_text(
        json.dumps({"model": "private-provider/gpt-5.4", "config": "configs/codex.local.toml"}),
        encoding="utf-8",
    )
    (attempt_dir / "score.json").write_text(json.dumps({"overall_score": 1.0}), encoding="utf-8")
    (attempt_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_demo",
                "backend": "openclaw",
                "model": "private-provider/gpt-5.4",
                "modelSlug": "private-provider-gpt-5-4",
                "finalStatus": "pass",
                "resolvedAttempt": 1,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir)}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [
                {
                    "backend": "openclaw",
                    "model_slug": "private-provider-gpt-5-4",
                    "model_label": "private-provider/gpt-5.4",
                    "category": "101_demo",
                    "task_id": "task_demo",
                    "score": 1.0,
                    "status": "pass",
                }
            ],
            "models": [{"model_slug": "private-provider-gpt-5-4"}],
            "backends": [{"backend": "openclaw"}],
        },
    )
    monkeypatch.setattr(aggregate, "list_task_yamls", lambda: [])

    out = tmp_path / "site"
    out.mkdir()
    (out / EXPORT_MARKER).write_text("old export", encoding="utf-8")
    detail_path = out / _attempt_detail_path("openclaw/private-provider-gpt-5-4/101_demo/task_demo")
    detail_path.parent.mkdir(parents=True)
    detail_path.write_text('{"leak":"/Users/example/private","config":"configs/codex.local.toml"}', encoding="utf-8")

    export(runs_root, out, resume=True)

    encoded = detail_path.read_text(encoding="utf-8")
    payload = json.loads(encoded)
    assert payload["taskSummary"]["model"] == "gpt-5.4"
    assert "/Users/example" not in encoded
    assert "private-provider" not in encoded
    assert "codex.local.toml" not in encoded


def test_static_export_forces_hidden_task_references_off(tmp_path, monkeypatch) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    tasks_root = tmp_path / "tasks"
    injection_root = tmp_path / "injection"
    task_id = "task_private"
    category = "101_demo"
    (tasks_root / category).mkdir(parents=True)
    (tasks_root / category / f"{task_id}.yaml").write_text(
        "\n".join(
            [
                f"task_id: {task_id}",
                f"category: {category}",
                "agent_sys: openclaw",
                "agent_id: main",
                "model: proxy-example/gpt-5.4",
                "task: demo",
                "references:",
                "  - references/eval_rule.md",
            ]
        ),
        encoding="utf-8",
    )
    refs = injection_root / category / task_id / "references"
    refs.mkdir(parents=True)
    (refs / "eval_rule.md").write_text("private rubric", encoding="utf-8")

    monkeypatch.setenv("CLAWBENCH_WEBUI_EXPOSE_HIDDEN_REFERENCES", "1")
    monkeypatch.setattr(aggregate, "TASKS", tasks_root)
    monkeypatch.setattr(aggregate, "INJECTION", injection_root)
    monkeypatch.setattr(
        aggregate,
        "aggregate_runs",
        lambda force=False: {
            "rows": [],
            "models": [],
            "backends": [],
            "model_backend_pairs": [],
            "categories": [category],
        },
    )

    out = tmp_path / "site"
    export(runs_root, out)

    detail = json.loads((out / "task-details" / f"{task_id}.json").read_text(encoding="utf-8"))
    encoded = json.dumps(detail)
    assert detail["eval_rule_md"] == ""
    assert detail["assets"]["references"] is None
    assert "private rubric" not in encoded
    assert "references" not in detail["task_yaml"]
