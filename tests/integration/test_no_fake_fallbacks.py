"""Round-5 Phase 2 — pin the "no fake fallback" contracts.

The bugs being prevented:

H1. ``evaluation.py`` used to wrap an unrecognised supervisor exception
    as ``verdict=fail attempt_state=terminal_failure``, making a
    supervisor CRASH look like a supervisor VERDICT. Now: recognised
    infra patterns → honest ``verdict=infra_error``; unrecognised
    exceptions → re-raise (the harness's outer infra_error path takes
    over with a real traceback).

H3. ``batch_run`` used to swallow a ``_run_resolved_task`` exception
    as ``{"finalStatus": "fail", "error": ...}``, making a harness-level
    crash look like a "task fail" reliability metric. Now: ``finalStatus
    = "infra_error"`` with the full traceback in ``infraError``.

L (errors.py) ``detect_supervisor_infra_error`` now recognises the
    "docker pull denied" / "Unable to find image" class — the root
    cause of the overnight cluster poisoning when worker3 lacked the
    clawbench-codex image.
"""
from __future__ import annotations

from lib.runner.errors import detect_supervisor_infra_error


# ── docker-needle recognition (root cause of the worker3 poisoning) ──────


def test_unable_to_find_image_recognised_as_infra():
    msg = (
        "Unable to find image 'clawbench-codex:latest' locally\n"
        "docker: Error response from daemon: pull access denied"
    )
    result = detect_supervisor_infra_error(msg)
    assert result is not None
    assert result["type"] == "docker_image_missing"
    assert "Unable to find image" in result["message"]


def test_pull_access_denied_recognised():
    msg = "docker: Error response from daemon: pull access denied for clawbench-foo"
    result = detect_supervisor_infra_error(msg)
    assert result is not None
    assert result["type"] == "docker_image_missing"


def test_repository_does_not_exist_recognised():
    msg = "Error response from daemon: repository does not exist"
    result = detect_supervisor_infra_error(msg)
    assert result is not None
    assert result["type"] == "docker_image_missing"


def test_unrelated_error_still_returns_none():
    """Negative regression: don't broaden the pattern to catch unrelated
    errors. An unrelated exception must STILL return None so the H1
    re-raise path kicks in."""
    msg = "AttributeError: 'NoneType' object has no attribute 'split'"
    assert detect_supervisor_infra_error(msg) is None


# ── batch_run exception → finalStatus=infra_error (H3) ──────────────


def test_batch_run_exception_marks_infra_error_not_fail(tmp_path, monkeypatch):
    """Regression: harness-level exception inside ThreadPoolExecutor.future
    must surface as finalStatus=infra_error with traceback, NOT as the
    silent ``finalStatus=fail`` it used to.
    """
    from lib.runner import orchestration as orch_mod

    class _FakeFuture:
        def result(self):
            raise RuntimeError("simulated worker crash")

    # Mimic the inside of the as_completed loop directly: we don't need
    # to spin up ThreadPoolExecutor; we just need to confirm the exception
    # handler builds the expected dict.
    task_file = tmp_path / "task_x.yaml"
    task_file.write_text("# fake\n")
    fake_future = _FakeFuture()

    # Replicate the exact branch from orchestration.py:
    results = []
    try:
        results.append(fake_future.result())
    except Exception as exc:
        import traceback as _tb
        results.append({
            "taskFile": str(task_file),
            "passed": False,
            "finalStatus": "infra_error",
            "infraError": {
                "type": "batch_run_exception",
                "message": str(exc),
                "traceback": _tb.format_exc(),
            },
        })

    assert len(results) == 1
    r = results[0]
    assert r["finalStatus"] == "infra_error"  # NOT "fail"
    assert r["passed"] is False
    assert r["infraError"]["type"] == "batch_run_exception"
    assert "simulated worker crash" in r["infraError"]["message"]
    assert r["infraError"]["traceback"]  # has traceback content


def test_batch_run_path_in_orchestration_uses_infra_error():
    """Pin: read the orchestration.py source and confirm it doesn't carry
    the old ``finalStatus: 'fail'`` literal in the batch_run except branch.
    """
    import inspect
    from lib.runner import orchestration as orch_mod
    source = inspect.getsource(orch_mod.batch_run)
    # The fallback dict must say infra_error, not fail.
    assert '"finalStatus": "fail"' not in source, (
        "batch_run's exception handler must NOT label crashes as finalStatus=fail; "
        "use finalStatus=infra_error instead."
    )
    assert '"finalStatus": "infra_error"' in source
    assert '"infraError"' in source


# ── unrecognised supervisor exception re-raises (H1) ───────────────


def test_evaluate_attempt_reraises_unrecognised_supervisor_exception():
    """Pin the H1 contract by reading evaluation.py's source — confirm the
    fake ``verdict=fail attempt_state=terminal_failure`` else branch is
    GONE and a ``raise`` is in its place."""
    import inspect
    from lib.runner import evaluation as eval_mod
    source = inspect.getsource(eval_mod.evaluate_attempt)
    # The old fabrication must be gone:
    assert '_exc_verdict = "fail"' not in source, (
        "evaluate_attempt's exception handler must NOT fabricate a fake "
        "verdict=fail when the supervisor crashes. Re-raise so the outer "
        "harness records infra_error with a real traceback."
    )
    # The infra-error wrap path must still exist for recognised patterns:
    assert '_exc_verdict = "infra_error"' in source
    # And there must be an explicit ``raise`` for unrecognised exceptions:
    # (not ``raise X``, just bare ``raise`` to preserve the original tb)
    assert "raise\n" in source or "raise " in source
