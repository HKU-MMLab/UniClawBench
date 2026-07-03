from __future__ import annotations

import json

from lib.proxy import read_proxy_usage_events
from lib.runner import (
    acquire_shared_proxy_tunnel,
    build_proxy_tunnel_command,
    normalize_provider_proxy_spec,
    start_proxy_adapter,
    start_proxy_tunnel,
    stop_proxy_tunnel,
)


def test_normalize_provider_proxy_spec_keeps_core_ssh_fields() -> None:
    spec = normalize_provider_proxy_spec(
        {
            "type": "ssh",
            "sshTarget": "remote-alias",
            "adapter": "drop_max_tokens",
            "adapterPort": 9001,
        }
    )
    assert spec is not None
    assert spec["ssh_target"] == "remote-alias"
    assert spec["adapter"] == "drop_max_tokens"
    assert spec["adapter_port"] == 9001


def test_normalize_provider_proxy_spec_defaults_adapter_host_for_loopback_tunnels() -> None:
    spec = normalize_provider_proxy_spec(
        {
            "type": "ssh",
            "sshTarget": "remote-alias",
            "localHost": "127.0.0.1",
            "adapter": "drop_max_tokens",
            "adapterPort": 9001,
        }
    )
    assert spec is not None
    assert spec["local_host"] == "127.0.0.1"
    assert spec["adapter_host"] == "0.0.0.0"


def test_build_proxy_tunnel_command_uses_host_user_and_ssh_options() -> None:
    command = build_proxy_tunnel_command(
        {
            "ssh_target": "",
            "ssh_host": "gateway.example.invalid",
            "ssh_user": "root",
            "local_host": "127.0.0.1",
            "local_port": 9000,
            "remote_host": "127.0.0.1",
            "remote_port": 9000,
            "ssh_options": ["ProxyJump=bastion"],
        }
    )
    assert command[:4] == ["ssh", "-N", "-L", "127.0.0.1:9000:127.0.0.1:9000"]
    assert "ProxyJump=bastion" in command
    assert "root@gateway.example.invalid" == command[-1]


def test_start_proxy_tunnel_probes_loopback_when_binding_wildcard(monkeypatch) -> None:
    # ``_port_ready`` moved to ``lib.proxy.tunnel`` — patch it there so
    # the tunnel's internal ``_port_ready(probe_host, local_port)``
    # call resolves to the fake.
    import lib.proxy.tunnel as proxy_tunnel

    probes: list[tuple[str, int]] = []

    def fake_port_ready(host: str, port: int) -> bool:
        probes.append((host, port))
        return True

    monkeypatch.setattr(proxy_tunnel, "_port_ready", fake_port_ready)
    state = start_proxy_tunnel(
        {
            "kind": "ssh",
            "ssh_target": "remote-alias",
            "local_host": "0.0.0.0",
            "local_port": 9000,
            "remote_host": "127.0.0.1",
            "remote_port": 9000,
            "wait_seconds": 1,
        }
    )
    assert probes == [("127.0.0.1", 9000)]
    assert state["reused"] is True


def test_start_proxy_adapter_uses_adapter_host_but_probes_loopback(monkeypatch) -> None:
    # ``start_proxy_adapter`` stays in ``lib.proxy.core`` but reaches
    # ``_port_ready`` through the tunnel module (``tunnel._port_ready``)
    # — patch at that name so the probe call resolves to the fake.
    import lib.proxy.tunnel as proxy_tunnel

    probes: list[tuple[str, int]] = []

    def fake_port_ready(host: str, port: int) -> bool:
        probes.append((host, port))
        return True

    monkeypatch.setattr(proxy_tunnel, "_port_ready", fake_port_ready)
    state = start_proxy_adapter(
        {
            "adapter": "drop_max_tokens",
            "adapter_host": "0.0.0.0",
            "adapter_port": 9001,
            "local_host": "127.0.0.1",
            "local_port": 9000,
        }
    )
    assert probes == [("127.0.0.1", 9001)]
    assert state is not None
    assert state["listen_host"] == "0.0.0.0"
    assert state["probe_host"] == "127.0.0.1"
    assert state["base_url"] == "http://127.0.0.1:9001"
    assert state["upstream_base"] == "http://127.0.0.1:9000"


