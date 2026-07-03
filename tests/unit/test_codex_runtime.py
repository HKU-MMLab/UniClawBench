from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.supervision.codex import (
    build_codex_execution_prompt,
    run_codex_prompt,
    should_force_toolless_retry,
)
from lib.supervision.content import sanitize_codex_context_text


ROOT = Path(__file__).resolve().parents[2]


# ── sanitize_codex_context_text ──────────────────────────────────────


def test_sanitize_keeps_normal_english_error_text() -> None:
    """Error text that's plain English (the common case) must pass through
    untouched except for path redactions — otherwise the retry loses the
    actionable hint (e.g. 'stream disconnected before completion')."""
    err = "stream disconnected before completion while running bash under landlock sandbox"
    out = sanitize_codex_context_text(err)
    assert "stream disconnected before completion" in out
    assert "landlock sandbox" in out
    assert "[binary-blob-elided]" not in out


def test_sanitize_redacts_long_base64_runs() -> None:
    """When an image / raw byte stream leaks into a failed upstream response
    body, it appears as a long run of [A-Za-z0-9+/=]. Replace it with a
    short placeholder so the retry prompt stays clean."""
    # 200 chars of base64-looking content embedded in ordinary error text.
    blob = "AbCdEfGhIjKlMnOpQrStUv0123456789+/=" * 6
    err = f"upstream returned 500: {blob} (request aborted)"
    out = sanitize_codex_context_text(err)
    assert "upstream returned 500:" in out
    assert "(request aborted)" in out
    assert "[binary-blob-elided]" in out
    # The replacement must be shorter than the original blob.
    assert len(out) < len(err)


def test_sanitize_strips_non_printable_bytes_to_question_marks() -> None:
    """Control characters / raw binary bytes that aren't caught by the
    base64 pattern (e.g. short bursts of 0x00 / 0xFF in a partial HTTP
    response) must not reach the retry prompt."""
    err = "timeout\x00\x01\x02 after 180s"
    out = sanitize_codex_context_text(err)
    assert "timeout" in out
    assert "after 180s" in out
    # Non-printable bytes replaced.
    for bad in ("\x00", "\x01", "\x02"):
        assert bad not in out


def test_sanitize_preserves_cjk_error_text() -> None:
    """Chinese error messages (e.g. 中文报错) should survive sanitization —
    the CJK Unified Ideographs range is in the allowlist."""
    err = "\u9519\u8bef\uff1a\u8fde\u63a5\u5931\u8d25"  # 错误：连接失败
    out = sanitize_codex_context_text(err)
    assert err in out


# ── should_force_toolless_retry ──────────────────────────────────────


def test_toolless_retry_triggers_on_real_sandbox_phrases() -> None:
    """Real sandbox / permission errors must still route to toolless retry."""
    assert should_force_toolless_retry(
        "exec failed: landlock sandbox denied read on /workspace"
    )
    assert should_force_toolless_retry("seccomp: blocked syscall")
    assert should_force_toolless_retry("operation not permitted")
    assert should_force_toolless_retry("failed to spawn child process")
    assert should_force_toolless_retry("permission denied reading /tmp/foo")


def test_toolless_retry_does_NOT_trigger_on_runtime_probe_content() -> None:
    """Regression: previously the word 'bash' / 'sh:' in TOOLLESS_RETRY_NEEDLES
    matched any occurrence — runtime_probe.json contains things like
    'bash -lc python3' and 'shell=True' as perfectly normal debug data.
    Those used to (wrongly) route the supervisor into toolless retry even
    when the actual failure was a network / upstream timeout."""
    runtime_probe_excerpt = (
        'payload = {"windows": run_shell("wmctrl -lp"), '
        '"processes": {"chromium": ["chrome --type=renderer ..."]}}, '
        '"1206 bash -lc python3 - <<PY", "shell=True"'
    )
    assert not should_force_toolless_retry(runtime_probe_excerpt)
    # A plain bare "bash" or "sh:" mention must also not trigger it.
    assert not should_force_toolless_retry("we invoked bash to list files")
    assert not should_force_toolless_retry("ls -la; echo sh:1")


# ── build_codex_execution_prompt ─────────────────────────────────────


