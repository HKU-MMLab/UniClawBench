"""Role-scoped workspace preparation.

``prepare_role_workspace`` assembles the on-disk workspace each Codex
role sees — executor transcripts, result artifacts, reference files,
privacy assets, history ledger — plus a ``workspace_manifest.json``
describing what's present. This is the materialisation step invoked
from ``answer_supervisor``, ``user_simulator``, and the orchestrator
just before each role's codex container is launched.

The transcript-chunking helpers (``_copy_transcript_with_optional_chunking``
and friends) are kept here because they're only used by
``_copy_visible_workspace_files``. They split transcripts >80 KB into
``transcript_full/part_NNN.jsonl`` slices plus a head+tail capped view,
so the role's prompt can cat a single small file by default and load
the exact chunk it needs on demand.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .codex import CONTAINER_WORKDIR
from .common import SupervisorContext


def _supervision_summary_mode_resolved() -> str:
    """Round 9 / A2: thin re-export of ``content.supervision_summary_mode``
    so the workspace builder can stamp the resolved mode into
    ``workspace_manifest.json`` without forcing a top-level import
    cycle (``content.py`` imports from this module via
    ``transcripts``)."""
    from .content import supervision_summary_mode

    return supervision_summary_mode()


def role_session_dir(context: SupervisorContext, role: str) -> Path:
    return context.attempt.out_dir / "codex_sessions" / role


def role_workspace_dir(context: SupervisorContext, role: str) -> Path:
    return role_session_dir(context, role) / "workspace"


def role_home_dir(context: SupervisorContext, role: str) -> Path:
    return role_session_dir(context, role) / "home"


def role_runtime_dir(context: SupervisorContext, role: str) -> Path:
    return role_session_dir(context, role) / "runtime"


def role_history_path(context: SupervisorContext, role: str) -> Path:
    return role_session_dir(context, role) / "history.jsonl"


def load_role_history(context: SupervisorContext, role: str) -> list[dict[str, Any]]:
    history_path = role_history_path(context, role)
    if not history_path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in history_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def append_role_history(context: SupervisorContext, role: str, payload: dict[str, Any]) -> None:
    session_dir = role_session_dir(context, role)
    session_dir.mkdir(parents=True, exist_ok=True)
    history_path = role_history_path(context, role)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _workspace_file_entry(path: Path, *, workspace_root: Path, purpose: str = "") -> dict[str, Any]:
    from .common import file_kind

    payload: dict[str, Any] = {
        "path": str(path.relative_to(workspace_root)),
        "kind": file_kind(path),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }
    if purpose:
        payload["purpose"] = purpose
    return payload


# Per-chunk byte budget for the ``transcript_full/part_NNN.jsonl`` slices.
# 80 KB ≈ 20K tokens, well below the typical single-tool-output ceiling even
# when the whole part is catted in one ``exec_command`` call. Triggering the
# split *only* when the source transcript exceeds this size means small
# transcripts (nanobot, openclaw single-cycle) stay as a single unchunked
# ``transcript.jsonl`` — no behavioral change for the common case.
_TRANSCRIPT_CHUNK_MAX_BYTES = 80 * 1024
_TRANSCRIPT_CAPPED_HEAD_BYTES = 30 * 1024
_TRANSCRIPT_CAPPED_TAIL_BYTES = 30 * 1024


def _transcript_line_chunks(text: str, *, max_bytes: int = _TRANSCRIPT_CHUNK_MAX_BYTES) -> list[tuple[str, int, int]]:
    """Split a JSONL text body into chunks of ≤ ``max_bytes`` each, splitting
    ONLY at line boundaries so no event record gets truncated mid-line.

    Returns a list of ``(chunk_text, byte_length, event_count)`` tuples. When
    a single line exceeds ``max_bytes`` that line is emitted as its own
    (oversized) chunk — we prefer preserving the event over forcing a size
    cap that would corrupt JSON.
    """
    lines = text.splitlines(keepends=True)
    chunks: list[tuple[str, int, int]] = []
    buf: list[str] = []
    buf_bytes = 0
    for line in lines:
        lb = len(line.encode("utf-8"))
        if buf and buf_bytes + lb > max_bytes:
            chunks.append(("".join(buf), buf_bytes, len(buf)))
            buf = []
            buf_bytes = 0
        buf.append(line)
        buf_bytes += lb
    if buf:
        chunks.append(("".join(buf), buf_bytes, len(buf)))
    return chunks


def _build_transcript_capped_view(text: str, *, head_bytes: int, tail_bytes: int, full_manifest_rel: str) -> str:
    """Build the head+tail capped view of a large transcript. Whole lines only
    (no mid-line truncation). Inserts a ``clawbench_truncation`` marker event
    between the head and tail so the consumer knows middle events were
    elided and where to find the full record.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return text

    head: list[str] = []
    head_b = 0
    for line in lines:
        lb = len(line.encode("utf-8"))
        if head and head_b + lb > head_bytes:
            break
        head.append(line)
        head_b += lb

    tail: list[str] = []
    tail_b = 0
    for line in reversed(lines):
        lb = len(line.encode("utf-8"))
        if tail and tail_b + lb > tail_bytes:
            break
        tail.insert(0, line)
        tail_b += lb

    total_events = len(lines)
    head_events = len(head)
    tail_events = len(tail)
    omitted_events = max(0, total_events - head_events - tail_events)
    omitted_bytes = max(0, len(text.encode("utf-8")) - head_b - tail_b)

    marker = {
        "type": "clawbench_truncation",
        "reason": "transcript too large for single-cat context budget",
        "original_bytes": len(text.encode("utf-8")),
        "original_events": total_events,
        "kept_head_events": head_events,
        "kept_tail_events": tail_events,
        "omitted_events": omitted_events,
        "omitted_bytes": omitted_bytes,
        "full_manifest": full_manifest_rel,
        "note": (
            "Only the first kept_head_events and last kept_tail_events lines "
            "are retained in this capped view. For the complete line-by-line "
            "transcript see the manifest at full_manifest (lists "
            f"transcript_full/part_NNN.jsonl slices, each ≤{_TRANSCRIPT_CHUNK_MAX_BYTES // 1024} KB)."
        ),
    }
    marker_line = json.dumps(marker, ensure_ascii=False) + "\n"

    return "".join(head) + marker_line + "".join(tail)


