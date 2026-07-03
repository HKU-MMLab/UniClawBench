#!/usr/bin/env python3
'''Shared constants + tiny utilities for the Clawbench proxy package.

``core.py`` now hosts only:

- The shared module-level constants (``ROOT``, ``DEFAULT_PROXY_KIND``,
  ``DEFAULT_PROXY_WAIT_SECONDS``, ``PROXY_REGISTRY_ROOT``,
  ``PROXY_ADAPTER_LOG_PATH``). Tests patch several of these via
  string path (e.g. ``monkeypatch.setattr("lib.proxy.core.PROXY_REGISTRY_ROOT",
  tmp)``), so they must stay here.
- ``write_local`` — tiny file-write utility shared across the package.
- ``start_proxy_adapter`` — re-exported from ``.adapter`` for legacy
  imports and string-path monkeypatches
  (``monkeypatch.setattr("lib.proxy.core.start_proxy_adapter", fake)``).
  The authoritative definition now lives in ``.adapter``, where the
  ``script = r""" ... """`` subprocess body also lives.

Spec parsing, tunnel lifecycle, usage/log discovery, and
module-level test-mirror transforms have moved to ``.spec`` /
``.tunnel`` / ``.usage`` / ``.transform`` respectively — see those
files for the split rationale.
'''
from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROXY_KIND = "ssh"
DEFAULT_PROXY_WAIT_SECONDS = max(5, int(os.environ.get("CLAWBENCH_PROXY_WAIT_SECONDS", "15")))
PROXY_REGISTRY_ROOT = ROOT / ".runtime" / "proxy_registry"
# Shared log file written by the adapter subprocess. Both upstream proxy events
# and per-call usage events (for executor token accounting) go here; the runner
# slices out executor-window entries per cycle into attempt-local ledgers.
PROXY_ADAPTER_LOG_PATH = ROOT / ".runtime" / "proxy_adapter.log"
# Optional companion log capturing the full request+response transcript per
# call (one JSON-Lines entry per HTTP request). Kept separate from
# ``PROXY_ADAPTER_LOG_PATH`` so the lightweight usage-event log stays
# cheap to scan during the per-cycle ledger slice while still giving us a
# replayable record on disk for debugging / future replay tooling.
PROXY_ADAPTER_REQUEST_LOG_PATH = ROOT / ".runtime" / "proxy_adapter_requests.log"


def write_local(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# Re-export start_proxy_adapter from .adapter so legacy imports
# (including string-path monkeypatches like
# monkeypatch.setattr("lib.proxy.core.start_proxy_adapter", fake)) keep
# resolving after the function body moved out of this module.
from .adapter import start_proxy_adapter  # noqa: E402,F401
