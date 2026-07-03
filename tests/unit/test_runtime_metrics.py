from __future__ import annotations

import json
from pathlib import Path

from lib.runtime_metrics import attempt_runtime_ms


def test_attempt_runtime_prefers_summary_then_meta(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "p1-host-abc123"
    attempt_dir.mkdir()
    (attempt_dir / "meta.json").write_text(json.dumps({"runtimeMs": 4321}), encoding="utf-8")

    assert attempt_runtime_ms({"runtimeMs": 1234}, attempt_dir) == 1234
    assert attempt_runtime_ms({"runtimeMs": 0}, attempt_dir) == 4321


def test_attempt_runtime_does_not_use_timeline_wall_clock(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "p1-host-abc123"
    attempt_dir.mkdir()
    (attempt_dir / "timeline.json").write_text(
        json.dumps({"attempt_started_ms": 1000, "attempt_ended_ms": 9000}),
        encoding="utf-8",
    )

    assert attempt_runtime_ms({}, attempt_dir) is None
    assert attempt_runtime_ms({}, attempt_dir, default=0) == 0
