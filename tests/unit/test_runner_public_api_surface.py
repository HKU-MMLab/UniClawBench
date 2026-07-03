"""Phase 6A — lock the ``lib.runner`` public-API surface.

``lib/runner/__init__.py`` exposes a curated set of stable names via
``__all__``. Underscore-prefixed helpers, backend-specific constants
(``_EDICT_*``, ``_API_*``, ``_SENSITIVE_*``), and module-private utilities
must NOT be part of the surface — they remain accessible by deep import
(``from lib.runner.evaluation import _api_stop_reason``) so existing
internal callers keep working, but ``from lib.runner import *`` stays
small and predictable.

If you intentionally add a new public name to ``lib.runner``, also add it
to the alphabetised allow-list below.
"""
from __future__ import annotations


def _surface() -> set[str]:
    import lib.runner as runner

    assert hasattr(runner, "__all__"), "lib.runner.__init__.py must define __all__"
    return set(runner.__all__)


def test_public_api_excludes_underscore_private_names() -> None:
    """No name in ``__all__`` may start with an underscore."""
    private = sorted(n for n in _surface() if n.startswith("_"))
    assert private == [], f"private names leaked into __all__: {private}"


def test_public_api_excludes_backend_specific_constants() -> None:
    """Backend-specific evaluator constants must stay package-internal.

    The strategy module owns those concerns now (Phase 4); the runner
    package surface should not pin them.
    """
    forbidden = {
        "_API_COMPLETE_STOP_REASONS",
        "_API_INCOMPLETE_STOP_REASONS",
        "_EDICT_FORWARDING_TOOL_NAMES",
        "_EDICT_ROUTING_PLACEHOLDER_PHRASES",
        "_SENSITIVE_PRIVACY_KEY_RE",
        "_TEXT_SCAN_EXTENSIONS",
        "_TOOL_CALL_CONTENT_TYPES",
        "_assistant_text",
        "_event_agent_id",
        "_last_assistant_message",
        "_last_message_has_tool_call",
        "_load_sensitive_privacy_values",
        "_taizi_recent_tool_calls",
    }
    leaked = forbidden & _surface()
    assert not leaked, (
        f"{sorted(leaked)} are backend-internal — should not be in __all__"
    )


def test_public_api_covers_phase_2_promotion_helper() -> None:
    surface = _surface()
    assert "apply_score_based_promotion" in surface
    assert "classify_attempt_outcome" in surface
    assert "status_rank" in surface


def test_public_api_covers_phase_3_artifact_profile() -> None:
    surface = _surface()
    assert "ARTIFACT_PROFILE_PUBLIC" in surface
    assert "ARTIFACT_PROFILE_DEBUG" in surface
    assert "DEFAULT_ARTIFACT_PROFILE" in surface
    assert "current_artifact_profile" in surface
    assert "write_score_json" in surface


def test_public_api_covers_phase_4_model_quirks() -> None:
    surface = _surface()
    assert "model_quirks" in surface
    assert "resolve_model_entry" in surface


def test_public_api_covers_load_bearing_orchestration_names() -> None:
    """Pin the entry-point names existing scripts and tests rely on."""
    required = {
        "run_task",
        "batch_run",
        "build_runtime_task_spec",
        "resolve_attempt_outcome",
        "run_supervisor",
        "evaluate_attempt",
        "continuation_decision",
        "TaskSpec",
        "load_task",
    }
    missing = required - _surface()
    assert not missing, f"load-bearing names missing from __all__: {sorted(missing)}"


def test_star_import_yields_curated_set_only() -> None:
    """``from lib.runner import *`` should respect ``__all__`` and bring in
    only those names. This is the property users actually rely on when
    they do ``from lib.runner import *`` in a notebook or REPL."""
    star_ns: dict[str, object] = {}
    exec("from lib.runner import *", star_ns)  # noqa: S102
    star_ns.pop("__builtins__", None)
    surface = _surface()
    extras = set(star_ns) - surface
    assert not extras, f"star import leaked names not in __all__: {sorted(extras)}"


def test_deep_import_of_underscore_helper_still_works() -> None:
    """``from lib.runner.evaluation import _assistant_text`` must keep working
    — the goal of the narrowing is to control the package surface, not to
    cut off internal/test deep imports.
    """
    from lib.runner.evaluation import _assistant_text, _last_assistant_message
    from lib.runner.evaluation import _EDICT_ROUTING_PLACEHOLDER_PHRASES

    assert callable(_assistant_text)
    assert callable(_last_assistant_message)
    assert isinstance(_EDICT_ROUTING_PLACEHOLDER_PHRASES, tuple)


def test_facade_no_longer_carries_underscore_re_exports() -> None:
    """Phase 8 narrowed the package facade so it stops re-exporting underscore
    helpers. Direct attribute access via the package object (``lib.runner._xxx``)
    should now fail; the deep-import path remains the supported way to reach
    these symbols.

    This test prevents future code from accidentally restoring the broad
    re-export pattern that obscured the public surface.
    """
    import lib.runner as runner

    forbidden = (
        "_assistant_text",
        "_api_stop_reason",
        "_EDICT_ROUTING_PLACEHOLDER_PHRASES",
        "_EDICT_FORWARDING_TOOL_NAMES",
        "_IMAGE_REWRITE_B64_TO_BYTES",
        "_run_resolved_task",
    )
    leaked = [name for name in forbidden if hasattr(runner, name)]
    assert not leaked, (
        f"facade leaked underscore symbols back into the package: {leaked}. "
        "Use deep imports (``from lib.runner.<submodule> import _xxx``) instead."
    )