def _copy_transcript_with_optional_chunking(
    src: Path,
    dest: Path,
    *,
    include_full_chunks: bool,
) -> dict[str, Any] | None:
    """Copy a JSONL transcript to ``dest``. If the source size is at or
    below ``_TRANSCRIPT_CHUNK_MAX_BYTES``, this is a plain copy and returns
    ``None`` (no chunk metadata). If larger:

    - When ``include_full_chunks`` is True (supervisor role), writes
      ``dest.parent / transcript_full/`` with ``part_NNN.jsonl`` slices + a
      ``manifest.json`` index, and writes a head+tail capped view at
      ``dest`` pointing to the manifest.
    - When ``include_full_chunks`` is False (user_simulator), only writes
      the head+tail capped view at ``dest``; the full chunk directory is
      NOT created. User_simulator doesn't need deep audit capability.

    Returns chunk metadata dict when chunking triggered, else None.
    """
    if not src.exists() or not src.is_file():
        return None
    raw = src.read_bytes()
    if len(raw) <= _TRANSCRIPT_CHUNK_MAX_BYTES:
        dest.write_bytes(raw)
        return None

    text = raw.decode("utf-8", errors="replace")
    dest_dir = dest.parent
    full_dir = dest_dir / "transcript_full"
    dest_name = dest.name  # e.g. "transcript.jsonl"
    full_manifest_rel = f"{dest_name.rsplit('.', 1)[0]}_full/manifest.json"  # "transcript_full/manifest.json"

    # Head+tail capped view (always written, for both supervisor and
    # user_simulator — it's the file the prompt refers to by default).
    capped_text = _build_transcript_capped_view(
        text,
        head_bytes=_TRANSCRIPT_CAPPED_HEAD_BYTES,
        tail_bytes=_TRANSCRIPT_CAPPED_TAIL_BYTES,
        full_manifest_rel=full_manifest_rel,
    )
    dest.write_text(capped_text, encoding="utf-8")

    if not include_full_chunks:
        # Round 8 / B1: don't emit host absolute paths into role workspace
        # metadata.  The role prompt only needs role-workspace-relative
        # info (the caller adds ``rel_path`` upstream); host paths were
        # leaking ``runs/<...>`` and external `.runs_root` into the
        # supervisor / user_simulator prompts, adding token noise and
        # leaking internal layout for no benefit.
        return {
            "source_bytes": len(raw),
            "capped_only": True,
        }

    # Sliced complete archive for supervisor.
    full_dir.mkdir(parents=True, exist_ok=True)
    chunks = _transcript_line_chunks(text, max_bytes=_TRANSCRIPT_CHUNK_MAX_BYTES)
    manifest = {
        "version": 1,
        "original_bytes": len(raw),
        "original_events": sum(c[2] for c in chunks),
        "part_size_target_bytes": _TRANSCRIPT_CHUNK_MAX_BYTES,
        "parts": [],
    }
    byte_cursor = 0
    event_cursor = 1
    part_paths: list[Path] = []
    for idx, (body, byte_len, event_count) in enumerate(chunks, start=1):
        part_name = f"part_{idx:03d}.jsonl"
        part_path = full_dir / part_name
        part_path.write_text(body, encoding="utf-8")
        part_paths.append(part_path)
        manifest["parts"].append({
            "name": part_name,
            "bytes": byte_len,
            "events": event_count,
            "byte_range": [byte_cursor, byte_cursor + byte_len - 1],
            "event_range": [event_cursor, event_cursor + event_count - 1],
        })
        byte_cursor += byte_len
        event_cursor += event_count

    manifest_path = full_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Round 8 / B1: replace host absolute paths with role-workspace
    # relative paths.  ``full_dir_rel`` / ``manifest_rel`` are relative
    # to the role's workspace_root, which is the only namespace the
    # role prompt understands.
    full_dir_rel = full_dir.relative_to(dest_dir.parent.parent) if dest_dir.parent.parent in full_dir.parents else Path("visible") / "transcript_full"
    manifest_rel = full_dir_rel / "manifest.json"
    return {
        "source_bytes": len(raw),
        "capped_only": False,
        "full_dir_rel": str(full_dir_rel),
        "manifest_rel": str(manifest_rel),
        "part_count": len(chunks),
    }


