#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 (e.g. a worker host on 3.10): tomllib is the
    import tomli as tomllib  # stdlib descendant of tomli — identical read API, drop-in.
from pathlib import Path
from typing import Any


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env_placeholders(value: Any, *, env: dict[str, str] | None = None) -> Any:
    mapping = env or os.environ
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda match: mapping.get(match.group(1), match.group(0)), value)
    if isinstance(value, list):
        return [expand_env_placeholders(item, env=mapping) for item in value]
    if isinstance(value, dict):
        return {key: expand_env_placeholders(item, env=mapping) for key, item in value.items()}
    return value


def container_visible_value(value: str, *, hostname: str = "host.docker.internal") -> str:
    return str(value or "").replace("127.0.0.1", hostname).replace("localhost", hostname)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def merged_env(*, files: list[Path] | None = None, env: dict[str, str] | None = None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in files or []:
        merged.update(parse_env_file(path))
    merged.update(env or os.environ)
    return merged


def resolve_config_path(base_path: Path, *, env_var: str = "", base_dir: Path | None = None) -> Path:
    raw = str(os.environ.get(env_var, "")).strip() if env_var else ""
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = (base_dir or Path.cwd()) / path
        return path.resolve()
    return base_path.resolve()


def load_json_config(
    base_path: Path,
    *,
    env_var: str = "",
    base_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    target = resolve_config_path(base_path, env_var=env_var, base_dir=base_dir)
    if not target.exists():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return expand_env_placeholders(payload, env=env)


def load_toml_config(
    base_path: Path,
    *,
    env_var: str = "",
    base_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    target = resolve_config_path(base_path, env_var=env_var, base_dir=base_dir)
    if not target.exists():
        return {}
    payload = tomllib.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return expand_env_placeholders(payload, env=env)
