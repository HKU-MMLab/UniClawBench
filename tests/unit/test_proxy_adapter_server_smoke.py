"""Round 10 / P2: smoke tests for ``lib.proxy.adapter_server`` as a
real module (previously a 1179-line inline string in ``adapter.py``).

The module now imports cleanly with default sentinels for the
argv-dependent globals, so unit tests can call any function or
instantiate any class without spinning up a subprocess.  These tests
exercise the formerly-untested-in-production helpers — log handlers,
tool-call extras cache, task-id extraction, response-payload reversal,
etc. — which were impossible to test before because they only existed
inside the inline-string body.
"""
from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from lib.proxy import adapter_server


def test_module_exposes_main_entrypoint() -> None:
    """``python3 -m lib.proxy.adapter_server`` must find ``main()``."""
    assert hasattr(adapter_server, "main")
    assert callable(adapter_server.main)


def test_module_has_handler_class() -> None:
    """``Handler`` is the BaseHTTPRequestHandler subclass that owns
    request routing.  Previously only accessible by re-executing the
    inline script."""
    from http.server import BaseHTTPRequestHandler
    assert issubclass(adapter_server.Handler, BaseHTTPRequestHandler)


def test_argv_globals_default_to_empty() -> None:
    """Importing the module without running ``main()`` must NOT raise
    IndexError on sys.argv.  Sentinel values must be safely typed."""
    assert isinstance(adapter_server.LISTEN_HOST, str)
    assert isinstance(adapter_server.LISTEN_PORT, int)
    assert isinstance(adapter_server.UPSTREAM_BASE, str)
    assert isinstance(adapter_server.ADAPTER, str)
    assert isinstance(adapter_server.LOG_PATH, str)
    assert isinstance(adapter_server.REQUEST_LOG_PATH, str)


def test_module_level_constants_are_set() -> None:
    """Constants that were always at module level in the inline
    version: ``REQUEST_LOG_MAX_BYTES`` (env-var read),
    ``TASK_ID_PREFIX_RE`` (compiled regex), ``TLS_CONTEXT`` (SSL),
    ``TOOL_CALL_EXTRA_CACHE`` (in-memory dict)."""
    assert isinstance(adapter_server.REQUEST_LOG_MAX_BYTES, int)
    assert adapter_server.REQUEST_LOG_MAX_BYTES > 0
    assert isinstance(adapter_server.TASK_ID_PREFIX_RE, re.Pattern)
    assert isinstance(adapter_server.TOOL_CALL_EXTRA_CACHE, dict)


# --------------------------------------------------------------------------
# extract_task_id — strip ``/_t/<id>/...`` prefix the runner injects
# --------------------------------------------------------------------------


def test_extract_task_id_with_prefix() -> None:
    task_id, stripped = adapter_server.extract_task_id("/_t/p1-abc123/v1/chat/completions")
    assert task_id == "p1-abc123"
    assert stripped == "/v1/chat/completions"


def test_extract_task_id_without_prefix() -> None:
    task_id, stripped = adapter_server.extract_task_id("/v1/chat/completions")
    assert task_id == ""
    assert stripped == "/v1/chat/completions"


def test_extract_task_id_just_prefix_no_trailing() -> None:
    """``/_t/<id>`` with no further path → task_id captured, path empty
    (Codex CLI sometimes hits the bare prefix probe)."""
    task_id, stripped = adapter_server.extract_task_id("/_t/p2-host-xyz")
    assert task_id == "p2-host-xyz"
    assert stripped in {"", "/"}


# --------------------------------------------------------------------------
# normalize_tool_call_id — strip / normalize tool call IDs
# --------------------------------------------------------------------------


def test_normalize_tool_call_id_handles_none() -> None:
    assert adapter_server.normalize_tool_call_id(None) == ""


def test_normalize_tool_call_id_handles_empty_string() -> None:
    assert adapter_server.normalize_tool_call_id("") == ""
    assert adapter_server.normalize_tool_call_id("   ") == ""