def test_acquire_shared_proxy_tunnel_reuses_single_host_proxy(monkeypatch, tmp_path) -> None:
    # ``PROXY_REGISTRY_ROOT`` lives in ``lib.proxy.core``; the tunnel
    # module reads it module-qualified (``core.PROXY_REGISTRY_ROOT``).
    # The other patched names (``start_proxy_tunnel``,
    # ``_port_ready``, ``_terminate_process_group_pid``) now live in
    # ``lib.proxy.tunnel``; ``start_proxy_adapter`` stays in ``core``
    # but is invoked as ``core.start_proxy_adapter`` from tunnel, so
    # patching the core attribute takes effect there.
    import lib.proxy.core as proxy_core
    import lib.proxy.tunnel as proxy_tunnel

    tunnel_starts: list[dict] = []
    adapter_starts: list[dict] = []
    stopped_pids: list[int] = []

    monkeypatch.setattr(proxy_core, "PROXY_REGISTRY_ROOT", tmp_path / "proxy-registry")

    def fake_start_proxy_tunnel(spec: dict[str, object]) -> dict[str, object]:
        tunnel_starts.append(dict(spec))
        return {
            "managed": True,
            "reused": False,
            "pid": 111,
            "local_host": spec["local_host"],
            "probe_host": "127.0.0.1",
            "local_port": spec["local_port"],
        }

    def fake_start_proxy_adapter(spec: dict[str, object]) -> dict[str, object]:
        adapter_starts.append(dict(spec))
        return {
            "kind": "drop_max_tokens",
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
    monkeypatch.setattr(proxy_tunnel, "_terminate_process_group_pid", lambda pid, grace_seconds=5.0: stopped_pids.append(int(pid)))

    spec = {
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

    lease_a = acquire_shared_proxy_tunnel(spec)
    lease_b = acquire_shared_proxy_tunnel(spec)

    assert len(tunnel_starts) == 1
    assert len(adapter_starts) == 1

    stop_proxy_tunnel(lease_a)
    assert stopped_pids == []

    stop_proxy_tunnel(lease_b)
    assert stopped_pids == [222, 111]


def test_read_proxy_usage_events_filters_by_time_window(tmp_path) -> None:
    log_path = tmp_path / "proxy_adapter.log"
    entries = [
        {"event": "usage", "ts": 100.0, "model": "gpt-5.4", "endpoint": "/responses",
         "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        {"path": "/v1/chat/completions", "method": "POST"},           # non-usage event, must be skipped
        {"event": "usage", "ts": 150.0, "model": "gpt-5.4", "endpoint": "/chat/completions",
         "prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
        {"event": "usage", "ts": 200.0, "model": "gpt-5.4", "endpoint": "/chat/completions",
         "prompt_tokens": 99, "completion_tokens": 1, "total_tokens": 100},  # outside window
        "not-json",                                                   # malformed line, must be skipped
    ]
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write((json.dumps(entry) if isinstance(entry, dict) else entry) + "\n")

    events = read_proxy_usage_events(log_path, start_ts=90.0, end_ts=180.0)
    assert [e["ts"] for e in events] == [100.0, 150.0]
    assert [e["endpoint"] for e in events] == ["/responses", "/chat/completions"]
    assert events[1]["prompt_tokens"] == 20
    assert events[1]["completion_tokens"] == 7


def test_read_proxy_usage_events_half_open_interval_prevents_double_count(tmp_path) -> None:
    log_path = tmp_path / "proxy_adapter.log"
    log_path.write_text(
        json.dumps({"event": "usage", "ts": 100.0, "prompt_tokens": 1, "completion_tokens": 2,
                    "total_tokens": 3}) + "\n",
        encoding="utf-8",
    )
    # ts == end_ts is excluded; ts == start_ts is included.
    first_cycle = read_proxy_usage_events(log_path, start_ts=50.0, end_ts=100.0)
    second_cycle = read_proxy_usage_events(log_path, start_ts=100.0, end_ts=150.0)
    assert first_cycle == []
    assert len(second_cycle) == 1


def test_read_proxy_usage_events_missing_log_returns_empty(tmp_path) -> None:
    assert read_proxy_usage_events(tmp_path / "nope.log", start_ts=0.0, end_ts=1.0) == []
    assert read_proxy_usage_events(None, start_ts=0.0, end_ts=1.0) == []