def _copy_visible_workspace_files(
    context: SupervisorContext,
    workspace_root: Path,
    *,
    include_full_transcript_chunks: bool = True,
) -> tuple[list[dict[str, Any]], list[Path], list[dict[str, Any]]]:
    """Returns (workspace_files, image_paths, chunked_transcripts).

    ``chunked_transcripts`` lists each transcript that exceeded the 80 KB
    threshold and therefore got split into ``transcript_full/part_NNN.jsonl``
    slices. The caller (``prepare_role_workspace``) surfaces this list in
    ``workspace_manifest.json`` so the role prompt can conditionally include
    the extra instructions about ``transcript_full/``.
    """
    from .common import (
        _strip_edict_routing_note,
        build_visible_payload,
        copy_file_into,
        copy_supervisor_asset,
        file_kind,
        read_text,
        write_json,
    )

    visible_root = workspace_root / "visible"
    visible_root.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    image_paths: list[Path] = []
    chunked_transcripts: list[dict[str, Any]] = []

    prompt_dest = visible_root / "executor_prompt.md"
    if context.attempt.prompt_file.exists():
        cleaned = _strip_edict_routing_note(read_text(context.attempt.prompt_file))
        prompt_dest.write_text(cleaned, encoding="utf-8")
        files.append(_workspace_file_entry(prompt_dest, workspace_root=workspace_root, purpose="executor prompt"))

    # Transcript gets special chunking treatment. Other direct files just copy.
    transcript_dest = visible_root / "transcript.jsonl"
    transcript_chunk_meta = _copy_transcript_with_optional_chunking(
        context.attempt.transcript_file,
        transcript_dest,
        include_full_chunks=include_full_transcript_chunks,
    )
    if transcript_dest.exists():
        files.append(_workspace_file_entry(transcript_dest, workspace_root=workspace_root, purpose="raw executor transcript"))
    if transcript_chunk_meta:
        chunked_transcripts.append({
            "rel_path": "visible/transcript.jsonl",
            **transcript_chunk_meta,
        })
        if not transcript_chunk_meta.get("capped_only"):
            for part in sorted((visible_root / "transcript_full").glob("part_*.jsonl")):
                files.append(_workspace_file_entry(part, workspace_root=workspace_root, purpose="transcript chunk"))
            manifest_path = visible_root / "transcript_full" / "manifest.json"
            if manifest_path.exists():
                files.append(_workspace_file_entry(manifest_path, workspace_root=workspace_root, purpose="transcript chunk manifest"))

    direct_files = [
        (context.attempt.tool_usage_file, visible_root / "tool_usage.json", "tool usage trace"),
        (context.attempt.runtime_probe_file, visible_root / "runtime_probe.json", "runtime probe"),
    ]
    desktop_image = context.attempt.out_dir / "runtime_probe_desktop.png"
    direct_files.append((desktop_image, visible_root / "runtime_probe_desktop.png", "desktop screenshot"))

    for src, dest, purpose in direct_files:
        # Includes runtime_probe_desktop.png which can be >250 KB — route
        # through the supervisor-asset path so large images get resized.
        copied = copy_supervisor_asset(src, dest)
        if not copied:
            continue
        files.append(_workspace_file_entry(copied, workspace_root=workspace_root, purpose=purpose))
        if file_kind(copied) == "image":
            image_paths.append(copied)

    # Mirror ``result/`` but downscale any large images we encounter. The
    # agent is free to save full-page screenshots (agent-browser `--full`);
    # we don't want that to blow supervisor context when view_image'd.
    src_result = context.attempt.result_dir
    if src_result.exists() and src_result.is_dir():
        dest_result = visible_root / "result"
        if dest_result.exists():
            shutil.rmtree(dest_result)
        for src_path in sorted(src_result.rglob("*")):
            if not src_path.is_file():
                continue
            rel = src_path.relative_to(src_result)
            dest_path = dest_result / rel
            copied = copy_supervisor_asset(src_path, dest_path)
            if not copied:
                continue
            files.append(_workspace_file_entry(copied, workspace_root=workspace_root, purpose="saved result artifact"))
            if file_kind(copied) == "image":
                image_paths.append(copied)

    agent_manifest = context.attempt.out_dir / "agent_sessions_manifest.json"
    copied_manifest = copy_file_into(agent_manifest, visible_root / "agent_sessions_manifest.json")
    if copied_manifest:
        files.append(_workspace_file_entry(copied_manifest, workspace_root=workspace_root, purpose="multi-agent manifest"))

    # Per-agent edict transcripts: apply same chunking logic individually. Each
    # sub-agent's transcript can be as large as the full merged one (e.g. taizi
    # alone has been observed at 2.3 MB), so they benefit from the split too.
    agent_sessions_src = context.attempt.out_dir / "agent_sessions"
    if agent_sessions_src.exists() and agent_sessions_src.is_dir():
        agent_sessions_dest = visible_root / "agent_sessions"
        agent_sessions_dest.mkdir(parents=True, exist_ok=True)
        for agent_src_dir in sorted(p for p in agent_sessions_src.iterdir() if p.is_dir()):
            agent_dest_dir = agent_sessions_dest / agent_src_dir.name
            agent_dest_dir.mkdir(parents=True, exist_ok=True)
            for src_item in sorted(agent_src_dir.iterdir()):
                if not src_item.is_file():
                    continue
                dest_item = agent_dest_dir / src_item.name
                if src_item.name == "transcript.jsonl":
                    chunk_meta = _copy_transcript_with_optional_chunking(
                        src_item,
                        dest_item,
                        include_full_chunks=include_full_transcript_chunks,
                    )
                    if dest_item.exists():
                        files.append(_workspace_file_entry(dest_item, workspace_root=workspace_root, purpose="per-agent session artifact"))
                    if chunk_meta:
                        rel = f"visible/agent_sessions/{agent_src_dir.name}/transcript.jsonl"
                        chunked_transcripts.append({
                            "rel_path": rel,
                            **chunk_meta,
                        })
                        if not chunk_meta.get("capped_only"):
                            for part in sorted((agent_dest_dir / "transcript_full").glob("part_*.jsonl")):
                                files.append(_workspace_file_entry(part, workspace_root=workspace_root, purpose="transcript chunk"))
                            mp = agent_dest_dir / "transcript_full" / "manifest.json"
                            if mp.exists():
                                files.append(_workspace_file_entry(mp, workspace_root=workspace_root, purpose="transcript chunk manifest"))
                else:
                    copied = copy_file_into(src_item, dest_item)
                    if copied:
                        files.append(_workspace_file_entry(copied, workspace_root=workspace_root, purpose="per-agent session artifact"))

    visible_summary = build_visible_payload(context)
    write_json(visible_root / "visible_summary.json", visible_summary)
    files.append(_workspace_file_entry(visible_root / "visible_summary.json", workspace_root=workspace_root, purpose="structured visible summary"))
    return files, image_paths, chunked_transcripts


