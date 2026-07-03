from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from lib.runner import (
    build_runtime_task_spec,
    reset_task_run_root,
    run_task,
)


ROOT = Path(__file__).resolve().parents[2]


def _example_models_payload() -> dict:
    return {"providers": {"proxy-example": {"models": [{"id": "gpt-4.1"}, {"id": "gpt-5.4"}]}}}


def test_reset_task_run_root_removes_stale_attempts(tmp_path, monkeypatch) -> None:
    import lib.runner as runner

    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setattr("lib.runner.task_config.load_models_payload", _example_models_payload)
    task = build_runtime_task_spec(ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml")
    run_root = runner.task_run_root(task)
    stale_attempt = run_root / "p1-deadbe" / "meta.json"
    stale_attempt.parent.mkdir(parents=True, exist_ok=True)
    stale_attempt.write_text("{}\n", encoding="utf-8")
    (run_root / "summary.json").write_text("{\"finalStatus\": \"fail\"}\n", encoding="utf-8")

    reset_task_run_root(task)

    assert run_root.exists()
    assert not stale_attempt.exists()
    assert not (run_root / "summary.json").exists()


def test_run_task_writes_structured_summary_when_proxy_bootstrap_fails(tmp_path, monkeypatch) -> None:
    import lib.runner as runner

    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setattr("lib.runner.task_config.load_models_payload", _example_models_payload)

    @contextmanager
    def broken_proxy_context(_tasks):
        raise RuntimeError("proxy bootstrap exploded")
        yield

    # ``run_task`` now lives in ``lib.runner.orchestration`` and calls
    # ``task_config.managed_task_proxy_tunnels`` via qualified access, so we
    # patch the source module rather than the ``lib.runner`` re-export.
    monkeypatch.setattr(
        "lib.runner.task_config.managed_task_proxy_tunnels",
        broken_proxy_context,
    )

    payload = run_task(
        ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml",
        agent_sys="openclaw",
        model="proxy-example/gpt-4.1",
        image_model="proxy-example/gpt-4.1",
    )

    assert payload["finalStatus"] == "infra_error"
    assert payload["infraError"]["type"] == "provider_proxy_bootstrap_failed"
    summary_path = runner.task_run_root(
        runner.build_runtime_task_spec(
            ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml",
            agent_sys="openclaw",
            model="proxy-example/gpt-4.1",
            image_model="proxy-example/gpt-4.1",
        )
    ) / "summary.json"
    session_meta_path = summary_path.with_name("session_meta.json")
    assert summary_path.exists()
    assert session_meta_path.exists()


def test_run_task_writes_structured_summary_when_runner_crashes(tmp_path, monkeypatch) -> None:
    import lib.runner as runner

    monkeypatch.setattr(runner, "RUNS", tmp_path / "runs")
    monkeypatch.setattr("lib.runner.task_config.load_models_payload", _example_models_payload)

    def crash(_task, *, image, keep_container):  # noqa: ANN001
        raise RuntimeError("runner exploded after bootstrap")

    monkeypatch.setattr("lib.runner.orchestration._run_resolved_task", crash)

    task_file = ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml"
    payload = run_task(
        task_file,
        agent_sys="openclaw",
        model="proxy-example/gpt-4.1",
        image_model="proxy-example/gpt-4.1",
        manage_provider_proxies=False,
    )

    assert payload["finalStatus"] == "infra_error"
    assert payload["infraError"]["type"] == "run_task_exception"
    assert "runner exploded after bootstrap" in payload["infraError"]["message"]
    task = runner.build_runtime_task_spec(
        task_file,
        agent_sys="openclaw",
        model="proxy-example/gpt-4.1",
        image_model="proxy-example/gpt-4.1",
    )
    summary_path = runner.task_run_root(task) / "summary.json"
    session_meta_path = summary_path.with_name("session_meta.json")
    assert summary_path.exists()
    assert session_meta_path.exists()