def test_normalize_tool_call_id_strips_and_lowers() -> None:
    """Strip whitespace, lowercase, keep only alphanumeric chars.
    The contract here is "produce a stable comparable token from a
    free-form tool_call_id" — strip whitespace + drop punctuation so
    downstream cache keys stay consistent across providers that emit
    differing punctuation (e.g. ``Call_ABC`` vs ``call-abc``)."""
    assert adapter_server.normalize_tool_call_id("  Call_ABC  ") == "callabc"
    assert adapter_server.normalize_tool_call_id("call-abc-123") == "callabc123"


# --------------------------------------------------------------------------
# Transform-function parity with lib.proxy.transform
# --------------------------------------------------------------------------


def test_item_text_matches_transform_module() -> None:
    """The pure transform functions must produce identical output in
    adapter_server and transform — they're the same code path now
    that adapter_server is a real module.  Going forward, transform.py
    is the test mirror; adapter_server.py is the production execution.
    """
    from lib.proxy import transform

    cases = [
        {"text": "hello"},
        {"input_text": "from input"},
        {"output_text": "from output"},
        {"image_url": {"url": "https://example.com/a.png"}},
        {},
        "not a dict",
        None,
    ]
    for c in cases:
        assert adapter_server.item_text(c) == transform.item_text(c)


def test_responses_to_chat_payload_round_trip_basic() -> None:
    """Minimal payload through the transform — non-crashing baseline."""
    payload = {
        "model": "test-model",
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "hello"}]},
        ],
        "stream": False,
    }
    chat = adapter_server.responses_to_chat_payload(payload)
    assert "messages" in chat
    assert chat["model"] == "test-model"
    assert any(m.get("role") == "user" for m in chat["messages"])


# --------------------------------------------------------------------------
# Sanity guard against inline-script regression
# --------------------------------------------------------------------------


def test_no_inline_script_remains_in_adapter() -> None:
    """The whole point of Round 10 / P2 was to eliminate the inline
    ``script = r\"\"\"...\"\"\"`` body.  Catch a regression where
    someone re-introduces it (e.g. by reverting the refactor).  We
    look for ``script = r\"\"\"`` at the *start of a line* (code,
    not docstring text) — the file's prose docstring deliberately
    mentions the deprecated form in past tense."""
    from pathlib import Path
    import re
    text = Path(adapter_server.__file__).parent.joinpath("adapter.py").read_text(encoding="utf-8")
    code_line_pattern = re.compile(r'^(\s*)script\s*=\s*r"""', re.MULTILINE)
    matches = code_line_pattern.findall(text)
    assert not matches, (
        f"adapter.py has an inline-script assignment ({len(matches)} occurrences) — "
        "Round 10 / P2 moved it to lib.proxy.adapter_server"
    )


# --------------------------------------------------------------------------
# KeyRotator — round-robin pool with per-key 429 cooldown
# --------------------------------------------------------------------------


def test_rotator_empty_pool_returns_empty() -> None:
    r = adapter_server.KeyRotator([])
    assert r.order() == []
    assert len(r) == 0


def test_rotator_filters_blank_keys() -> None:
    r = adapter_server.KeyRotator(["a", "", "  ", None, "b"])
    assert len(r) == 2
    assert sorted(r.order()) == ["a", "b"]


def test_rotator_round_robin_advances_cursor() -> None:
    r = adapter_server.KeyRotator(["k1", "k2", "k3", "k4"])
    # order() always returns ALL keys, but the lead element rotates.
    o1 = r.order()
    o2 = r.order()
    assert sorted(o1) == ["k1", "k2", "k3", "k4"]
    assert sorted(o2) == ["k1", "k2", "k3", "k4"]
    assert o1[0] != o2[0]  # cursor advanced -> different lead key


def test_rotator_hot_key_goes_last() -> None:
    r = adapter_server.KeyRotator(["k1", "k2", "k3", "k4"], cooldown_s=100.0)
    r.mark_hot("k1")
    order = r.order()
    assert set(order) == {"k1", "k2", "k3", "k4"}  # all keys still present
    assert order[-1] == "k1"  # cooling key sorted to the end


def test_rotator_cooldown_expires() -> None:
    r = adapter_server.KeyRotator(["k1", "k2"], cooldown_s=0.0)
    r.mark_hot("k1")
    # cooldown 0 -> immediately "fresh" again, so it is not forced last
    order = r.order()
    assert set(order) == {"k1", "k2"}