def test_retry_prompt_embeds_sanitized_error_not_raw_binary() -> None:
    """End-to-end: a retry prompt built from a dirty error must contain the
    redacted placeholder, never the raw binary blob."""
    dirty_error = (
        "upstream returned 500: "
        + ("AbCdEfGhIjKlMnOpQr0123456789+/=" * 10)
        + " aborted."
    )
    prompt = build_codex_execution_prompt(
        "main prompt body",
        retry_error=dirty_error,
        force_toolless=True,
    )
    assert "[binary-blob-elided]" in prompt
    # The raw 300-char base64 blob must not appear in the final prompt.
    assert ("AbCdEfGhIjKlMnOpQr0123456789+/=" * 5) not in prompt


def test_run_codex_prompt_retries_with_toolless_prompt_on_runtime_instability(tmp_path, monkeypatch) -> None:
    # ``run_codex_prompt`` and the helpers it calls live in
    # ``lib.supervision.codex`` now (split out from ``common.py``); patching
    # on that module is the real binding the function sees.
    import lib.supervision.codex as sc

    prompts: list[str] = []
    sleeps: list[float] = []

    def fake_run_codex_via_container(**kwargs):
        prompts.append(kwargs["prompt"])
        output_path = kwargs["output_path"]
        if len(prompts) == 1:
            output_path.unlink(missing_ok=True)
            return subprocess.CompletedProcess(
                args=["codex"],
                returncode=1,
                stdout="",
                stderr="stream disconnected before completion while running bash under landlock sandbox",
            )
        output_path.write_text('{"mode":"silent"}', encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sc, "load_codex_base_config", lambda path: {"model_providers": {"native-openai-proxy": {"env_key": "KEY", "wire_api": "chat"}}})
    monkeypatch.setattr(sc, "resolve_codex_env_vars", lambda base, path: {"KEY": "test-key"})
    monkeypatch.setattr(sc, "required_codex_env_keys", lambda base: ["KEY"])
    monkeypatch.setattr(sc, "ensure_isolated_codex_home", lambda **kwargs: kwargs["target"])
    monkeypatch.setattr(sc, "run_codex_via_container", fake_run_codex_via_container)
    monkeypatch.setattr(sc, "codex_rollout_summary", lambda home: {"excerpt": "landlock sandbox failure", "tool_misuse_detected": False})
    monkeypatch.setattr(sc.time, "sleep", lambda seconds: sleeps.append(seconds))

    workspace_root = tmp_path / "workspace"
    (workspace_root / "visible").mkdir(parents=True, exist_ok=True)
    (workspace_root / "references").mkdir(parents=True, exist_ok=True)
    (workspace_root / "public_task.md").write_text("public task\n", encoding="utf-8")
    (workspace_root / "turn_state.json").write_text('{"turn": 1}\n', encoding="utf-8")
    (workspace_root / "role_history.jsonl").write_text("", encoding="utf-8")
    (workspace_root / "visible/visible_summary.json").write_text('{"summary":"visible"}\n', encoding="utf-8")
    (workspace_root / "references/hidden_summary.json").write_text('{"summary":"hidden"}\n', encoding="utf-8")

    response = run_codex_prompt(
        prompt="Return a JSON object.",
        model="native-openai-proxy/gpt-4.1",
        provider="native-openai-proxy",
        base_config_path=ROOT / "configs/codex.local.toml",
        session_root=tmp_path / "session",
        workspace_root=workspace_root,
        codex_home=tmp_path / "home",
        reasoning_effort="medium",
        images=[],
        workspace_manifest={"role": "answer_supervisor"},
        workspace_readme="",
        output_schema=None,
    )

    assert response["parsed"] == {"mode": "silent"}
    assert len(prompts) == 2
    assert "Do not use bash, exec, file inspection, or network tools" in prompts[1]
    assert sleeps


