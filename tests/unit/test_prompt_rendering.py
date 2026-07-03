"""Tests for ``prompt_prefix`` and ``build_initial_prompt`` post-consolidation.

The executor runtime-context preamble lives in
``lib/templates/executor_runtime.py`` as ``EXECUTOR_RUNTIME_PREFIX_LINES``.
``prompt_prefix()`` in ``lib/runner.py`` assembles the final text by
``.format()``-ing each line with runtime values and joining with ``\\n``.

These tests lock:

  - required substrings that the executor relies on (workspace path,
    browser guidance, duckduckgo fallback, final-message instruction)
  - runtime base skills render BEFORE task-declared skills
  - the EDICT routing note appears only for ``agent_sys == "openclaw_edict"``
  - ``prompt_prefix`` output is byte-identical to reconstructing it from
    ``EXECUTOR_RUNTIME_PREFIX_LINES`` directly (golden test against the
    consolidation source of truth)
"""
from __future__ import annotations

from pathlib import Path

from lib.runner import build_initial_prompt, build_runtime_task_spec, prompt_prefix
from lib.templates.executor_runtime import EDICT_ROUTING_NOTE, EXECUTOR_RUNTIME_PREFIX_LINES


ROOT = Path(__file__).resolve().parents[2]


def _task(**overrides):
    task = build_runtime_task_spec(
        ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml",
        **overrides,
    )
    return task


def test_prompt_prefix_includes_required_runtime_lines() -> None:
    task = _task()
    prompt = prompt_prefix(task)

    # Core workspace context
    assert "/tmp_workspace" in prompt
    assert "/tmp_workspace/results" in prompt

    # Search-tool fallback guidance (relied on by the duckduckgo-search skill)
    assert "duckduckgo-search" in prompt

    # Completion instruction — final turn must be a text message, not a tool call
    assert "final text message" in prompt.lower()


def test_prompt_prefix_runtime_skills_render_before_declared_skills() -> None:
    """The base runtime skills (apt-package-manager, agent-browser-control,
    etc.) must appear in the prompt before any task-declared skills so the
    executor grounds in the runtime environment first."""
    task = _task()
    prompt = prompt_prefix(task)

    # YouTube smoketest declares a few skills; runtime base skills always come
    # first in the assembled list.
    runtime_marker = "/root/skills/agent-browser-control/SKILL.md"
    assert runtime_marker in prompt

    # If the task declares skills, at least one base runtime skill must
    # appear earlier than the last declared one.
    if task.skills:
        runtime_idx = prompt.find(runtime_marker)
        declared_idxes = [prompt.find(f"/root/skills/{name}/SKILL.md") for name in task.skills]
        declared_idxes = [i for i in declared_idxes if i >= 0]
        assert declared_idxes, "declared skills should render in the prompt"
        assert runtime_idx <= max(declared_idxes), "runtime skills must appear before task skills"


def test_build_initial_prompt_omits_edict_note_for_openclaw() -> None:
    task = _task(agent_sys="openclaw")
    prompt = build_initial_prompt(task)

    # The EDICT note's unmistakable opening should NOT appear
    assert "EDICT routing note:" not in prompt
    assert "三省六部" not in prompt


def test_build_initial_prompt_includes_edict_note_for_openclaw_edict() -> None:
    task = _task(agent_sys="openclaw_edict")
    prompt = build_initial_prompt(task)

    assert "EDICT routing note:" in prompt
    assert "三省六部" in prompt
    # Full note should render exactly as defined in the template module
    assert EDICT_ROUTING_NOTE in prompt


def test_prompt_prefix_output_matches_template_when_reassembled() -> None:
    """Byte-identity golden: what prompt_prefix() returns must equal what
    you get if you format the EXECUTOR_RUNTIME_PREFIX_LINES tuple directly
    with the same runtime values. This catches any accidental drift between
    the template module and the runner's assembly code.
    """
    import lib.runner as runner

    task = _task()
    prompt = prompt_prefix(task)

    declared_skill_lines = [f"- /root/skills/{name}/SKILL.md" for name in task.skills]
    runtime_skill_lines = [f"- /root/skills/{name}/SKILL.md" for name in runner.runtime_base_skills()]
    skill_lines = "\n".join(dict.fromkeys([*runtime_skill_lines, *declared_skill_lines])) or "- none"
    expected = "\n".join(
        line.format(results_root=runner.RESULTS_ROOT, skill_lines=skill_lines)
        for line in EXECUTOR_RUNTIME_PREFIX_LINES
    ) + "\n"

    assert prompt == expected
