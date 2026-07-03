"""Smoke imports for the three main lib packages.

These tests do not exercise behaviour — they only confirm that the
public re-export tables stay intact across refactors.  Round-3 + Round-4
moved several files; any future cleanup that accidentally drops a
load-bearing re-export will fail one of these tests instead of breaking
a real caller at runtime.

The names checked here are the surface-API consumers external to the
defining module: things like ``run_task``, ``run_supervisor``,
``acquire_shared_proxy_tunnel`` etc. that downstream code or scripts
import as ``from lib.X import Y``.
"""
from __future__ import annotations


def test_runner_package_exposes_load_bearing_names() -> None:
    from lib.runner import (
        run_task,
        batch_run,
        collect_attempt_artifacts,
        start_container,
        start_services,
        run_openclaw_agent,
        run_nanobot_agent,
        run_agent,
        executor_completion_state,
        recording_session,
        TimelineRecorder,
        prepare_runtime,
        inject_nanobot_config,
        inject_openclaw_config,
    )
    # Sanity: each one is callable / a class.
    assert callable(run_task)
    assert callable(batch_run)
    assert callable(collect_attempt_artifacts)
    assert callable(start_container)
    assert callable(executor_completion_state)
    assert isinstance(TimelineRecorder, type)


def test_supervision_package_exposes_load_bearing_names() -> None:
    from lib.supervision import (
        run_supervisor,
        run_answer_supervisor,
        run_public_user_simulator,
        rewrite_feedback,
        build_public_feedback,
        build_visible_payload,
        build_hidden_payload,
        SupervisorContext,
        AttemptSupervisorContext,
        TaskSupervisorContext,
        prepare_role_workspace,
        render_template,
    )
    assert callable(run_supervisor)
    assert callable(run_answer_supervisor)
    assert callable(rewrite_feedback)
    assert SupervisorContext.__name__ == "SupervisorContext"


def test_supervision_internals_are_not_in_surface_all() -> None:
    """Underscore-prefixed helpers stay accessible via deep import but
    must not pollute ``from lib.supervision import *``."""
    import lib.supervision as sup

    for hidden in (
        "_normalize_answer_decision",
        "_role_workspace_prompt_files",
        "_strip_edict_routing_note",
        "dedupe_lines",
    ):
        assert hidden not in sup.__all__, (
            f"{hidden!r} must not be in lib.supervision.__all__ — it is "
            "package-internal; external callers should deep-import from the "
            "defining module instead."
        )

    # Deep import still works (callers / tests use this form):
    from lib.supervision.orchestrator import _normalize_answer_decision
    from lib.supervision.workspace import _role_workspace_prompt_files
    from lib.supervision.content import _strip_edict_routing_note
    from lib.util.dedup import dedupe_lines

    assert callable(_normalize_answer_decision)
    assert callable(_role_workspace_prompt_files)
    assert callable(_strip_edict_routing_note)
    assert callable(dedupe_lines)


def test_proxy_package_exposes_load_bearing_names() -> None:
    from lib.proxy import (
        acquire_shared_proxy_tunnel,
        release_shared_proxy_tunnel,
        start_proxy_tunnel,
        stop_proxy_tunnel,
        start_proxy_adapter,
        provider_proxy_spec,
        normalize_provider_proxy_spec,
        write_local,
        PROXY_REGISTRY_ROOT,
        PROXY_ADAPTER_LOG_PATH,
    )
    assert callable(acquire_shared_proxy_tunnel)
    assert callable(provider_proxy_spec)
    # Constants are paths — just verify they exist as attributes:
    assert PROXY_REGISTRY_ROOT is not None
    assert PROXY_ADAPTER_LOG_PATH is not None


def test_proxy_string_path_patch_anchor_resolves() -> None:
    """Tests in ``tests/integration/test_usage_attempt_rollup.py`` patch
    ``lib.proxy.core.PROXY_REGISTRY_ROOT`` via ``monkeypatch.setattr`` with
    a string path.  That requires ``lib.proxy.core`` to remain a real
    importable module with the named attribute.  This pin makes sure
    nobody deletes the module in a future cleanup."""
    import lib.proxy.core as proxy_core

    assert hasattr(proxy_core, "PROXY_REGISTRY_ROOT")
    assert hasattr(proxy_core, "PROXY_ADAPTER_LOG_PATH")
    assert hasattr(proxy_core, "start_proxy_adapter")
    assert hasattr(proxy_core, "write_local")


def test_templates_package_render_lookup_still_works() -> None:
    """``render_template("session_wrapper", ...)`` does
    ``importlib.import_module("lib.templates.session_wrapper")`` at
    runtime.  If the file is moved/absorbed, this dynamic lookup breaks
    silently.  Pin the lookup so future cleanups can't drop the file."""
    from lib.supervision.codex import render_template

    rendered = render_template(
        "session_wrapper",
        {
            "role_name": "answer_supervisor",
            "role_instructions": "test",
            "key_files_list": "- `foo`",
        },
    )
    assert "answer_supervisor" in rendered
    assert "test" in rendered