def _copy_reference_workspace_files(
    context: SupervisorContext, workspace_root: Path,
) -> tuple[list[dict[str, Any]], list[Path], dict[str, Any]]:
    """Copy hidden references into the role workspace.

    Returns ``(files, image_paths, status)`` where ``status`` carries
    the manifest fields introduced in Round 9 / A4:

      - ``hidden_references_copied_count``: how many references the
        supervisor will actually see.
      - ``hidden_references_missing``: the relative paths the task
        declared but that aren't readable on disk.
      - ``primary_eval_rule_available``: whether
        ``references/eval_rule.md`` was copied successfully (the
        supervisor's primary scoring contract — if False, the
        supervisor cannot rubric-score and the caller should treat
        this as a config/infra failure).
      - ``primary_eval_rule_path``: the relative path used (constant
        for now: ``references/eval_rule.md``).
    """
    from .common import (
        build_hidden_payload,
        copy_supervisor_asset,
        file_kind,
        resolve_reference_path,
        write_json,
    )

    refs_root = workspace_root / "references"
    refs_root.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    image_paths: list[Path] = []
    copied_count = 0
    missing: list[str] = []
    primary_eval_rule_rel = "references/eval_rule.md"
    primary_eval_rule_available = False
    for raw in context.task.references:
        src = resolve_reference_path(context, raw)
        if not src.exists() or not src.is_file():
            missing.append(str(raw))
            continue
        dest = refs_root / raw
        # Reference images — often ~500 KB-1 MB screenshots — get
        # downscaled to keep supervisor view_image results under the
        # provider's 272 K-token context ceiling. See
        # ``copy_supervisor_asset`` for the size/format policy.
        copied = copy_supervisor_asset(src, dest)
        if not copied:
            missing.append(str(raw))
            continue
        files.append(_workspace_file_entry(copied, workspace_root=workspace_root, purpose="hidden reference"))
        if file_kind(copied) == "image":
            image_paths.append(copied)
        copied_count += 1
        if str(raw) == primary_eval_rule_rel and copied.exists():
            primary_eval_rule_available = True
    write_json(refs_root / "hidden_summary.json", build_hidden_payload(context))
    files.append(_workspace_file_entry(refs_root / "hidden_summary.json", workspace_root=workspace_root, purpose="structured hidden summary"))
    status = {
        "hidden_references_copied_count": copied_count,
        "hidden_references_missing": missing,
        "primary_eval_rule_available": primary_eval_rule_available,
        "primary_eval_rule_path": primary_eval_rule_rel,
    }
    return files, image_paths, status


