"""Visual / media pipeline for one attempt.

Merged from ``recording.py`` + ``images.py`` in the third-round refactor.
Both files were dealing with the same concern — capturing or rewriting
visual artefacts produced by an attempt — and the call graph confirmed
they're invoked from the same step of ``collect_attempt_artifacts``.

Three concerns live here, kept distinct by section headers:

1. **TimelineRecorder** — per-phase span accumulator that persists to
   ``<attempt>/timeline.json`` incrementally so the WebUI's Execution
   Timeline Gantt panel can render in-flight attempts.  A process-global
   "current recorder" lets downstream modules (e.g. supervision) emit
   spans without plumbing a recorder arg through every signature.

2. **Desktop video recording** — drives an ffmpeg instance inside the
   container that captures the virtual X display and post-processes the
   raw MP4 into a 16x-speed replay.  Never raises: recording failure
   must not block the task.

3. **Inline-image salvage** — base64-armoured image payloads that snuck
   into text content (MCP tool results, OpenAI data URLs, historical
   nanobot playwright-mcp str()-ified dicts) are decoded to disk under
   ``inline_images/`` and replaced in-text with
   ``[image: inline_images/<hash>.<ext>]`` pointers.  A second helper
   rewrites ASCII-base64 image files left behind by generic
   write/edit tools to real binary bytes.
"""
from __future__ import annotations

import base64 as _base64
import hashlib
import json
import logging
import mimetypes
import re
import subprocess
import sys
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

from ..defaults import (
    RECORDING_DISPLAY,
    RECORDING_FINAL,
    RECORDING_INPUT_FPS,
    RECORDING_LOG,
    RECORDING_OUTPUT_FPS,
    RECORDING_PID_FILE,
    RECORDING_RAW,
    RECORDING_SPEEDUP,
    RECORDING_STOP_WAIT_STEPS,
    RECORDING_SUPPORTED_AGENT_SYSTEMS,
    RECORDING_VIDEO_SIZE,
)
from ..proxy import write_local
from ..task import TaskSpec
from .docker import docker_cp_from_container, docker_exec


# ─────────────────────────────────────────────────────────────────────
# Section 1: Timeline recorder
# ─────────────────────────────────────────────────────────────────────


