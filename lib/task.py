#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from .defaults import (
    DEFAULT_CODEX_CONFIG_PATH,
    DEFAULT_CODEX_MODEL,
    DEFAULT_EXECUTOR_MODEL,
    DEFAULT_MAX_USER_FOLLOWUPS,
    DEFAULT_REASONING_EFFORT,
    load_base_skills_manifest,
)
from .privacy import load_task_privacy_keys, resolve_privacy_env
from .templates.user_simulator import DEFAULT_USER_SIMULATOR_POLICY

SUPPORTED_AGENT_SYSTEMS = {"openclaw", "openclaw_edict", "nanobot"}
LEGACY_AGENT_SYSTEM_ALIASES = {
    "edict": "openclaw_edict",
    "openclaw+edict": "openclaw_edict",
}


@dataclass
class ServiceSpec:
    name: str
    path: str
    start: str
    oneshot: bool = False


@dataclass
class CodexRoleSpec:
    model: str = DEFAULT_CODEX_MODEL
    provider: str = ""
    config: str = DEFAULT_CODEX_CONFIG_PATH
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    # `instructions` is read by the supervisor only. The public user simulator
    # ignores this field — its task-level customization entry is `policy`.
    instructions: str = ""
    policy: str = ""


@dataclass
class CodexSpec:
    max_user_followups: int = 2
    user_simulator: CodexRoleSpec = field(
        default_factory=lambda: CodexRoleSpec(policy=DEFAULT_USER_SIMULATOR_POLICY)
    )
    supervisor: CodexRoleSpec = field(default_factory=CodexRoleSpec)