def test_rotator_thread_safety_smoke() -> None:
    """Concurrent order()/mark_hot() must not corrupt the cursor/cooldown
    (ThreadingHTTPServer serves requests concurrently)."""
    r = adapter_server.KeyRotator(["k1", "k2", "k3", "k4"])
    errors: list[Exception] = []

    def hammer() -> None:
        try:
            for _ in range(500):
                o = r.order()
                assert sorted(o) == ["k1", "k2", "k3", "k4"]
                r.mark_hot(o[0])
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors


# --------------------------------------------------------------------------
# _is_rotated_model / _load_rotation_keys
# --------------------------------------------------------------------------


def test_is_rotated_model_default_off() -> None:
    assert adapter_server._is_rotated_model("rotate-model-v1") is False
    assert adapter_server._is_rotated_model("") is False
    assert adapter_server._is_rotated_model(None) is False


def test_is_rotated_model_env_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAWBENCH_ROTATE_MODELS", "foo-model, bar-model")
    assert adapter_server._is_rotated_model("acme/foo-model-v2") is True
    assert adapter_server._is_rotated_model("bar-model") is True
    assert adapter_server._is_rotated_model("unlisted-model") is False


def test_load_rotation_keys_from_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    env_file = tmp_path / "api.local.env"
    env_file.write_text(
        "ROTATE_KEY_A=keyA\n"
        "ROTATE_KEY_B=keyB\n"
        "ROTATE_KEY_C=keyC\n"
        "UNRELATED_KEY=should-not-load\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAWBENCH_API_ENV_FILE", str(env_file))
    monkeypatch.setenv("CLAWBENCH_ROTATE_KEY_ENVS", "ROTATE_KEY_A,ROTATE_KEY_B,ROTATE_KEY_C")
    for var in ("ROTATE_KEY_A", "ROTATE_KEY_B", "ROTATE_KEY_C"):
        monkeypatch.delenv(var, raising=False)
    keys = adapter_server._load_rotation_keys()
    assert keys == ["keyA", "keyB", "keyC"]
    assert "should-not-load" not in keys


