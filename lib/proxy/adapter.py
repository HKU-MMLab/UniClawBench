#!/usr/bin/env python3
'''HTTP compatibility adapter subprocess for Clawbench's proxy layer.

``start_proxy_adapter`` is the Codex CLI compatibility shim: it spawns
a standalone Python subprocess (``python3 -m lib.proxy.adapter_server``)
that listens on a loopback port, receives Codex-shaped JSON requests,
and forwards them upstream — optionally after rewriting the request to
match the remote provider's quirks (``drop_max_tokens``) or converting
between ``/responses`` and ``/chat/completions`` envelopes
(``responses_via_chat``).

Round 10 / P2: the subprocess body used to live in a 1179-line
``script = r""" ... """`` string here, with ``transform.py`` keeping a
hand-mirrored copy of 4 transform functions for unit tests.  That
arrangement meant production code was never imported / linted /
tested directly, and the mirror drifted (most notoriously the
``str(output)`` image-stringification regression).  The script body
now lives in ``lib.proxy.adapter_server`` as a real module; this file
just spawns it.

Module-level constants (``PROXY_ADAPTER_LOG_PATH``,
``DEFAULT_PROXY_WAIT_SECONDS``, ``ROOT``) still live in ``core.py``.
This module reads them via ``core.<name>`` so string-path monkeypatches
(``monkeypatch.setattr("lib.proxy.core.PROXY_ADAPTER_LOG_PATH", tmp)``)
keep taking effect. The sibling helpers ``tunnel._port_ready`` and
``tunnel._terminate_process_group`` are likewise looked up
module-qualified to let tests patch them at the new owner.
'''
from __future__ import annotations

import os
import subprocess
import time
from typing import Any

from . import core, tunnel


def start_proxy_adapter(spec: dict[str, Any]) -> dict[str, Any] | None:
    adapter = str(spec.get("adapter") or "").strip().lower().replace("-", "_")
    if not adapter:
        return None
    if adapter not in {"drop_max_tokens", "responses_via_chat"}:
        raise RuntimeError(f"unsupported proxy adapter: {adapter}")
    listen_host = str(spec.get("adapter_host") or spec.get("local_host") or "127.0.0.1")
    probe_host = tunnel._probe_host_for_bind_host(listen_host)
    listen_port = int(spec.get("adapter_port") or 0)
    if listen_port <= 0:
        listen_port = int(spec["local_port"]) + 1
    upstream_base = str(spec.get("upstream_base") or "").strip()
    if not upstream_base:
        upstream_base = f"http://{spec['local_host']}:{int(spec['local_port'])}"
    adapter_log = str(core.PROXY_ADAPTER_LOG_PATH.resolve())
    request_log = str(core.PROXY_ADAPTER_REQUEST_LOG_PATH.resolve())
    if tunnel._port_ready(probe_host, listen_port):
        return {
            "kind": adapter,
            "managed": False,
            "reused": True,
            "listen_host": listen_host,
            "probe_host": probe_host,
            "listen_port": listen_port,
            "base_url": f"http://{probe_host}:{listen_port}",
            "upstream_base": upstream_base,
            # We don't have direct knowledge of the running adapter's
            # actual log paths in the reused branch — fall back to this
            # checkout's defaults. ``discover_active_proxy_adapter_*``
            # in ``usage.py`` does the cross-checkout reconciliation
            # against the shared registry / ``/proc/<pid>/cmdline``.
            "log_path": adapter_log,
            "request_log_path": request_log,
            "pid": 0,
        }
    # Round 10 / P2: spawn the adapter server as a real module.  argv
    # order matches the prior inline-script contract:
    # [host, port, upstream_base, adapter_kind, log_path, request_log_path].
    # cwd=core.ROOT so the ``lib.proxy.adapter_server`` import resolves
    # to this checkout's source (not a globally-installed copy).
    process = subprocess.Popen(
        [
            "python3", "-m", "lib.proxy.adapter_server",
            listen_host, str(listen_port), upstream_base,
            adapter, adapter_log, request_log,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        cwd=core.ROOT,
        env=dict(os.environ),
        start_new_session=True,
    )
    deadline = time.time() + max(3, int(spec.get("wait_seconds") or core.DEFAULT_PROXY_WAIT_SECONDS))
    while time.time() < deadline:
        if tunnel._port_ready(probe_host, listen_port):
            return {
                "kind": adapter,
                "managed": True,
                "reused": False,
                "listen_host": listen_host,
                "probe_host": probe_host,
                "listen_port": listen_port,
                "base_url": f"http://{probe_host}:{listen_port}",
                "upstream_base": upstream_base,
                "process": process,
                "log_path": adapter_log,
                "request_log_path": request_log,
                "pid": process.pid,
            }
        if process.poll() is not None:
            stderr = ""
            if process.stderr is not None:
                stderr = process.stderr.read().strip()
            raise RuntimeError(stderr or f"failed to start proxy adapter on {listen_host}:{listen_port}")
        time.sleep(0.2)
    tunnel._terminate_process_group(process)
    raise TimeoutError(f"proxy adapter did not become ready on {listen_host}:{listen_port}")
