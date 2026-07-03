#!/usr/bin/env python3
"""Backward-compat shim: forward ``inspect_ui.py <window>`` to
``a11y.py tree <window>`` so agents / docs that still reference the
old name keep working. New code should call ``a11y.py`` directly —
see the Quick Start / "Clicking a named widget without knowing its
pixel coordinates" section of SKILL.md for the full set of
accessibility primitives (tree / find / click / type / enter).

Behaviour difference from the old script: the window argument is
matched against both application names AND top-level window titles
(frames / dialogs), so passing e.g. ``"Save As"`` now works even
though ``Save As`` is a window title, not an application name.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A11Y = os.path.join(HERE, "a11y.py")

if not os.path.isfile(A11Y):
    sys.stderr.write(
        f"linux-gui-control: a11y.py not found next to inspect_ui.py "
        f"(looked in {HERE!r}); the accessibility layer is broken.\n"
    )
    sys.exit(2)

argv = [sys.executable, A11Y, "tree", *sys.argv[1:]]
os.execv(argv[0], argv)
