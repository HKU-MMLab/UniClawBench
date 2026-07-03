"""Container lifecycle — the three phases that bring an attempt's
container from "no docker process" to "ready to receive the agent's
first turn".

Merged from ``pre_exec.py`` + ``container.py`` + ``services.py`` in the
third-round refactor.  All three files were sequential phases of
``initialize_session_container`` and split the same concern across
three modules; consolidating them here keeps the lifecycle readable
top-to-bottom and removes the cross-module import dance.

Three sections live here, in execution order:

* **Section 1 — pre-exec hooks** (was ``pre_exec.py``).
  Host-side scripts that refresh time-sensitive state BEFORE the
  container starts.  Populator scripts run under a TTL-guarded
  ``populator_lock`` so parallel workers don't double-fire mutating
  side effects.

* **Section 2 — container boot + per-backend config injection** (was
  ``container.py``).  Starts the docker container, mounts proxy /
  privacy env vars, populates ``/tmp_workspace`` (sources / services /
  skills), installs the per-backend ``openclaw.json`` / nanobot config
  fragment, and renders the tiny proxy-env script that the agent
  sources before spawning any subprocess.

* **Section 3 — service readiness** (was ``services.py``).
  After the container is up, spin up the desktop / openclaw gateway /
  per-task ``oneshot`` services and poll them until they answer
  requests.  Every function in this section runs inside the container
  via ``docker exec``.

Three files of ~180/530/330 lines merged into one ~1050-line file
because they're the same operational concern and were always called
in sequence from ``orchestration.initialize_session_container``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..config_stack import container_visible_value
from ..defaults import (
    BROWSER_HEADED,
    EXECUTOR_CONTEXT_WINDOW_TOKENS,
    ROOT,
    load_base_skills_manifest,
)
from ..privacy import resolve_privacy_env
from ..proxy import write_local
from ..task import TaskSpec
from . import artifacts, docker as docker_mod, edict, openclaw, task_config
from .populator_lock import mark_populator_ok, populator_lock


# ─────────────────────────────────────────────────────────────────────
# Section 1 — Pre-exec hooks
# ─────────────────────────────────────────────────────────────────────
#
# Why host-side: a populator script encodes ground truth (what data
# goes where, which records count as "urgent", etc.).  Mounting it
# into the container would leak the rubric to the executor.  So these
# scripts run on the host, refresh the live API + regenerate the
# task's snapshot / ground_truth assets, and everything inside the
# container continues to read the injection directory normally.
#
# Why a task-level opt-in (vs. always running populators): most tasks
# don't have time-sensitive state.  For the ones that do (Trello dues
# anchored to "today", Todoist deadlines, etc.), the task yaml lists
# its populator under ``pre_exec:`` and the runner invokes it before
# ``start_container``.
#
# Scripts run under the repo's Python, inherit the current environment
# plus the task's ``privacy`` env vars, and fail the attempt if any
# script returns non-zero — a failed pre_exec means the executor would
# see stale or wrong data, so we must not proceed.


PRE_EXEC_TIMEOUT_SECONDS = max(
    60,
    int(os.environ.get("CLAWBENCH_PRE_EXEC_TIMEOUT_SECONDS", "600")),
)


class PreExecError(RuntimeError):
    """Raised when a pre_exec script fails. Surfaced as an infra_error so
    the attempt is recorded with a clear reason rather than crashing the
    runner.
    """

    def __init__(self, script: str, returncode: int, tail: str):
        self.script = script
        self.returncode = returncode
        self.tail = tail
        super().__init__(
            f"pre_exec script {script!r} failed with exit code {returncode}: {tail}"
        )


def _script_env(task: TaskSpec) -> dict[str, str]:
    env = dict(os.environ)
    if task.privacy:
        try:
            env.update({k: str(v) for k, v in resolve_privacy_env(task.privacy).items()})
        except Exception:
            pass
    env.setdefault("CLAWBENCH_ROOT", str(ROOT))
    env.setdefault("CLAWBENCH_TASK_ID", task.task_id)
    env.setdefault("CLAWBENCH_TASK_INJECTION_ROOT", str(task.injection_root))
    return env


def run_pre_exec_scripts(task: TaskSpec) -> list[dict[str, str]]:
    """Run every script in ``task.pre_exec`` sequentially. Returns a list of
    per-script records (script, returncode, tail of stdout/stderr) for
    session_meta logging.

    Raises ``PreExecError`` on first non-zero exit so downstream container
    setup doesn't start against stale data.

    Concurrency: the entire loop is wrapped in a host-side flock keyed on
    ``task.task_id`` (see ``populator_lock``). Concurrent workers for the
    same task serialize on the lock; whichever gets in first runs the
    populator and writes the TTL state, and every worker that gets the
    lock within TTL seconds afterward sees ``skip=True`` and records a
    ``skipped_fresh`` no-op. This is what lets ``workers>1`` be safe on
    populator-bearing tasks.
    """
    if not task.pre_exec:
        return []

    env = _script_env(task)
    records: list[dict[str, str]] = []
    injection_root = task.injection_root.resolve()
    script_paths = [(injection_root / rel).resolve() for rel in task.pre_exec]

    # ── Cache invalidation strategy ────────────────────────────────
    # Two independent levers control whether populator_lock skips a
    # fresh state — the design merges main's broader fingerprint with
    # skill_usage's TTL-controlled freshness:
    #
    # (1) ``fingerprint_paths`` — what content changes invalidate the
    #     cache. The populator output is part of the task contract,
    #     not just the populator source. If the public prompt,
    #     supervisor rule, or any reference / source file changes
    #     between syncs, reusing a previous fresh state would leave
    #     live ground truth out of sync with the runner-host task
    #     files. We therefore fingerprint the populator scripts AND
    #     the task yaml AND every ``references/`` and ``sources/``
    #     file.
    #
    # (2) ``ttl_seconds`` — how long the cache is allowed to stay
    #     fresh when the fingerprint is unchanged. Parallel-safe
    #     populators (``task.pre_exec_parallel_safe = True``) opt
    #     into the module default TTL (~1 hour) so a worker burst can
    #     share idempotent setup. Non-parallel-safe populators (the
    #     common case for live-API tasks that mutate external state)
    #     force ``TTL=0`` so each attempt re-runs the populator,
    #     ensuring live state is reset rather than silently reused
    #     from a prior model run.
    #
    # Composition: TTL=0 collapses to "always re-run" regardless of
    # fingerprint; TTL=None + matching fingerprint reuses; TTL=None +
    # changed fingerprint re-runs. This gives precise control over
    # both freshness window and content-driven invalidation.
    fingerprint_paths = [*script_paths, task.file_path.resolve()]
    for rel in task.references:
        fingerprint_paths.append((injection_root / rel).resolve())
    for rel in task.sources:
        fingerprint_paths.append((injection_root / "sources" / rel).resolve())
    ttl_seconds = None if task.pre_exec_parallel_safe else 0

    with populator_lock(task.task_id, fingerprint_paths, ttl_seconds=ttl_seconds) as guard:
        if guard["skip"]:
            records.append(
                {
                    "script": ",".join(task.pre_exec),
                    "returncode": "skipped_fresh",
                    "tail": (
                        "populator state fresh (ttl-guarded); "
                        f"fingerprint={guard['fingerprint']}"
                    ),
                }
            )
            return records

        for rel, script_path in zip(task.pre_exec, script_paths):
            cmd = [sys.executable, str(script_path)]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(injection_root),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=PRE_EXEC_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                tail = (exc.stdout or "") + (exc.stderr or "")
                records.append(
                    {
                        "script": rel,
                        "returncode": "timeout",
                        "tail": tail[-4000:],
                    }
                )
                raise PreExecError(rel, -1, tail[-2000:]) from exc

            tail_stdout = (proc.stdout or "")[-2000:]
            tail_stderr = (proc.stderr or "")[-2000:]
            record = {
                "script": rel,
                "returncode": str(proc.returncode),
                "tail": (tail_stdout + "\n---stderr---\n" + tail_stderr)[-4000:],
            }
            records.append(record)
            if proc.returncode != 0:
                # Populator failed — intentionally do NOT mark state ok,
                # so the next worker that acquires the lock sees stale
                # state and retries.
                raise PreExecError(rel, proc.returncode, record["tail"])

        mark_populator_ok(guard["state_path"], guard["fingerprint"])

    return records


# ─────────────────────────────────────────────────────────────────────
# Section 2 — Container boot + per-backend config injection
# ─────────────────────────────────────────────────────────────────────


CONTAINER_HOST_ALIASES = {
    "host.docker.internal": os.environ.get("CLAWBENCH_HOST_GATEWAY", "host-gateway").strip(),
    "match-stream.local": os.environ.get("CLAWBENCH_HOST_GATEWAY", "host-gateway").strip(),
}


def runtime_base_skills() -> list[str]:
    manifest = load_base_skills_manifest()
    return [str(item).strip() for item in manifest.get("skills") or [] if str(item).strip()]


def runtime_base_skill_fallbacks() -> set[str]:
    manifest = load_base_skills_manifest()
    return {str(item).strip() for item in manifest.get("fallback_skills") or [] if str(item).strip()}


def build_proxy_env_script() -> str:
    keys = [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "no_proxy",
        "NO_PROXY",
    ]
    lines = []
    for key in keys:
        value = os.environ.get(key)
        if value:
            lines.append(f"export {key}={json.dumps(artifacts.normalize_proxy_value(value))}")
    return "\n".join(lines) + ("\n" if lines else "")


def start_container(image: str, task: TaskSpec, attempt_id: str) -> str:
    container_name = f"clawbench-{task_config.slugify(task.task_id)}-{attempt_id}"
    docker_mod.docker_rm(container_name, timeout_seconds=5.0)
    proxy_env_args: list[str] = []
    for key in (
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "no_proxy",
        "NO_PROXY",
    ):
        value = os.environ.get(key)
        if value:
            proxy_env_args.extend(["-e", f"{key}={artifacts.normalize_proxy_value(value)}"])
    # Tell the agent-browser CLI (used by every backend — openclaw, edict,
    # and nanobot — via the agent-browser-control skill) to launch
    # Chromium with a visible window instead of its default
    # ``--headless=new``. Without this, recordings captured by ffmpeg
    # x11grab on display :99 only show the empty desktop because Chromium
    # never renders to the screen.
    #
    # Round 11 / B1: the recording tier on the task couples to headed
    # mode.  ``high`` runs headed (visible Chromium so the high-fidelity
    # recording is meaningful).  ``low`` and ``none`` force headless
    # (saves ~500MB per container of GUI compositor + the empty-desktop
    # capture overhead).  This is computed before the global
    # ``BROWSER_HEADED`` env-var check so the task-level decision wins.
    browser_env_args: list[str] = []
    # Default fallback is "none" — matches ``TaskSpec.recording`` default
    # (lib/task.py).  Real TaskSpec objects always have the attribute,
    # so this fallback only triggers for synthetic test-doubles or other
    # non-TaskSpec inputs.  Pre-Round-15 this fell back to "high" which
    # would silently make those callers run headed + record; the new
    # default keeps the resource-cheap path (headless + no recording).
    task_recording_mode = getattr(task, "recording", "none") or "none"
    task_headed_mode = (getattr(task, "headed", "auto") or "auto").lower()
    # Explicit ``headed`` wins over the recording-coupled default.
    if task_headed_mode == "true":
        browser_env_args.extend(["-e", "AGENT_BROWSER_HEADED=1"])
    elif task_headed_mode == "false":
        browser_env_args.extend(["-e", "AGENT_BROWSER_HEADED=0"])
    elif task_recording_mode == "high":
        # high tier: visible Chromium so recording captures real UI
        browser_env_args.extend(["-e", "AGENT_BROWSER_HEADED=1"])
    elif task_recording_mode in ("none", "low"):
        # none/low: force headless regardless of global default; saves
        # the ~500MB X compositor + GUI rendering overhead per container
        browser_env_args.extend(["-e", "AGENT_BROWSER_HEADED=0"])
    elif BROWSER_HEADED:
        # Fallback for unexpected mode values: respect the global flag
        browser_env_args.extend(["-e", "AGENT_BROWSER_HEADED=1"])
    # Privacy credentials: each KEY declared in the task's `.privacy`
    # file becomes an env var inside the container, sourced from
    # configs/privacy.local.env. Task prompts must refer to these by
    # env-var name (e.g. "$EMAIL_PASSWORD"), never by filesystem path.
    # resolve_privacy_env() already raised at load-time if any declared
    # key was missing/empty, so this call is defensive.
    privacy_env_args: list[str] = []
    for key, value in resolve_privacy_env(task.privacy).items():
        privacy_env_args.extend(["-e", f"{key}={value}"])
    extra_host_args: list[str] = []
    for host, target in CONTAINER_HOST_ALIASES.items():
        if host and target:
            extra_host_args.extend(["--add-host", f"{host}:{target}"])
    result = docker_mod.docker(
        [
            "run",
            "--platform",
            "linux/amd64",
            "-d",
            "--shm-size",
            "2g",
            "--name",
            container_name,
            *proxy_env_args,
            *browser_env_args,
            *privacy_env_args,
            *extra_host_args,
            image,
            "/bin/bash",
            "-lc",
            "tail -f /dev/null",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to start container")
    return container_name


def prepare_runtime(container: str, task: TaskSpec) -> None:
    agent_sys = task_config.normalize_agent_sys(task.agent_sys)
    shell = """
