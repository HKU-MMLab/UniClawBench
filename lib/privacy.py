#!/usr/bin/env python3
"""Privacy / credential injection for Clawbench tasks.

A task declares which env-var names it needs via a per-task
``.privacy`` plain-text file under ``injection/{category}/{task_id}/``.
The file has one KEY per line; blank lines and ``# ...`` comments are
skipped.

At runtime the runner resolves each declared KEY against a single
shared config file at ``configs/privacy.local.env`` (standard env-file
format, gitignored) and injects the value into the executor container
as an environment variable. The supervisor workspace gets a
``privacy/env.env`` mirror of the same KEY=VALUE pairs for hidden
rubric checks; the public user simulator never sees them.

Fresh clones copy ``configs/privacy.example.env`` to
``configs/privacy.local.env`` and fill real values there. A task whose
``.privacy`` file lists a KEY that is absent (or empty) in the local
config fails to load with a loud "missing key" error, so we never
silently run against placeholders. The one exception is an auth-capable
task running with ``SNAPSHOT_MODE=1``: live-service credentials declared
beside ``SNAPSHOT_MODE`` are intentionally optional and are not injected.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config_stack import parse_env_file
from .defaults import ROOT


PRIVACY_CONFIG_PATH = ROOT / "configs" / "privacy.local.env"
PRIVACY_EXAMPLE_CONFIG_PATH = ROOT / "configs" / "privacy.example.env"
TASK_PRIVACY_FILENAME = ".privacy"

# Env-var names must be shell-safe: start with letter/underscore and
# contain only letters, digits, or underscore. Anything else is rejected
# so we never hand a garbled string to ``docker run -e KEY=VALUE``.
_ENV_VAR_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_PLACEHOLDER_MARKERS = (
    "REPLACE_ME",
    "CHANGE_ME",
    "CHANGEME",
    "TODO",
    "YOUR_",
    "...",
)
_PLACEHOLDER_EXACT = {
    "you@outlook.com",
    "outlook_password",
    "password",
    "token",
    "api_key",
    "secret",
}


def parse_privacy_keys_file(path: Path) -> list[str]:
    """Parse a ``.privacy`` manifest and return declared env-var names.

    One KEY per line. Blank lines and ``# ...`` comments are skipped.
    Trailing ``=...`` (if someone pastes a whole env line by mistake) is
    tolerated — only the left-hand name is kept, and the user will hit
    the missing-value error later if their local config doesn't carry it.

    Raises ``ValueError`` if any non-comment line does not parse as a
    valid env-var name, or if the same KEY is listed twice.
    """
    if not path.exists():
        return []
    keys: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Tolerate accidental ``KEY=VALUE`` lines — strip the RHS silently.
        candidate = stripped.split("=", 1)[0].strip()
        if not _ENV_VAR_NAME_RE.fullmatch(candidate):
            raise ValueError(
                f"{path}: line {line_number}: invalid env-var name {candidate!r} "
                f"(must match [A-Za-z_][A-Za-z0-9_]*)"
            )
        if candidate in seen:
            raise ValueError(f"{path}: line {line_number}: duplicate env-var name {candidate!r}")
        seen.add(candidate)
        keys.append(candidate)
    return keys


def load_privacy_config(config_path: Path | None = None) -> dict[str, str]:
    """Return all KEY=VALUE pairs from ``configs/privacy.local.env``.

    Missing file collapses to an empty dict. Callers use
    ``resolve_privacy_env`` to fail loudly when a task needs a key that
    isn't configured.
    """
    target = Path(config_path) if config_path is not None else PRIVACY_CONFIG_PATH
    return parse_env_file(target)


def _looks_like_placeholder(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    lower = normalized.lower()
    upper = normalized.upper()
    if lower in _PLACEHOLDER_EXACT:
        return True
    return any(marker in upper for marker in _PLACEHOLDER_MARKERS)


def resolve_privacy_env(
    keys: list[str],
    *,
    config_path: Path | None = None,
) -> dict[str, str]:
    """Resolve the runtime env-var map for a task's declared keys.

    Raises ``ValueError`` listing every KEY that is missing (no entry in
    config) or has an empty value. The error message also hints at the config
    path so operators can edit the right file.

    If a task declares ``SNAPSHOT_MODE`` and the local config explicitly sets
    ``SNAPSHOT_MODE=1``, only that flag is returned. Other declared live API
    credentials are optional in this offline mode and are deliberately not
    injected into the executor or supervisor workspace.
    """
    if not keys:
        return {}
    available = load_privacy_config(config_path)
    resolved: dict[str, str] = {}
    missing: list[str] = []
    empty: list[str] = []
    placeholder: list[str] = []
    snapshot_mode_enabled = "SNAPSHOT_MODE" in keys and str(available.get("SNAPSHOT_MODE", "")).strip() == "1"
    for key in keys:
        if snapshot_mode_enabled and key != "SNAPSHOT_MODE":
            continue
        value = available.get(key, "")
        if key not in available:
            missing.append(key)
            continue
        if not value:
            empty.append(key)
            continue
        if _looks_like_placeholder(value):
            placeholder.append(key)
            continue
        resolved[key] = value
    if missing or empty or placeholder:
        target = Path(config_path) if config_path is not None else PRIVACY_CONFIG_PATH
        parts: list[str] = []
        if missing:
            parts.append(f"missing keys: {', '.join(sorted(missing))}")
        if empty:
            parts.append(f"empty keys: {', '.join(sorted(empty))}")
        if placeholder:
            parts.append(f"placeholder keys: {', '.join(sorted(placeholder))}")
        hint = (
            f"Edit {target} (copy from {PRIVACY_EXAMPLE_CONFIG_PATH} if absent) "
            f"and set real values. configs/privacy.local.env is gitignored."
        )
        raise ValueError(f"privacy config incomplete — {'; '.join(parts)}. {hint}")
    return resolved


def task_privacy_file(injection_root: Path) -> Path:
    """Return the path to ``{injection_root}/.privacy``."""
    return Path(injection_root) / TASK_PRIVACY_FILENAME


def load_task_privacy_keys(injection_root: Path) -> list[str]:
    """Load the env-var names declared by the task's ``.privacy`` file.

    Returns an empty list when the task has no ``.privacy`` file — tasks
    without credentials are a valid, common case.
    """
    return parse_privacy_keys_file(task_privacy_file(injection_root))


__all__ = [
    "PRIVACY_CONFIG_PATH",
    "PRIVACY_EXAMPLE_CONFIG_PATH",
    "TASK_PRIVACY_FILENAME",
    "parse_privacy_keys_file",
    "load_privacy_config",
    "resolve_privacy_env",
    "task_privacy_file",
    "load_task_privacy_keys",
]