def test_run_codex_prompt_retries_after_context_window_error(tmp_path, monkeypatch) -> None:
    # ``run_codex_prompt`` and the helpers it calls live in
    # ``lib.supervision.codex`` now (split out from ``common.py``); patching
    # on that module is the real binding the function sees.
    import lib.supervision.codex as sc

    prompts: list[str] = []

    def fake_run_codex_via_container(**kwargs):
        prompts.append(kwargs["prompt"])
        output_path = kwargs["output_path"]
        if len(prompts) == 1:
            output_path.unlink(missing_ok=True)
            return subprocess.CompletedProcess(
                args=["codex"],
                returncode=1,
                stdout="",
                stderr="stream disconnected before completion while running bash under landlock sandbox",
            )
        if len(prompts) == 2:
            output_path.unlink(missing_ok=True)
            return subprocess.CompletedProcess(
                args=["codex"],
                returncode=1,
                stdout="",
                stderr="ERROR: Codex ran out of room in the model's context window.",
            )
        output_path.write_text('{"mode":"silent"}', encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sc, "load_codex_base_config", lambda path: {"model_providers": {"native-openai-proxy": {"env_key": "KEY", "wire_api": "chat"}}})
    monkeypatch.setattr(sc, "resolve_codex_env_vars", lambda base, path: {"KEY": "test-key"})
    monkeypatch.setattr(sc, "required_codex_env_keys", lambda base: ["KEY"])
    monkeypatch.setattr(sc, "ensure_isolated_codex_home", lambda **kwargs: kwargs["target"])
    monkeypatch.setattr(sc, "run_codex_via_container", fake_run_codex_via_container)
    monkeypatch.setattr(
        sc,
        "codex_rollout_summary",
        lambda home: {
            "excerpt": "landlock sandbox failure" if len(prompts) <= 1 else "context window exhausted",
            "tool_misuse_detected": False,
        },
    )
    monkeypatch.setattr(sc.time, "sleep", lambda seconds: None)

    workspace_root = tmp_path / "workspace"
    (workspace_root / "visible").mkdir(parents=True, exist_ok=True)
    (workspace_root / "references").mkdir(parents=True, exist_ok=True)
    (workspace_root / "public_task.md").write_text("public task\n", encoding="utf-8")
    (workspace_root / "turn_state.json").write_text('{"turn": 1}\n', encoding="utf-8")
    (workspace_root / "role_history.jsonl").write_text("", encoding="utf-8")
    noisy_block = "A" * 40000
    (workspace_root / "visible/visible_summary.json").write_text(json.dumps({"summary": noisy_block}, ensure_ascii=False), encoding="utf-8")
    (workspace_root / "references/hidden_summary.json").write_text(json.dumps({"summary": noisy_block}, ensure_ascii=False), encoding="utf-8")

    response = run_codex_prompt(
        prompt="Return a JSON object.",
        model="native-openai-proxy/gpt-4.1",
        provider="native-openai-proxy",
        base_config_path=ROOT / "configs/codex.local.toml",
        session_root=tmp_path / "session",
        workspace_root=workspace_root,
        codex_home=tmp_path / "home",
        reasoning_effort="medium",
        images=[],
        workspace_manifest={"role": "answer_supervisor"},
        workspace_readme="",
        output_schema=None,
    )

    assert response["parsed"] == {"mode": "silent"}
    assert len(prompts) == 3
    assert "Do not use bash, exec, file inspection, or network tools" in prompts[1]
    assert "Do not use bash, exec, file inspection, or network tools" in prompts[2]


# ── rate-limit retry (supervisor / user-simulator) ───────────────────
# Supervisor / user-simulator 429 retries are UNBOUNDED (no max_attempts
# cap). A throttled grader should wait out the upstream rather than
# crash the attempt. Below we stub run_codex_via_container to return 429
# five times — well past DEFAULT_CODEX_MAX_ATTEMPTS=3 — and verify the
# sixth call, which returns success, is the one that resolves.


def test_is_rate_limit_codex_error_recognizes_common_429_shapes() -> None:
    from lib.supervision.codex import is_rate_limit_codex_error

    assert is_rate_limit_codex_error("HTTP 429 Too Many Requests")
    assert is_rate_limit_codex_error('{"error":{"type":"rate_limit_exceeded","message":"..."}}')
    assert is_rate_limit_codex_error("anthropic.RateLimitError: rate_limit_error")
    assert is_rate_limit_codex_error("upstream returned status 429")
    assert is_rate_limit_codex_error("", "stderr: too many requests")
    # Negative: transient transport errors (already handled by the
    # capped-budget branch) must NOT be mistaken for rate-limit.
    assert not is_rate_limit_codex_error("stream disconnected before completion")
    assert not is_rate_limit_codex_error("ssl handshake failed")
    assert not is_rate_limit_codex_error("")


