"""SSH tunnel lifecycle + shared registry + proxy-spec parsing.

Merged in Phase 4 of the third-round refactor: the leaf-level
``spec.py`` (parsing + host-string helpers) folded in here because
tunnel logic is the only consumer outside of ``__init__.py``'s
re-exports, and the call graph is purely leaf → trunk.

Two sections live here:

* **Section 1 — Spec parsing** (was ``spec.py``).  Pure value
  transformation: coerce a raw ``proxy: {...}`` dict (from
  ``configs/models.json`` or ``configs/codex.toml``) into the canonical
  shape consumed by ``tunnel`` / ``adapter``.  Host-string helpers
  (``_is_loopback_host`` / ``_is_wildcard_bind_host`` / etc.) shared
  with tunnel/adapter lifecycle code.

* **Section 2 — Tunnel lifecycle** (was ``tunnel.py``'s body).
  Everything from "spawn ``ssh -N -L ...``" through "refcount the
  shared state under ``.runtime/proxy_registry/<sha1>.json``" — but
  *not* the HTTP adapter itself.  ``start_proxy_adapter`` (which forks
  a Python subprocess via ``python3 -c <script>`` for Codex
  compatibility shims) lives in ``.adapter``; we still call it here
  as ``core.start_proxy_adapter`` because ``core`` re-exports the
  name so string-path monkeypatches like
  ``monkeypatch.setattr("lib.proxy.core.start_proxy_adapter", fake)``
  keep taking effect inside ``acquire_shared_proxy_tunnel``.

Public entry points (re-exported via ``lib.proxy.__init__``):
- ``normalize_provider_proxy_spec`` / ``provider_proxy_spec`` (spec)
- ``build_proxy_tunnel_command`` — build the ``ssh`` argv for a spec.
- ``start_proxy_tunnel`` / ``stop_proxy_tunnel`` — unshared lifecycle.
- ``acquire_shared_proxy_tunnel`` / ``release_shared_proxy_tunnel`` —
  refcounted multi-process lifecycle backed by the registry.
- ``_ensure_no_adapter_conflict`` — adapter-kind/upstream_base
  conflict detector.

Module-level constants ``PROXY_REGISTRY_ROOT``, ``DEFAULT_PROXY_KIND``,
``DEFAULT_PROXY_WAIT_SECONDS``, and ``ROOT`` still live in ``core.py``.
This module looks them up via ``core.<name>`` so string-path
monkeypatches like ``monkeypatch.setattr("lib.proxy.core.PROXY_REGISTRY_ROOT",
tmp)`` keep taking effect.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import core


# ─────────────────────────────────────────────────────────────────────
# Section 1 — Spec parsing (was lib/proxy/spec.py)
# ─────────────────────────────────────────────────────────────────────


def _proxy_string(value: Any, *keys: str, default: str = "") -> str:
    if not isinstance(value, dict):
        return default
    for key in keys:
        candidate = str(value.get(key) or "").strip()
        if candidate:
            return candidate
    return default


def _proxy_int(value: Any, *keys: str, default: int) -> int:
    if not isinstance(value, dict):
        return default
    for key in keys:
        candidate = value.get(key)
        if candidate in {None, ""}:
            continue
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    return default


def _proxy_bool(value: Any, *keys: str, default: bool) -> bool:
    if not isinstance(value, dict):
        return default
    for key in keys:
        if key not in value:
            continue
        candidate = value.get(key)
        if isinstance(candidate, bool):
            return candidate
        if isinstance(candidate, (int, float)):
            return bool(candidate)
        if isinstance(candidate, str):
            stripped = candidate.strip().lower()
            if stripped in {"true", "yes", "1", "on"}:
                return True
            if stripped in {"false", "no", "0", "off", ""}:
                return False
    return default


def _is_loopback_host(value: str) -> bool:
    host = str(value or "").strip().lower().strip("[]")
    return host in {"127.0.0.1", "localhost", "::1"}


def _is_wildcard_bind_host(value: str) -> bool:
    host = str(value or "").strip().lower().strip("[]")
    return host in {"", "0.0.0.0", "::"}


def _probe_host_for_bind_host(value: str) -> str:
    host = str(value or "").strip()
    normalized = host.lower().strip("[]")
    if normalized in {"", "0.0.0.0"}:
        return "127.0.0.1"
    if normalized == "::":
        return "::1"
    return host or "127.0.0.1"


def _listen_hosts_conflict(left: str, right: str) -> bool:
    left_host = str(left or "").strip().lower().strip("[]")
    right_host = str(right or "").strip().lower().strip("[]")
    if left_host == right_host:
        return True
    return _is_wildcard_bind_host(left_host) or _is_wildcard_bind_host(right_host)


def normalize_provider_proxy_spec(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = _proxy_string(raw, "type", "kind", default=core.DEFAULT_PROXY_KIND).lower().replace("-", "_")
    if kind in {"ssh", "ssh_tunnel"}:
        normalized_kind = "ssh"
    elif kind in {"adapter", "http_adapter", "compat", "compatibility"}:
        normalized_kind = "adapter"
    else:
        return None
    upstream_base = _proxy_string(raw, "upstreamBase", "upstream_base", "upstreamUrl", "upstream_url", "baseUrl", "base_url")
    ssh_target = _proxy_string(raw, "sshTarget", "ssh_target", "target")
    ssh_host = _proxy_string(raw, "sshHost", "ssh_host", "host")
    if normalized_kind == "ssh" and not ssh_host and not ssh_target:
        return None
    if normalized_kind == "adapter" and not upstream_base:
        return None
    local_host = _proxy_string(raw, "localHost", "local_host", default="127.0.0.1")
    adapter = _proxy_string(raw, "adapter", "compat", "compatibility")
    adapter_host = _proxy_string(raw, "adapterHost", "adapter_host")
    if not adapter_host:
        adapter_host = "0.0.0.0" if adapter and _is_loopback_host(local_host) else local_host
    need_adapter = _proxy_bool(raw, "needAdapter", "need_adapter", default=bool(adapter))
    spec = {
        "kind": normalized_kind,
        "ssh_target": ssh_target,
        "ssh_host": ssh_host,
        "ssh_user": _proxy_string(raw, "sshUser", "ssh_user", "user", default=os.environ.get("USER", "")),
        "local_host": local_host,
        "local_port": _proxy_int(raw, "localPort", "local_port", default=9000),
        "remote_host": _proxy_string(raw, "remoteHost", "remote_host", default="127.0.0.1"),
        "remote_port": _proxy_int(raw, "remotePort", "remote_port", default=9000),
        "wait_seconds": _proxy_int(raw, "waitSeconds", "wait_seconds", default=core.DEFAULT_PROXY_WAIT_SECONDS),
        "ssh_options": [str(item).strip() for item in (raw.get("sshOptions") or raw.get("ssh_options") or []) if str(item).strip()],
        "adapter": adapter,
        "adapter_host": adapter_host,
        "adapter_port": _proxy_int(raw, "adapterPort", "adapter_port", "shimPort", "shim_port", default=0),
        "need_adapter": need_adapter,
        "upstream_base": upstream_base,
    }
    return spec


def provider_proxy_spec(provider_cfg: dict[str, Any], *, proxy_definitions: dict[str, Any] | None = None) -> dict[str, Any] | None:
    inline = (provider_cfg or {}).get("proxy")
    if isinstance(inline, dict):
        return normalize_provider_proxy_spec(inline)
    ref = str((provider_cfg or {}).get("proxyRef") or (provider_cfg or {}).get("proxy_ref") or "").strip()
    if ref and isinstance(proxy_definitions, dict):
        return normalize_provider_proxy_spec(proxy_definitions.get(ref))
    return None


def _proxy_spec_key(spec: dict[str, Any]) -> str:
    return json.dumps(
        {
            key: value
            for key, value in spec.items()
            if key
            in {
                "kind",
                "ssh_target",
                "ssh_host",
                "ssh_user",
                "local_host",
                "local_port",
                "remote_host",
                "remote_port",
                "ssh_options",
                "adapter",
                "adapter_host",
                "adapter_port",
                "upstream_base",
            }
        },
        sort_keys=True,
        ensure_ascii=False,
    )


# ─────────────────────────────────────────────────────────────────────
# Section 2 — Tunnel lifecycle (was lib/proxy/tunnel.py body)
# ─────────────────────────────────────────────────────────────────────


def _port_ready(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=1):
            return True
    except OSError:
        return False


def _adapter_listen_target(spec: dict[str, Any]) -> tuple[str, int] | None:
    adapter = str(spec.get("adapter") or "").strip().lower().replace("-", "_")
    if not adapter:
        return None
    listen_host = str(spec.get("adapter_host") or spec.get("local_host") or "127.0.0.1")
    listen_port = int(spec.get("adapter_port") or 0)
    if listen_port <= 0:
        listen_port = int(spec["local_port"]) + 1
    return listen_host, listen_port


def _ensure_no_adapter_conflict(spec: dict[str, Any], states: list[dict[str, Any]]) -> None:
    target = _adapter_listen_target(spec)
    if target is None:
        return
    listen_host, listen_port = target
    adapter_kind = str(spec.get("adapter") or "").strip().lower().replace("-", "_")
    upstream_base = str(spec.get("upstream_base") or "").strip()
    for state in states:
        adapter_state = state.get("adapter_state")
        if not isinstance(adapter_state, dict):
            continue
        existing_host = str(adapter_state.get("listen_host") or "")
        existing_port = int(adapter_state.get("listen_port") or 0)
        if not _listen_hosts_conflict(existing_host, listen_host) or existing_port != listen_port:
            continue
        existing_kind = str(adapter_state.get("kind") or "").strip().lower()
        existing_base = str(adapter_state.get("upstream_base") or adapter_state.get("base_url") or "").strip()
        desired_base = upstream_base or f"http://{spec['local_host']}:{int(spec['local_port'])}"
        if existing_kind != adapter_kind or (adapter_kind == "responses_via_chat" and existing_base != desired_base):
            raise RuntimeError(
                "proxy adapter port conflict: "
                f"{listen_host}:{listen_port} already serves {existing_kind} ({existing_base}), "
                f"cannot reuse it for {adapter_kind} ({desired_base}). "
                "Use a different adapter_port."
            )


def _proxy_registry_key(spec: dict[str, Any]) -> str:
    return hashlib.sha1(_proxy_spec_key(spec).encode("utf-8")).hexdigest()


def _proxy_registry_paths(spec: dict[str, Any]) -> tuple[Path, Path]:
    key = _proxy_registry_key(spec)
    core.PROXY_REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    return core.PROXY_REGISTRY_ROOT / f"{key}.json", core.PROXY_REGISTRY_ROOT / f"{key}.lock"


@contextmanager
def _locked_proxy_registry(spec: dict[str, Any]):
    state_path, lock_path = _proxy_registry_paths(spec)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield state_path
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_proxy_registry_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_proxy_registry_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    core.write_local(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _terminate_process_group_pid(pid: int | None, *, grace_seconds: float = 5.0) -> None:
    if not pid or int(pid) <= 0:
        return
    try:
        os.killpg(int(pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + max(1.0, grace_seconds)
    while time.time() < deadline:
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    try:
        os.killpg(int(pid), signal.SIGKILL)
    except ProcessLookupError:
        return


def _cleanup_proxy_registry_state(path: Path, payload: dict[str, Any]) -> None:
    adapter = payload.get("adapter") if isinstance(payload.get("adapter"), dict) else {}
    tunnel = payload.get("tunnel") if isinstance(payload.get("tunnel"), dict) else {}
    if adapter.get("managed"):
        _terminate_process_group_pid(int(adapter.get("pid") or 0))
    if tunnel.get("managed"):
        _terminate_process_group_pid(int(tunnel.get("pid") or 0))
    path.unlink(missing_ok=True)


def _proxy_registry_state_ready(payload: dict[str, Any]) -> bool:
    tunnel = payload.get("tunnel") if isinstance(payload.get("tunnel"), dict) else {}
    if tunnel:
        probe_host = str(tunnel.get("probe_host") or "")
        port = int(tunnel.get("local_port") or 0)
        if probe_host and port > 0 and not _port_ready(probe_host, port):
            return False
    adapter = payload.get("adapter") if isinstance(payload.get("adapter"), dict) else {}
    if adapter:
        probe_host = str(adapter.get("probe_host") or "")
        port = int(adapter.get("listen_port") or 0)
        if probe_host and port > 0 and not _port_ready(probe_host, port):
            return False
    return bool(tunnel or adapter)


def _reap_orphan_adapter_processes_locked(
    spec: dict[str, Any], known_pid: int | None,
) -> int:
    """V7: kill stray ``lib.proxy.adapter_server`` PIDs whose listen_port
    matches this spec but which aren't recorded in our registry.

    Such orphans appear when a previous worker_runner that forked an
    adapter was killed mid-handshake (Round-16 V6 root-cause: SSH
    ``kex_exchange_identification`` storm killed worker_runner before
    it could register the adapter PID; the next task's
    ``acquire_shared_proxy_tunnel`` saw an empty registry, tried to
    bind port 9001, and crashed with ``EADDRINUSE``).

    Caller MUST hold the ``_locked_proxy_registry`` flock for ``spec``
    — without that lock, we could SIGTERM an adapter that a concurrent
    ``acquire_shared_proxy_tunnel`` just forked.  ``known_pid`` (the
    PID listed in the current registry, if any) is skipped so we don't
    kill the legitimately-registered one.

    Returns the number of orphans signalled.  Sleeps 1.5s after a kill
    so the next ``bind()`` doesn't race the kernel's port-release.
    """
    target = _adapter_listen_target(spec)
    if target is None:
        return 0
    _, listen_port = target
    if listen_port <= 0:
        return 0
    try:
        result = subprocess.run(
            ["pgrep", "-af", "lib.proxy.adapter_server"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 0
    killed = 0
    port_token = f" {listen_port} "
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if known_pid and pid == int(known_pid):
            continue
        # adapter_server.main reads argv: <host> <port> <upstream> <kind> <log> <reqlog>
        # so port appears space-delimited in the cmdline.  Anchor on
        # the space token so port=9001 doesn't match listen_host=10.0.0.9001.
        if port_token not in (parts[1] + " "):
            continue
        try:
            os.killpg(pid, signal.SIGTERM)
            killed += 1
        except (ProcessLookupError, PermissionError, OSError):
            pass
    if killed:
        time.sleep(1.5)  # let SIGTERM land before the caller binds the port
    return killed


def ensure_shared_proxy_with_reap(spec: dict[str, Any]) -> dict[str, Any]:
    """V7 public entry for ensure_adapter.py — atomically reap + acquire.

    Wraps two operations under the same flock:
      1. read registry, compare listed PID against live ps output, and
         SIGTERM any ``lib.proxy.adapter_server`` PID that doesn't match
         the registry.  This salvages the post-SSH-storm state where an
         orphan adapter occupies port 9001 with no registry entry.
      2. delegate to ``acquire_shared_proxy_tunnel`` for the normal
         check-then-start flow.  If the orphan was on the same port,
         it was reaped above and acquire's start_proxy_adapter is free
         to bind.

    Idempotent: calling twice in quick succession yields the same shared
    state.  Safe for two ``ensure_adapter`` processes racing on the same
    spec — the second one observes a healthy registry under flock and
    just refcounts via the inner ``acquire_shared_proxy_tunnel``.
    """
    with _locked_proxy_registry(spec) as state_path:
        payload = _read_proxy_registry_state(state_path)
        registered_pid: int | None = None
        if payload:
            adapter = payload.get("adapter") if isinstance(payload.get("adapter"), dict) else {}
            registered_pid = int(adapter.get("pid") or 0) or None
            if not _proxy_registry_state_ready(payload):
                # Registry is stale (process gone, port dead).  Drop it
                # so the orphan reaper's kill won't also clobber a
                # legitimate registered PID we're about to forget.
                _cleanup_proxy_registry_state(state_path, payload)
                payload = {}
                registered_pid = None
        _reap_orphan_adapter_processes_locked(spec, registered_pid)
    # acquire_shared_proxy_tunnel re-takes the flock; that's fine, the
    # orphans are gone and no third party can race us (the spec key
    # serialises everything that touches this adapter's lifecycle).
    return acquire_shared_proxy_tunnel(spec)


def acquire_shared_proxy_tunnel(spec: dict[str, Any]) -> dict[str, Any]:
    with _locked_proxy_registry(spec) as state_path:
        payload = _read_proxy_registry_state(state_path)
        if payload and not _proxy_registry_state_ready(payload):
            _cleanup_proxy_registry_state(state_path, payload)
            payload = {}
        if payload:
            payload["refcount"] = max(0, int(payload.get("refcount") or 0)) + 1
            _write_proxy_registry_state(state_path, payload)
            return {
                "spec": dict(spec),
                "shared_proxy": True,
                "registry_state_path": str(state_path),
                "adapter_state": payload.get("adapter") if isinstance(payload.get("adapter"), dict) else None,
                "tunnel_state": payload.get("tunnel") if isinstance(payload.get("tunnel"), dict) else None,
            }

        tunnel_state = start_proxy_tunnel(spec)
        should_start_adapter = bool(spec.get("need_adapter", spec.get("adapter")))
        adapter_state = core.start_proxy_adapter(spec) if should_start_adapter else None
        payload = {
            "schema_version": 1,
            "refcount": 1,
            "spec_key": _proxy_spec_key(spec),
            "tunnel": {
                "managed": bool(tunnel_state.get("managed")),
                "reused": bool(tunnel_state.get("reused")),
                "pid": int(tunnel_state.get("pid") or 0),
                "local_host": str(tunnel_state.get("local_host") or spec.get("local_host") or ""),
                "probe_host": str(tunnel_state.get("probe_host") or _probe_host_for_bind_host(str(spec.get("local_host") or ""))),
                "local_port": int(tunnel_state.get("local_port") or spec.get("local_port") or 0),
            },
            "adapter": {
                "kind": str((adapter_state or {}).get("kind") or ""),
                "managed": bool((adapter_state or {}).get("managed")),
                "reused": bool((adapter_state or {}).get("reused")),
                "pid": int((adapter_state or {}).get("pid") or 0),
                "listen_host": str((adapter_state or {}).get("listen_host") or ""),
                "probe_host": str((adapter_state or {}).get("probe_host") or ""),
                "listen_port": int((adapter_state or {}).get("listen_port") or 0),
                "base_url": str((adapter_state or {}).get("base_url") or ""),
                "upstream_base": str((adapter_state or {}).get("upstream_base") or ""),
                # Persist the adapter subprocess's actual log path so a
                # different Clawbench checkout reusing this shared adapter
                # can discover where per-call usage events are going,
                # instead of guessing at its own ROOT/.runtime/... path
                # (which is what happens when two checkouts with
                # different paths share the same running adapter — the
                # reader ends up looking at a file that was never
                # written to).
                "log_path": str((adapter_state or {}).get("log_path") or ""),
                # Companion log carrying the full request+response
                # transcript (see PROXY_ADAPTER_REQUEST_LOG_PATH); same
                # cross-checkout discovery story as ``log_path``.
                "request_log_path": str((adapter_state or {}).get("request_log_path") or ""),
            }
            if adapter_state
            else {},
        }
        _write_proxy_registry_state(state_path, payload)
        return {
            "spec": dict(spec),
            "shared_proxy": True,
            "registry_state_path": str(state_path),
            "adapter_state": adapter_state,
            "tunnel_state": tunnel_state,
        }


def release_shared_proxy_tunnel(state: dict[str, Any]) -> None:
    state_path_value = str(state.get("registry_state_path") or "").strip()
    if not state_path_value:
        return
    state_path = Path(state_path_value)
    spec = dict(state.get("spec") or {})
    with _locked_proxy_registry(spec) as locked_state_path:
        if locked_state_path != state_path:
            state_path = locked_state_path
        payload = _read_proxy_registry_state(state_path)
        if not payload:
            return
        remaining = max(0, int(payload.get("refcount") or 0) - 1)
        if remaining > 0:
            payload["refcount"] = remaining
            _write_proxy_registry_state(state_path, payload)
            return
        _cleanup_proxy_registry_state(state_path, payload)


def _terminate_process_group(process: subprocess.Popen[str], *, grace_seconds: float = 5.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + max(1.0, grace_seconds)
    while time.time() < deadline:
        if process.poll() is not None:
            return
        time.sleep(0.2)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def build_proxy_tunnel_command(spec: dict[str, Any]) -> list[str]:
    target = str(spec.get("ssh_target") or "").strip()
    if not target:
        target = str(spec["ssh_host"])
        ssh_user = str(spec.get("ssh_user") or "").strip()
        if ssh_user:
            target = f"{ssh_user}@{target}"
    command = ["ssh"]
    command.extend(
        [
            "-N",
            "-L",
            f"{spec['local_host']}:{int(spec['local_port'])}:{spec['remote_host']}:{int(spec['remote_port'])}",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "StrictHostKeyChecking=accept-new",
        ]
    )
    for option in spec.get("ssh_options") or []:
        command.extend(["-o", str(option)])
    command.append(target)
    return command


def start_proxy_tunnel(spec: dict[str, Any]) -> dict[str, Any]:
    if str(spec.get("kind") or "").strip() != "ssh":
        return {
            "spec": dict(spec),
            "managed": False,
            "reused": False,
            "command": [],
            "local_host": str(spec.get("local_host") or ""),
            "probe_host": _probe_host_for_bind_host(str(spec.get("local_host") or "")),
            "local_port": int(spec.get("local_port") or 0),
            "pid": 0,
        }
    local_host = str(spec["local_host"])
    local_port = int(spec["local_port"])
    probe_host = _probe_host_for_bind_host(local_host)
    if _port_ready(probe_host, local_port):
        return {
            "spec": dict(spec),
            "managed": False,
            "reused": True,
            "command": [],
            "local_host": local_host,
            "probe_host": probe_host,
            "local_port": local_port,
            "pid": 0,
        }
    command = build_proxy_tunnel_command(spec)
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        cwd=core.ROOT,
        env=dict(os.environ),
        start_new_session=True,
    )
    deadline = time.time() + max(3, int(spec.get("wait_seconds") or core.DEFAULT_PROXY_WAIT_SECONDS))
    while time.time() < deadline:
        if _port_ready(probe_host, local_port):
            return {
                "spec": dict(spec),
                "managed": True,
                "reused": False,
                "process": process,
                "command": command,
                "local_host": local_host,
                "probe_host": probe_host,
                "local_port": local_port,
                "pid": process.pid,
            }
        if process.poll() is not None:
            stderr = ""
            if process.stderr is not None:
                stderr = process.stderr.read().strip()
            tail = stderr or f"failed to start proxy tunnel: {' '.join(command)}"
            # Classify so operators don't have to grep stderr to know
            # whether to free a port, restart sshd, or look at the
            # adapter's own log.  Proxy is opt-in per provider — see
            # ``configs/models.local.json`` ``proxy:`` blocks — so a
            # failure here means a provider that opted-in is wedged,
            # not that the cluster is broken.
            lower = stderr.lower()
            if "address already in use" in lower or "bind: address" in lower:
                category = "port-in-use"
            elif "connection refused" in lower or "kex_exchange_identification" in lower:
                category = "ssh-unreachable"
            elif "permission denied" in lower:
                category = "ssh-auth"
            elif process.returncode and process.returncode != 0:
                category = f"adapter-exit-rc={process.returncode}"
            else:
                category = "tunnel-died"
            raise RuntimeError(
                f"proxy tunnel failed on {local_host}:{local_port} "
                f"({category}): {tail}"
            )
        time.sleep(0.2)
    _terminate_process_group(process)
    raise TimeoutError(
        f"proxy tunnel did not become ready on {local_host}:{local_port} "
        f"within deadline; check the adapter's own log for stalls"
    )


def stop_proxy_tunnel(state: dict[str, Any]) -> None:
    if state.get("shared_proxy"):
        release_shared_proxy_tunnel(state)
        return
    adapter_state = state.get("adapter_state")
    if isinstance(adapter_state, dict):
        process = adapter_state.get("process")
        if isinstance(process, subprocess.Popen):
            _terminate_process_group(process)
    process = state.get("process")
    if isinstance(process, subprocess.Popen):
        _terminate_process_group(process)