@dataclass
class TaskSpec:
    task_id: str
    category: str
    agent_sys: str
    agent_id: str
    model: str
    image_model: str
    # Per-turn executor timeout (one invocation of the agent process). This is
    # the ONLY per-turn cap — `cycle_timeout_seconds` has been removed because
    # a cycle from the executor's perspective is just one agent turn (the
    # subsequent supervisor/user-simulator calls happen in separate Codex
    # containers and are NOT billed to the executor). Default 1200s (20 min).
    # The in-container watchdog enforces this; also passed to `openclaw agent
    # --timeout` as the agent's own internal timeout.
    timeout_seconds: int
    # Cumulative executor wall-clock cap across ALL turns of one attempt.
    # Only executor agent calls count — supervisor Codex calls, user-simulator
    # Codex calls, artifact-collection, and continuation write-outs are
    # infrastructure and are NOT deducted from this budget. Default 1800s
    # (30 min). When exceeded the attempt stops with finalStatus=global_timeout.
    max_total_seconds: int
    success_threshold: float
    # The task's primary, default prompt — used when SNAPSHOT_MODE is unset
    # or set to anything other than "1". The runner never exposes
    # SNAPSHOT_MODE to the executor, so this prompt should read as a normal
    # user request and assume live resources (real APIs, live data).
    task: str
    # Optional fallback used instead of ``task`` when SNAPSHOT_MODE=1. The
    # snapshot variant should refer to the preloaded ``*_snapshot.json``
    # file under ``/tmp_workspace/clawbench/sources/`` rather than the live
    # API. Leave empty for tasks that don't have a snapshot mode.
    task_snapshot: str
    references: list[str]
    sources: list[str]
    skills: list[str]
    services: list[ServiceSpec]
    # Host-side scripts run before the container starts. Paths are
    # relative to this task's injection root (``injection/{cat}/{task_id}/``)
    # so each task ships its populator alongside its sources/skills/
    # services. The runner resolves + executes them on the host — the
    # injection ``ops/`` subdirectory is NEVER copied into the container
    # (only ``sources/`` is), so populator source code cannot leak to the
    # executor.
    pre_exec: list[str]
    # Env-var names this task requires, read from the task's
    # ``.privacy`` file (committed, contains only names). Values live in
    # ``configs/privacy.local.env`` and are injected into the executor
    # container as environment variables at container-start time.
    privacy: list[str]
    file_path: Path
    injection_root: Path
    codex: CodexSpec
    # Opt-in declaration that this task's populator is safe to run under
    # ``workers > 1``. Default False (populator_lock only protects the
    # bootstrap race; populators that do partial delete/rewrite sequences
    # can still expose mid-flight state to another worker that acquires
    # the lock within the TTL window — those populators must be scheduled
    # serially). The runner lock still guards the local pre-exec script; the
    # orchestra dispatcher also reads this declaration and avoids starting
    # identical non-safe task cells concurrently across model/backend cells.
    pre_exec_parallel_safe: bool = False

    # Round 11 / B1: 3-tier desktop recording knob.  Round 12 / E4
    # promoted the default from ``"low"`` to ``"none"`` based on Round
    # 11 E5 throughput data — recording=none + headless was the
    # winning config (39.4 runs/hr, 3x Round 10).  GUI-fidelity tasks
    # opt back in per-yaml with ``recording: high``.
    #
    # ``high`` (pre-Round-11 default): ffmpeg @ 10 fps, 1440x900,
    #     headed browser.  Costs ~5-10% wall-clock + 50-100MB disk per
    #     cycle + ~5-15% per-container CPU.  Necessary when the
    #     supervisor / replay needs visual fidelity (GUI tasks in
    #     105_cross_platform, image fidelity checks).
    # ``low``: ffmpeg @ 5 fps, 1280x720, headless browser.  Saves
    #     ~50% of recording overhead; trace still has a usable but
    #     lower-fidelity video for debug.
    # ``none`` (Round 12 default): no ffmpeg, headless browser.
    #     Saves the entire recording cost (CPU + disk + ~30%
    #     per-container RAM that goes to ffmpeg buffers + GUI
    #     compositor).  Trace + screenshot + logs remain available in
    #     each cycle dir for post-hoc debug.
    #
    # The HEADED env var is coupled: ``none``/``low`` force headless,
    # ``high`` uses the existing CLAWBENCH_BROWSER_HEADED default
    # (typically headed).  Coupling lives in container_lifecycle.py.
    recording: str = "none"

    # Explicit headed-vs-headless override for the executor browser.
    # ``auto`` (default): keep the recording-coupled behaviour above
    # — ``recording=high`` runs headed, anything else runs headless.
    # ``true`` / ``headed`` / ``1``: force headed regardless of
    # recording tier.  Useful for GUI-fidelity tasks that need a
    # visible Chromium without the ~5–10% wall-clock cost of
    # ``recording=high``.
    # ``false`` / ``headless`` / ``0``: force headless regardless
    # of recording tier.  Useful for diagnostic ``recording=high``
    # captures on a headless target.
    # Parsed via ``_parse_headed_mode`` so typos raise at task-load
    # time rather than silently picking a wrong default.
    headed: str = "auto"


def canonical_agent_sys(
    value: object,
    *,
    strict: bool = True,
    field_name: str = "agent_sys",
) -> str:
    """Normalise an ``agent_sys`` token; with ``strict=True`` also validate.

    Single source of truth for ``agent_sys`` value handling.

    Args:
        value: raw value from a config / CLI / kwarg. ``None`` and empty
            strings normalise to ``"openclaw"``.
        strict: when True (the default and the recommended posture), the
            return value is also validated against ``SUPPORTED_AGENT_SYSTEMS``
            and rejected if it is a deprecated alias in
            ``LEGACY_AGENT_SYSTEM_ALIASES``. When False, the return value
            is only lower/strip'd — used by callers that intentionally
            want a path-safe token from an unsanitised input (e.g. legacy
            cleanup scripts that may receive removed backends).
        field_name: appears in the error message under strict mode so
            multi-field validators can point at which field is wrong.

    Raises:
        ValueError: under ``strict=True`` when the input is a known
        legacy alias or an unknown backend.
    """
    raw = str(value or "openclaw").strip().lower()
    if not strict:
        return raw
    if raw in LEGACY_AGENT_SYSTEM_ALIASES:
        canonical = LEGACY_AGENT_SYSTEM_ALIASES[raw]
        raise ValueError(f"{field_name}={raw!r} is no longer supported; use {canonical!r}")
    if raw not in SUPPORTED_AGENT_SYSTEMS:
        allowed = ", ".join(sorted(SUPPORTED_AGENT_SYSTEMS))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return raw