def _copy_privacy_workspace_files(context: SupervisorContext, workspace_root: Path) -> list[dict[str, Any]]:
    """Write the task's privacy env-vars into the role workspace as privacy/env.env.

    The runner injects these same KEY=VALUE pairs into the executor
    container as environment variables, so the supervisor needs a
    parallel view to verify executor behavior against the hidden
    rubric (e.g. "the executor must have signed in with EMAIL_ADDRESS
    but never echoed EMAIL_PASSWORD").

    Only called for roles allowed to see private task assets (currently
    answer_supervisor). The public user simulator never sees these.
    """
    from ..privacy import resolve_privacy_env

    declared = list(context.task.privacy or [])
    if not declared:
        return []
    try:
        env_map = resolve_privacy_env(declared)
    except ValueError:
        # Load-time validation already raised on missing keys; if we got
        # here with an incomplete config anyway (e.g. test harness),
        # there's nothing to mirror. Fail open rather than crash the
        # supervisor path.
        return []
    if not env_map:
        return []
    privacy_root = workspace_root / "privacy"
    privacy_root.mkdir(parents=True, exist_ok=True)
    env_file = privacy_root / "env.env"
    lines = [
        "# Task privacy credentials — supervisor-only view of the env vars",
        "# injected into the executor container. Never echo VALUES into the",
        "# public feedback payload; it is fine to reference KEYs by name.",
        "",
    ]
    for key in declared:
        value = env_map.get(key, "")
        lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [
        _workspace_file_entry(
            env_file,
            workspace_root=workspace_root,
            purpose="task privacy env vars (supervisor-only)",
        )
    ]


