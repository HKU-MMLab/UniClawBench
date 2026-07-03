"""openclaw session/transcript path discovery.

openclaw (and its edict extension) stores each agent's chat log as one or
more ``<uuid>.jsonl`` files under
``/root/.openclaw/agents/<agent_id>/sessions/`` inside the container. This
module wraps the :func:`lib.runner.docker.docker_exec` primitive so the
host can ask "where are the transcripts?" without shelling out or knowing
the directory layout.

Exposed API:

``resolve_openclaw_agent_all_session_paths``
    Return every session file (main + subagent) per edict agent,
    ordered most-recent-first.

``resolve_openclaw_agent_transcript_paths``
    Thin wrapper that keeps only the newest file per agent — used by
    callers that don't care about the full subagent chain.

``resolve_openclaw_transcript_path``
    Legacy "one agent, one path" shortcut for single-agent openclaw runs.
"""
from __future__ import annotations

import json

from ..task import TaskSpec
from .docker import docker_exec
from .edict import edict_agent_ids
from .task_config import effective_agent_id_for_task, normalize_agent_sys


def resolve_openclaw_agent_all_session_paths(container: str, task: TaskSpec) -> dict[str, list[str]]:
    """Return every session file (main + nested subagent) under each
    edict agent's sessions dir, ordered most-recent-first.

    Each agent dir ``/root/.openclaw/agents/<id>/sessions/`` may contain:
    - the agent's own "main" chat session (session key ``agent:<id>:main``)
    - one or more subagent sessions spawned via ``sessions_spawn``
      (session key ``agent:<id>:subagent:<uuid>``)

    All of them land in the same directory as individual ``<uuid>.jsonl``
    files. Earlier versions of this helper returned only the most recent
    one, which hid the entire subagent chain from the supervisor — see
    the ``openclaw_edict`` post-mortem for why that matters.
    """
    preferred_agent_id = effective_agent_id_for_task(task)
    preferred_agents = [preferred_agent_id]
    if normalize_agent_sys(task.agent_sys) == "openclaw_edict":
        preferred_agents.extend(agent_id for agent_id in edict_agent_ids() if agent_id != preferred_agent_id)
    script = f"""python3 - <<'PY'
import json
from pathlib import Path

preferred_agents = json.loads({json.dumps(json.dumps(preferred_agents, ensure_ascii=False))})
root = Path("/root/.openclaw/agents")

def candidates_for(agent_dir: Path):
    session_dir = agent_dir / "sessions"
    if not session_dir.exists():
        return []
    candidates = []
    index_path = session_dir / "sessions.json"
    if index_path.exists():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {{}}
        if isinstance(payload, dict):
            for value in payload.values():
                if not isinstance(value, dict):
                    continue
                session_file = str(value.get("sessionFile") or "").strip()
                if not session_file:
                    continue
                candidates.append((int(value.get("updatedAt") or 0), session_file))
    for path in sorted(session_dir.glob("*.jsonl"), key=lambda item: item.stat().st_mtime_ns, reverse=True):
        candidates.append((int(path.stat().st_mtime_ns), str(path)))
    seen = set()
    ranked = []
    for updated_at, raw_path in sorted(candidates, key=lambda item: item[0], reverse=True):
        if not raw_path or raw_path in seen:
            continue
        seen.add(raw_path)
        path = Path(raw_path)
        if path.exists() and path.is_file():
            ranked.append(str(path))
    return ranked

result = {{}}
visited = set()
for agent_id in preferred_agents:
    if not agent_id or agent_id in visited:
        continue
    visited.add(agent_id)
    agent_dir = root / agent_id
    ranked = candidates_for(agent_dir)
    if ranked:
        result[agent_id] = ranked

if root.exists():
    for agent_dir in sorted(root.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name in visited:
            continue
        ranked = candidates_for(agent_dir)
        if ranked:
            result[agent_dir.name] = ranked

print(json.dumps(result, ensure_ascii=False))
PY"""
    result = docker_exec(container, script)
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for agent_id, value in payload.items():
        if isinstance(value, list):
            paths = [str(item) for item in value if str(item).strip()]
        elif isinstance(value, str) and value.strip():
            # Backward compat: older callers sent a single path string.
            paths = [value.strip()]
        else:
            paths = []
        if paths:
            normalized[str(agent_id)] = paths
    return normalized


def resolve_openclaw_agent_transcript_paths(container: str, task: TaskSpec) -> dict[str, str]:
    """Return the most-recent session file per edict agent.

    Thin wrapper over ``resolve_openclaw_agent_all_session_paths`` kept
    for callers that only care about the primary ("main") session, not
    the whole subagent chain.
    """
    all_sessions = resolve_openclaw_agent_all_session_paths(container, task)
    return {agent_id: paths[0] for agent_id, paths in all_sessions.items() if paths}


def resolve_openclaw_transcript_path(container: str, task: TaskSpec) -> str:
    preferred_agent_id = effective_agent_id_for_task(task)
    paths = resolve_openclaw_agent_transcript_paths(container, task)
    if preferred_agent_id in paths:
        return str(paths[preferred_agent_id])
    return next(iter(paths.values()), "")
