from __future__ import annotations

import json
from pathlib import Path


def test_aggregate_passed_uses_normalized_status(tmp_path: Path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "101_a" / "task_pass"
    attempt_dir = task_dir / "p1-worker1-abcdef"
    attempt_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_pass",
                "backend": "openclaw",
                "model": "provider/model-a",
                "modelSlug": "model-a",
                "finalStatus": "PASS",
                "finalScore": 1.0,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "finalStatus": "PASS"}],
            }
        ),
        encoding="utf-8",
    )

    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    data = aggregate.aggregate_runs(force=True)

    assert data["models"][0]["total"]["pass_rate"] == 1.0


def test_aggregate_pass_rate_uses_summary_passed_flag(tmp_path: Path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "203_monitor" / "task_low_score_pass"
    attempt_dir = task_dir / "p1-worker1-abcdef"
    attempt_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_low_score_pass",
                "backend": "openclaw",
                "model": "provider/model-a",
                "modelSlug": "model-a",
                "finalStatus": "pass",
                "passed": False,
                "finalScore": 0.55,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "finalStatus": "pass", "passed": False}],
            }
        ),
        encoding="utf-8",
    )

    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    data = aggregate.aggregate_runs(force=True)

    assert data["rows"][0]["passed"] is False
    assert data["models"][0]["total"]["pass_rate"] == 0.0


def test_runs_index_preserves_summary_passed_flag(tmp_path: Path) -> None:
    from scripts.orchestra import refresh_summary
    from webui import server

    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "model-a" / "203_monitor" / "task_low_score_pass"
    task_dir.mkdir(parents=True)
    summary = {
        "taskId": "task_low_score_pass",
        "backend": "openclaw",
        "model": "provider/model-a",
        "modelSlug": "model-a",
        "finalStatus": "pass",
        "passed": False,
        "finalScore": 0.55,
        "attempts": [],
    }

    row = refresh_summary._build_index_row(task_dir, summary, runs_root=runs)

    assert server._RUNS_INDEX_SCHEMA_VERSION == refresh_summary.INDEX_SCHEMA_VERSION
    assert row["finalStatus"] == "pass"
    assert row["passed"] is False


def test_aggregate_model_labels_are_public_display_names(tmp_path: Path, monkeypatch) -> None:
    runs = tmp_path / "runs"
    task_dir = runs / "openclaw" / "private-provider-vendor-claude-opus-4-8-private" / "101_a" / "task_pass"
    attempt_dir = task_dir / "p1-worker1-abcdef"
    attempt_dir.mkdir(parents=True)
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "taskId": "task_pass",
                "backend": "openclaw",
                "model": "private-provider/vendor-claude-opus-4.8-private",
                "modelSlug": "private-provider-vendor-claude-opus-4-8-private",
                "finalStatus": "pass",
                "finalScore": 1.0,
                "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "finalStatus": "pass"}],
            }
        ),
        encoding="utf-8",
    )

    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    data = aggregate.aggregate_runs(force=True)

    assert data["models"][0]["label"] == "claude-opus-4.8"
    assert data["rows"][0]["model_label"] == "claude-opus-4.8"


def test_aggregate_dedupes_public_model_aliases(tmp_path: Path, monkeypatch) -> None:
    runs = tmp_path / "runs"

    def write_run(model_dir: str, model: str, score: float) -> None:
        task_dir = runs / "openclaw" / model_dir / "101_a" / "task_same"
        attempt_dir = task_dir / "p1-worker1-abcdef"
        attempt_dir.mkdir(parents=True)
        (task_dir / "summary.json").write_text(
            json.dumps(
                {
                    "taskId": "task_same",
                    "backend": "openclaw",
                    "model": model,
                    "modelSlug": model_dir,
                    "finalStatus": "pass",
                    "finalScore": score,
                    "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "finalStatus": "pass"}],
                }
            ),
            encoding="utf-8",
        )

    write_run("provider-a-gpt-5-4", "provider-a/gpt-5.4", 0.2)
    write_run("provider-b-gpt-5-4", "provider-b/gpt-5.4", 1.0)

    from webui import aggregate

    monkeypatch.setattr(aggregate, "RUNS", runs)
    monkeypatch.setattr(aggregate, "_AGG_CACHE", None)
    monkeypatch.setattr(aggregate, "_AGG_KEY", None)

    data = aggregate.aggregate_runs(force=True)

    assert len(data["rows"]) == 1
    assert data["rows"][0]["model_label"] == "gpt-5.4"


