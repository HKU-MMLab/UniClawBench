#!/usr/bin/env python3
"""Accessibility-tree dumper for linux-gui-control.

Walks the AT-SPI accessibility bus (via dogtail / pyatspi) and prints
the widget hierarchy under a given top-level window — with coordinates
— as JSON. Consumers read the JSON, locate the widget they want by
``name`` / ``role``, and drive it with the usual xdotool pattern:

    # After `inspect_ui.py "Save As"` gives you
    #   {"role": "push button", "name": "Save", "x": 1176, "y": 819, "w": 86, "h": 34}
    # compute the button center and click it:
    xdotool mousemove $((1176 + 86/2)) $((819 + 34/2)) click 1

This script is purely a *viewer* (matches the original skill's
``inspect_ui.py`` contract — dump tree, do not act). Actuation stays
on the ``gui_action.sh`` side.

Usage
-----
    a11y.py tree <window> [--depth N]
        Dump the widget tree rooted at a top-level window whose
        application name or window title contains <window>.

    a11y.py find <window> <widget-name> [--role R]
        Shortcut: print only the first widget whose name matches, in
        the form "x y w h" so callers can xargs it straight into
        xdotool.

The bus prerequisites (at-spi-bus-launcher, at-spi2-registryd,
atk-bridge, toolkit-accessibility=true) are set up by
start-desktop.sh; Electron / Chromium apps additionally need
``--force-renderer-accessibility`` to publish their widgets — see
``scripts/launch_with_a11y.sh`` and the SKILL.md notes.
"""
from __future__ import annotations

import argparse
import json
import sys
import time


def _import_dogtail():
    # Bypass dogtail's gsettings-based a11y check at module import
    # time. The check assumes a GNOME session with a dconf write
    # path, which we don't have under xfwm4 + Xvfb. As long as the
    # AT-SPI bus is actually running, dogtail itself works fine.
    from dogtail import config
    config.checkForA11y = False
    config.logDebugToFile = False
    config.logDebugToStdOut = False
    from dogtail import tree
    return tree


def _find_app(tree, window_substr, timeout=5.0):
    """Find the subtree rooted at a top-level window identified by
    <window_substr>. Matches (case-insensitive, substring) against:

    1. Application names (``xterm``, ``gedit``, ...)
    2. Top-level frame / dialog / window titles under each app
       (``"Save As"``, ``"Welcome - Visual Studio Code"``, ...)

    Retries for <timeout> seconds so just-launched apps / just-opened
    dialogs have a chance to register on the bus.
    """
    needle = window_substr.lower()
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            apps = list(tree.root.applications())
            # Pass 1: application name match
            for a in apps:
                name = getattr(a, "name", "") or ""
                if needle in name.lower():
                    return a
            # Pass 2: top-level window title match (frames, dialogs,
            # file choosers) — the most common case for titled
            # windows like "Save As"
            for a in apps:
                try:
                    children = list(a.children)
                except Exception:
                    continue
                for c in children:
                    cname = (getattr(c, "name", "") or "").lower()
                    crole = getattr(c, "roleName", "") or ""
                    if needle in cname and crole in {
                        "frame", "dialog", "window",
                        "file chooser", "application",
                    }:
                        return c
        except Exception as e:
            last_err = e
        time.sleep(0.25)
    raise SystemExit(
        f"inspect_ui: no application / top-level window whose name "
        f"contains {window_substr!r} found on the AT-SPI bus within "
        f"{timeout}s. Either the window is not open yet, or the app "
        f"did not register with accessibility. For Electron / "
        f"Chromium apps (VSCode, Slack, etc.) launch via "
        f"`launch_with_a11y.sh <app>` so the renderer joins the bus. "
        f"(last error: {last_err})"
    )


def _iter_widgets(node, depth=0, max_depth=10):
    yield depth, node
    if depth >= max_depth:
        return
    try:
        for child in node.children:
            yield from _iter_widgets(child, depth + 1, max_depth)
    except Exception:
        return


def _widget_entry(depth, w):
    try:
        x, y = w.position or (None, None)
    except Exception:
        x = y = None
    try:
        ww, wh = w.size or (None, None)
    except Exception:
        ww = wh = None
    return {
        "depth": depth,
        "name": getattr(w, "name", ""),
        "role": getattr(w, "roleName", ""),
        "x": x, "y": y, "w": ww, "h": wh,
    }


def cmd_tree(args):
    tree = _import_dogtail()
    app = _find_app(tree, args.window, timeout=args.wait)
    items = [_widget_entry(d, w)
             for d, w in _iter_widgets(app, max_depth=args.depth)]
    json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def cmd_find(args):
    tree = _import_dogtail()
    app = _find_app(tree, args.window, timeout=args.wait)
    needle = args.name
    needle_l = needle.lower()
    # Exact match first, then case-insensitive equality, then substring.
    for matcher in (
        lambda w: (getattr(w, "name", "") or "") == needle,
        lambda w: (getattr(w, "name", "") or "").lower() == needle_l,
        lambda w: needle_l in (getattr(w, "name", "") or "").lower(),
    ):
        for _, w in _iter_widgets(app, max_depth=args.depth):
            if args.role and getattr(w, "roleName", "") != args.role:
                continue
            if matcher(w):
                e = _widget_entry(0, w)
                if e["x"] is None or e["w"] is None:
                    continue  # no usable geometry, keep searching
                print(f"{e['x']} {e['y']} {e['w']} {e['h']}")
                return
    raise SystemExit(
        f"inspect_ui: no widget with name={needle!r} "
        + (f"role={args.role!r} " if args.role else "")
        + f"found under window {args.window!r}"
    )


def main():
    p = argparse.ArgumentParser(
        description="AT-SPI accessibility-tree viewer (read-only). "
                    "Use the coordinates it returns to drive xdotool "
                    "via gui_action.sh."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_tree = sub.add_parser("tree", help="dump full widget tree + coords")
    p_tree.add_argument("window", help="application name / window title substring")
    p_tree.add_argument("--depth", type=int, default=10,
                        help="max tree depth to walk (default 10)")
    p_tree.add_argument("--wait", type=float, default=5.0,
                        help="seconds to wait for the window to appear on the bus")
    p_tree.set_defaults(func=cmd_tree)

    p_find = sub.add_parser(
        "find",
        help="locate one widget and print 'x y w h' of its bounding box",
    )
    p_find.add_argument("window")
    p_find.add_argument("name")
    p_find.add_argument("--role")
    p_find.add_argument("--depth", type=int, default=10)
    p_find.add_argument("--wait", type=float, default=5.0)
    p_find.set_defaults(func=cmd_find)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
