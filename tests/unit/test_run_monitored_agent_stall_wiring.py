"""``run_monitored_agent`` must inline lib/runner/agent_monitor.py into the
in-container ``docker exec`` heredoc and drive the loop via ``run_monitor`` with
a rolling stall timeout.

The injection is brittle by nature (a Python module source spliced into an
f-string spliced into a bash heredoc), so the key guard here is that the emitted
in-container Python is *syntactically valid* — that catches any brace / quote /
heredoc-terminator escaping bug at test time instead of on a live worker.
"""
from __future__ import annotations

from types import SimpleNamespace

from lib.runner import agents


def _extract_inlined_python(script: str) -> str:
    """Pull the python body out of ``python3 - <<'PY' ... PY`` heredoc."""
    after = script.split("<<'PY'", 1)[1]
    return after.rsplit("\nPY", 1)[0]


def test_emitted_monitor_script_compiles_and_uses_rolling_stall(monkeypatch):
    captured: dict[str, str] = {}

    def fake_exec(container, command, **kwargs):
        captured["script"] = command
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("lib.runner.docker.docker_exec", fake_exec)

    agents.run_monitored_agent(
        "clawbench-test",
        ["openclaw", "agent", "--message", "hi"],
        1200,
        progress_paths=["/tmp_workspace/results/transcript.jsonl"],
    )

    script = captured["script"]
    py = _extract_inlined_python(script)

    # Must be valid Python — guards the heredoc/f-string injection escaping.
    compile(py, "<emitted-monitor>", "exec")

    # The injected agent_monitor source + the rolling-stall wiring are present.
    assert "def decide(" in py
    assert "def run_monitor(" in py
    assert "run_monitor(" in py
    assert "stall_timeout" in py
    # The startup-silence guard is preserved alongside the new rolling stall.
    assert "startup_silence_timeout" in py


def test_stall_timeout_is_env_tunable(monkeypatch):
    captured: dict[str, str] = {}

    def fake_exec(container, command, **kwargs):
        captured["script"] = command
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("lib.runner.docker.docker_exec", fake_exec)
    monkeypatch.setenv("CLAWBENCH_AGENT_STALL_TIMEOUT_SECONDS", "777")

    import importlib

    reloaded = importlib.reload(agents)
    try:
        assert reloaded.AGENT_STALL_TIMEOUT_SECONDS == 777
        reloaded.run_monitored_agent("c", ["echo", "x"], 1200)
        py = _extract_inlined_python(captured["script"])
        assert "777" in py
    finally:
        monkeypatch.delenv("CLAWBENCH_AGENT_STALL_TIMEOUT_SECONDS", raising=False)
        importlib.reload(reloaded)
