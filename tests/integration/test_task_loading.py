from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib.config_stack import load_json_config, load_toml_config, merged_env
from lib.runner import build_runtime_task_spec, resolve_models_provider_entry
from lib.runner import task_config as task_config_mod
from lib.templates.user_simulator import DEFAULT_USER_SIMULATOR_POLICY
from lib.supervision import codex as codex_mod
from lib.supervision.codex import load_codex_base_config, resolve_codex_provider
from lib.task import _parse_codex, discover_task_files, load_task


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_override_syncs_image_model_with_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAWBENCH_ALLOW_EXAMPLE_CONFIG", "1")
    task = build_runtime_task_spec(
        ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml",
        model="proxy-example/gpt-4.1",
    )
    assert task.model == "proxy-example/gpt-4.1"
    assert task.image_model == "proxy-example/gpt-4.1"


def test_load_task_rejects_legacy_edict_agent_sys(tmp_path) -> None:
    task_file = tmp_path / "tasks" / "demo" / "task.yaml"
    injection_root = tmp_path / "injection" / "demo" / "legacy_agent"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    (injection_root / "references").mkdir(parents=True, exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text("rule\n", encoding="utf-8")
    task_file.write_text(
        "\n".join(
            [
                "task_id: legacy_agent",
                "category: demo",
                "agent_sys: edict",
                "model: provider/model",
                "task: |",
                "  Example task.",
                "references:",
                "  - references/eval_rule.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="openclaw_edict"):
        load_task(task_file, tmp_path)


def test_load_task_requires_declared_assets_to_exist(tmp_path) -> None:
    task_file = tmp_path / "tasks" / "demo" / "task.yaml"
    injection_root = tmp_path / "injection" / "demo" / "asset_check"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    (injection_root / "references").mkdir(parents=True, exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text("rule\n", encoding="utf-8")
    task_file.write_text(
        "\n".join(
            [
                "task_id: asset_check",
                "category: demo",
                "agent_sys: openclaw",
                "model: provider/model",
                "task: |",
                "  Example task.",
                "references:",
                "  - references/eval_rule.md",
                "sources:",
                "  - data/input.json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing source asset"):
        load_task(task_file, tmp_path)


def test_load_task_happy_path(tmp_path) -> None:
    task_file = tmp_path / "tasks" / "demo" / "task.yaml"
    injection_root = tmp_path / "injection" / "demo" / "my_task"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    (injection_root / "references").mkdir(parents=True, exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text("rule\n", encoding="utf-8")
    task_file.write_text(
        "\n".join([
            "task_id: my_task",
            "category: demo",
            "agent_sys: openclaw",
            "model: provider/model",
            "timeout_seconds: 300",
            "success_threshold: 0.8",
            "task: |",
            "  Do something useful.",
            "references:",
            "  - references/eval_rule.md",
            "codex:",
            "  max_user_followups: 3",
        ]) + "\n",
        encoding="utf-8",
    )
    task = load_task(task_file, tmp_path)
    assert task.task_id == "my_task"
    assert task.category == "demo"
    assert task.agent_sys == "openclaw"
    assert task.model == "provider/model"
    # timeout_seconds explicitly set in YAML; max_total_seconds falls back
    # to the documented default (30 min cumulative executor budget).
    assert task.timeout_seconds == 300
    assert task.max_total_seconds == 1800
    assert task.success_threshold == 0.8
    assert task.task == "Do something useful."
    assert task.references == ["references/eval_rule.md"]
    assert task.codex.max_user_followups == 3
    assert task.codex.user_simulator.policy == DEFAULT_USER_SIMULATOR_POLICY


def test_load_task_respects_explicit_timeout_fields(tmp_path) -> None:
    """Both timeout_seconds and max_total_seconds declared in YAML must round-trip."""
    task_file = tmp_path / "tasks" / "demo" / "task.yaml"
    injection_root = tmp_path / "injection" / "demo" / "my_task"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    (injection_root / "references").mkdir(parents=True, exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text("rule\n", encoding="utf-8")
    task_file.write_text(
        "\n".join([
            "task_id: my_task",
            "category: demo",
            "agent_sys: openclaw",
            "model: provider/model",
            "timeout_seconds: 450",
            "max_total_seconds: 1200",
            "task: |",
            "  Do something.",
            "references:",
            "  - references/eval_rule.md",
        ]) + "\n",
        encoding="utf-8",
    )
    task = load_task(task_file, tmp_path)
    assert task.timeout_seconds == 450
    assert task.max_total_seconds == 1200


def test_discover_task_files_excludes_templates(tmp_path) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    # Legacy flat-file convention (filename contains "template")
    (tasks_dir / "task_000_template.yaml").write_text("task_id: template\n", encoding="utf-8")
    # New category-dir convention (parent directory contains "template")
    (tasks_dir / "000_template").mkdir()
    (tasks_dir / "000_template" / "task_000_example.yaml").write_text("task_id: example\n", encoding="utf-8")
    # Real tasks alongside
    (tasks_dir / "sub").mkdir()
    (tasks_dir / "sub" / "task_001_real.yaml").write_text("task_id: real\n", encoding="utf-8")
    (tasks_dir / "sub" / "task_002_Template_example.yaml").write_text("task_id: template2\n", encoding="utf-8")
    files = discover_task_files(tasks_dir)
    assert len(files) == 1
    assert files[0].name == "task_001_real.yaml"


def test_parse_codex_with_partial_fields() -> None:
    spec = _parse_codex({"max_user_followups": 5})
    assert spec.max_user_followups == 5
    assert spec.user_simulator.policy == DEFAULT_USER_SIMULATOR_POLICY
    assert spec.supervisor.model == "gpt-5.4"

    # None returns defaults
    spec = _parse_codex(None)
    assert spec.max_user_followups == 2
    assert spec.user_simulator.policy == DEFAULT_USER_SIMULATOR_POLICY


def _write_minimal_task(
    tmp_path,
    *,
    extra_yaml_lines: list[str] | None = None,
) -> tuple[Path, Path]:
    task_file = tmp_path / "tasks" / "demo" / "task.yaml"
    injection_root = tmp_path / "injection" / "demo" / "my_task"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    (injection_root / "references").mkdir(parents=True, exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text("rule\n", encoding="utf-8")
    lines = [
        "task_id: my_task",
        "category: demo",
        "agent_sys: openclaw",
        "model: provider/model",
        "task: |",
        "  Do something useful.",
        "references:",
        "  - references/eval_rule.md",
    ]
    if extra_yaml_lines:
        lines.extend(extra_yaml_lines)
    task_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return task_file, injection_root


def test_load_task_empty_privacy_is_ok(tmp_path) -> None:
    task_file, _ = _write_minimal_task(tmp_path)
    task = load_task(task_file, tmp_path)
    assert task.privacy == []


def test_load_task_reads_privacy_keys_from_file(tmp_path, monkeypatch) -> None:
    task_file, injection_root = _write_minimal_task(tmp_path)
    (injection_root / ".privacy").write_text(
        "EMAIL_ADDRESS\nEMAIL_PASSWORD\n", encoding="utf-8"
    )
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text(
        "EMAIL_ADDRESS=you@example.com\nEMAIL_PASSWORD=pw\n", encoding="utf-8"
    )
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    task = load_task(task_file, tmp_path)
    assert task.privacy == ["EMAIL_ADDRESS", "EMAIL_PASSWORD"]


def test_load_task_rejects_yaml_privacy_field(tmp_path) -> None:
    task_file, _ = _write_minimal_task(
        tmp_path,
        extra_yaml_lines=[
            "privacy:",
            "  - email_credentials.env",
        ],
    )
    with pytest.raises(ValueError, match="no longer accepts a `privacy:` field"):
        load_task(task_file, tmp_path)


def test_load_task_rejects_missing_privacy_value(tmp_path, monkeypatch) -> None:
    task_file, injection_root = _write_minimal_task(tmp_path)
    (injection_root / ".privacy").write_text("EMAIL_PASSWORD\n", encoding="utf-8")
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("EMAIL_ADDRESS=you@example.com\n", encoding="utf-8")
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    with pytest.raises(ValueError, match="missing keys: EMAIL_PASSWORD"):
        load_task(task_file, tmp_path)


def test_load_task_snapshot_mode_allows_blank_live_credentials(tmp_path, monkeypatch) -> None:
    task_file, injection_root = _write_minimal_task(tmp_path)
    (injection_root / ".privacy").write_text(
        "TRELLO_API_KEY\nTRELLO_API_TOKEN\nSNAPSHOT_MODE\n",
        encoding="utf-8",
    )
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text(
        "SNAPSHOT_MODE=1\n"
        "TRELLO_API_KEY=\n"
        "TRELLO_API_TOKEN=\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    task = load_task(task_file, tmp_path)
    assert task.privacy == ["TRELLO_API_KEY", "TRELLO_API_TOKEN", "SNAPSHOT_MODE"]


def test_load_task_rejects_placeholder_privacy_value(tmp_path, monkeypatch) -> None:
    task_file, injection_root = _write_minimal_task(tmp_path)
    (injection_root / ".privacy").write_text("API_TOKEN\n", encoding="utf-8")
    cfg = tmp_path / "privacy.local.env"
    cfg.write_text("API_TOKEN=REPLACE_ME_WITH_REAL_TOKEN\n", encoding="utf-8")
    monkeypatch.setattr("lib.privacy.PRIVACY_CONFIG_PATH", cfg)

    with pytest.raises(ValueError, match="placeholder keys: API_TOKEN"):
        load_task(task_file, tmp_path)


def test_load_task_rejects_invalid_env_var_name_in_privacy_file(tmp_path) -> None:
    task_file, injection_root = _write_minimal_task(tmp_path)
    (injection_root / ".privacy").write_text("3BAD_START\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid env-var name"):
        load_task(task_file, tmp_path)


def test_load_task_rejects_unsafe_service_name(tmp_path) -> None:
    task_file, injection_root = _write_minimal_task(
        tmp_path,
        extra_yaml_lines=[
            "services:",
            "  - name: bad name",
            "    path: demo-service",
            "    start: bash run.sh",
        ],
    )
    (injection_root / "services" / "demo-service").mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="services\\[0\\]\\.name"):
        load_task(task_file, tmp_path)


def test_load_task_rejects_unsafe_service_path(tmp_path) -> None:
    task_file, _ = _write_minimal_task(
        tmp_path,
        extra_yaml_lines=[
            "services:",
            "  - name: demo-service",
            "    path: ../escape",
            "    start: bash run.sh",
        ],
    )
    with pytest.raises(ValueError, match="services\\[0\\]\\.path entries must be safe relative paths"):
        load_task(task_file, tmp_path)


def test_load_task_rejects_unsafe_task_id(tmp_path) -> None:
    task_file = tmp_path / "tasks" / "demo" / "task.yaml"
    injection_root = tmp_path / "injection" / "demo" / "unsafe_id"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    (injection_root / "references").mkdir(parents=True, exist_ok=True)
    (injection_root / "references" / "eval_rule.md").write_text("rule\n", encoding="utf-8")
    task_file.write_text(
        "\n".join(
            [
                "task_id: ../escape",
                "category: demo",
                "agent_sys: openclaw",
                "model: provider/model",
                "task: |",
                "  Example task.",
                "references:",
                "  - references/eval_rule.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="task_id"):
        load_task(task_file, tmp_path)


def test_smoketest_tasks_use_clone_friendly_defaults() -> None:
    for task_path in (
        ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml",
        ROOT / "tasks/001_smoketest/task_001_outlook_login.yaml",
    ):
        raw = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        assert raw["model"] == "gpt-5.4"
        assert "provider" not in ((raw.get("codex") or {}).get("user_simulator") or {})
        assert "provider" not in ((raw.get("codex") or {}).get("supervisor") or {})


def test_example_configs_resolve_providerless_defaults() -> None:
    env = merged_env(files=[ROOT / "configs/api.example.env"])
    models_payload = load_json_config(ROOT / "configs/models.example.json", env=env)
    provider_name, _ = resolve_models_provider_entry("gpt-5.4", models_payload)
    assert provider_name == "proxy-example"

    codex_payload = load_toml_config(ROOT / "configs/codex.example.toml", env=env)
    codex_provider_name, codex_model = resolve_codex_provider(codex_payload, model="gpt-5.4", provider="")
    assert codex_provider_name == "proxy-example"
    assert codex_model == "gpt-5.4"


def test_runtime_models_config_is_required_by_default(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAWBENCH_ALLOW_EXAMPLE_CONFIG", raising=False)
    monkeypatch.delenv("CLAWBENCH_MODELS_CONFIG", raising=False)
    monkeypatch.setattr(task_config_mod, "DEFAULT_MODELS_CONFIG", tmp_path / "models.local.json")
    with pytest.raises(FileNotFoundError, match="models.local.json is required"):
        task_config_mod.load_models_payload()


def test_codex_config_is_required_by_default(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAWBENCH_ALLOW_EXAMPLE_CONFIG", raising=False)
    missing_default = tmp_path / "codex.local.toml"
    monkeypatch.setattr(codex_mod, "DEFAULT_CODEX_CONFIG", missing_default)
    with pytest.raises(FileNotFoundError, match="codex.local.toml"):
        load_codex_base_config(missing_default)


def test_runtime_model_resolution_rejects_unknown_example_model() -> None:
    env = merged_env(files=[ROOT / "configs/api.example.env"])
    models_payload = load_json_config(ROOT / "configs/models.example.json", env=env)
    with pytest.raises(ValueError, match="unknown executor model"):
        resolve_models_provider_entry("not-a-real-model", models_payload)


def test_codex_resolution_rejects_unknown_example_provider_and_model() -> None:
    env = merged_env(files=[ROOT / "configs/api.example.env"])
    codex_payload = load_toml_config(ROOT / "configs/codex.example.toml", env=env)
    with pytest.raises(ValueError, match="unknown codex model provider"):
        resolve_codex_provider(codex_payload, model="gpt-5.4", provider="missing-provider")
    with pytest.raises(ValueError, match="unknown codex model"):
        resolve_codex_provider(codex_payload, model="not-a-real-model", provider="")