set -euo pipefail
rm -rf /tmp_workspace
mkdir -p /tmp_workspace/results
mkdir -p /tmp_workspace/clawbench/sources
mkdir -p /tmp_workspace/clawbench/logs
mkdir -p /tmp_workspace/clawbench/runtime
mkdir -p /root/skills
"""
    result = docker_mod.docker_exec(container, shell)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to prepare runtime")

    # Snapshot gating: when the task declares SNAPSHOT_MODE and it is not
    # set to "1", the agent MUST hit the live API, so the canonical offline
    # snapshot files (`*_snapshot.json`) must NOT be copied into the
    # container — otherwise the agent could read the expected answer shape
    # off-line and skip the real API call. Non-snapshot source files are
    # always copied. Tasks that don't declare SNAPSHOT_MODE behave as
    # before (everything in sources/ is copied).
    sources_dir = task.injection_root / "sources"
    privacy_env = resolve_privacy_env(task.privacy)
    snapshot_mode = privacy_env.get("SNAPSHOT_MODE", "").strip() == "1"
    snapshot_declared = "SNAPSHOT_MODE" in privacy_env
    if sources_dir.exists():
        for child in sorted(sources_dir.iterdir()):
            is_snapshot = child.name.endswith("_snapshot.json")
            if snapshot_declared and not snapshot_mode and is_snapshot:
                continue
            docker_mod.docker_cp_to_container(child, container, "/tmp_workspace/clawbench/sources/")

    # Privacy credentials are no longer copied as files. They are
    # injected as environment variables by `start_container` (see the
    # `-e KEY=VALUE` args sourced from configs/privacy.local.env), so
    # nothing is written to /tmp_workspace/clawbench/.privacy here.

    # Services copy into a private harness-only path (chmod 0700 below) so the
    # executor cannot wander into them via ``ls /opt/clawbench/...``.  Root
    # within the container can still override, but a default LLM ``ls`` returns
    # EACCES, and any explicit ``chmod`` from the executor becomes a clear
    # privilege-escalation signal in the transcript.
    for service in task.services:
        local_service = task.injection_root / "services" / service.path
        if local_service.exists():
            target_root = artifacts.private_service_dir(task, service.path)
            docker_mod.docker_exec(container, f"mkdir -p {json.dumps(target_root)}")
            docker_mod.copy_tree_contents_to_container(local_service, container, target_root)
    if task.services:
        docker_mod.docker_exec(
            container,
            f"chmod 0700 {json.dumps(str(artifacts.PRIVATE_SERVICE_ROOT.parent))}",
        )
        docker_mod.docker_exec(
            container,
            f"chmod 0700 {json.dumps(str(artifacts.PRIVATE_SERVICE_ROOT))}",
        )

    for skill in task.skills:
        local_skill = task.injection_root / "skills" / skill
        if local_skill.exists():
            docker_mod.docker_cp_to_container(local_skill, container, "/root/skills/")
            continue
        if skill in runtime_base_skill_fallbacks():
            bundled = ROOT / "docker" / "base_skills" / skill
            if bundled.exists():
                docker_mod.docker_cp_to_container(bundled, container, "/root/skills/")

    fd, proxy_name = tempfile.mkstemp(prefix="clawbench-proxy-", suffix=".sh")
    os.close(fd)
    proxy_path = Path(proxy_name)
    write_local(proxy_path, build_proxy_env_script())
    try:
        docker_mod.docker_cp_to_container(proxy_path, container, "/tmp_workspace/clawbench/runtime/proxy_env.sh")
    finally:
        proxy_path.unlink(missing_ok=True)

    if agent_sys == "nanobot":
        workspace_skills = docker_mod.docker_exec(
            container,
            """
