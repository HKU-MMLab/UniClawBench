"""Round 9 / B2: Clawbench's single-process EDICT adapter is a
condensed re-implementation of cft0808/edict's Orchestrator +
Dispatcher pair.  Because we maintain the adapter ourselves while
pulling the official agent specs / SOUL files from the upstream
tarball, the state machine / agent registry / org routing can drift
silently when upstream changes.

These tests parse the official source we extract to ``downloads/edict/``
and assert that the Clawbench adapter agrees on:

- The set of agent IDs (``openclaw.json`` ↔ ``agents.json``)
- The terminal state set
- The state → agent dispatch table
- The org → agent dispatch table
- SOUL.md availability for every agent we expect to dispatch to

A failure here means the upstream `cft0808/edict` snapshot moved in a
direction the adapter does not yet handle.  Fix the adapter, NOT the
test.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
EDICT_DIR = ROOT / "downloads" / "edict"
OFFICIAL_TASK_MODEL = EDICT_DIR / "edict" / "backend" / "app" / "models" / "task.py"
OFFICIAL_AGENTS_JSON = EDICT_DIR / "agents.json"
OFFICIAL_OPENCLAW_JSON = EDICT_DIR / "docker" / "demo_data" / "openclaw.json"

ORCHESTRATOR = ROOT / "docker" / "edict_orchestrator.py"


pytestmark = pytest.mark.skipif(
    not OFFICIAL_TASK_MODEL.is_file(),
    reason="downloads/edict/edict/backend/app/models/task.py not present "
    "(offline test env or missing tarball extraction)",
)


# --------------------------------------------------------------------------
# Parsers — pull dicts out of the official + adapter source without
# importing them (the official module needs sqlalchemy, which Clawbench
# doesn't ship; the orchestrator runs inside docker).
# --------------------------------------------------------------------------


def _parse_python_dict(source: str, name: str) -> dict:
    """Extract a top-level ``name = {...}`` assignment from a Python
    source file and return the resulting dict.  We can't ``import`` the
    official module (sqlalchemy isn't a host dep), but
    ``ast.literal_eval`` handles the simple dict shape used here.

    Both files use ``TaskState.<Name>: "<agent>"`` keys for STATE_AGENT_MAP;
    we strip the ``TaskState.`` prefix so values become plain strings.
    """
    tree = ast.parse(source)
    for node in tree.body:
        targets: list[str] = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            # Adapter uses ``STATE_AGENT_MAP: dict[str, str] = {...}``
            # which parses as AnnAssign, not Assign.
            targets = [node.target.id]
        if name not in targets:
            continue
        segment = ast.get_source_segment(source, node)
        if segment is None:
            continue
        rhs = segment.split("=", 1)[1].strip()
        rhs = re.sub(r"TaskState\.([A-Za-z_]+)", r'"\1"', rhs)
        return ast.literal_eval(rhs)
    raise AssertionError(f"name={name!r} not found as top-level assignment")


def _parse_python_set(source: str, name: str) -> set:
    """Same as _parse_python_dict but for a set assignment."""
    value = _parse_python_dict(source, name)
    return set(value)


# --------------------------------------------------------------------------
# Cached source loads (one read per file across all tests in the module)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def official_task_source() -> str:
    return OFFICIAL_TASK_MODEL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def orchestrator_source() -> str:
    return ORCHESTRATOR.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def official_agents_ids() -> list[str]:
    items = json.loads(OFFICIAL_AGENTS_JSON.read_text(encoding="utf-8"))
    return sorted({item["id"] for item in items if isinstance(item, dict) and item.get("id")})


@pytest.fixture(scope="module")
def openclaw_demo_ids() -> list[str]:
    payload = json.loads(OFFICIAL_OPENCLAW_JSON.read_text(encoding="utf-8"))
    items = (payload.get("agents") or {}).get("list") or []
    return sorted({item["id"] for item in items if isinstance(item, dict) and item.get("id")})


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_agent_ids_match_between_agents_json_and_openclaw_json(
    official_agents_ids: list[str],
    openclaw_demo_ids: list[str],
) -> None:
    """``agents.json`` is the canonical agent registry; ``openclaw.json``
    is the path-rewritten copy Clawbench reads via ``edict_agent_specs``.
    Drift between the two means our single-process adapter sees a
    different roster than the upstream system."""
    assert official_agents_ids == openclaw_demo_ids, (
        f"agents.json ({official_agents_ids}) != openclaw.json "
        f"({openclaw_demo_ids}); upstream changed the agent set"
    )


def test_clawbench_specs_match_official_agent_set(openclaw_demo_ids: list[str]) -> None:
    """The lib/runner/edict.py loader (``edict_agent_ids``) must return
    the same agent set as the upstream ``openclaw.json`` it parses."""
    from lib.runner.edict import edict_agent_ids

    assert sorted(edict_agent_ids()) == openclaw_demo_ids


def test_terminal_states_match(
    official_task_source: str,
    orchestrator_source: str,
) -> None:
    """``Done`` / ``Cancelled`` are terminal in upstream; the adapter
    must agree, otherwise a Done task wouldn't trigger the final taizi
    report (or worse, a Cancelled task keeps spinning)."""
    official = _parse_python_set(official_task_source, "TERMINAL_STATES")
    adapter = _parse_python_set(orchestrator_source, "TERMINAL_STATES")
    assert official == adapter, (
        f"upstream TERMINAL_STATES={official}, adapter={adapter}"
    )


def test_org_agent_map_matches(
    official_task_source: str,
    orchestrator_source: str,
) -> None:
    """六部 dispatch: 户部/礼部/兵部/刑部/工部/吏部 → hubu/libu/bingbu/xingbu/gongbu/libu_hr.
    If upstream renames an org (e.g. a 七部 expansion), the adapter
    silently fails to route those tasks."""
    official = _parse_python_dict(official_task_source, "ORG_AGENT_MAP")
    adapter = _parse_python_dict(orchestrator_source, "ORG_AGENT_MAP")
    assert official == adapter, (
        f"ORG_AGENT_MAP drift: upstream={official}, adapter={adapter}"
    )


def test_state_agent_map_values_match_for_dispatchable_states(
    official_task_source: str,
    orchestrator_source: str,
) -> None:
    """For every state the adapter dispatches on, the agent_id must
    match upstream.  We don't require the adapter to dispatch on EVERY
    upstream state — Doing / Next / Blocked are intentionally skipped
    because they indicate an agent is already running or external
    intervention is needed (no waking).  But where the adapter does
    have a mapping, the value must agree."""
    official = _parse_python_dict(official_task_source, "STATE_AGENT_MAP")
    adapter = _parse_python_dict(orchestrator_source, "STATE_AGENT_MAP")
    # Every adapter state must exist in official + with matching value
    for state, agent in adapter.items():
        assert state in official, (
            f"adapter dispatches on state={state!r} that doesn't exist "
            f"in upstream TaskState"
        )
        assert official[state] == agent, (
            f"adapter routes state={state!r} → {agent!r} but upstream "
            f"routes it → {official[state]!r}"
        )


def test_state_agent_map_covers_dispatchable_upstream_states(
    official_task_source: str,
    orchestrator_source: str,
) -> None:
    """The adapter must dispatch on every upstream state EXCEPT:
    - Doing / Next: an agent is already running, no need to wake
    - Blocked: external intervention; no autonomous progress
    - Done / Cancelled: terminal, handled by TERMINAL_STATES branch

    If upstream adds a new dispatchable state and we don't, tasks will
    stall in that state until wall-clock timeout."""
    official = _parse_python_dict(official_task_source, "STATE_AGENT_MAP")
    adapter = _parse_python_dict(orchestrator_source, "STATE_AGENT_MAP")
    missing = set(official) - set(adapter)
    assert not missing, (
        f"adapter is missing dispatch for upstream STATE_AGENT_MAP entries: "
        f"{sorted(missing)} — these states will stall until timeout"
    )


def test_every_dispatched_agent_has_soul_md(orchestrator_source: str) -> None:
    """Every agent id the adapter dispatches to (via STATE_AGENT_MAP /
    ORG_AGENT_MAP) must have an upstream SOUL.md.  Missing SOUL means
    the agent boots with an empty role spec and produces nonsense."""
    state_map = _parse_python_dict(orchestrator_source, "STATE_AGENT_MAP")
    org_map = _parse_python_dict(orchestrator_source, "ORG_AGENT_MAP")
    dispatched = set(state_map.values()) | set(org_map.values())
    missing: list[str] = []
    for agent_id in sorted(dispatched):
        soul_path = EDICT_DIR / "agents" / agent_id / "SOUL.md"
        if not soul_path.is_file():
            missing.append(agent_id)
    assert not missing, (
        f"adapter dispatches to agents without upstream SOUL.md: {missing}"
    )


def test_clawbench_agent_group_covers_all_dispatchable_agents() -> None:
    """``edict_agent_group()`` returning "" silently drops the agent
    from the AGENTS.md group-rule injection.  Every agent that the
    orchestrator dispatches to MUST get a non-empty group.  Agents that
    are in the registry but never dispatched (e.g. zaochao =
    钦天监 news aggregator) are allowed empty."""
    from lib.runner.edict import edict_agent_group

    text = ORCHESTRATOR.read_text(encoding="utf-8")
    state_map = _parse_python_dict(text, "STATE_AGENT_MAP")
    org_map = _parse_python_dict(text, "ORG_AGENT_MAP")
    dispatched = set(state_map.values()) | set(org_map.values())
    bad = [a for a in sorted(dispatched) if not edict_agent_group(a)]
    assert not bad, (
        f"edict_agent_group() returns '' for dispatchable agents {bad}; "
        "they will miss group-level AGENTS.md content"
    )


def test_upstream_state_machine_has_no_new_dispatchable_terminals(
    official_task_source: str,
) -> None:
    """Sanity: official TERMINAL_STATES + dispatched states + non-dispatched
    transitions (Doing/Next/Blocked) must cover every TaskState enum
    member.  If upstream introduces a brand-new state we haven't
    classified, this test catches it before silent dispatch failure."""
    # Pull TaskState enum members out of the source.
    members: set[str] = set()
    for line in official_task_source.splitlines():
        m = re.match(r"\s+([A-Za-z]+)\s*=\s*\"([A-Za-z]+)\"\s*$", line)
        if m and m.group(1) == m.group(2):
            members.add(m.group(1))
    terminal = _parse_python_set(official_task_source, "TERMINAL_STATES")
    dispatchable = set(_parse_python_dict(official_task_source, "STATE_AGENT_MAP"))
    skipped = {"Doing", "Next", "Blocked"}  # intentionally non-dispatchable
    classified = terminal | dispatchable | skipped
    unclassified = members - classified
    assert not unclassified, (
        f"upstream introduced TaskState members {sorted(unclassified)} that "
        f"the adapter has not classified.  Either add them to "
        f"STATE_AGENT_MAP, TERMINAL_STATES, or extend the 'skipped' set "
        f"in test_edict_adapter_parity.py with an explanation."
    )