def validate_agent_sys(value: object, *, field_name: str = "agent_sys") -> str:
    """Backwards-compatible wrapper around ``canonical_agent_sys(strict=True)``.

    Kept under its historical name so callers don't have to migrate in
    one shot; new code should call ``canonical_agent_sys`` directly.
    """
    return canonical_agent_sys(value, strict=True, field_name=field_name)


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _string_list(value: object) -> list[str]:
    return [str(item) for item in _as_list(value)]


def _parse_codex_role(raw: object, *, default_policy: str = "") -> CodexRoleSpec:
    if raw is None:
        return CodexRoleSpec(policy=default_policy)
    if not isinstance(raw, dict):
        raise ValueError("codex role spec must be a mapping")
    return CodexRoleSpec(
        model=str(raw.get("model") or DEFAULT_CODEX_MODEL).strip(),
        provider=str(raw.get("provider") or "").strip(),
        config=str(raw.get("config") or DEFAULT_CODEX_CONFIG_PATH).strip(),
        reasoning_effort=str(raw.get("reasoning_effort") or DEFAULT_REASONING_EFFORT).strip(),
        instructions=str(raw.get("instructions") or "").strip(),
        policy=str(raw.get("policy") or default_policy).strip(),
    )


def _parse_codex(raw: object) -> CodexSpec:
    if raw is None:
        return CodexSpec()
    if not isinstance(raw, dict):
        raise ValueError("codex must be a mapping")
    return CodexSpec(
        max_user_followups=int(raw.get("max_user_followups", DEFAULT_MAX_USER_FOLLOWUPS)),
        user_simulator=_parse_codex_role(raw.get("user_simulator"), default_policy=DEFAULT_USER_SIMULATOR_POLICY),
        supervisor=_parse_codex_role(raw.get("supervisor")),
    )


def _validate_relative_paths(paths: list[str], *, field_name: str) -> list[str]:
    validated: list[str] = []
    for raw in paths:
        path = Path(str(raw or "").strip())
        if not path.as_posix() or path.is_absolute() or ".." in path.parts:
            raise ValueError(f"{field_name} entries must be safe relative paths: {raw!r}")
        validated.append(path.as_posix())
    return validated


_SAFE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _validate_safe_name(value: str, *, field_name: str) -> str:
    candidate = str(value or "").strip()
    if not candidate or not _SAFE_NAME_RE.fullmatch(candidate):
        raise ValueError(
            f"{field_name} must use only letters, digits, '.', '_', or '-' and cannot contain path separators: {value!r}"
        )
    return candidate


def _validate_services(services: list[ServiceSpec]) -> list[ServiceSpec]:
    validated: list[ServiceSpec] = []
    for index, service in enumerate(services):
        validated.append(
            replace(
                service,
                name=_validate_safe_name(service.name, field_name=f"services[{index}].name"),
                path=_validate_relative_paths([service.path], field_name=f"services[{index}].path")[0],
            )
        )
    return validated


