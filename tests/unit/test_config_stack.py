from __future__ import annotations

import json
from pathlib import Path

from lib.config_stack import (
    container_visible_value,
    expand_env_placeholders,
    load_json_config,
    load_toml_config,
    merged_env,
    parse_env_file,
    resolve_config_path,
)


# ── expand_env_placeholders ──────────────────────────────────────


def test_expand_env_placeholders_replaces_known_vars() -> None:
    env = {"FOO": "bar", "NUM": "42"}
    assert expand_env_placeholders("${FOO}/${NUM}", env=env) == "bar/42"


def test_expand_env_placeholders_preserves_unknown_vars() -> None:
    assert expand_env_placeholders("${UNKNOWN_VAR}", env={}) == "${UNKNOWN_VAR}"


def test_expand_env_placeholders_handles_nested_structures() -> None:
    env = {"KEY": "value"}
    result = expand_env_placeholders({"a": "${KEY}", "b": ["${KEY}", "plain"]}, env=env)
    assert result == {"a": "value", "b": ["value", "plain"]}


def test_expand_env_placeholders_passes_through_non_string_types() -> None:
    assert expand_env_placeholders(42) == 42
    assert expand_env_placeholders(None) is None
    assert expand_env_placeholders(True) is True


# ── container_visible_value ──────────────────────────────────────


def test_container_visible_value_replaces_loopback() -> None:
    assert container_visible_value("http://127.0.0.1:9000") == "http://host.docker.internal:9000"


def test_container_visible_value_replaces_localhost() -> None:
    assert container_visible_value("http://localhost:9000") == "http://host.docker.internal:9000"


def test_container_visible_value_custom_hostname() -> None:
    result = container_visible_value("http://127.0.0.1:8080", hostname="myhost")
    assert result == "http://myhost:8080"


def test_container_visible_value_handles_empty() -> None:
    assert container_visible_value("") == ""
    assert container_visible_value(None) == ""


# ── parse_env_file ───────────────────────────────────────────────


def test_parse_env_file_basic(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")
    result = parse_env_file(env_file)
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_file_comments_and_blanks(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\n\nKEY=val\n", encoding="utf-8")
    result = parse_env_file(env_file)
    assert result == {"KEY": "val"}


def test_parse_env_file_export_prefix(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("export API_KEY=secret123\n", encoding="utf-8")
    result = parse_env_file(env_file)
    assert result == {"API_KEY": "secret123"}


def test_parse_env_file_quoted_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('SINGLE=\'hello world\'\nDOUBLE="foo bar"\n', encoding="utf-8")
    result = parse_env_file(env_file)
    assert result == {"SINGLE": "hello world", "DOUBLE": "foo bar"}


def test_parse_env_file_skips_malformed_lines(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("no_equals_sign\n123BAD=invalid_key\nGOOD=ok\n", encoding="utf-8")
    result = parse_env_file(env_file)
    assert result == {"GOOD": "ok"}


def test_parse_env_file_missing_file(tmp_path: Path) -> None:
    result = parse_env_file(tmp_path / "nonexistent")
    assert result == {}


# ── merged_env ───────────────────────────────────────────────────


def test_merged_env_combines_files_and_env(tmp_path: Path) -> None:
    f1 = tmp_path / "a.env"
    f2 = tmp_path / "b.env"
    f1.write_text("A=1\nB=from_file\n", encoding="utf-8")
    f2.write_text("C=3\n", encoding="utf-8")
    result = merged_env(files=[f1, f2], env={"B": "from_env", "D": "4"})
    assert result["A"] == "1"
    assert result["B"] == "from_env"  # env overrides file
    assert result["C"] == "3"
    assert result["D"] == "4"


# ── resolve_config_path ─────────────────────────────────────────


def test_resolve_config_path_uses_base_path_by_default(tmp_path: Path) -> None:
    base = tmp_path / "config.json"
    assert resolve_config_path(base) == base.resolve()


def test_resolve_config_path_uses_env_var(tmp_path: Path, monkeypatch) -> None:
    override = tmp_path / "override.json"
    monkeypatch.setenv("TEST_CFG", str(override))
    result = resolve_config_path(tmp_path / "default.json", env_var="TEST_CFG")
    assert result == override.resolve()


# ── load_json_config ─────────────────────────────────────────────


def test_load_json_config_happy_path(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"key": "${VAL}"}), encoding="utf-8")
    result = load_json_config(cfg, env={"VAL": "resolved"})
    assert result == {"key": "resolved"}


def test_load_json_config_missing_file(tmp_path: Path) -> None:
    assert load_json_config(tmp_path / "missing.json") == {}


def test_load_json_config_non_dict_returns_empty(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert load_json_config(cfg) == {}


# ── load_toml_config ─────────────────────────────────────────────


def test_load_toml_config_happy_path(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('[section]\nkey = "${VAL}"\n', encoding="utf-8")
    result = load_toml_config(cfg, env={"VAL": "resolved"})
    assert result == {"section": {"key": "resolved"}}


def test_load_toml_config_missing_file(tmp_path: Path) -> None:
    assert load_toml_config(tmp_path / "missing.toml") == {}