class TimelineRecorder:
    """Accumulate (kind, name, start_ms, end_ms, extras) phase spans for a
    single attempt and persist to ``timeline.json`` incrementally so the
    WebUI can render progress for in-flight attempts.

    Every ``span()`` close / ``append_phase()`` / ``annotate_last()`` triggers
    a best-effort flush to disk. ``dump()`` remains as the authoritative
    end-of-attempt persist.
    """

    def __init__(
        self,
        attempt_started_ms: int,
        out_dir: Path | None = None,
    ) -> None:
        self.attempt_started_ms = int(attempt_started_ms)
        self.phases: list[dict[str, Any]] = []
        self._out_dir: Path | None = Path(out_dir) if out_dir is not None else None

    def bind_out_dir(self, out_dir: Path) -> None:
        """Late-bind the attempt directory. Useful if the recorder was
        created before the attempt dir was materialised on disk."""
        self._out_dir = Path(out_dir)
        # Flush once so in-flight viewers immediately get any spans already
        # recorded before the bind call.
        self._flush()

    def _flush(self) -> None:
        if self._out_dir is None:
            return
        try:
            if not self._out_dir.exists():
                self._out_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "attempt_started_ms": self.attempt_started_ms,
                "attempt_ended_ms": int(time.time() * 1000),
                "phases": self.phases,
                # ``in_progress`` flips to False inside ``dump()`` — the
                # WebUI uses it to decorate still-running attempts.
                "in_progress": True,
            }
            write_local(
                self._out_dir / "timeline.json",
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            )
        except Exception:
            pass

    @contextmanager
    def span(
        self,
        kind: str,
        name: str,
        *,
        cycle: int | None = None,
        extra: dict[str, Any] | None = None,
    ):
        start_ms = int(time.time() * 1000)
        # Flush NOW (on span open) so any consumer watching timeline.json
        # sees the already-accumulated phases even when the current span
        # is long-running (e.g. the executor span wraps several minutes of
        # ``run_agent`` work and would otherwise block the next flush until
        # it closes). This also re-creates timeline.json if a caller upstream
        # wiped the attempt dir between phases (run_primary_attempt rmtrees
        # its out_dir on entry) — the open-flush rebuilds it immediately so
        # the in-flight view never goes dark for long.
        self._flush()
        try:
            yield
        finally:
            entry: dict[str, Any] = {
                "kind": str(kind),
                "name": str(name),
                "start_ms": start_ms,
                "end_ms": int(time.time() * 1000),
            }
            if cycle is not None:
                entry["cycle"] = int(cycle)
            if extra:
                for k, v in extra.items():
                    if k not in entry:
                        entry[k] = v
            self.phases.append(entry)
            self._flush()

    def append_phase(
        self,
        kind: str,
        name: str,
        *,
        start_ms: int,
        end_ms: int,
        cycle: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "kind": str(kind),
            "name": str(name),
            "start_ms": int(start_ms),
            "end_ms": int(end_ms),
        }
        if cycle is not None:
            entry["cycle"] = int(cycle)
        if extra:
            for k, v in extra.items():
                if k not in entry:
                    entry[k] = v
        self.phases.append(entry)
        self._flush()

    def annotate_last(self, predicate, extra: dict[str, Any]) -> None:
        """Backfill extra fields onto the most recent phase matching the
        predicate. Used to attach tool_calls to the containing executor span.
        """
        for entry in reversed(self.phases):
            if predicate(entry):
                for k, v in extra.items():
                    entry[k] = v
                self._flush()
                return

    def dump(self, out_dir: Path) -> None:
        if self._out_dir is None:
            self._out_dir = Path(out_dir)
        payload = {
            "version": 1,
            "attempt_started_ms": self.attempt_started_ms,
            "attempt_ended_ms": int(time.time() * 1000),
            "phases": self.phases,
            "in_progress": False,
        }
        write_local(out_dir / "timeline.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


_ACTIVE_RECORDER: TimelineRecorder | None = None


def active_timeline_recorder() -> TimelineRecorder | None:
    """Return the currently-installed TimelineRecorder, or None if no attempt
    is in progress. Downstream modules (e.g. ``supervision_common``) call
    this to emit ``supervisor`` / ``user_simulator`` spans without plumbing
    a recorder argument through every signature."""
    return _ACTIVE_RECORDER


# DEPRECATED: kept for compat. Main flow now assigns ``_ACTIVE_RECORDER``
# directly. Scheduled for removal in the next minor — see
# ``docs/deprecations.md`` for the migration window.
@contextmanager
def attach_timeline_recorder(recorder: TimelineRecorder):
    global _ACTIVE_RECORDER
    prev = _ACTIVE_RECORDER
    _ACTIVE_RECORDER = recorder
    try:
        yield recorder
    finally:
        _ACTIVE_RECORDER = prev


def timeline_span(
    kind: str,
    name: str,
    *,
    cycle: int | None = None,
    extra: dict[str, Any] | None = None,
):
    """Return a span context for the currently active recorder, or a
    ``nullcontext`` no-op when no attempt is being timelined. Use this so
    instrumentation sites stay readable:
        with timeline_span("container_lifecycle", "start_container"):
            ...
    """
    rec = active_timeline_recorder()
    if rec is None:
        return nullcontext()
    return rec.span(kind, name, cycle=cycle, extra=extra)


# ─────────────────────────────────────────────────────────────────────
# Section 2: Desktop video recording (ffmpeg inside the container)
# ─────────────────────────────────────────────────────────────────────


def _recording_warn(message: str) -> None:
    print(f"[recording] {message}", file=sys.stderr, flush=True)


def _recording_params(mode: str) -> tuple[int, int, str]:
    """Round 11 / B1: return (input_fps, output_fps, video_size) for a tier."""
    from ..defaults import (
        RECORDING_LOW_INPUT_FPS,
        RECORDING_LOW_OUTPUT_FPS,
        RECORDING_LOW_VIDEO_SIZE,
    )
    if mode == "low":
        return (RECORDING_LOW_INPUT_FPS, RECORDING_LOW_OUTPUT_FPS, RECORDING_LOW_VIDEO_SIZE)
    # ``high`` (and any other value) → existing high-fidelity defaults.
    # ``none`` is short-circuited earlier in ``recording_session`` and
    # never reaches start_recording.
    return (RECORDING_INPUT_FPS, RECORDING_OUTPUT_FPS, RECORDING_VIDEO_SIZE)


def start_recording(container: str, *, mode: str = "high") -> bool:
    """Launch ffmpeg as a background process inside the container, recording the
    virtual X display to a raw MP4. Returns True if ffmpeg appears to have
    started, False otherwise. Never raises — recording failure must not block
    the task.

    Round 11 / B1: ``mode`` selects the recording tier (``high``/``low``).
    ``high`` reproduces pre-Round-11 behavior (10 fps, 1440x900).  ``low``
    runs at 5 fps + 1280x720 — usable for debug, ~50% less encode work.
    Callers wanting ``none`` should skip calling this function entirely
    (handled by ``recording_session``).
    """
    input_fps, _output_fps, video_size = _recording_params(mode)
    start_cmd = (
        "set -e; "
        "command -v ffmpeg >/dev/null 2>&1; "
        "mkdir -p /tmp_workspace/clawbench/logs; "
        "rm -f " + RECORDING_RAW + " " + RECORDING_FINAL + " " + RECORDING_PID_FILE + "; "
        "( ffmpeg -y -nostdin "
        "-f x11grab "
        f"-framerate {input_fps} "
        f"-video_size {video_size} "
        f"-i {RECORDING_DISPLAY} "
        "-codec:v libx264 -preset ultrafast -crf 30 -pix_fmt yuv420p "
        f"{RECORDING_RAW} "
        f">{RECORDING_LOG} 2>&1 & "
        f"echo $! > {RECORDING_PID_FILE} ); "
        "sleep 0.5; "
        f"test -s {RECORDING_PID_FILE} && kill -0 \"$(cat {RECORDING_PID_FILE})\""
    )
    try:
        result = docker_exec(container, start_cmd, timeout_seconds=20)
    except subprocess.TimeoutExpired:
        _recording_warn(f"start timed out for container {container}")
        return False
    except Exception as exc:  # pragma: no cover - defensive
        _recording_warn(f"start raised {exc!r} for container {container}")
        return False
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or (result.stdout or "").strip()
        _recording_warn(f"ffmpeg did not start in {container}: {stderr or 'unknown error'}")
        return False
    return True


def stop_recording(container: str, out_dir: Path, *, mode: str = "high") -> bool:
    """Signal the recorder to stop, post-process the raw capture into a 16x
    speed MP4, and copy it back to the attempt directory. Returns True iff
    recording.mp4 was copied to out_dir successfully. Never raises.

    Round 11 / B1: ``mode`` controls post-process output fps (high uses
    24 fps, low uses 12 fps — matches the recorded input).
    """
    _input_fps, output_fps, _video_size = _recording_params(mode)
    stop_cmd = (
        "PID=$(cat " + RECORDING_PID_FILE + " 2>/dev/null || true); "
        "if [ -n \"$PID\" ]; then "
        "  kill -INT \"$PID\" 2>/dev/null || true; "
        f"  for i in $(seq 1 {RECORDING_STOP_WAIT_STEPS}); do "
        "    kill -0 \"$PID\" 2>/dev/null || break; "
        "    sleep 0.5; "
        "  done; "
        "  kill -KILL \"$PID\" 2>/dev/null || true; "
        "fi; "
        f"rm -f {RECORDING_PID_FILE}"
    )
    try:
        stop_result = docker_exec(container, stop_cmd, timeout_seconds=30)
    except subprocess.TimeoutExpired:
        _recording_warn(f"stop timed out for container {container}")
        return False
    except Exception as exc:  # pragma: no cover - defensive
        _recording_warn(f"stop raised {exc!r} for container {container}")
        return False
    if stop_result.returncode != 0:
        stderr = (stop_result.stderr or "").strip() or (stop_result.stdout or "").strip()
        _recording_warn(f"failed to stop ffmpeg in {container}: {stderr or 'unknown'}")
        # Continue — the raw file may still be salvageable.

    postprocess_cmd = (
        "set -e; "
        f"test -s {RECORDING_RAW} || {{ echo 'empty raw recording' >&2; exit 2; }}; "
        "ffmpeg -y -nostdin "
        f"-i {RECORDING_RAW} "
        f'-filter:v "setpts=PTS/{RECORDING_SPEEDUP}" -an -r {output_fps} '
        "-c:v libx264 -preset faster -crf 28 -movflags +faststart -pix_fmt yuv420p "
        f"{RECORDING_FINAL} "
        f">>{RECORDING_LOG} 2>&1; "
        f"rm -f {RECORDING_RAW}"
    )
    try:
        pp_result = docker_exec(container, postprocess_cmd, timeout_seconds=600)
    except subprocess.TimeoutExpired:
        _recording_warn(f"post-process timed out for container {container}")
        return False
    except Exception as exc:  # pragma: no cover - defensive
        _recording_warn(f"post-process raised {exc!r} for container {container}")
        return False
    if pp_result.returncode != 0:
        stderr = (pp_result.stderr or "").strip() or (pp_result.stdout or "").strip()
        _recording_warn(f"ffmpeg post-process failed in {container}: {stderr or 'unknown'}")
        return False

    copied = docker_cp_from_container(container, RECORDING_FINAL, out_dir / "recording.mp4")
    # Best-effort cleanup inside the container so the next attempt starts clean.
    try:
        docker_exec(container, f"rm -f {RECORDING_FINAL}", timeout_seconds=10)
    except Exception:  # pragma: no cover - defensive
        pass
    if not copied:
        _recording_warn(f"docker cp recording.mp4 failed for container {container}")
        return False
    return True


@contextmanager
def recording_session(container: str, task: TaskSpec, out_dir: Path):
    """Context manager that records the virtual display while the `with` body
    executes. A no-op if the agent system isn't supported for recording or if
    ffmpeg fails to start. Always attempts to stop the recorder on exit.

    Round 11 / B1: gated by ``task.recording`` (``none``/``low``/``high``).
    - ``none`` → no ffmpeg, ``yield False``
    - ``low`` → ffmpeg at 5 fps + 1280x720
    - ``high`` → ffmpeg at 10 fps + 1440x900 (pre-Round-11 default)
    """
    # Lazy import avoids a module-init cycle: ``normalize_agent_sys`` lives
    # in the package's ``__init__.py`` (task_config bucket) which itself
    # imports from this module.
    from . import normalize_agent_sys

    agent_sys = normalize_agent_sys(task.agent_sys)
    if agent_sys not in RECORDING_SUPPORTED_AGENT_SYSTEMS:
        yield False
        return
    # Default fallback is "none" so synthetic / test-double tasks that
    # omit the attribute do NOT silently start an ffmpeg recording.
    # Real TaskSpec objects always set it (default "none" — see
    # lib/task.py), so this fallback path is for defensive use only.
    mode = getattr(task, "recording", "none") or "none"
    if mode == "none":
        # Skip ffmpeg entirely; the high-throughput path.  WebUI trace
        # won't have a video for this cycle but transcript/screenshots
        # remain available for debug.
        yield False
        return
    started = start_recording(container, mode=mode)
    try:
        yield started
    finally:
        if started:
            stop_recording(container, out_dir, mode=mode)


# ─────────────────────────────────────────────────────────────────────
# Section 3: Inline-image salvage (base64 → real files)
# ─────────────────────────────────────────────────────────────────────


_ACTIVE_INLINE_IMAGES_DIR: Path | None = None


def active_inline_images_dir() -> Path | None:
    return _ACTIVE_INLINE_IMAGES_DIR


@contextmanager
def attach_inline_images_dir(dir_path: Path):
    global _ACTIVE_INLINE_IMAGES_DIR
    prev = _ACTIVE_INLINE_IMAGES_DIR
    _ACTIVE_INLINE_IMAGES_DIR = Path(dir_path) if dir_path is not None else None
    try:
        yield _ACTIVE_INLINE_IMAGES_DIR
    finally:
        _ACTIVE_INLINE_IMAGES_DIR = prev


_INLINE_IMAGE_EXT_FALLBACK = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

# Some MCP tool results (notably playwright-mcp's screenshot helper)
# str()-ify their image content blocks into the surrounding text instead
# of emitting them as proper JSON content. We see things like
#     type='image' data='iVBORw0KGgo...'
# embedded in a longer text payload. Detect these in-band base64 blobs
# by their image magic prefix and extract them just like a real image
# block. Quick prefix check keeps the slow-path off the typical text.
_INLINE_BASE64_MAGIC_TO_MIME = {
    "iVBORw0KGgo": "image/png",
    "/9j/": "image/jpeg",
    "R0lGOD": "image/gif",
    "UklGR": "image/webp",
}

# Patterns matching base64-armoured images that snuck into a text block.
# Each pattern's first capture group is the base64 payload (no padding
# normalization needed — _persist_inline_image's b64decode handles it).
#
# Closing quote is OPTIONAL on every pattern: nanobot's playwright-mcp
# truncates its image str() representation with ``... (truncated)`` in
# the middle of the base64 string, so the original closing ``'`` never
# appears in the transcript line. We still match the leading base64 run
# (and persist whatever decodes successfully) — even a partial PNG can
# render a recognisable thumbnail; if decode fails entirely we still
# strip the noise and fall back to ``[image: <truncated by upstream>]``.
_INLINE_IMAGE_INLINE_PATTERNS: list[tuple[re.Pattern, str | None]] = [
    (re.compile(r"data:image/([A-Za-z0-9.+-]+);base64,([A-Za-z0-9+/=]{32,})"), "url"),
    (
        re.compile(
            r"['\"]?type['\"]?\s*[:=]\s*['\"]image['\"][^A-Za-z0-9+/=]{1,80}?"
            r"['\"]?(?:data|b64_json|base64)['\"]?\s*[:=]\s*['\"]([A-Za-z0-9+/=]{32,})['\"]?",
            re.DOTALL,
        ),
        None,
    ),
    (
        re.compile(
            r"['\"]?(?:data|b64_json|base64)['\"]?\s*[:=]\s*['\"]?"
            r"((?:iVBORw0KGgo|/9j/|R0lGOD|UklGR)[A-Za-z0-9+/=]{32,})['\"]?",
        ),
        None,
    ),
    (
        re.compile(
            r"((?:iVBORw0KGgo|/9j/|R0lGOD|UklGR)[A-Za-z0-9+/=]{200,})",
        ),
        None,
    ),
]


def _guess_image_mime_from_b64_prefix(b64: str, fallback: str = "image/png") -> str:
    for prefix, mime in _INLINE_BASE64_MAGIC_TO_MIME.items():
        if b64.startswith(prefix):
            return mime
    return fallback


def _strip_inline_image_base64(text: Any) -> Any:
    """Find base64-armoured images embedded in a text payload (Python-repr
    or data-URL form), persist each to inline_images/, and replace the
    inline blob with ``[image: inline_images/<hash>.<ext>]``. Pass-through
    when no active inline_images directory is bound or when the text has
    no image-magic markers."""
    if _ACTIVE_INLINE_IMAGES_DIR is None:
        return text
    if not isinstance(text, str) or not text:
        return text
    if not any(marker in text for marker in _INLINE_BASE64_MAGIC_TO_MIME.keys()):
        return text
    out = text
    for pat, mode in _INLINE_IMAGE_INLINE_PATTERNS:
        def _replace(m):
            if mode == "url":
                ext = (m.group(1) or "").strip().lower()
                b64 = m.group(2)
                mime = f"image/{ext or 'png'}"
            else:
                b64 = m.group(1)
                mime = _guess_image_mime_from_b64_prefix(b64)
            rel = _persist_inline_image(b64, mime)
            if rel:
                return f"[image: {rel}]"
            # Persistence failed (typically because the base64 payload was
            # truncated upstream by playwright-mcp's "... (truncated)"
            # placeholder, so b64decode produces nothing usable). Still
            # strip the multi-KB base64 noise from the transcript so the
            # supervisor / user-simulator workspaces stay slim — fall back
            # to a single-line placeholder describing the size.
            kb = len(b64) // 1024
            return f"[image: <truncated upstream, {kb}KB base64 stripped>]"
        out = pat.sub(_replace, out)
    return out


def _data_from_image_url(image_url_value: Any) -> tuple[str, str]:
    """Extract (base64-data, mime-type) from either:
      - a plain string ``"data:image/png;base64,AAAA..."``
      - a dict ``{"url": "data:..."}`` (OpenAI image_url format)
    Returns (``""``, ``""``) when the input isn't a recognizable data URL.
    """
    if isinstance(image_url_value, dict):
        url = image_url_value.get("url") or ""
    else:
        url = image_url_value or ""
    if not isinstance(url, str):
        return "", ""
    match = re.match(r"^data:(image/[\w.+-]+);base64,(.+)$", url.strip(), re.DOTALL)
    if not match:
        return "", ""
    return match.group(2), match.group(1)


def _persist_inline_image(
    data_b64: Any,
    mime: str = "image/png",
    *,
    label: str = "",
) -> str | None:
    """Decode a base64 image payload, save it to the currently-active
    inline_images directory under a ``<sha256-prefix>.<ext>`` filename, and
    return the attempt-relative path (e.g. ``inline_images/abcd1234.png``).

    Returns ``None`` when no active directory is bound, the data is empty,
    or decoding fails. Idempotent — the same base64 input always maps to
    the same filename so the transcript stays stable across re-normalization.
    """
    out_dir = _ACTIVE_INLINE_IMAGES_DIR
    if out_dir is None:
        return None
    if not isinstance(data_b64, str):
        return None
    clean = data_b64.strip()
    if not clean:
        return None
    if clean.startswith("data:"):
        pure, pure_mime = _data_from_image_url(clean)
        if pure:
            clean = pure
            mime = pure_mime or mime
    mime_key = str(mime or "image/png").strip().lower() or "image/png"
    ext = _INLINE_IMAGE_EXT_FALLBACK.get(mime_key) or mimetypes.guess_extension(mime_key) or ".png"
    try:
        raw_bytes = _base64.b64decode(clean, validate=False)
    except Exception as e:
        # Round-5 Phase 2 (H4): inline-image base64 decode failure used to
        # return None silently, leaving supervisor with a missing image slot
        # that looked like the agent never produced output.  Log loudly so
        # operators can grep "inline image decode failed" to find the
        # source attempt.
        LOG.error(
            "inline image base64 decode failed (mime=%s, %d chars): %s",
            mime, len(clean or ""), e,
        )
        return None
    if not raw_bytes:
        return None
    digest = hashlib.sha256(raw_bytes).hexdigest()[:16]
    filename = f"{digest}{ext}"
    target = out_dir / filename
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(raw_bytes)
    except Exception as e:
        # Same rationale as the base64 except above.
        LOG.error("inline image write failed (target=%s): %s", target, e)
        return None
    return f"inline_images/{filename}"


# When an agent saves a screenshot by calling a generic ``write``/``edit``
# tool with the raw base64 string as file content, the resulting file is
# ASCII text (e.g. ``iVBORw0KGgo...``) rather than image bytes. The WebUI
# serves such a file with an ``image/png`` Content-Type, but the browser
# can't decode the ASCII so the picture appears broken.
#
# ``_rewrite_base64_image_files_in_tree`` detects these files by their
# initial ASCII bytes (a known image-base64 magic prefix) and rewrites
# them to real binary bytes in place. Safeguards:
#   1. Files whose first bytes are already valid image magic are skipped.
#   2. We only decode when the leading bytes look like a recognised
#      image-base64 prefix (PNG/JPEG/GIF/WEBP).
#   3. The decoded bytes must themselves start with the corresponding
#      binary magic before we overwrite, so we never replace unrelated
#      text files that happened to begin with similar characters.
# The function is idempotent: once a file has been rewritten its leading
# bytes become binary magic and step 1 skips it next cycle.

_IMAGE_REWRITE_B64_TO_BYTES: list[tuple[bytes, bytes]] = [
    (b"iVBORw0KGgo", b"\x89PNG\r\n\x1a\n"),
    (b"/9j/", b"\xff\xd8\xff"),
    (b"R0lGOD", b"GIF8"),
    (b"UklGR", b"RIFF"),
]

_IMAGE_REWRITE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _maybe_rewrite_base64_image_file(path: Path) -> bool:
    """If ``path`` contains the ASCII base64 of an image (rather than
    image bytes), rewrite the file in place with the decoded bytes.
    Returns ``True`` on a successful rewrite, ``False`` otherwise.
    """
    try:
        with path.open("rb") as fh:
            head = fh.read(32)
    except Exception as e:
        # Round-5 Phase 2 (H4): file open failure here used to silently
        # skip the rewrite; the file might still be ASCII-base64 and the
        # WebUI would serve garbage.  Log so operators can investigate.
        LOG.error("image rewrite probe failed (path=%s): %s", path, e)
        return False
    if not head:
        return False
    for _, byte_magic in _IMAGE_REWRITE_B64_TO_BYTES:
        if head.startswith(byte_magic):
            return False
    stripped = head.lstrip()
    looks_like_b64_image = any(
        stripped.startswith(b64m) for b64m, _ in _IMAGE_REWRITE_B64_TO_BYTES
    ) or stripped.startswith(b"data:image/")
    if not looks_like_b64_image:
        return False
    try:
        raw_text = path.read_text(encoding="ascii", errors="strict")
    except Exception:
        return False
    stripped_text = raw_text.strip()
    data_url_match = re.match(
        r"^data:image/[\w.+-]+;base64,(.+)$", stripped_text, re.DOTALL
    )
    if data_url_match:
        stripped_text = data_url_match.group(1).strip()
    candidate = "".join(stripped_text.split())
    if not candidate:
        return False
    if not any(
        candidate.startswith(b64m.decode("ascii"))
        for b64m, _ in _IMAGE_REWRITE_B64_TO_BYTES
    ):
        return False
    expected_bytes = next(
        (
            byte_magic
            for b64m, byte_magic in _IMAGE_REWRITE_B64_TO_BYTES
            if candidate.startswith(b64m.decode("ascii"))
        ),
        None,
    )
    if expected_bytes is None:
        return False
    decoded: bytes | None = None
    for variant in _base64_repair_variants(candidate):
        try:
            buf = _base64.b64decode(variant, validate=False)
        except Exception:
            continue
        if buf and buf.startswith(expected_bytes):
            decoded = buf
            break
    if decoded is None:
        return False
    try:
        path.write_bytes(decoded)
    except Exception:
        return False
    return True


def _base64_repair_variants(candidate: str) -> list[str]:
    """Yield a small set of base64 strings to try, in order:
      1. pad the raw string to a multiple of 4
      2. truncate 1-3 trailing characters then pad
      3. raw (no padding, may still decode with validate=False)
    """
    variants: list[str] = []
    base = candidate.rstrip("=")
    for drop in (0, 1, 2, 3):
        if drop > len(base):
            break
        trimmed = base[: len(base) - drop] if drop else base
        pad = (-len(trimmed)) % 4
        variants.append(trimmed + ("=" * pad))
    variants.append(candidate)
    seen: set[str] = set()
    unique: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def _rewrite_base64_image_files_in_tree(root: Path) -> list[Path]:
    """Walk ``root`` and rewrite any base64-as-text image files in place.
    Returns the list of paths that were fixed (useful for logging).
    """
    if not root.exists():
        return []
    rewritten: list[Path] = []
    try:
        it = root.rglob("*")
    except Exception:
        return rewritten
    for path in it:
        try:
            if not path.is_file():
                continue
        except Exception:
            continue
        if path.suffix.lower() not in _IMAGE_REWRITE_EXTS:
            continue
        try:
            if _maybe_rewrite_base64_image_file(path):
                rewritten.append(path)
        except Exception:
            continue
    return rewritten