def _role_workspace_prompt_files(role: str, *, has_privacy: bool = False) -> list[str]:
    files = [
        "README.md",
        "workspace_manifest.json",
        "public_task.md",
        "turn_state.json",
        "visible/executor_prompt.md",
        "visible/transcript.jsonl",
        "visible/tool_usage.json",
        "visible/runtime_probe.json",
        "visible/result/",
        "visible/visible_summary.json",
    ]
    if role == "answer_supervisor":
        files.extend(["references/", "references/hidden_summary.json"])
        if has_privacy:
            files.append("privacy/")
    if role == "public_user_simulator":
        files.append("supervisor_feedback.json")
    return files


def build_role_workspace_readme(*, role: str, manifest: dict[str, Any]) -> str:
    lines = [
        f"# {role}",
        "",
        "This is an isolated workspace for the current Codex role.",
        "Treat it as read-only for benchmark integrity; do not modify files here.",
        "Only files inside this workspace are available to this role.",
        "Inspect files directly instead of relying on the prompt for raw evidence.",
        "",
        "## Start Here",
    ]
    has_privacy = bool(manifest.get("privacy_available"))
    for path in _role_workspace_prompt_files(role, has_privacy=has_privacy):
        lines.append(f"- `{path}`")
    if has_privacy and role == "answer_supervisor":
        lines.extend(
            [
                "",
                "## Privacy Assets",
                "The `privacy/env.env` file lists the task-local credentials that",
                "are also injected into the executor container as environment",
                "variables. Use them strictly to verify behavior and ground-truth",
                "— never echo secret VALUES into the public feedback payload",
                "returned to the executor or user simulator (referencing KEYs by",
                "name is fine).",
            ]
        )
    lines.extend(["", "## File Inventory"])
    for item in manifest.get("files") or []:
        path = str(item.get("path") or "").strip()
        purpose = str(item.get("purpose") or "").strip()
        if path:
            lines.append(f"- `{path}`: {purpose or 'workspace file'}")
    # Images are NOT pre-attached to the prompt. Surface them here so the role
    # can find them quickly and decide whether to inspect with ``view_image``.
    available_images = [str(p).strip() for p in (manifest.get("available_images") or []) if str(p).strip()]
    if available_images:
        lines.extend(
            [
                "",
                "## Available Images",
                "Use the built-in `view_image` tool with the relative path below",
                "(e.g. `view_image(path=\"visible/result/screenshots/foo.png\")`)",
                "only when an image's content is material to your judgement.",
                "For screenshot-evidence checkpoints, prefer saved result text,",
                "file presence, filenames, transcript capture steps, and OCR/text",
                "summaries when those are enough; avoid opening social/video/login",
                "screenshots just to confirm that a screenshot exists.",
                "No image is pre-attached — `view_image` is the only way to see them.",
                "",
            ]
        )
        for path in available_images:
            lines.append(f"- `{path}`")
    return "\n".join(lines).strip() + "\n"


