"""Per-attempt artifact collection entry point.

This module owns the orchestration of "what artefacts do we copy out
of the container once the executor has finished a turn?" — the
container-side ``cp`` calls, the inline-image rewriter, the
post-collection transcript normalisation, AND the edict multi-agent
session fan-out (because the fan-out happens as one step of the
collection pipeline; splitting it out as a sibling module added a
file without adding clarity).

Two related concerns still live next door because they have their
own optional dependency / independent test surface:

* :mod:`lib.runner.quality_artifacts` — PPTX layout/density probing
  (optional Pillow dependency)
* :mod:`lib.runner.usage_ledger` — token accounting & rollups
  (independent test files exercise the proxy-adapter event slicing)

Everything here takes plain :class:`Path` / :class:`TaskSpec` arguments
and holds no runtime state of its own — the module is safe to re-import
and to call repeatedly within a single attempt.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

from ..proxy import write_local
from ..status import SCORE_SCHEMA_VERSION
from ..supervision.transcripts import EDICT_AGENT_LABELS
from ..task import TaskSpec
from .docker import docker_cp_from_container, docker_exec
from .edict import edict_agent_group, edict_agent_ids, read_edict_runtime_metadata
from .media import _rewrite_base64_image_files_in_tree, attach_inline_images_dir
from .quality_artifacts import _generate_pptx_quality_artifacts
from .sessions import (
    resolve_openclaw_agent_all_session_paths,
    resolve_openclaw_transcript_path,
)
from .task_config import (
    effective_agent_id_for_task,
    normalize_agent_sys,
    transcript_targets_for_task,
)
from .transcripts import (
    annotate_transcript_with_agent,
    build_tool_usage_summary,
    merge_agent_transcripts,
    normalize_transcript_text,
    parse_json_lines,
    summarize_transcript_tools,
)


PRIVATE_SERVICE_ROOT = Path("/opt/clawbench/.harness/services")
AGENT_SESSION_ARTIFACTS_DIR = "agent_sessions"


# ── artifact profile gate ────────────────────────────────────────────────
# The supervisor and user simulator each generate a full prompt and raw
# response per cycle. Persisting all of that by default leaks framework
# monitoring details — hidden rubric framing, workspace manifests, internal
# debug commentary — into per-attempt directories, which is fine for local
# debugging but unsuitable for open-source / public sharing.
#
# Profiles:
#   - "public"  (default): only safe summaries persist — decision JSON,
#                          transport/elapsed_ms/image_inputs. No full
#                          prompts, no raw responses, no workspace manifest.
#   - "debug"            : full prompts, raw responses, stdout/stderr,
#                          workspace manifest, readme. Use only when you
#                          need to inspect supervisor behaviour locally.
#
# Selection is via env var ``CLAWBENCH_ARTIFACT_PROFILE``.

ARTIFACT_PROFILE_PUBLIC = "public"
ARTIFACT_PROFILE_DEBUG = "debug"
_VALID_ARTIFACT_PROFILES = frozenset({ARTIFACT_PROFILE_PUBLIC, ARTIFACT_PROFILE_DEBUG})
DEFAULT_ARTIFACT_PROFILE = ARTIFACT_PROFILE_PUBLIC


def current_artifact_profile() -> str:
    """Return the active artifact profile, defaulting to ``public``.

    An unrecognised value falls back to ``public`` rather than raising — the
    runner is long-running and an env-var typo must never abort an attempt.
    """
    raw = (os.environ.get("CLAWBENCH_ARTIFACT_PROFILE") or "").strip().lower()
    return raw if raw in _VALID_ARTIFACT_PROFILES else DEFAULT_ARTIFACT_PROFILE


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_score_json(out_dir: Path, task: TaskSpec, score: dict[str, Any]) -> None:
    """Persist a score dict to ``<out_dir>/score.json`` with ``success_threshold``.

    Path B (``scripts/orchestra/refresh_summary.py:_derive_status_from_artifacts``)
    must apply the same score-based pass-promotion as Path A, but it has no
    access to the task YAML at refresh time. Persisting ``task.success_threshold``
    here lets both paths share the same threshold for free; older artifacts that
    pre-date this field gracefully skip promotion at refresh time.
    """
    payload = dict(score or {})
    payload["schema_version"] = SCORE_SCHEMA_VERSION
    payload["success_threshold"] = float(task.success_threshold)
    write_local(out_dir / "score.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(content if content.endswith("\n") else content + "\n")


def normalize_proxy_value(value: str) -> str:
    return value.strip().rstrip("/")


def private_service_dir(task: TaskSpec, service_path: str) -> str:
    return str(PRIVATE_SERVICE_ROOT / task.task_id / service_path)


# ── edict multi-agent transcript fan-out ──────────────────────────────
# When an edict backend run completes the container holds one
# ``/root/.openclaw/agents/<id>/sessions/*.jsonl`` per registered agent
# plus any nested subagent sessions spawned via ``sessions_spawn``.
# This function copies every one of those streams out, annotates them
# with the owning agent id, and merges the result into a single canonical
# ``<attempt>/transcript.jsonl`` that downstream readers (WebUI,
# supervisor workspace prep) can consume identically to a single-agent
# transcript.  Lives here because it's a step within
# ``collect_attempt_artifacts`` — the openclaw_edict branch invokes it
# before the normal transcript copy fallback.


def collect_edict_agent_session_artifacts(container: str, out_dir: Path, task: TaskSpec) -> bool:
    agent_session_paths = resolve_openclaw_agent_all_session_paths(container, task)
    if not agent_session_paths:
        return False
    session_root = out_dir / AGENT_SESSION_ARTIFACTS_DIR
    session_root.mkdir(parents=True, exist_ok=True)
    collected_streams: list[tuple[str, str]] = []
    per_agent_usage: dict[str, dict[str, Any]] = {}
    manifest_agents: list[dict[str, Any]] = []
    for agent_id in edict_agent_ids():
        paths = agent_session_paths.get(agent_id) or []
        if not paths:
            continue
        agent_dir = session_root / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        # Index 0 is the most-recent session (the agent's main ``chat``
        # session for every cycle after the first). Copy it as the
        # canonical ``transcript.jsonl`` so existing downstream readers
        # (WebUI, supervisor workspace prep) keep working unchanged.
        primary_path = str(paths[0]).strip()
        if not primary_path:
            continue
        copied = docker_cp_from_container(container, primary_path, agent_dir / "transcript.jsonl")
        if not copied:
            continue
        session_index_path = f"/root/.openclaw/agents/{agent_id}/sessions/sessions.json"
        docker_cp_from_container(container, session_index_path, agent_dir / "sessions.json")
        transcript_text = (agent_dir / "transcript.jsonl").read_text(encoding="utf-8", errors="ignore")
        if not transcript_text.strip():
            continue
        annotated_text = annotate_transcript_with_agent(transcript_text, agent_id)
        summary = build_tool_usage_summary(annotated_text)
        per_agent_usage[agent_id] = summary
        write_local(agent_dir / "tool_usage.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        collected_streams.append((agent_id, transcript_text))
        # Additional sessions (nested subagents spawned via
        # ``sessions_spawn``) go under ``<agent>/subagents/<uuid>.jsonl``
        # so the supervisor can audit what the subagent actually did
        # without confusing it with the agent's main chat session.
        subagent_records: list[dict[str, Any]] = []
        for extra_path_raw in paths[1:]:
            extra_path = str(extra_path_raw).strip()
            if not extra_path:
                continue
            subagent_uuid = Path(extra_path).stem or f"session-{len(subagent_records)}"
            subagents_dir = agent_dir / "subagents"
            subagents_dir.mkdir(parents=True, exist_ok=True)
            dest_file = subagents_dir / f"{subagent_uuid}.jsonl"
            if not docker_cp_from_container(container, extra_path, dest_file):
                continue
            sub_text = dest_file.read_text(encoding="utf-8", errors="ignore")
            if not sub_text.strip():
                continue
            annotated_sub = annotate_transcript_with_agent(sub_text, agent_id)
            sub_summary = build_tool_usage_summary(annotated_sub)
            write_local(subagents_dir / f"{subagent_uuid}.tool_usage.json", json.dumps(sub_summary, ensure_ascii=False, indent=2) + "\n")
            # Merge the subagent events into the same cross-agent stream
            # so the merged transcript reflects the real wall-clock order
            # (nested subagent work often falls between two of the
            # parent's main-session events).
            collected_streams.append((agent_id, sub_text))
            subagent_records.append(
                {
                    "sessionId": subagent_uuid,
                    "sourcePath": extra_path,
                    "eventCount": len(parse_json_lines(annotated_sub)),
                    "toolCallCount": len(sub_summary.get("tool_calls") or []),
                    "toolCounts": sub_summary.get("tool_counts") or {},
                }
            )
        manifest_agents.append(
            {
                "agentId": agent_id,
                "label": EDICT_AGENT_LABELS.get(agent_id, agent_id),
                "group": edict_agent_group(agent_id),
                "sourcePath": primary_path,
                "eventCount": len(parse_json_lines(annotated_text)),
                "toolCallCount": len(summary.get("tool_calls") or []),
                "toolCounts": summary.get("tool_counts") or {},
                "subagents": subagent_records,
            }
        )
    if not collected_streams:
        return False
    merged_text = merge_agent_transcripts(collected_streams)
    if merged_text:
        write_local(out_dir / "transcript.jsonl", merged_text)
        merged_summary = build_tool_usage_summary(merged_text)
        merged_summary["agents"] = per_agent_usage
        write_local(out_dir / "tool_usage.json", json.dumps(merged_summary, ensure_ascii=False, indent=2) + "\n")
    # Round 9 / B3: surface the upstream cft0808/edict revision baked
    # into the image so the WebUI can render an "EDICT @ <commit>"
    # badge.  Read from inside the container first (that's what
    # actually ran); fall back to the host downloads/ snapshot when
    # the in-container files are missing (older image pre-Round-9-B1).
    edict_meta = _read_edict_metadata_from_container(container)
    write_local(
        out_dir / "agent_sessions_manifest.json",
        json.dumps(
            {
                "primaryAgentId": effective_agent_id_for_task(task),
                "edictMode": edict_meta["mode"],
                "edictCommit": edict_meta["commit"],
                "edictVersion": edict_meta["version"],
                "agents": manifest_agents,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return True


def _read_edict_metadata_from_container(container: str) -> dict[str, str]:
    """Best-effort read of /opt/edict/EDICT_COMMIT + EDICT_VERSION from
    the live container.  Falls back to host-side downloads/ snapshot
    when the in-container files are absent (e.g. legacy image built
    before Round 9 / B1 added the COPY).
    """
    fallback = read_edict_runtime_metadata()
    result = dict(fallback)
    for key, in_container_path in (
        ("commit", "/opt/edict/EDICT_COMMIT"),
        ("version", "/opt/edict/EDICT_VERSION"),
    ):
        try:
            proc = docker_exec(container, f"cat {in_container_path}", timeout_seconds=10)
        except Exception:
            continue
        if proc.returncode != 0:
            continue
        value = (proc.stdout or "").strip()
        if value:
            result[key] = value
    return result


def collect_attempt_artifacts(container: str, out_dir: Path, task: TaskSpec) -> None:
    result_dir = out_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)
    docker_cp_from_container(container, "/tmp_workspace/results/.", result_dir)
    # Fix up screenshots that the agent accidentally saved as base64 text
    # instead of raw bytes (generic write/edit tools don't decode for
    # the model). Purely a display salvage — the WebUI and downstream
    # viewers can't decode ASCII base64 as an image otherwise.
    rewritten = _rewrite_base64_image_files_in_tree(result_dir)
    if rewritten:
        print(
            f"[artifacts] rewrote {len(rewritten)} base64-as-text image file(s): "
            + ", ".join(str(p.relative_to(result_dir)) for p in rewritten),
            file=sys.stderr,
            flush=True,
        )
    pptx_quality_artifacts = _generate_pptx_quality_artifacts(result_dir)
    if pptx_quality_artifacts:
        print(
            "[artifacts] generated PPTX quality evidence for supervisor: "
            + ", ".join(str(p.relative_to(result_dir)) for p in pptx_quality_artifacts[:8])
            + (" ..." if len(pptx_quality_artifacts) > 8 else ""),
            file=sys.stderr,
            flush=True,
        )
    docker_cp_from_container(container, "/tmp_workspace/clawbench/logs/.", out_dir / "logs")
    # Mirror MCP tool artifacts (playwright-mcp auto-saved screenshots,
    # console logs, DOM snapshots) into an ``mcp_artifacts/`` sibling dir
    # on the host. Deliberately separate from ``result/`` so the
    # supervisor / user-simulator workspace (which only sees ``result/``
    # via ``_copy_visible_workspace_files``) is NOT flooded with dozens of
    # auto-screenshots — that previously caused Codex to call view_image
    # on 5+ images and blow the 272K token context limit. The WebUI picks
    # these up via a separate ``mcpArtifacts`` field so they still render
    # in the Execution Flow panel.
    mcp_artifacts_dir = out_dir / "mcp_artifacts"
    mcp_artifacts_dir.mkdir(parents=True, exist_ok=True)
    docker_cp_from_container(container, "/tmp_workspace/.mcp_artifacts/.", mcp_artifacts_dir)
    agent_sys = normalize_agent_sys(task.agent_sys)
    # Bind the attempt's inline_images/ directory so any ``type:"image"``
    # blocks inside transcript events get their base64 payload persisted
    # to ``<attempt>/inline_images/<hash>.<ext>`` and replaced in-text
    # with a small ``[image: inline_images/...]`` reference. Keeps the
    # transcript (which supervisor / user-simulator mirror as
    # ``visible/transcript.jsonl``, plus the per-agent transcripts under
    # ``agent_sessions/``) free of multi-MB base64 blobs while letting the
    # WebUI still render the images.
    inline_images_dir = out_dir / "inline_images"
    inline_images_dir.mkdir(parents=True, exist_ok=True)
    with attach_inline_images_dir(inline_images_dir):
        if agent_sys in {"openclaw", "openclaw_edict"}:
            docker_cp_from_container(container, "/tmp/openclaw/.", out_dir / "openclaw")
            if agent_sys == "openclaw_edict" and collect_edict_agent_session_artifacts(container, out_dir, task):
                transcript_targets = []
            else:
                transcript_targets = []
                resolved_transcript = resolve_openclaw_transcript_path(container, task)
                if resolved_transcript:
                    transcript_targets.append(resolved_transcript)
                transcript_targets.extend(transcript_targets_for_task(task))
                for transcript_target in transcript_targets:
                    if docker_cp_from_container(container, transcript_target, out_dir / "transcript.jsonl"):
                        break
        elif agent_sys == "nanobot":
            for transcript_target in transcript_targets_for_task(task):
                if docker_cp_from_container(container, transcript_target, out_dir / "transcript.jsonl"):
                    break

        transcript_path = out_dir / "transcript.jsonl"
        if transcript_path.exists():
            transcript = transcript_path.read_text(encoding="utf-8", errors="ignore")
            normalized_transcript = normalize_transcript_text(transcript)
            if normalized_transcript != transcript:
                write_local(out_dir / "transcript_raw.jsonl", transcript)
                write_local(transcript_path, normalized_transcript)
                transcript = normalized_transcript
            # Also normalize each per-agent edict transcript in-place so the
            # supervisor's ``visible/agent_sessions/`` copy (which
            # ``_copy_visible_workspace_files`` will tree-cp later) stays
            # base64-free. Safe no-op on non-edict runs since the loop iter
            # is empty.
            for per_agent in sorted((out_dir / AGENT_SESSION_ARTIFACTS_DIR).glob("*/transcript.jsonl")):
                try:
                    raw = per_agent.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    # Round-5 Phase 2 (H5): log silent skips so transcript I/O
                    # bugs are debuggable.  Continue is still correct here —
                    # one corrupt per-agent file shouldn't kill the whole
                    # collection pipeline — but operators need to see it.
                    LOG.error("per-agent transcript read failed (%s): %s", per_agent, e)
                    continue
                norm = normalize_transcript_text(raw)
                if norm != raw:
                    # Preserve the pre-normalization copy for evidence.
                    raw_backup = per_agent.with_name("transcript_raw.jsonl")
                    try:
                        write_local(raw_backup, raw)
                    except Exception as e:
                        LOG.error("transcript_raw.jsonl backup write failed (%s): %s", raw_backup, e)
                    write_local(per_agent, norm)
            if agent_sys == "openclaw_edict" and (out_dir / "agent_sessions_manifest.json").exists():
                summary = build_tool_usage_summary(transcript)
                per_agent_usage: dict[str, dict] = {}
                for path in sorted((out_dir / AGENT_SESSION_ARTIFACTS_DIR).glob("*/tool_usage.json")):
                    agent_id = path.parent.name
                    try:
                        per_agent_usage[agent_id] = json.loads(path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as e:
                        # Round-5 Phase 2 (H5): log so partial tool-usage data
                        # gaps don't hide silently.
                        LOG.error("per-agent tool_usage.json decode failed (%s): %s", path, e)
                        continue
                if per_agent_usage:
                    summary["agents"] = per_agent_usage
                write_local(out_dir / "tool_usage.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
            else:
                summarize_transcript_tools(transcript, out_dir)

        # (usage.json is written at turn-end by ``finalize_cycle_usage_
        # payload``, NOT here — ``collect_attempt_artifacts`` runs
        # BEFORE ``append_executor_usage_ledger`` + ``append_role_usage_
        # ledger`` have finished writing this cycle's rows, so rolling
        # up at this point would miss them.)


def collect_runtime_probe(container: str, out_dir: Path) -> None:
    probe_script = """python3 - <<'PY'
