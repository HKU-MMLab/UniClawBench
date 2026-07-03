"""V7 — orphan-adapter reaper + ensure_shared_proxy_with_reap.

Pins the V7 contract that ``ensure_shared_proxy_with_reap``:
  - kills only adapter_server PIDs matching our spec's listen port,
  - leaves the registered PID alone,
  - performs reap + acquire atomically under one flock (no third party
    can race in between),
  - is idempotent: calling twice yields the same lease state without
    starting a second adapter.

These tests follow the same monkeypatch pattern as
``test_proxy.test_acquire_shared_proxy_tunnel_reuses_single_host_proxy``
— fake ``start_proxy_tunnel`` + ``start_proxy_adapter`` + ``_port_ready``
+ a captured pgrep result so we never spawn a real adapter subprocess.
"""
from __future__ import annotations

import subprocess
from typing import Any


def _spec() -> dict[str, Any]:
    return {
        "kind": "ssh",
        "ssh_target": "aliyun",
        "local_host": "127.0.0.1",
        "local_port": 9000,
        "remote_host": "127.0.0.1",
        "remote_port": 9000,
        "adapter": "drop_max_tokens",
        "adapter_host": "0.0.0.0",
        "adapter_port": 9001,
    }


def _patch_proxy_internals(monkeypatch, tmp_path, *,
                           pgrep_lines: list[str] | None = None,
                           ) -> dict[str, list[int]]:
    """Common scaffolding: redirect the registry to ``tmp_path``, mock
    out tunnel + adapter spawn, capture killed PIDs.  Returns a dict
    with hooks the test can inspect (killed_pids, tunnel_starts,
    adapter_starts).
    """
    import lib.proxy.core as proxy_core
    import lib.proxy.tunnel as proxy_tunnel

    state: dict[str, list[int] | list[dict]] = {
        "killed_pids": [],
        "tunnel_starts": [],
        "adapter_starts": [],
        "slept": [],
    }

    monkeypatch.setattr(proxy_core, "PROXY_REGISTRY_ROOT", tmp_path / "proxy-registry")

    def fake_pgrep(*args, **kwargs):  # noqa: ANN001, ARG001
        if not args or args[0][:2] != ["pgrep", "-af"]:
            return subprocess.CompletedProcess(args=args, returncode=0,
                                               stdout="", stderr="")
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout="\n".join(pgrep_lines or []) + ("\n" if pgrep_lines else ""),
            stderr="",
        )
    monkeypatch.setattr(proxy_tunnel.subprocess, "run", fake_pgrep)

    def fake_killpg(pid: int, sig):  # noqa: ANN001, ARG001
        state["killed_pids"].append(int(pid))
    monkeypatch.setattr(proxy_tunnel.os, "killpg", fake_killpg)

    def fake_sleep(secs: float) -> None:
        state["slept"].append(secs)
    monkeypatch.setattr(proxy_tunnel.time, "sleep", fake_sleep)

    def fake_start_proxy_tunnel(spec: dict) -> dict:
        state["tunnel_starts"].append(dict(spec))
        return {
            "managed": True,
            "reused": False,
            "pid": 111,
            "local_host": spec["local_host"],
            "probe_host": "127.0.0.1",
            "local_port": spec["local_port"],
        }

    def fake_start_proxy_adapter(spec: dict) -> dict:
        state["adapter_starts"].append(dict(spec))
        return {
            "kind": spec["adapter"],
            "managed": True,
            "reused": False,
            "pid": 222,
            "listen_host": spec["adapter_host"],
            "probe_host": "127.0.0.1",
            "listen_port": spec["adapter_port"],
            "base_url": "http://127.0.0.1:9001",
            "upstream_base": "http://127.0.0.1:9000",
        }

    monkeypatch.setattr(proxy_tunnel, "start_proxy_tunnel", fake_start_proxy_tunnel)
    monkeypatch.setattr(proxy_core, "start_proxy_adapter", fake_start_proxy_adapter)
    monkeypatch.setattr(proxy_tunnel, "_port_ready", lambda host, port: True)

    return state


def test_ensure_shared_proxy_with_reap_starts_when_no_orphan(monkeypatch, tmp_path) -> None:
    """First call on an empty registry: no orphan, start_proxy_adapter
    runs exactly once."""
    from lib.proxy.tunnel import ensure_shared_proxy_with_reap

    hooks = _patch_proxy_internals(monkeypatch, tmp_path, pgrep_lines=[])
    lease = ensure_shared_proxy_with_reap(_spec())

    assert hooks["killed_pids"] == []
    assert len(hooks["adapter_starts"]) == 1
    adapter = lease["adapter_state"]
    assert adapter["pid"] == 222
    assert adapter["listen_port"] == 9001


