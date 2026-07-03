#!/usr/bin/env python3
"""Runtime default values and path constants for Clawbench.

Keep this module minimal — it owns only the "what value do we use when
the user does not configure one" knobs:

- Model / reasoning-effort defaults for the three roles
- Max user-followups per attempt
- Paths to default config files
- Loader for the base-skills manifest

Prompt text lives under ``lib/templates/`` and translatable strings live
in ``lib/i18n.py``. Enum-like value sets live in ``lib/constants.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_SKILLS_MANIFEST_PATH = ROOT / "configs" / "base_skills.json"
DEFAULT_CODEX_CONFIG_PATH = "configs/codex.local.toml"
DEFAULT_EXECUTOR_MODEL = "gpt-5.4"
DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_MAX_USER_FOLLOWUPS = 2
ENABLE_PRIVACY_LEAKAGE_CAP = False

# Master switch for executor-side browser headed-vs-headless mode.
#
# **Important Round-12 update:** this flag is now ONLY honoured when the
# task's ``recording`` tier is ``high`` (or when the task object happens
# to be missing the field entirely, which only happens in defensive
# fallbacks — real ``TaskSpec`` objects always set it).  Real YAML tasks
# default to ``recording: none`` (see ``lib/task.py:TaskSpec.recording``)
# which forces ``AGENT_BROWSER_HEADED=0`` via ``container_lifecycle
# .start_container()`` regardless of this flag.  So the effective default
# in production is **headless + no recording**, not "headed for capture"
# as the pre-Round-12 comment suggested.
#
# Setting CLAWBENCH_BROWSER_HEADED=0 still forces headless across every
# code path; setting it to 1 only matters for the high-recording tier or
# the missing-attribute fallback.
#
# All three backends — openclaw, openclaw_edict, nanobot — drive Chromium
# through the ``agent-browser`` CLI skill, never through any MCP server.
# When the resolved mode is headed, ``AGENT_BROWSER_HEADED=1`` is
# exported into the executor container so agent-browser launches
# Chromium with a visible window (its default is ``--headless=new``).
#
# CLAWBENCH_PLAYWRIGHT_HEADED is honored as a legacy alias (historical
# name from when nanobot still launched playwright-mcp).
def _truthy_env(*names: str, default: str = "1") -> bool:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None:
            return raw.strip() not in {"", "0", "false", "False", "no", "off"}
    return default not in {"", "0", "false", "False", "no", "off"}


BROWSER_HEADED = _truthy_env("CLAWBENCH_BROWSER_HEADED", "CLAWBENCH_PLAYWRIGHT_HEADED", default="1")
# Legacy alias retained for code that imported the old name.
PLAYWRIGHT_HEADED = BROWSER_HEADED


# Unified context window for the executor-side agent LLM across ALL backends
# (openclaw / openclaw_edict / nanobot). Each backend exposes a different
# config key under its agents.defaults section, but this constant resolves
# the value fed into every one of them so a single env override adjusts
# behaviour everywhere:
#
#   - openclaw / openclaw_edict: written as ``agents.defaults.contextTokens``
#     in the generated ``/root/.openclaw/openclaw.json``.
#   - nanobot: written as ``agents.defaults.context_window_tokens`` in the
#     generated ``/root/.nanobot/config.json``.
#
# This is separate from the Codex-side context window used by
# supervisor/user_simulator — that one is configured in
# ``lib/supervision_common.py:render_codex_config`` via
# ``CLAWBENCH_CODEX_MODEL_CONTEXT_WINDOW`` / corresponding TOML keys. The
# two values can legitimately differ: the executor often runs against a
# narrower deployed window while Codex can use the full provider limit.
#
# Override globally:  CLAWBENCH_EXECUTOR_CONTEXT_WINDOW_TOKENS=<int>
EXECUTOR_CONTEXT_WINDOW_TOKENS = max(
    1024,
    int(os.environ.get("CLAWBENCH_EXECUTOR_CONTEXT_WINDOW_TOKENS", "200000")),
)


def load_base_skills_manifest() -> dict[str, Any]:
    """Load ``configs/base_skills.json`` and return a normalized dict.

    Missing file or malformed payload collapses to empty lists — callers
    treat "no base skills configured" as a valid runtime state.
    """
    if not BASE_SKILLS_MANIFEST_PATH.exists():
        return {"skills": [], "fallback_skills": []}
    payload = json.loads(BASE_SKILLS_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"skills": [], "fallback_skills": []}
    skills = [str(item).strip() for item in (payload.get("skills") or []) if str(item).strip()]
    fallback_skills = [str(item).strip() for item in (payload.get("fallback_skills") or []) if str(item).strip()]
    return {
        "skills": skills,
        "fallback_skills": fallback_skills,
    }


# ── Runtime identifiers shared across roles ──────────────────────────
# Single session id reused across every turn for every backend — that's
# how we guarantee the executor faces ONE continuous session. openclaw
# and nanobot pass this on the CLI; the edict orchestrator reads it via
# ``CLAWBENCH_EDICT_SESSION_ID`` env var (default ``"chat"``).
AGENT_SESSION_ID = "chat"

# ── Container image registry ─────────────────────────────────────────
DEFAULT_IMAGE = "clawbench-openclaw:latest"
DEFAULT_IMAGE_BY_AGENT_SYS = {
    "openclaw": "clawbench-openclaw:latest",
    "openclaw_edict": "clawbench-openclaw-edict:latest",
    "nanobot": "clawbench-nanobot:latest",
}

# ── Per-user local configs (optional; templates under configs/*.example.*) ─
DEFAULT_MODELS_CONFIG = ROOT / "configs" / "models.local.json"
DEFAULT_SHARED_ENV_FILE = ROOT / "configs" / "api.local.env"

# ── Container-side results root (where the executor saves evidence) ──
RESULTS_ROOT = "/tmp_workspace/results"

# ── Desktop recording constants (ffmpeg x11grab per supervision cycle) ─
RECORDING_LOG = "/tmp_workspace/clawbench/logs/recording.log"
RECORDING_RAW = "/tmp_workspace/clawbench/recording_raw.mp4"
RECORDING_FINAL = "/tmp_workspace/clawbench/recording.mp4"
RECORDING_PID_FILE = "/tmp_workspace/clawbench/recorder.pid"
RECORDING_DISPLAY = ":99"
RECORDING_VIDEO_SIZE = "1440x900"
RECORDING_INPUT_FPS = 10
RECORDING_OUTPUT_FPS = 24
RECORDING_SPEEDUP = 16
RECORDING_STOP_WAIT_STEPS = 20
RECORDING_SUPPORTED_AGENT_SYSTEMS = {"openclaw", "nanobot", "openclaw_edict"}

# Round 11 / B1: recording-mode tiers selectable via ``TaskSpec.recording``.
# Each tier picks fps + resolution + browser-headed coupling.  The
# default ``high`` tier reproduces pre-Round-11 behavior exactly; ``low``
# is the new task-yaml default (saves ~50% recording overhead); ``none``
# disables ffmpeg entirely (saves ~100% recording overhead + frees the
# RAM/CPU previously consumed by the encoder).
RECORDING_LOW_INPUT_FPS = 5
RECORDING_LOW_OUTPUT_FPS = 12
RECORDING_LOW_VIDEO_SIZE = "1280x720"
RECORDING_LOW_SPEEDUP = 16  # final video is 16x speedup regardless of tier


__all__ = [
    "ROOT",
    "BASE_SKILLS_MANIFEST_PATH",
    "DEFAULT_CODEX_CONFIG_PATH",
    "DEFAULT_EXECUTOR_MODEL",
    "DEFAULT_CODEX_MODEL",
    "DEFAULT_REASONING_EFFORT",
    "DEFAULT_MAX_USER_FOLLOWUPS",
    "ENABLE_PRIVACY_LEAKAGE_CAP",
    "BROWSER_HEADED",
    "PLAYWRIGHT_HEADED",
    "EXECUTOR_CONTEXT_WINDOW_TOKENS",
    "load_base_skills_manifest",
    "AGENT_SESSION_ID",
    "DEFAULT_IMAGE",
    "DEFAULT_IMAGE_BY_AGENT_SYS",
    "DEFAULT_MODELS_CONFIG",
    "DEFAULT_SHARED_ENV_FILE",
    "RESULTS_ROOT",
    "RECORDING_LOG",
    "RECORDING_RAW",
    "RECORDING_FINAL",
    "RECORDING_PID_FILE",
    "RECORDING_DISPLAY",
    "RECORDING_VIDEO_SIZE",
    "RECORDING_INPUT_FPS",
    "RECORDING_OUTPUT_FPS",
    "RECORDING_SPEEDUP",
    "RECORDING_STOP_WAIT_STEPS",
    "RECORDING_SUPPORTED_AGENT_SYSTEMS",
    "RECORDING_LOW_INPUT_FPS",
    "RECORDING_LOW_OUTPUT_FPS",
    "RECORDING_LOW_VIDEO_SIZE",
    "RECORDING_LOW_SPEEDUP",
]
