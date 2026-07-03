"""Round 10 / P2 source-level regression guard.

Locks the fact that ``lib.proxy.adapter.start_proxy_adapter`` spawns
the subprocess via ``python3 -m lib.proxy.adapter_server <args>`` and
not the previous inline ``python3 -c <script>`` form.  A future
refactor could accidentally revert by re-introducing a script string;
this test catches that immediately.
"""
from __future__ import annotations

import ast
from pathlib import Path

import lib.proxy.adapter as adapter_mod


ADAPTER_PY = Path(adapter_mod.__file__)


def test_popen_uses_module_invocation_not_inline_script() -> None:
    """Inspect the source text: must NOT contain ``["python3", "-c", script,``."""
    text = ADAPTER_PY.read_text(encoding="utf-8")
    assert '"-c"' not in text or "lib.proxy.adapter_server" in text, (
        "adapter.py subprocess.Popen must use ``-m lib.proxy.adapter_server``, "
        "not the inline ``-c <script>`` form that prevents real-module testing"
    )
    assert "lib.proxy.adapter_server" in text, (
        "adapter.py must reference lib.proxy.adapter_server as the spawn target"
    )


def test_inline_script_string_is_gone() -> None:
    """Catch regression where someone re-introduces a ``script = r\"\"\"``
    string literal as a way to bundle inline code into the subprocess.

    Looks for the assignment at the start of a code line (any indent),
    not inside docstrings — adapter.py's prose mentions the deprecated
    form in past tense for historical context."""
    import re
    text = ADAPTER_PY.read_text(encoding="utf-8")
    code_line_pattern = re.compile(r'^(\s*)script\s*=\s*r"""', re.MULTILINE)
    matches = code_line_pattern.findall(text)
    assert not matches, (
        f"adapter.py has {len(matches)} inline-script assignment(s) — "
        "Round 10 / P2 moved the body to lib.proxy.adapter_server"
    )


def test_adapter_py_is_compact() -> None:
    """Before the refactor adapter.py was 1286 lines (1179 of which
    were inline script).  After the refactor it should be ~100-150
    lines — just the prologue + Popen + ready loop.  Catch a future
    drift where someone inlines a big helper back here instead of
    extending adapter_server."""
    lines = ADAPTER_PY.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 200, (
        f"adapter.py grew to {len(lines)} lines — Round 10 / P2 left it "
        f"around 100-150.  Inline-script regression?"
    )


def test_argv_order_matches_adapter_server_main() -> None:
    """The Popen argv must match what ``adapter_server.main`` reads
    via ``sys.argv``: [host, port, upstream_base, adapter_kind,
    log_path, request_log_path].  AST-walk the call site to extract
    the literal list contents."""
    text = ADAPTER_PY.read_text(encoding="utf-8")
    tree = ast.parse(text)

    # Find the subprocess.Popen call with a "-m" arg
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # We want subprocess.Popen([...], ...)
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "Popen":
            continue
        if not node.args:
            continue
        argv_arg = node.args[0]
        if not isinstance(argv_arg, ast.List):
            continue
        # Look for the literal "-m" entry
        literals = [e for e in argv_arg.elts if isinstance(e, ast.Constant)]
        consts = [e.value for e in literals]
        if "-m" not in consts:
            continue
        # Must reference lib.proxy.adapter_server
        assert "lib.proxy.adapter_server" in consts, (
            f"Popen argv has -m but target is not lib.proxy.adapter_server; got {consts}"
        )
        # And remaining 6 argv slots should be variable references
        # (listen_host, str(listen_port), upstream_base, adapter,
        # adapter_log, request_log) — at least 6 non-constant entries
        non_const = [e for e in argv_arg.elts if not isinstance(e, ast.Constant)]
        assert len(non_const) >= 6, (
            f"Popen argv missing argv entries (host/port/upstream/adapter/logs); "
            f"got {len(non_const)} non-constant entries"
        )
        found = True
        break

    assert found, (
        "did not find subprocess.Popen([..., '-m', 'lib.proxy.adapter_server', ...]) "
        "in adapter.py — Round 10 / P2 invocation contract broken"
    )
