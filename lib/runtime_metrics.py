"""Helpers for reading timing metrics from attempt artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _positive_int(value: Any) -> int | None:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def attempt_runtime_ms(
    summary_attempt: dict | None,
    attempt_dir: Path | str | None,
    attempt_meta: dict | None = None,
    *,
    default: int | None = None,
) -> int | None:
    """Best-effort elapsed runtime for one attempt.

    Preferred source is the per-attempt ``runtimeMs`` written into the task
    summary. Some recovered attempts have that field missing or zero, so we
    fall back to ``meta.json:runtimeMs``. We deliberately do not use
    ``timeline.json`` attempt spans here: those are wall-clock attempt
    durations and include supervisor/user-simulator/container overhead, while
    ``runtimeMs`` is executor-only. Callers that need an arithmetic sum can
    pass ``default=0``; aggregate callers keep the default ``None`` so missing
    values do not skew averages.
    """
    summary_attempt = summary_attempt or {}
    attempt_dir = Path(attempt_dir) if attempt_dir else None

    for value in (summary_attempt.get("runtimeMs"), summary_attempt.get("runtime_ms")):
        ms = _positive_int(value)
        if ms is not None:
            return ms

    if attempt_meta is None and attempt_dir:
        attempt_meta = _read_json(attempt_dir / "meta.json")
    for value in ((attempt_meta or {}).get("runtimeMs"), (attempt_meta or {}).get("runtime_ms")):
        ms = _positive_int(value)
        if ms is not None:
            return ms

    return default