set -euo pipefail
mkdir -p /tmp_workspace/skills
for skill_dir in /root/skills/*; do
  [ -d "$skill_dir" ] || continue
  ln -sfn "$skill_dir" "/tmp_workspace/skills/$(basename "$skill_dir")"
done
""",
        )
        if workspace_skills.returncode != 0:
            raise RuntimeError(workspace_skills.stderr.strip() or workspace_skills.stdout.strip() or "failed to link nanobot skills into workspace")


def inject_openclaw_config(container: str, task: TaskSpec, attempt_id: str = "") -> None:
    model_ref = task_config.model_id_for_backend(task.model, "openclaw")
    config_fragment = openclaw.normalize_openclaw_config_fragment(
        task_config.load_models_payload(),
        for_container=True,
        attempt_id=attempt_id,
    )
    explicit_image_model = task_config.resolve_model_ref(str(task.image_model or "").strip())
    image_model_ref = explicit_image_model or openclaw.select_openclaw_image_model(config_fragment, model_ref)
    openclaw._copy_openclaw_models_fragment(container, config_fragment)
    model_registry = openclaw.openclaw_agent_models_registry(config_fragment)
    script = openclaw.build_openclaw_config_script(
        model_ref=model_ref,
        image_model_ref=image_model_ref,
        model_registry=model_registry,
        workspace="/tmp_workspace",
    )
    result = docker_mod.docker_exec(container, script)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to inject openclaw config")

    link_workspace = docker_mod.docker_exec(
        container,
        "rm -rf /root/.openclaw/workspace && ln -s /tmp_workspace /root/.openclaw/workspace",
    )
    if link_workspace.returncode != 0:
        raise RuntimeError(link_workspace.stderr.strip() or link_workspace.stdout.strip() or "failed to link openclaw workspace")

    openclaw.validate_openclaw_config(container, label="openclaw")


def inject_edict_config(container: str, task: TaskSpec, attempt_id: str = "") -> None:
    model_ref = task_config.model_id_for_backend(task.model, "openclaw_edict")
    config_fragment = openclaw.normalize_openclaw_config_fragment(
        task_config.load_models_payload(),
        for_container=True,
        attempt_id=attempt_id,
    )
    explicit_image_model = task_config.resolve_model_ref(str(task.image_model or "").strip())
    image_model_ref = explicit_image_model or openclaw.select_openclaw_image_model(config_fragment, model_ref)
    openclaw._copy_openclaw_models_fragment(container, config_fragment)
    model_registry = openclaw.openclaw_agent_models_registry(config_fragment)
    specs = edict.edict_agent_specs()
    if not specs:
        raise RuntimeError(f"missing edict demo config: {edict.EDICT_DEMO_CONFIG}")
    agent_payload = []
    for spec in specs:
        agent_id = spec["id"]
        workspace = f"/root/.openclaw/workspace-{agent_id}"
        agent_payload.append(
            {
                "id": agent_id,
                "workspace": workspace,
                "default": agent_id == "taizi",
                "subagents": spec.get("subagents", {}),
            }
        )
    script = openclaw.build_openclaw_config_script(
        model_ref=model_ref,
        image_model_ref=image_model_ref,
        model_registry=model_registry,
        workspace="/root/.openclaw/workspace-taizi",
        agents_list=agent_payload,
        sessions_visibility="all",
        sandbox_session_visibility="all",
        agent_to_agent_allow=[spec["id"] for spec in specs if spec.get("id")],
    )
    result = docker_mod.docker_exec(container, script)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to inject edict config")

    runtime_assets = docker_mod.docker_exec(
        container,
        f"""
set -euo pipefail
rm -rf {edict.EDICT_RUNTIME_ROOT}
mkdir -p {edict.EDICT_RUNTIME_ROOT}
cp -a /opt/edict/. {edict.EDICT_RUNTIME_ROOT}/
mkdir -p {edict.EDICT_RUNTIME_ROOT}/data {edict.EDICT_RUNTIME_ROOT}/logs
for seed in {' '.join(edict.EDICT_DEMO_SEED_FILES)}; do
  if [ -f "{edict.EDICT_RUNTIME_ROOT}/demo/$seed" ]; then
    cp -f "{edict.EDICT_RUNTIME_ROOT}/demo/$seed" "{edict.EDICT_RUNTIME_ROOT}/data/$seed"
  fi
done
""",
    )
    if runtime_assets.returncode != 0:
        raise RuntimeError(runtime_assets.stderr.strip() or runtime_assets.stdout.strip() or "failed to prepare edict runtime assets")

    for agent_dir in sorted(p.name for p in edict.EDICT_AGENTS_ROOT.iterdir() if p.is_dir()):
        soul_content = edict.render_edict_soul(agent_dir, task)
        if not soul_content:
            continue
        docker_mod.docker_exec(container, f"mkdir -p /root/.openclaw/workspace-{agent_dir}")
        docker_mod.docker_write_text_file(
            container,
            f"/root/.openclaw/workspace-{agent_dir}/SOUL.md",
            soul_content,
            prefix=f"clawbench-edict-soul-{agent_dir}-",
            suffix=".md",
        )
        docker_mod.docker_write_text_file(
            container,
            f"/root/.openclaw/workspace-{agent_dir}/AGENTS.md",
            edict.build_edict_agents_md(agent_dir, task),
            prefix=f"clawbench-edict-agents-{agent_dir}-",
            suffix=".md",
        )
        docker_mod.docker_write_text_file(
            container,
            f"/root/.openclaw/workspace-{agent_dir}/TOOLS.md",
            edict.build_edict_tools_md(agent_dir),
            prefix=f"clawbench-edict-tools-{agent_dir}-",
            suffix=".md",
        )
        docker_mod.docker_exec(
            container,
            f"""
set -euo pipefail
mkdir -p /root/.openclaw/workspace-{agent_dir}/skills
ln -sfn {edict.EDICT_RUNTIME_ROOT}/scripts /root/.openclaw/workspace-{agent_dir}/scripts
ln -sfn {edict.EDICT_RUNTIME_ROOT}/data /root/.openclaw/workspace-{agent_dir}/data
ln -sfn {edict.EDICT_RUNTIME_ROOT}/dashboard /root/.openclaw/workspace-{agent_dir}/dashboard
ln -sfn {edict.EDICT_RUNTIME_ROOT}/agents /root/.openclaw/workspace-{agent_dir}/agents
ln -sfn {edict.EDICT_RUNTIME_ROOT}/edict /root/.openclaw/workspace-{agent_dir}/edict
ln -sfn {edict.EDICT_RUNTIME_ROOT} /root/.openclaw/workspace-{agent_dir}/edict_home
ln -sfn /tmp_workspace/clawbench /root/.openclaw/workspace-{agent_dir}/clawbench
ln -sfn /tmp_workspace/results /root/.openclaw/workspace-{agent_dir}/results
ln -sfn /tmp_workspace /root/.openclaw/workspace-{agent_dir}/tmp_workspace
""",
        )

    openclaw.validate_openclaw_config(container, label="edict")


# Note: the playwright-mcp helpers (``_playwright_mcp_args`` /
# ``_playwright_mcp_env``) that lived here have been removed.  All three
# agent backends (openclaw, openclaw_edict, nanobot) now drive the
# browser exclusively via the ``agent-browser`` CLI skill rather than
# through any MCP server.  See ``inject_nanobot_config`` below where the
# nanobot config explicitly registers no MCP servers, and ``openclaw``'s
# config which disables its built-in ``browser`` MCP.  The transcript-
# rewriting code that compensates for base64 ImageContent blocks (in
# ``lib/runner/transcripts.py`` and ``media.py``) is intentionally kept
# so historical attempts containing those blocks still render correctly
# in the webui.


def inject_nanobot_config(container: str, task: TaskSpec, attempt_id: str = "") -> None:
    models_payload = task_config.load_models_payload()
    provider_name, provider_cfg = task_config.resolve_models_provider_entry(task.model, models_payload)
    base_url = os.environ.get("CLAWBENCH_EVAL_BASE_URL") or str(provider_cfg.get("baseUrl") or "")
    if not base_url:
        raise ValueError(
            f"nanobot provider {provider_name!r} for model {task.model!r} is missing baseUrl; "
            "set providers.<name>.baseUrl in configs/models.local.json or export CLAWBENCH_EVAL_BASE_URL"
        )
    api_key = os.environ.get("CLAWBENCH_EVAL_API_KEY", str(provider_cfg.get("apiKey") or ""))
    # Detect adapter-routed providers: when the resolved provider goes
    # through one of our compat adapters (drop_max_tokens / responses_via
    # _chat), prepend the per-attempt URL prefix so the adapter can tag
    # every nanobot usage event with this attempt's task_id. This is what
    # finally makes nanobot token usage observable AND correctly per-task
    # under parallel batch_run — without the prefix, nanobot calls land
    # in the shared adapter log with no task identifier and the rollup in
    # ``build_attempt_usage_payload`` falls back to ``available=False``.
    proxy_defs = openclaw._proxy_definitions_from_payload(models_payload)
    api_base_for_container = container_visible_value(base_url)
    if attempt_id and openclaw._is_adapter_routed_provider(provider_cfg, proxy_defs):
        api_base_for_container = openclaw.inject_attempt_url_prefix(api_base_for_container, attempt_id)
    payload = {
        "providers": {
            "custom": {
                "apiKey": api_key or "missing-api-key",
                "apiBase": api_base_for_container,
            }
        },
        "agents": {
            "defaults": {
                "provider": "custom",
                "model": task_config.model_id_for_backend(task.model, "nanobot"),
                "workspace": "/tmp_workspace",
                "timezone": os.environ.get("TZ", "Asia/Shanghai"),
                # Unified cross-backend executor context window (see
                # ``lib/defaults.py:EXECUTOR_CONTEXT_WINDOW_TOKENS``). nanobot's
                # internal default is only 65_536, which badly under-utilises
                # modern 200K+ token models and caused premature context-length
                # pressure on long multi-turn tasks. Setting this aligns
                # nanobot with the openclaw-side ``contextTokens`` value so
                # both backends target the same provider ceiling.
                "context_window_tokens": EXECUTOR_CONTEXT_WINDOW_TOKENS,
                # Sampling/decode overrides come from the resolved model
                # entry's ``quirks`` dict in configs/models*.json, not from
                # model-name substring checks in code. Example: Moonshot
                # ``kimi-k2.x`` rejects nanobot's default 0.1 with
                # ``invalid temperature: only 1 is allowed for this model``,
                # so the kimi entries set ``quirks: {"temperature": 1.0}``.
                # Other models keep nanobot's defaults by declaring no quirks.
                **task_config.model_quirks(task.model, models_payload),
            }
        },
        "tools": {
            "restrictToWorkspace": False,
            "exec": {
                "enable": True,
                "timeout": 120,
                "pathAppend": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            },
            "web": {
                "search": {
                    "provider": "duckduckgo",
                }
            },
            # No MCP servers configured — nanobot drives the browser via the
            # ``agent-browser`` CLI skill, same as openclaw now does. The
            # ``agent-browser-control`` SKILL.md under ``/tmp_workspace/skills/``
            # (symlinked from ``/root/skills/`` by ``prepare_runtime``) carries
            # ``always: true`` frontmatter so nanobot's SkillsLoader injects
            # the full body into the system prompt at turn 1. This removes
            # three playwright-mcp footguns observed in earlier runs:
            #   (a) 16 KB tool-result cap mid-base64 forced placeholder
            #       stripping in transcripts (see ``_strip_inline_image_base64``).
            #   (b) ``browser_run_code`` returning 1.4 MB DOM text when the
            #       agent asked for page script evaluation on YouTube / Amazon.
            #   (c) stdio env whitelist dropping ``DISPLAY`` so recordings
            #       were empty desktops unless we patched the env.
            # agent-browser respects path/fullPage/type directly, runs
            # headed against :99 via the container's default env, and its
            # daemon persists across calls so there is no spawn overhead.
        },
    }
    script = f"""python3 - <<'PY'
import json
from pathlib import Path

cfg_path = Path('/root/.nanobot/config.json')
cfg_path.parent.mkdir(parents=True, exist_ok=True)
cfg = json.loads({json.dumps(json.dumps(payload, ensure_ascii=False))})
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
PY"""
    result = docker_mod.docker_exec(container, script)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to inject nanobot config")


# ─────────────────────────────────────────────────────────────────────
# Section 3 — Service readiness
# ─────────────────────────────────────────────────────────────────────
#
# After the container is up, spin up the desktop / openclaw gateway /
# per-task ``oneshot`` services and poll them until they answer
# requests, then hand off to ``lib/runner/agents.py``.  All functions
# here run inside the container via ``docker exec`` and use
# ``time.sleep`` / loop-and-probe patterns.  No artefact collection or
# orchestration happens here.


BROWSER_GATEWAY_LOG = "/tmp_workspace/clawbench/logs/gateway.log"
DEFAULT_ONESHOT_SERVICE_TIMEOUT_SECONDS = 1200


def oneshot_service_timeout_seconds() -> int:
    raw = os.environ.get("CLAWBENCH_ONESHOT_SERVICE_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_ONESHOT_SERVICE_TIMEOUT_SECONDS
    try:
        return max(60, int(raw))
    except ValueError:
        return DEFAULT_ONESHOT_SERVICE_TIMEOUT_SECONDS


def start_desktop(container: str) -> None:
    result = docker_mod.docker_exec(container, "/usr/local/bin/start-desktop.sh >/tmp_workspace/clawbench/logs/desktop.log 2>&1", detach=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to start desktop")
    time.sleep(8)


def start_gateway(container: str) -> None:
    result = docker_mod.docker_exec(
        container,
        "openclaw gateway --allow-unconfigured --port 18789 >/tmp_workspace/clawbench/logs/gateway.log 2>&1",
        detach=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to start gateway")
    for _ in range(60):
        probe = docker_mod.docker_exec(container, "curl -fsS --max-time 2 http://127.0.0.1:18789/healthz >/dev/null")
        if probe.returncode == 0:
            return
        time.sleep(1)
    raise TimeoutError("openclaw gateway did not become ready")


def gateway_ready(container: str) -> bool:
    try:
        probe = docker_mod.docker_exec(
            container,
            "curl -fsS --max-time 2 http://127.0.0.1:18789/healthz >/dev/null",
            timeout_seconds=15,
        )
    except subprocess.TimeoutExpired:
        return False
    return probe.returncode == 0


def ensure_gateway_ready(container: str) -> None:
    for _ in range(3):
        if gateway_ready(container):
            return
        time.sleep(2)
    start_gateway(container)


def task_likely_uses_browser(task: TaskSpec) -> bool:
    haystacks = [
        str(task.task or "").lower(),
        " ".join(str(item) for item in (task.skills or [])).lower(),
        " ".join(str(item) for item in (task.sources or [])).lower(),
    ]
    keywords = [
        "browser",
        "search",
        "page",
        "site",
        "video",
        "bilibili",
        "youtube",
        "taobao",
        "manmanbuy",
        "网页",
        "页面",
        "网站",
        "搜索",
        "视频",
        "浏览器",
        "慢慢买",
        "淘宝",
        "截图",
    ]
    return any(keyword in haystack for haystack in haystacks for keyword in keywords)


def browser_service_ready(container: str) -> bool:
    try:
        probe = docker_mod.docker_exec(
            container,
            "curl -sS --max-time 2 -o /dev/null http://127.0.0.1:18791/healthz",
            timeout_seconds=15,
        )
    except subprocess.TimeoutExpired:
        return False
    return probe.returncode == 0


def browser_profile_running(container: str) -> bool:
    try:
        probe = docker_mod.docker_exec(
            container,
            """python3 - <<'PY'
import socket
import subprocess
import sys

checks = [
    "pgrep -af '/usr/local/bin/chromium.*--remote-debugging-port=18800' >/dev/null",
    "pgrep -af '/usr/local/bin/chromium.*user-data-dir=/root/.openclaw/browser/openclaw/user-data' >/dev/null",
]
for command in checks:
    proc = subprocess.run(command, shell=True, text=True, capture_output=True)
    if proc.returncode == 0:
        sys.exit(0)

sock = socket.socket()
sock.settimeout(1.5)
try:
    sock.connect(('127.0.0.1', 18800))
except OSError:
    sys.exit(1)
finally:
    sock.close()
sys.exit(0)
PY""",
            timeout_seconds=15,
        )
    except subprocess.TimeoutExpired:
        return False
    return probe.returncode == 0


def start_openclaw_browser_profile(container: str) -> tuple[bool, str]:
    if browser_profile_running(container):
        return True, "browser profile already running"
    try:
        probe = docker_mod.docker_exec(
            container,
            """python3 - <<'PY'
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

cfg_path = Path('/root/.openclaw/openclaw.json')
cfg = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {}
token = str((((cfg.get('gateway') or {}).get('auth') or {}).get('token')) or '').strip()
if not token:
    print('missing gateway auth token')
    sys.exit(2)

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}
urls = [
    'http://127.0.0.1:18791/start',
    'http://127.0.0.1:18791/start?profile=openclaw',
]
payload = b'{}'
errors = []
for url in urls:
    req = urllib.request.Request(url, data=payload, method='POST', headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode('utf-8', errors='ignore').strip()
            print(body or f'HTTP {resp.status}')
            sys.exit(0)
    except urllib.error.HTTPError as err:
        errors.append(f'{url} -> HTTP {err.code}: {err.read().decode("utf-8", errors="ignore").strip()}')
    except Exception as err:
        errors.append(f'{url} -> {err}')
print(' | '.join(errors))
sys.exit(1)
PY""",
            timeout_seconds=20,
        )
    except subprocess.TimeoutExpired:
        return browser_profile_running(container), "browser profile start timed out"
    detail = (probe.stdout or probe.stderr or "").strip()
    if probe.returncode == 0:
        return True, detail
    if browser_profile_running(container):
        return True, detail
    return False, detail


# DEPRECATED: superseded by ``ensure_gateway_ready`` / ``start_services``.
# No callers remain in the runtime. Scheduled for removal in the next minor —
# see ``docs/deprecations.md`` for the migration window.
def wait_for_browser_service_ready(container: str, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        if browser_service_ready(container):
            started, detail = start_openclaw_browser_profile(container)
            if started:
                time.sleep(1)
                return
            if detail:
                last_error = detail
        time.sleep(1)
    gateway_tail = docker_mod.docker_exec(container, f"tail -n 160 {json.dumps(BROWSER_GATEWAY_LOG)} || true")
    detail = "\n".join(
        part.strip()
        for part in [
            gateway_tail.stdout or gateway_tail.stderr or "",
            last_error,
        ]
        if part.strip()
    )
    if detail:
        raise TimeoutError(f"openclaw browser service did not become ready: {detail}")
    raise TimeoutError("openclaw browser service did not become ready")


def ensure_openclaw_runtime_ready(container: str, task: TaskSpec) -> None:
    ensure_gateway_ready(container)
    # openclaw's built-in browser service is globally disabled
    # (``cfg.browser.enabled = False``, see ``build_openclaw_config_script``);
    # the agent uses the ``agent-browser`` CLI skill instead, which does
    # not depend on openclaw's control service. We therefore skip
    # ``wait_for_browser_service_ready`` — it would otherwise burn the
    # full 90 s timeout and trigger the container-boot retry loop.
    # ``task_likely_uses_browser`` is still exported for callers/tests.
    _ = task_likely_uses_browser


def _salvage_service_logs(container: str, host_out_dir: Path | None) -> Path | None:
    """Copy ``/tmp_workspace/clawbench/logs`` out of the container.

    When a service install dies the only artefact otherwise available is a
    short log tail.  Copy the whole directory so the full install transcript
    travels back via rsync and we can post-mortem the failure without sshing
    the worker (which by then has deleted the container anyway).

    Returns the host destination path on success, ``None`` otherwise.
    """
    if host_out_dir is None:
        return None
    try:
        dest = Path(host_out_dir) / "logs" / "container"
        dest.mkdir(parents=True, exist_ok=True)
        cp = subprocess.run(
            ["docker", "cp", f"{container}:/tmp_workspace/clawbench/logs/.", str(dest)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if cp.returncode != 0:
            return None
        return dest
    except (OSError, subprocess.SubprocessError):
        return None


def start_services(
    container: str,
    task: TaskSpec,
    *,
    host_out_dir: Path | None = None,
) -> list[dict]:
    started = []
    for service in task.services:
        log_path = f"/tmp_workspace/clawbench/logs/{service.name}.log"
        preamble = (
            "set -euo pipefail\n"
            f"cd {json.dumps(artifacts.private_service_dir(task, service.path))}\n"
            "if [ -f /tmp_workspace/clawbench/runtime/proxy_env.sh ]; then . /tmp_workspace/clawbench/runtime/proxy_env.sh; fi\n"
        )
        if service.oneshot:
            # Blocking: finish before the agent launches. Per-task installers
            # (pip, apt, data fetches) belong here — their output must be on
            # disk before any turn runs, otherwise the agent races the package
            # manager.
            command = (
                preamble
                + f"bash -lc {json.dumps(service.start)} >{log_path} 2>&1\n"
                + "echo oneshot"
            )
            result = docker_mod.docker_exec(container, command, timeout_seconds=oneshot_service_timeout_seconds())
            if result.returncode != 0:
                tail = docker_mod.docker_exec(container, f"tail -n 40 {log_path} 2>/dev/null || true")
                detail = (tail.stdout or tail.stderr or "").strip()
                # Pull the full /tmp_workspace/clawbench/logs out of the
                # container before it dies, so the controller receives the
                # install transcript with the attempt.
                salvaged = _salvage_service_logs(container, host_out_dir)
                hint = f" (full logs at {salvaged})" if salvaged else ""
                raise RuntimeError(
                    f"oneshot service {service.name!r} failed{hint}: {detail[-600:]}"
                )
            started.append({"name": service.name, "pid": "oneshot", "oneshot": True})
            continue
        command = (
            preamble
            + f"nohup bash -lc {json.dumps(service.start)} >{log_path} 2>&1 </dev/null &\n"
            + "echo $!"
        )
        result = docker_mod.docker_exec(container, command)
        if result.returncode != 0:
            _salvage_service_logs(container, host_out_dir)
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"failed to start service {service.name}")
        started.append({"name": service.name, "pid": result.stdout.strip()})
    return started
