"""Architectural invariants for the edict AGENTS.md / TOOLS.md builders.

``lib.runner.build_edict_agents_md`` and ``lib.runner.build_edict_tools_md``
compose the per-agent prompt bundle that Clawbench writes into every
edict agent's workspace before the run starts. These docs are the
ONLY places where nested subagents (spawned via ``sessions_spawn``)
pick up Clawbench-specific runtime rules — the initial
``EDICT_ROUTING_NOTE`` goes only to taizi, and upstream edict SOUL /
GLOBAL files know nothing about Clawbench's disabled-native-browser
policy.

The post-mortem for the first ``openclaw_edict`` smoketest showed what
happens when these invariants break: the nested ``shangshu:subagent``
tried to call the native ``browser`` MCP tool (disabled), then fell
back to fabricating HTML evidence, which wasted cycle 1. These tests
lock the guidance in place so any future consolidation can't silently
drop it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.runner import build_edict_agents_md, build_edict_tools_md, build_runtime_task_spec


ROOT = Path(__file__).resolve().parents[2]


# The three-省 agents are the ones most likely to spawn subagents; the
# six ministries also need the same guidance because they're often the
# actual browser-using executor.
EDICT_AGENTS_TO_TEST: tuple[str, ...] = (
    "taizi",
    "zhongshu",
    "menxia",
    "shangshu",
    "hubu",
    "libu",
    "bingbu",
    "xingbu",
    "gongbu",
    "libu_hr",
)


@pytest.fixture(scope="module")
def edict_task():
    return build_runtime_task_spec(
        ROOT / "tasks/001_smoketest/task_000_youtube_earbuds_amazon.yaml",
        agent_sys="openclaw_edict",
    )


@pytest.mark.parametrize("agent_id", EDICT_AGENTS_TO_TEST)
def test_agents_md_tells_every_agent_to_use_agent_browser_cli(agent_id: str, edict_task) -> None:
    """Every edict agent's AGENTS.md must name ``agent-browser`` as the
    canonical browser entry. Native ``browser`` MCP is disabled in
    Clawbench, so without this bullet subagents silently fall back."""
    doc = build_edict_agents_md(agent_id, edict_task)
    assert "agent-browser" in doc, f"{agent_id} AGENTS.md missing agent-browser CLI mention"
    assert "SKILL.md" in doc, f"{agent_id} AGENTS.md missing SKILL.md pointer"


@pytest.mark.parametrize("agent_id", EDICT_AGENTS_TO_TEST)
def test_agents_md_warns_every_agent_that_native_browser_mcp_is_disabled(agent_id: str, edict_task) -> None:
    """Each AGENTS.md must explicitly tell the agent that the native
    openclaw ``browser`` MCP tool is disabled — otherwise the model
    (and any subagent it spawns) will assume it still works."""
    doc = build_edict_agents_md(agent_id, edict_task)
    lowered = doc.lower()
    # Accept either an English or Chinese phrasing; just require both
    # the "browser" word and "disabled/关闭/off" in some combination.
    assert "browser" in lowered, f"{agent_id} AGENTS.md lost the word 'browser'"
    assert any(marker in doc for marker in ("已关闭", "已被", "disabled", "不要调用")), (
        f"{agent_id} AGENTS.md lost the 'native browser is disabled' warning"
    )


@pytest.mark.parametrize("agent_id", EDICT_AGENTS_TO_TEST)
def test_agents_md_requires_restating_browser_rule_in_sessions_spawn(agent_id: str, edict_task) -> None:
    """The spawn-time propagation rule: whenever an agent dispatches a
    task via ``sessions_spawn``, it must restate the browser rule in
    the task text, so the child agent gets the rule even if it doesn't
    read its own AGENTS.md first."""
    doc = build_edict_agents_md(agent_id, edict_task)
    assert "sessions_spawn" in doc
    assert "复述" in doc or "restate" in doc.lower() or "task 文本" in doc, (
        f"{agent_id} AGENTS.md missing the sessions_spawn propagation rule"
    )


@pytest.mark.parametrize("agent_id", EDICT_AGENTS_TO_TEST)
def test_tools_md_lists_agent_browser_under_tool_mapping(agent_id: str) -> None:
    doc = build_edict_tools_md(agent_id)
    assert "agent-browser" in doc, f"{agent_id} TOOLS.md missing agent-browser CLI mapping"
    # Common verbs the executor will actually use — lock at least a
    # couple so an accidental shortening of the mapping still catches.
    assert "open" in doc and "snapshot" in doc and "screenshot" in doc


@pytest.mark.parametrize("agent_id", EDICT_AGENTS_TO_TEST)
def test_tools_md_warns_spawn_parent_to_forward_browser_rule(agent_id: str) -> None:
    doc = build_edict_tools_md(agent_id)
    assert "sessions_spawn" in doc
    # Either language is fine — we just want SOMETHING that tells the
    # spawning parent to include the rule in the child's task text.
    assert "task" in doc.lower()
    assert "browser" in doc.lower()


def test_agents_md_preserves_upstream_global_and_soul_sections(
    edict_task, tmp_path, monkeypatch
) -> None:
    """Adding the Clawbench runtime addendum must not drop the upstream
    GLOBAL.md / group-md / SOUL.md content — those sections are still
    the source of truth for the three-省 flow semantics.

    The upstream edict assets live under ``downloads/edict/agents/`` and
    are fetched at runtime by ``scripts/fetch_edict.sh`` (gitignored, so
    absent in a clean checkout).  ``build_edict_agents_md`` includes the
    Shared Global / Group / Role sections *only when those files exist*;
    to actually exercise the "addendum doesn't drop upstream content"
    invariant we materialise a minimal asset tree and point the builder's
    path constants at it."""
    from lib.runner import edict as edict_mod

    agents_root = tmp_path / "agents"
    (agents_root / "taizi").mkdir(parents=True)
    (agents_root / "GLOBAL.md").write_text("UPSTREAM-GLOBAL-BODY", encoding="utf-8")
    groups_root = agents_root / "groups"
    groups_root.mkdir()
    # "taizi" belongs to the sansheng group (see edict_agent_group).
    (groups_root / "sansheng.md").write_text("UPSTREAM-GROUP-BODY", encoding="utf-8")
    (agents_root / "taizi" / "SOUL.md").write_text("UPSTREAM-SOUL-BODY", encoding="utf-8")

    monkeypatch.setattr(edict_mod, "EDICT_AGENTS_ROOT", agents_root)
    monkeypatch.setattr(edict_mod, "EDICT_GLOBAL_MD", agents_root / "GLOBAL.md")
    monkeypatch.setattr(edict_mod, "EDICT_GROUPS_ROOT", groups_root)

    doc = build_edict_agents_md("taizi", edict_task)
    assert "## Shared Global Rules" in doc
    assert "UPSTREAM-GLOBAL-BODY" in doc
    assert "## Group Rules" in doc
    assert "UPSTREAM-GROUP-BODY" in doc
    assert "## Role Rules" in doc
    assert "UPSTREAM-SOUL-BODY" in doc
    # Clawbench addendum header must be present but NOT replace the
    # upstream sections.
    assert "## Clawbench Runtime Addendum" in doc