def test_ensure_shared_proxy_with_reap_kills_orphan_on_port(monkeypatch, tmp_path) -> None:
    """An adapter_server PID listening on the same port but NOT in the
    registry must be SIGTERMed before we acquire."""
    from lib.proxy.tunnel import ensure_shared_proxy_with_reap

    # PID 9999's argv contains our listen_port 9001 — it's the orphan.
    # PID 7777 has a different port — it must be left alone.
    pgrep_lines = [
        "9999 python3 -m lib.proxy.adapter_server 0.0.0.0 9001 http://upstream drop_max_tokens /tmp/a /tmp/b",
        "7777 python3 -m lib.proxy.adapter_server 0.0.0.0 9101 http://other responses_via_chat /tmp/c /tmp/d",
    ]
    hooks = _patch_proxy_internals(monkeypatch, tmp_path, pgrep_lines=pgrep_lines)

    ensure_shared_proxy_with_reap(_spec())

    assert 9999 in hooks["killed_pids"], "orphan on :9001 must be killed"
    assert 7777 not in hooks["killed_pids"], "PID on a different port must survive"
    # post-kill sleep so the next bind doesn't race
    assert any(secs >= 1.0 for secs in hooks["slept"])
    # acquire still spawned a fresh adapter
    assert len(hooks["adapter_starts"]) == 1


def test_ensure_shared_proxy_with_reap_idempotent(monkeypatch, tmp_path) -> None:
    """Calling twice on a healthy registry must not respawn the
    adapter; ``start_proxy_adapter`` runs exactly once."""
    from lib.proxy.tunnel import ensure_shared_proxy_with_reap

    hooks = _patch_proxy_internals(monkeypatch, tmp_path, pgrep_lines=[])
    ensure_shared_proxy_with_reap(_spec())
    ensure_shared_proxy_with_reap(_spec())

    assert len(hooks["adapter_starts"]) == 1, (
        "second ensure must reuse the registered adapter — not spawn a new one"
    )


def test_ensure_shared_proxy_with_reap_skips_killing_registered_pid(
    monkeypatch, tmp_path,
) -> None:
    """After a healthy first acquire (registered_pid=222), a second
    ensure must NOT SIGTERM 222 even though pgrep would list it.

    Simulates the timeline: pgrep returns empty on call #1 (before any
    adapter is spawned), then returns the registered PID 222 on calls
    #2+ (after our first ensure_adapter populated the registry).
    """
    from lib.proxy.tunnel import ensure_shared_proxy_with_reap

    # Each call to pgrep pops one pre-canned response.  Last response
    # is sticky so any further pgrep calls reuse it.
    pgrep_calls = {"count": 0}
    pgrep_responses = [
        "",
        "222 python3 -m lib.proxy.adapter_server 0.0.0.0 9001 http://upstream drop_max_tokens /tmp/a /tmp/b",
    ]

    import lib.proxy.core as proxy_core
    import lib.proxy.tunnel as proxy_tunnel

    state: dict[str, list[int] | list[dict]] = {
        "killed_pids": [],
        "tunnel_starts": [],
        "adapter_starts": [],
        "slept": [],
    }
    monkeypatch.setattr(proxy_core, "PROXY_REGISTRY_ROOT", tmp_path / "proxy-registry")

    def fake_pgrep(*args, **kwargs):  # noqa: ANN001, ARG001
        if not args or args[0][:2] != ["pgrep", "-af"]:
            return subprocess.CompletedProcess(args=args, returncode=0,
                                               stdout="", stderr="")
        idx = min(pgrep_calls["count"], len(pgrep_responses) - 1)
        pgrep_calls["count"] += 1
        out = pgrep_responses[idx]
        return subprocess.CompletedProcess(args=args, returncode=0,
                                           stdout=(out + "\n") if out else "",
                                           stderr="")
    monkeypatch.setattr(proxy_tunnel.subprocess, "run", fake_pgrep)
    monkeypatch.setattr(proxy_tunnel.os, "killpg",
                        lambda pid, sig: state["killed_pids"].append(int(pid)))
    monkeypatch.setattr(proxy_tunnel.time, "sleep", lambda secs: None)

    def fake_start_proxy_tunnel(spec: dict) -> dict:
        return {"managed": True, "reused": False, "pid": 111,
                "local_host": spec["local_host"], "probe_host": "127.0.0.1",
                "local_port": spec["local_port"]}

    def fake_start_proxy_adapter(spec: dict) -> dict:
        return {"kind": spec["adapter"], "managed": True, "reused": False,
                "pid": 222, "listen_host": spec["adapter_host"],
                "probe_host": "127.0.0.1", "listen_port": spec["adapter_port"],
                "base_url": "http://127.0.0.1:9001",
                "upstream_base": "http://127.0.0.1:9000"}

    monkeypatch.setattr(proxy_tunnel, "start_proxy_tunnel", fake_start_proxy_tunnel)
    monkeypatch.setattr(proxy_core, "start_proxy_adapter", fake_start_proxy_adapter)
    monkeypatch.setattr(proxy_tunnel, "_port_ready", lambda host, port: True)

    ensure_shared_proxy_with_reap(_spec())  # registers pid=222
    ensure_shared_proxy_with_reap(_spec())  # pgrep now shows pid=222

    assert state["killed_pids"] == [], (
        "registered PID must be skipped by the orphan reaper "
        f"(killed instead: {state['killed_pids']})"
    )