import json
import subprocess
from pathlib import Path

def run_shell(command: str) -> list[str]:
    proc = subprocess.run(command, shell=True, text=True, capture_output=True)
    return [line for line in proc.stdout.splitlines() if line.strip()]

payload = {
    "windows": run_shell("wmctrl -lp || true"),
    "processes": {
        "code": run_shell("pgrep -af '[c]ode' || true"),
        "chromium": run_shell("pgrep -af '[c]hromium|[c]hrome' || true"),
        "openclaw": run_shell("pgrep -af '[o]penclaw' || true"),
        "nanobot": run_shell("pgrep -af '[n]anobot' || true"),
    },
    "result_files": sorted(
        str(path.relative_to('/tmp_workspace/results'))
        for path in Path('/tmp_workspace/results').rglob('*')
        if path.is_file()
    ),
}
print(json.dumps(payload, ensure_ascii=False))
PY"""
    result = docker_exec(container, probe_script)
    if result.returncode == 0 and (result.stdout or "").strip():
        write_local(out_dir / "runtime_probe.json", result.stdout.strip() + "\n")
    docker_exec(
        container,
        "mkdir -p /tmp_workspace/clawbench && (scrot /tmp_workspace/clawbench/runtime_probe_desktop.png >/dev/null 2>&1 || true)",
    )
    docker_cp_from_container(container, "/tmp_workspace/clawbench/runtime_probe_desktop.png", out_dir / "runtime_probe_desktop.png")


def write_supervision_component_artifacts(
    cycle_dir: Path,
    name: str,
    component: dict | None,
    *,
    profile: str | None = None,
) -> None:
    """Persist supervisor / user-simulator side files for one cycle.

    ``profile`` defaults to :func:`current_artifact_profile`. In ``public``
    mode only ``{name}_decision.json`` is written — the supervisor's
    structured judgement is the public-safe contract. In ``debug`` mode the
    full set (prompt, raw response, stdout/stderr, workspace manifest,
    readme) is also persisted, matching the legacy behaviour.
    """
    if not isinstance(component, dict) or not component:
        return
    effective_profile = profile if profile in _VALID_ARTIFACT_PROFILES else current_artifact_profile()
    decision = component.get("decision")
    if decision is not None:
        write_local(cycle_dir / f"{name}_decision.json", json.dumps(decision, ensure_ascii=False, indent=2) + "\n")
    if effective_profile != ARTIFACT_PROFILE_DEBUG:
        return
    prompt = component.get("prompt")
    raw_response = component.get("raw_response")
    stdout = component.get("stdout")
    stderr = component.get("stderr")
    input_workspace = component.get("input_workspace")
    input_readme = component.get("input_readme")
    if prompt:
        write_local(cycle_dir / f"{name}_prompt.txt", str(prompt))
    if raw_response:
        write_local(cycle_dir / f"{name}_response.txt", str(raw_response))
    if stdout:
        write_local(cycle_dir / f"{name}_stdout.log", str(stdout))
    if stderr:
        write_local(cycle_dir / f"{name}_stderr.log", str(stderr))
    if input_workspace is not None:
        write_local(cycle_dir / f"{name}_input_workspace.json", json.dumps(input_workspace, ensure_ascii=False, indent=2) + "\n")
    if input_readme:
        write_local(cycle_dir / f"{name}_input_readme.md", str(input_readme))


def supervision_component_summary(component: dict | None, *, profile: str | None = None) -> dict:
    """Compact summary embedded in ``supervision_trace.jsonl`` components.

    ``public`` profile keeps only transport / elapsed_ms / image_inputs and
    a ``decision`` reference; the prompt and workspace manifest are
    intentionally omitted because supervision_trace.jsonl is consumed by
    operators who can always opt into ``debug`` for a richer reproduction.
    """
    if not isinstance(component, dict) or not component:
        return {}
    effective_profile = profile if profile in _VALID_ARTIFACT_PROFILES else current_artifact_profile()
    summary = {
        "transport": str(component.get("transport") or ""),
        "elapsed_ms": int(component.get("elapsed_ms") or 0),
        "image_inputs": list(component.get("image_inputs") or []),
    }
    if component.get("decision") is not None:
        summary["decision"] = component.get("decision")
    if effective_profile == ARTIFACT_PROFILE_DEBUG:
        if component.get("prompt"):
            summary["prompt"] = str(component.get("prompt"))
        if component.get("input_workspace") is not None:
            summary["input_workspace"] = component.get("input_workspace")
        if component.get("input_readme"):
            summary["input_readme"] = component.get("input_readme")
        if component.get("workspace_root"):
            summary["workspace_root"] = str(component.get("workspace_root"))
    return summary