def test_trace_slim_rows_publicize_model_fields() -> None:
    from webui import server

    row = server.slim_task_run(
        {
            "category": "101_a",
            "taskId": "task_demo",
            "backend": "openclaw",
            "model": "example-router-claude-opus-4.8-daily",
            "modelSlug": "example-router-claude-opus-4-8-daily",
            "settingKey": "openclaw::example-router-claude-opus-4-8-daily",
            "summaryPath": "openclaw/example-router-claude-opus-4-8-daily/101_a/task_demo",
        }
    )

    assert row["model"] == "claude-opus-4.8"
    assert row["modelSlug"] == "claude-opus-4.8"
    assert row["settingKey"] == "openclaw::claude-opus-4.8"


def test_trace_rows_filter_non_openclaw_gemini_pro() -> None:
    from webui import server

    rows = server.slim_task_runs(
        [
            {
                "category": "101_a",
                "taskId": "keep_openclaw",
                "backend": "openclaw",
                "model": "provider-all-new/gemini-3.1-pro-preview",
                "modelSlug": "provider-all-new-gemini-3-1-pro-preview",
            },
            {
                "category": "101_a",
                "taskId": "drop_nanobot",
                "backend": "nanobot",
                "model": "provider-all-new/gemini-3.1-pro-preview",
                "modelSlug": "provider-all-new-gemini-3-1-pro-preview",
            },
            {
                "category": "001_smoketest",
                "taskId": "drop_smoketest",
                "backend": "openclaw",
                "model": "provider-all-new/gpt-5.4",
                "modelSlug": "provider-all-new-gpt-5-4",
            },
            {
                "category": "101_a",
                "taskId": "keep_flash",
                "backend": "nanobot",
                "model": "provider-all/gemini-3-flash-preview",
                "modelSlug": "provider-all-gemini-3-flash-preview",
            },
        ]
    )

    assert {row["taskId"] for row in rows} == {"keep_openclaw", "keep_flash"}


def test_trace_rows_dedup_public_model_aliases() -> None:
    from webui import server

    rows = server.slim_task_runs(
        [
            {
                "category": "101_a",
                "taskId": "task_same",
                "backend": "openclaw",
                "model": "provider-a/gpt-5.4",
                "modelSlug": "provider-a-gpt-5-4",
                "createdAt": 1,
                "finalStatus": "pass",
                "summaryPath": "openclaw/provider-a-gpt-5-4/101_a/task_same",
            },
            {
                "category": "101_a",
                "taskId": "task_same",
                "backend": "openclaw",
                "model": "provider-b/gpt-5.4",
                "modelSlug": "provider-b-gpt-5-4",
                "createdAt": 2,
                "finalStatus": "pass",
                "summaryPath": "openclaw/provider-b-gpt-5-4/101_a/task_same",
            },
        ]
    )

    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-5.4"
    assert rows[0]["summaryPath"] == "openclaw/provider-b-gpt-5-4/101_a/task_same"


def test_trace_slim_fallback_filters_public_rows(tmp_path: Path, monkeypatch) -> None:
    from webui import server

    def write_run(backend: str, model_dir: str, category: str, task_id: str, model: str) -> None:
        task_dir = tmp_path / "runs" / backend / model_dir / category / task_id
        attempt_dir = task_dir / "p1-ol1-deadbeef"
        attempt_dir.mkdir(parents=True)
        (task_dir / "summary.json").write_text(
            json.dumps(
                {
                    "taskId": task_id,
                    "backend": backend,
                    "model": model,
                    "modelSlug": model_dir,
                    "finalStatus": "pass",
                    "finalScore": 1.0,
                    "attempts": [{"attempt": 1, "outDir": str(attempt_dir), "finalStatus": "pass"}],
                    "resolvedAttempt": 1,
                }
            ),
            encoding="utf-8",
        )

    write_run("nanobot", "provider-all-new-gemini-3-1-pro-preview", "101_a", "drop_gemini", "provider-all-new/gemini-3.1-pro-preview")
    write_run("openclaw", "provider-all-new-gpt-5-4", "001_smoketest", "drop_smoke", "provider-all-new/gpt-5.4")
    write_run("openclaw", "provider-all-new-gpt-5-4", "101_a", "keep_task", "provider-all-new/gpt-5.4")

    monkeypatch.setattr(server, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(server, "_SLIM_RUNS_CACHE", None)
    monkeypatch.setattr(server, "_SLIM_RUNS_CACHE_TTL_SECONDS", 0)

    rows = server.list_task_runs_slim()

    assert [row["taskId"] for row in rows] == ["keep_task"]