def test_load_rotation_keys_missing_file_is_safe(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("CLAWBENCH_API_ENV_FILE", str(tmp_path / "nope.env"))
    monkeypatch.setenv("CLAWBENCH_ROTATE_KEY_ENVS", "ROTATE_KEY_A")
    monkeypatch.delenv("ROTATE_KEY_A", raising=False)
    assert adapter_server._load_rotation_keys() == []


# --------------------------------------------------------------------------
# End-to-end: drive the real Handler against a fake upstream, asserting
# rotation behavior and verbatim-forwarding for non-matching paths/models.
# --------------------------------------------------------------------------


class _FakeUpstream:
    """A loopback HTTP server standing in for UPSTREAM_BASE. Records every
    inbound Authorization header. 429s the keys named in ``hot_keys`` (the
    bearer token after 'Bearer '); everything else gets a 200 JSON body that
    echoes the key it saw."""

    def __init__(self, hot_keys=None):
        self.hot_keys = set(hot_keys or [])
        self.seen_auth: list[str] = []
        self._lock = threading.Lock()
        outer = self

        class _H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # noqa: A003 - silence test noise
                return

            def _read_body(self):
                length = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(length) if length > 0 else b""

            def do_POST(self):  # noqa: N802
                self._read_body()
                auth = self.headers.get("Authorization", "")
                with outer._lock:
                    outer.seen_auth.append(auth)
                token = auth[len("Bearer "):] if auth.startswith("Bearer ") else auth
                if token in outer.hot_keys:
                    body = json.dumps({"error": {"message": "rate limited"}}).encode("utf-8")
                    self.send_response(429)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = json.dumps({
                    "model": "rotate-model-v1",
                    "saw_auth": auth,
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                auth = self.headers.get("Authorization", "")
                with outer._lock:
                    outer.seen_auth.append(auth)
                body = json.dumps({"ok": True, "saw_auth": auth}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _H)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def _start_adapter(adapter_kind: str):
    """Start the production Handler on a loopback port. Returns (port, close)."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), adapter_server.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def close() -> None:
        server.shutdown()
        server.server_close()

    return port, close


@pytest.fixture
def adapter_env(monkeypatch: pytest.MonkeyPatch):
    """Configure module globals for an end-to-end test and restore after.

    Yields a helper that wires UPSTREAM_BASE/ADAPTER/ROTATOR to a fresh fake
    upstream + adapter server and returns (adapter_port, fake_upstream)."""
    saved = {
        "UPSTREAM_BASE": adapter_server.UPSTREAM_BASE,
        "ADAPTER": adapter_server.ADAPTER,
        "ROTATOR": adapter_server.ROTATOR,
        "LOG_PATH": adapter_server.LOG_PATH,
        "REQUEST_LOG_PATH": adapter_server.REQUEST_LOG_PATH,
    }
    # Keep logging side-effects off the disk during tests.
    adapter_server.LOG_PATH = ""
    adapter_server.REQUEST_LOG_PATH = ""
    monkeypatch.setenv("CLAWBENCH_ROTATE_MODELS", "rotate-model")
    closers: list = []

    def setup(*, adapter_kind="drop_max_tokens", rotator=None, hot_keys=None):
        upstream = _FakeUpstream(hot_keys=hot_keys)
        closers.append(upstream.close)
        adapter_server.UPSTREAM_BASE = upstream.base
        adapter_server.ADAPTER = adapter_kind
        adapter_server.ROTATOR = rotator
        port, close = _start_adapter(adapter_kind)
        closers.append(close)
        return port, upstream

    yield setup

    for close in closers:
        try:
            close()
        except Exception:
            pass
    for key, value in saved.items():
        setattr(adapter_server, key, value)


def _post_chat(port: int, *, model: str, auth: str):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "hi"}]}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": auth},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=10)


def test_rotation_failover_on_429(adapter_env) -> None:
    """A matching model POST whose first rotated key 429s retries the next key and
    SUCCEED, and the Authorization seen upstream must change across attempts."""
    rotator = adapter_server.KeyRotator(["Rk1", "Rk2", "Rk3", "Rk4"], cooldown_s=100.0)
    # Make exactly one rotated key 429 upstream. Whichever attempt order the
    # handler picks, at most one attempt 429s before a success — and the
    # inbound client key must never be forwarded.
    port, upstream = adapter_env(adapter_kind="drop_max_tokens", rotator=rotator, hot_keys={"Rk1"})

    resp = _post_chat(port, model="rotate-model-v1", auth="Bearer INBOUND-CLIENT-KEY")
    assert resp.status == 200
    payload = json.loads(resp.read().decode("utf-8"))
    # The succeeding upstream call used a rotated key, NOT the inbound key.
    assert payload["saw_auth"].startswith("Bearer Rk")
    assert payload["saw_auth"] != "Bearer INBOUND-CLIENT-KEY"
    # The inbound client Authorization was never forwarded.
    assert "Bearer INBOUND-CLIENT-KEY" not in upstream.seen_auth
    # All keys upstream saw were rotated keys.
    assert all(a.startswith("Bearer Rk") for a in upstream.seen_auth)


def test_rotation_distinct_keys_across_attempts(adapter_env) -> None:
    """When earlier keys 429, later attempts use DIFFERENT keys, and the
    request still succeeds on the one non-saturated key.

    The handler's pool ordering is round-robin (cursor-dependent), so we make
    the rotator's cooldown deterministic: pre-mark the three saturated keys
    hot so order() always returns them FIRST-tried-last is not what we want —
    instead we 429 three of four keys upstream and pre-mark the SAME three hot
    in the rotator so they sort to the end; that forces the fresh key 'Gd'
    last, guaranteeing 3 failed attempts before the success."""
    rotator = adapter_server.KeyRotator(["Ra", "Rb", "Rc", "Rd"], cooldown_s=100.0)
    for k in ("Ra", "Rb", "Rc"):
        rotator.mark_hot(k)
    # With Ra/Rb/Rc cooling, order() => [Rd, <the three cooling, in rr order>].
    # Rd is NOT hot upstream, so it succeeds on the FIRST attempt. To instead
    # exercise multi-attempt failover deterministically, 429 Rd upstream and
    # leave one cooling key (Rc) live upstream.
    upstream_hot = {"Rd", "Ra", "Rb"}
    port, upstream = adapter_env(
        adapter_kind="drop_max_tokens", rotator=rotator, hot_keys=upstream_hot,
    )
    resp = _post_chat(port, model="rotate-model-v1", auth="Bearer INBOUND")
    assert resp.status == 200
    payload = json.loads(resp.read().decode("utf-8"))
    # Succeeded on the single live key Rc.
    assert payload["saw_auth"] == "Bearer Rc"
    # Multiple distinct rotated keys were attempted; inbound never forwarded.
    assert len(upstream.seen_auth) >= 2
    assert len(set(upstream.seen_auth)) >= 2
    assert all(a.startswith("Bearer R") for a in upstream.seen_auth)
    assert "Bearer INBOUND" not in upstream.seen_auth


def test_non_matching_model_forwards_inbound_auth_verbatim(adapter_env) -> None:
    """A non-matching model must forward its ORIGINAL inbound Authorization and
    never rotate, even with a live rotator."""
    rotator = adapter_server.KeyRotator(["Rx1", "Rx2"], cooldown_s=100.0)
    port, upstream = adapter_env(adapter_kind="drop_max_tokens", rotator=rotator)
    resp = _post_chat(port, model="gpt-5.4", auth="Bearer ORIGINAL-GPT-KEY")
    assert resp.status == 200
    payload = json.loads(resp.read().decode("utf-8"))
    assert payload["saw_auth"] == "Bearer ORIGINAL-GPT-KEY"
    assert upstream.seen_auth == ["Bearer ORIGINAL-GPT-KEY"]


def test_all_keys_429_relays_429_to_client(adapter_env) -> None:
    """When every rotated key 429s, the terminal 429 must be relayed to the
    client (behavior of the last attempt is unchanged)."""
    rotator = adapter_server.KeyRotator(["Rz1", "Rz2", "Rz3", "Rz4"], cooldown_s=100.0)
    port, upstream = adapter_env(
        adapter_kind="drop_max_tokens", rotator=rotator,
        hot_keys={"Rz1", "Rz2", "Rz3", "Rz4"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        _post_chat(port, model="rotate-model-v1", auth="Bearer INBOUND")
    assert exc_info.value.code == 429
    # All 4 keys were attempted before relaying the 429.
    assert len(upstream.seen_auth) == 4
    assert all(a.startswith("Bearer Rz") for a in upstream.seen_auth)


def test_matching_model_without_rotator_forwards_verbatim(adapter_env) -> None:
    """ROTATOR None (e.g. key load failed) -> a matching request forwards the
    inbound Authorization verbatim, single attempt (fail-safe)."""
    port, upstream = adapter_env(adapter_kind="drop_max_tokens", rotator=None)
    resp = _post_chat(port, model="rotate-model-v1", auth="Bearer INBOUND-ROTATE")
    assert resp.status == 200
    payload = json.loads(resp.read().decode("utf-8"))
    assert payload["saw_auth"] == "Bearer INBOUND-ROTATE"
    assert upstream.seen_auth == ["Bearer INBOUND-ROTATE"]


def test_get_request_not_rotated(adapter_env) -> None:
    """GET (non-chat-completions, non-POST) must forward verbatim, no rotation,
    even with a live rotator."""
    rotator = adapter_server.KeyRotator(["Rg1", "Rg2"], cooldown_s=100.0)
    port, upstream = adapter_env(adapter_kind="drop_max_tokens", rotator=rotator)
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/models",
        headers={"Authorization": "Bearer GET-ORIGINAL"},
        method="GET",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    assert resp.status == 200
    assert upstream.seen_auth == ["Bearer GET-ORIGINAL"]


def test_non_chat_post_not_rotated(adapter_env) -> None:
    """A POST to a non /chat/completions path with a matching model must not
    rotate (gate requires the path to end with /chat/completions)."""
    rotator = adapter_server.KeyRotator(["Rp1", "Rp2"], cooldown_s=100.0)
    port, upstream = adapter_env(adapter_kind="drop_max_tokens", rotator=rotator)
    body = json.dumps({"model": "rotate-model-v1", "input": "x"}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/embeddings",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer EMBED-ORIGINAL"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    assert resp.status == 200
    assert upstream.seen_auth == ["Bearer EMBED-ORIGINAL"]