def _validate_task_assets(task: TaskSpec) -> TaskSpec:
    if "references/eval_rule.md" not in task.references:
        raise ValueError("references must include 'references/eval_rule.md'")
    for raw in task.references:
        path = task.injection_root / raw
        if not path.exists():
            raise ValueError(f"missing reference asset: {raw}")
    for raw in task.sources:
        path = task.injection_root / "sources" / raw
        if not path.exists():
            raise ValueError(f"missing source asset: {raw}")
    base_skills = set(load_base_skills_manifest().get("skills") or [])
    base_skills.update(load_base_skills_manifest().get("fallback_skills") or [])
    for raw in task.skills:
        # Built-in runtime skills don't need a per-task injection
        # directory — they live in the image at /root/skills/ and
        # are copied from docker/base_skills/<name>/ at runtime as a
        # fallback (see lib/runner.py).
        if raw in base_skills or raw in {"linux-gui-control", "desktop-control"}:
            continue
        path = task.injection_root / "skills" / raw
        if not path.exists():
            raise ValueError(f"missing skill asset: {raw}")
    for service in task.services:
        path = task.injection_root / "services" / service.path
        if not path.exists():
            raise ValueError(f"missing service asset: services/{service.path}")
    if task.privacy:
        # Verify every declared KEY has a real value in
        # configs/privacy.local.env. Raises a loud error otherwise so
        # fresh clones cannot silently run against placeholders.
        resolve_privacy_env(task.privacy)
    return task


def _validate_pre_exec_paths(paths: list[str], injection_root: Path) -> list[str]:
    """pre_exec scripts live under the task's injection root so each task
    ships its populator alongside its other assets (references, sources,
    etc.). Only ``sources/`` is copied into the container, so scripts
    placed under ``ops/`` (or any non-``sources/`` subdirectory) are
    host-only — they cannot leak into the executor's view.
    """
    validated: list[str] = []
    injection_root_resolved = injection_root.resolve()
    for raw in paths:
        rel = Path(str(raw or "").strip())
        if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"pre_exec entries must be safe relative paths: {raw!r}")
        if rel.parts and rel.parts[0] == "sources":
            raise ValueError(
                f"pre_exec path lives under sources/ (would leak populator into container): {raw!r}"
            )
        resolved = (injection_root_resolved / rel).resolve()
        try:
            resolved.relative_to(injection_root_resolved)
        except ValueError as exc:
            raise ValueError(f"pre_exec path escapes task injection root: {raw!r}") from exc
        if not resolved.exists():
            raise ValueError(f"pre_exec script not found: {raw!r}")
        validated.append(rel.as_posix())
    return validated


def load_task(task_file: Path, repo_root: Path) -> TaskSpec:
    raw = yaml.safe_load(task_file.read_text(encoding="utf-8")) or {}
    task_prompt = str(raw.get("task") or "").strip()
    task_snapshot_prompt = str(raw.get("task_snapshot") or "").strip()
    if "task_live" in raw:
        raise ValueError(
            "task yaml no longer accepts `task_live:` — put the live/default "
            "prompt directly in `task:` and declare `task_snapshot:` only as "
            "an override for SNAPSHOT_MODE=1."
        )
    if not task_prompt:
        raise ValueError("task yaml must define task")
    services = [
        ServiceSpec(
            name=str(item["name"]).strip(),
            path=str(item.get("path", item["name"])).strip(),
            start=str(item["start"]).strip(),
            oneshot=bool(item.get("oneshot", False)),
        )
        for item in _as_list(raw.get("services", []))
    ]
    task_id = _validate_safe_name(str(raw["task_id"]), field_name="task_id")
    category = _validate_safe_name(str(raw["category"]), field_name="category")
    injection_root = (repo_root / "injection" / category / task_id).resolve()
    if "privacy" in raw:
        raise ValueError(
            "task yaml no longer accepts a `privacy:` field — declare required "
            "env-var names one per line in the task's `.privacy` file "
            "(same directory as sources/, skills/, services/)."
        )
    privacy_keys = load_task_privacy_keys(injection_root)
    task = TaskSpec(
        task_id=task_id,
        category=category,
        agent_sys=validate_agent_sys(raw.get("agent_sys", "openclaw"), field_name="task.agent_sys"),
        agent_id=str(raw.get("agent_id", "main")),
        model=str(raw.get("model") or DEFAULT_EXECUTOR_MODEL).strip(),
        image_model=str(raw.get("image_model") or raw.get("model") or "").strip(),
        # Defaults: single executor turn up to 20 min (timeout_seconds=1200),
        # cumulative executor time across all turns up to 30 min
        # (max_total_seconds=1800). Supervisor / user simulator time is NOT
        # counted — those are infrastructure, not evaluated activity.
        timeout_seconds=int(raw.get("timeout_seconds", 1200)),
        max_total_seconds=int(raw.get("max_total_seconds", 1800)),
        success_threshold=float(raw.get("success_threshold", 1.0)),
        task=task_prompt,
        task_snapshot=task_snapshot_prompt,
        references=_validate_relative_paths(_string_list(raw.get("references")), field_name="references"),
        sources=_validate_relative_paths(_string_list(raw.get("sources")), field_name="sources"),
        skills=_validate_relative_paths(_string_list(raw.get("skills", [])), field_name="skills"),
        services=_validate_services(services),
        pre_exec=_validate_pre_exec_paths(_string_list(raw.get("pre_exec", [])), injection_root),
        privacy=privacy_keys,
        file_path=task_file.resolve(),
        injection_root=injection_root,
        codex=_parse_codex(raw.get("codex")),
        pre_exec_parallel_safe=bool(raw.get("pre_exec_parallel_safe", False)),
        recording=_parse_recording_mode(raw.get("recording")),
        headed=_parse_headed_mode(raw.get("headed")),
    )
    return _validate_task_assets(task)