def test_codex_rate_limit_backoff_has_expected_exponential_schedule() -> None:
    from lib.supervision.codex import (
        DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP,
        codex_rate_limit_backoff_seconds,
    )

    # 1, 2, 4, 8, 16, 32 then capped at DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP.
    assert codex_rate_limit_backoff_seconds(0) == 1.0
    assert codex_rate_limit_backoff_seconds(1) == 2.0
    assert codex_rate_limit_backoff_seconds(2) == 4.0
    assert codex_rate_limit_backoff_seconds(3) == 8.0
    assert codex_rate_limit_backoff_seconds(4) == 16.0
    assert codex_rate_limit_backoff_seconds(5) == 32.0
    # Cap hits before the 7th retry (2^6=64 > default cap 60).
    assert codex_rate_limit_backoff_seconds(6) == DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP
    assert codex_rate_limit_backoff_seconds(15) == DEFAULT_CODEX_RATE_LIMIT_BACKOFF_CAP


def test_run_codex_prompt_retries_past_max_attempts_on_persistent_429(tmp_path, monkeypatch) -> None:
    """A 429 must NOT consume the 3-attempt transient budget. We stub 5
    rate-limit responses (past the cap) followed by one success, and
    verify the 6th call is the one that returns — proving the loop kept
    retrying after the nominal DEFAULT_CODEX_MAX_ATTEMPTS."""
    import lib.supervision.codex as sc

    prompts: list[str] = []
    sleeps: list[float] = []

    def fake_run_codex_via_container(**kwargs):
        prompts.append(kwargs["prompt"])
        output_path = kwargs["output_path"]
        if len(prompts) <= 5:
            output_path.unlink(missing_ok=True)
            return subprocess.CompletedProcess(
                args=["codex"],
                returncode=1,
                stdout="",
                stderr="Anthropic API error: HTTP 429 rate_limit_exceeded",
            )
        output_path.write_text('{"verdict":"pass","overall_score":0.9}', encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sc, "load_codex_base_config", lambda path: {"model_providers": {"native-openai-proxy": {"env_key": "KEY", "wire_api": "chat"}}})
    monkeypatch.setattr(sc, "resolve_codex_env_vars", lambda base, path: {"KEY": "test-key"})
    monkeypatch.setattr(sc, "required_codex_env_keys", lambda base: ["KEY"])
    monkeypatch.setattr(sc, "ensure_isolated_codex_home", lambda **kwargs: kwargs["target"])
    monkeypatch.setattr(sc, "run_codex_via_container", fake_run_codex_via_container)
    monkeypatch.setattr(sc, "codex_rollout_summary", lambda home: {"excerpt": "429 too many requests", "tool_misuse_detected": False})
    monkeypatch.setattr(sc.time, "sleep", lambda seconds: sleeps.append(seconds))

    workspace_root = tmp_path / "workspace"
    (workspace_root / "visible").mkdir(parents=True, exist_ok=True)
    (workspace_root / "references").mkdir(parents=True, exist_ok=True)
    (workspace_root / "public_task.md").write_text("public task\n", encoding="utf-8")
    (workspace_root / "turn_state.json").write_text('{"turn": 1}\n', encoding="utf-8")
    (workspace_root / "role_history.jsonl").write_text("", encoding="utf-8")
    (workspace_root / "visible/visible_summary.json").write_text('{"summary":"visible"}\n', encoding="utf-8")
    (workspace_root / "references/hidden_summary.json").write_text('{"summary":"hidden"}\n', encoding="utf-8")

    response = run_codex_prompt(
        prompt="Return a JSON object.",
        model="native-openai-proxy/gpt-4.1",
        provider="native-openai-proxy",
        base_config_path=ROOT / "configs/codex.local.toml",
        session_root=tmp_path / "session",
        workspace_root=workspace_root,
        codex_home=tmp_path / "home",
        reasoning_effort="medium",
        images=[],
        workspace_manifest={"role": "answer_supervisor"},
        workspace_readme="",
        output_schema=None,
    )

    # Six total calls: five 429s then one success. The five 429s are well
    # past DEFAULT_CODEX_MAX_ATTEMPTS=3, which would have raised under the
    # old single-counter logic.
    assert len(prompts) == 6
    assert response["parsed"] == {"verdict": "pass", "overall_score": 0.9}
    # Backoff schedule for the first five retries: 1, 2, 4, 8, 16.
    assert sleeps[:5] == [1.0, 2.0, 4.0, 8.0, 16.0]