def prepare_role_workspace(
    context: SupervisorContext,
    role: str,
    *,
    include_hidden_references: bool,
    include_privacy: bool = False,
    supervisor_feedback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .common import reset_dir, write_json

    session_root = role_session_dir(context, role).resolve()
    workspace_root = reset_dir(role_workspace_dir(context, role))
    reset_dir(role_runtime_dir(context, role))
    role_home_dir(context, role).mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    images: list[Path] = []
    # Only the answer_supervisor gets the full chunked transcript archive
    # under ``visible/transcript_full/``. user_simulator gets the head+tail
    # capped view alone — it doesn't need deep audit capability to write a
    # next-turn follow-up.
    include_full_transcript_chunks = role == "answer_supervisor"
    visible_files, visible_images, chunked_transcripts = _copy_visible_workspace_files(
        context,
        workspace_root,
        include_full_transcript_chunks=include_full_transcript_chunks,
    )
    files.extend(visible_files)
    images.extend(visible_images)

    followups_used = max(0, context.attempt.turn - 1)
    turn_state = {
        "task_id": context.task.task_id,
        "role": role,
        "agent_turn_index": context.attempt.turn,
        "max_user_followups": context.task.max_user_followups,
        "followups_used_before_this_turn": followups_used,
        "remaining_followups_after_this_turn": max(0, context.task.max_user_followups - followups_used),
    }
    write_json(workspace_root / "turn_state.json", turn_state)
    files.append(_workspace_file_entry(workspace_root / "turn_state.json", workspace_root=workspace_root, purpose="turn state"))
    (workspace_root / "public_task.md").write_text(context.task.public_task.strip() + "\n", encoding="utf-8")
    files.append(_workspace_file_entry(workspace_root / "public_task.md", workspace_root=workspace_root, purpose="public task text"))

    history = load_role_history(context, role)
    history_path = workspace_root / "role_history.jsonl"
    if history:
        history_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in history), encoding="utf-8")
    else:
        history_path.write_text("", encoding="utf-8")
    files.append(_workspace_file_entry(history_path, workspace_root=workspace_root, purpose="prior role decisions"))

    # Round 9 / A4: capture real copy state for the manifest.  Pre-fix,
    # ``hidden_references_available`` was just the caller-passed flag —
    # it lied when the task declared references that weren't actually
    # on disk (eval_rule.md missing, image path typo, …).
    hidden_ref_status: dict[str, Any] = {
        "hidden_references_copied_count": 0,
        "hidden_references_missing": [],
        "primary_eval_rule_available": False,
        "primary_eval_rule_path": "references/eval_rule.md",
    }
    if include_hidden_references:
        ref_files, ref_images, hidden_ref_status = _copy_reference_workspace_files(
            context, workspace_root,
        )
        files.extend(ref_files)
        images.extend(ref_images)

    privacy_available = False
    if include_privacy:
        privacy_files = _copy_privacy_workspace_files(context, workspace_root)
        if privacy_files:
            files.extend(privacy_files)
            privacy_available = True

    if supervisor_feedback is not None:
        write_json(workspace_root / "supervisor_feedback.json", supervisor_feedback)
        files.append(_workspace_file_entry(workspace_root / "supervisor_feedback.json", workspace_root=workspace_root, purpose="public-facing supervisor feedback"))

    unique_images: list[Path] = []
    seen_images: set[Path] = set()
    for path in images:
        resolved = path.resolve()
        if resolved in seen_images or not resolved.exists():
            continue
        unique_images.append(resolved)
        seen_images.add(resolved)

    manifest = {
        "role": role,
        "workspace_root": str(CONTAINER_WORKDIR),
        "public_task_file": "public_task.md",
        "turn_state_file": "turn_state.json",
        "role_history_file": "role_history.jsonl",
        "files": sorted(files, key=lambda item: str(item.get("path") or "")),
        # ``available_images`` is the canonical list of PNG/JPG files present
        # in this role's workspace. Roles are expected to call ``view_image`` on
        # demand when an image's content is material to their judgement — the
        # images are NOT pre-attached to the codex prompt by default. The old
        # key ``attached_images`` is kept as a back-compat alias (same value).
        "available_images": [str(path.relative_to(workspace_root)) for path in unique_images if path.is_relative_to(workspace_root)],
        "attached_images": [str(path.relative_to(workspace_root)) for path in unique_images if path.is_relative_to(workspace_root)],
        # Round 9 / A4 — accurate hidden-references manifest.
        # ``hidden_references_requested`` reflects the caller's intent
        # (was the role allowed to see hidden refs?).
        # ``hidden_references_available`` reflects reality (did we
        # copy at least one ref successfully AND eval_rule.md is
        # readable?).  Pre-fix this conflated the two so an empty /
        # broken reference dir still showed ``available=True``.
        "hidden_references_requested": bool(include_hidden_references),
        "hidden_references_available": bool(
            include_hidden_references
            and hidden_ref_status.get("primary_eval_rule_available")
        ),
        "hidden_references_copied_count": hidden_ref_status.get(
            "hidden_references_copied_count", 0,
        ),
        "hidden_references_missing": list(
            hidden_ref_status.get("hidden_references_missing") or [],
        ),
        "primary_eval_rule_available": bool(
            hidden_ref_status.get("primary_eval_rule_available")
        ),
        "primary_eval_rule_path": str(
            hidden_ref_status.get("primary_eval_rule_path") or ""
        ),
        "privacy_available": privacy_available,
        "supervisor_feedback_available": supervisor_feedback is not None,
        # List of transcripts that exceeded the 80 KB chunking threshold;
        # the prompt template uses this to conditionally emit the
        # ``transcript_full/`` usage instructions (only supervisor gets
        # the full chunked archive; user_simulator's list will be empty
        # because its visible/transcript.jsonl is capped but no
        # transcript_full/ is written for that role).
        "chunked_transcripts": chunked_transcripts,
        # Round 9 / A2: record the supervision-summary mode that
        # governed the visible/hidden payload preparation.  Surfaces
        # the hyperparameter choice for post-run audit ("did the
        # supervisor get OCR? semantic blocks? full hidden refs?").
        "supervision_summary_mode": _supervision_summary_mode_resolved(),
    }
    readme = build_role_workspace_readme(role=role, manifest=manifest)
    (workspace_root / "README.md").write_text(readme, encoding="utf-8")
    write_json(workspace_root / "workspace_manifest.json", manifest)
    return {
        "session_root": session_root,
        "workspace_root": workspace_root,
        "runtime_root": role_runtime_dir(context, role).resolve(),
        "images": unique_images,
        "manifest": manifest,
        "readme": readme,
    }