_VALID_RECORDING_MODES = {"none", "low", "high"}

_HEADED_TRUE_TOKENS = {"true", "headed", "1", "yes"}
_HEADED_FALSE_TOKENS = {"false", "headless", "0", "no"}
_HEADED_AUTO_TOKENS = {"auto", ""}


def _parse_headed_mode(value: object) -> str:
    """Parse + validate the ``headed`` task field.

    None / absent / empty string / ``auto`` → ``"auto"`` (the
    recording-coupled default).  Truthy tokens normalise to ``"true"``,
    falsy tokens to ``"false"``.  Anything else raises ``ValueError``
    so typos don't silently land on the wrong default.
    """
    if value is None:
        return "auto"
    normalized = str(value).strip().lower()
    if normalized in _HEADED_AUTO_TOKENS:
        return "auto"
    if normalized in _HEADED_TRUE_TOKENS:
        return "true"
    if normalized in _HEADED_FALSE_TOKENS:
        return "false"
    raise ValueError(
        f"task yaml ``headed`` must be one of auto/true/false (or aliases "
        f"headed/headless/1/0/yes/no), got {value!r}"
    )


def _parse_recording_mode(value: object) -> str:
    """Round 11 / B1: parse + validate ``recording`` field.

    None / absent / empty string → default ``none`` (Round 12 / E4
    promoted the default from ``low`` based on Round 11 throughput
    data; GUI-fidelity tasks opt back in per-yaml with
    ``recording: high``).  Anything else must be one of
    ``none``/``low``/``high`` (case-insensitive).  Invalid values
    raise ``ValueError`` early at task-load time rather than silently
    defaulting; this keeps typos from quietly running everything at
    the wrong recording tier.
    """
    if value is None or value == "":
        return "none"
    normalized = str(value).strip().lower()
    if normalized not in _VALID_RECORDING_MODES:
        raise ValueError(
            f"task yaml ``recording`` must be one of {sorted(_VALID_RECORDING_MODES)}, "
            f"got {value!r}"
        )
    return normalized


def discover_task_files(root: Path) -> list[Path]:
    # Skip any yaml whose filename OR any ancestor directory (relative to root)
    # contains "template" — this covers both the flat-file convention
    # (tasks/task_000_template.yaml) and the category-dir convention
    # (tasks/000_template/task_000_example.yaml).
    return sorted(
        path
        for path in root.rglob("*.yaml")
        if not any("template" in part.lower() for part in path.relative_to(root).parts)
    )
