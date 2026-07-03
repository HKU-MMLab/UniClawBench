"""Proxy package.

The original 2000-line ``lib/proxy.py`` has been split into:

- ``.core`` — shared module-level constants (``PROXY_REGISTRY_ROOT``,
  ``PROXY_ADAPTER_LOG_PATH``, ``DEFAULT_PROXY_KIND``, etc.) plus the
  tiny ``write_local`` file-writer. Re-exports ``start_proxy_adapter``
  from ``.adapter`` for legacy callers and monkeypatches.
- ``.adapter`` — ``start_proxy_adapter`` and the ``script = r\"\"\" ... \"\"\"``
  subprocess body that it spawns via ``python3 -c <script>``. The
  functions inside that string (``sanitize_chat_payload``,
  ``responses_to_chat_payload``, ``cache_tool_call_extras``, ``Handler``,
  etc.) are NOT the same symbols as the module-level copies in
  ``.transform`` — the module-level versions are test-visible mirrors,
  and any fix applied in the subprocess script MUST be mirrored in
  ``.transform`` (and vice versa).
- ``.tunnel`` — SSH tunnel lifecycle + shared registry
  (``acquire_shared_proxy_tunnel``, ``start_proxy_tunnel``,
  ``build_proxy_tunnel_command``, and private registry helpers).
- ``.spec`` — provider proxy-spec normalization and host-string
  helpers.
- ``.usage`` — proxy-adapter usage/log discovery + readers used by
  per-cycle token accounting.
- ``.transform`` — test-visible mirror of the subprocess-side payload
  transforms.

External consumers and tests that previously imported from ``lib.proxy``
as a single module continue to work unchanged: ``from lib.proxy import
X``, ``lib.proxy.PROXY_REGISTRY_ROOT``, and string-path patches like
``monkeypatch.setattr("lib.proxy.PROXY_REGISTRY_ROOT", ...)`` all resolve
to this package's ``__init__``, which re-exports the full surface.
"""
from __future__ import annotations

from .core import (  # noqa: F401
    # Constants (also used by tests via string-path monkeypatch)
    DEFAULT_PROXY_KIND,
    DEFAULT_PROXY_WAIT_SECONDS,
    PROXY_ADAPTER_LOG_PATH,
    PROXY_REGISTRY_ROOT,
    ROOT,
    start_proxy_adapter,
    write_local,
)
# Tunnel lifecycle now lives in ``.tunnel`` — re-exported here so
# external callers (``lib.runner.task_config`` et al.) and
# string-path monkeypatches keep resolving.
from .tunnel import (  # noqa: F401
    _ensure_no_adapter_conflict,
    _terminate_process_group,
    _terminate_process_group_pid,
    acquire_shared_proxy_tunnel,
    build_proxy_tunnel_command,
    ensure_shared_proxy_with_reap,
    release_shared_proxy_tunnel,
    start_proxy_tunnel,
    stop_proxy_tunnel,
)
# Spec parsing + host-string helpers now live in ``.spec`` — re-exported
# here so external callers (``lib.runner.task_config`` et al.) and
# string-path monkeypatches keep resolving.
from .tunnel import (  # noqa: F401  (spec parsing was inlined into tunnel.py in Phase 4)
    _proxy_spec_key,
    normalize_provider_proxy_spec,
    provider_proxy_spec,
)
# Usage/log discovery helpers now live in ``.usage`` — re-exported here
# so external callers (``lib.runner.artifacts``, ``lib.runner`` et al.)
# and string-path monkeypatches keep resolving.
from .usage import (  # noqa: F401
    discover_active_proxy_adapter_log_paths,
    discover_active_proxy_adapter_request_log_paths,
    read_proxy_request_events,
    read_proxy_request_events_across_all_logs,
    read_proxy_usage_events,
    read_proxy_usage_events_across_all_logs,
)
# Module-level payload-transform mirrors live in ``.transform`` — the
# subprocess script inside ``.adapter.start_proxy_adapter`` keeps its own
# embedded copy (that's the authoritative one); these module-level
# copies are only for unit tests that exercise the transforms without
# spawning the adapter.
from .transform import (  # noqa: F401
    item_text,
    normalize_content,
    responses_to_chat_payload,
    sanitize_chat_payload,
)

__all__ = [
    "DEFAULT_PROXY_KIND",
    "DEFAULT_PROXY_WAIT_SECONDS",
    "PROXY_ADAPTER_LOG_PATH",
    "PROXY_REGISTRY_ROOT",
    "ROOT",
    "acquire_shared_proxy_tunnel",
    "build_proxy_tunnel_command",
    "ensure_shared_proxy_with_reap",
    "discover_active_proxy_adapter_log_paths",
    "discover_active_proxy_adapter_request_log_paths",
    "item_text",
    "normalize_content",
    "normalize_provider_proxy_spec",
    "provider_proxy_spec",
    "read_proxy_request_events",
    "read_proxy_request_events_across_all_logs",
    "read_proxy_usage_events",
    "read_proxy_usage_events_across_all_logs",
    "release_shared_proxy_tunnel",
    "responses_to_chat_payload",
    "sanitize_chat_payload",
    "start_proxy_adapter",
    "start_proxy_tunnel",
    "stop_proxy_tunnel",
    "write_local",
    "_ensure_no_adapter_conflict",
    "_proxy_spec_key",
    "_terminate_process_group",
    "_terminate_process_group_pid",
]
