from __future__ import annotations

from pathlib import Path

from scripts.orchestra.config import (
    CodexRoleCfg,
    ControllerCfg,
    OrchestraConfig,
    PriorityCfg,
    SupervisionCfg,
    WorkerCfg,
)


def _cfg(tmp_path: Path) -> OrchestraConfig:
    return OrchestraConfig(
        controller=ControllerCfg(host="controller", data_root=tmp_path, webui_port=9016),
        workers=(WorkerCfg(name="w1", ssh="w1", parallel=1),),
        priorities=(
            PriorityCfg(
                id="missing",
                label="missing",
                backend_in=("openclaw",),
                model_in=("private-provider-gpt-5-4",),
                status_in=("missing",),
            ),
        ),
        model_caps={},
        default_model_cap=None,
        images=(),
        supervision=SupervisionCfg(
            supervisor=CodexRoleCfg(provider="codex-provider", model="grader-model"),
            user_simulator=CodexRoleCfg(provider="codex-provider", model="user-model"),
        ),
    )


def test_ensure_adapter_collects_specs_from_orchestra_runtime_overrides(tmp_path, monkeypatch) -> None:
    from scripts.orchestra import ensure_adapter

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_demo"
    suite_dir.mkdir(parents=True)
    task_yaml = suite_dir / "task_demo.yaml"
    task_yaml.write_text("task_id: task_demo\ncategory: 101_demo\n", encoding="utf-8")

    calls: list[dict] = []

    class _FakeTask:
        def __init__(self, model: str, overrides: dict):
            self.model = model
            self.codex_role_overrides = overrides

    def fake_build_runtime_task_spec(path, *, model=None, codex_role_overrides=None, **_kwargs):
        calls.append(
            {
                "path": Path(path),
                "model": model,
                "codex_role_overrides": codex_role_overrides,
            }
        )
        return _FakeTask(str(model), codex_role_overrides or {})

    def fake_collect(task):
        return [
            {
                "kind": "ssh",
                "ssh_host": "worker",
                "local_host": "127.0.0.1",
                "local_port": 9001,
                "remote_host": "127.0.0.1",
                "remote_port": 443,
                "adapter": "responses_via_chat",
                "adapter_port": 9001,
                "source": "executor",
                "model": task.model,
            }
        ]

    monkeypatch.setattr(ensure_adapter, "discover_task_files", lambda root: [task_yaml])
    monkeypatch.setattr(ensure_adapter.cfg_mod, "model_full_for", lambda model_dir: "private-provider/gpt-5.4")
    monkeypatch.setattr(ensure_adapter, "build_runtime_task_spec", fake_build_runtime_task_spec)
    monkeypatch.setattr(ensure_adapter, "collect_task_proxy_specs", fake_collect)

    specs = ensure_adapter._gather_specs_from_tasks(tasks_root, cfg=_cfg(tmp_path))

    assert len(specs) == 1
    assert specs[0]["model"] == "private-provider/gpt-5.4"
    assert calls == [
        {
            "path": task_yaml,
            "model": "private-provider/gpt-5.4",
            "codex_role_overrides": {
                "supervisor": {"provider": "codex-provider", "model": "grader-model"},
                "user_simulator": {"provider": "codex-provider", "model": "user-model"},
            },
        }
    ]


def test_ensure_adapter_collects_specs_from_local_cli_overrides(tmp_path, monkeypatch) -> None:
    from scripts.orchestra import ensure_adapter

    tasks_root = tmp_path / "tasks"
    suite_dir = tasks_root / "101_demo"
    suite_dir.mkdir(parents=True)
    task_yaml = suite_dir / "task_demo.yaml"
    task_yaml.write_text("task_id: task_demo\ncategory: 101_demo\n", encoding="utf-8")

    calls: list[dict] = []

    class _FakeTask:
        def __init__(self, model: str, agent_sys: str):
            self.model = model
            self.agent_sys = agent_sys

    def fake_build_runtime_task_spec(path, *, agent_sys=None, model=None, **_kwargs):
        calls.append({"path": Path(path), "agent_sys": agent_sys, "model": model})
        return _FakeTask(str(model), str(agent_sys))

    def fake_collect(task):
        return [
            {
                "kind": "ssh",
                "ssh_host": "worker",
                "local_host": "127.0.0.1",
                "local_port": 9001,
                "remote_host": "127.0.0.1",
                "remote_port": 443,
                "adapter": "responses_via_chat",
                "adapter_port": 9001,
                "source": task.agent_sys,
                "model": task.model,
            }
        ]

    monkeypatch.setattr(ensure_adapter, "discover_task_files", lambda root: [task_yaml])
    monkeypatch.setattr(ensure_adapter, "build_runtime_task_spec", fake_build_runtime_task_spec)
    monkeypatch.setattr(ensure_adapter, "collect_task_proxy_specs", fake_collect)

    specs = ensure_adapter._gather_specs_from_tasks(
        tasks_root,
        agent_sys="openclaw_edict",
        model="private-provider/gpt-5.4",
    )

    assert len(specs) == 1
    assert specs[0]["source"] == "openclaw_edict"
    assert specs[0]["model"] == "private-provider/gpt-5.4"
    assert calls == [
        {
            "path": task_yaml,
            "agent_sys": "openclaw_edict",
            "model": "private-provider/gpt-5.4",
        }
    ]
