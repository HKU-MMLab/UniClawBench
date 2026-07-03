#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

action="${1:-}"
case "${action}" in
  activate)
    xdotool search --name "${2:?window name required}" windowactivate
    ;;
  click)
    xdotool mousemove "${2:?x required}" "${3:?y required}" click 1
    ;;
  type)
    shift
    xdotool type --delay 20 "$*"
    ;;
  key)
    xdotool key "${2:?key required}"
    ;;
  inspect)
    # Convenience: invoke the accessibility-tree viewer so callers
    # can use `gui_action.sh inspect "<window>"` instead of the long
    # path. Delegates to scripts/inspect_ui.py.
    shift
    exec python3 "${HERE}/inspect_ui.py" "$@"
    ;;
  find)
    # Convenience: find one widget, print "x y w h".
    shift
    exec python3 "${HERE}/a11y.py" find "$@"
    ;;
  *)
    cat >&2 <<'EOF'
usage: gui_action.sh <action> [args...]

xdotool-based actuation (coordinates come from `inspect` below):
  activate  <window-title-substring>
  click     <x> <y>
  type      <text>
  key       <key>

accessibility-tree viewer (read-only, returns coords):
  inspect   <window> [--depth N]          dump widget tree as JSON
  find      <window> <widget-name> [--role R]
                                          print "x y w h" of one widget

Typical flow:
  1. wmctrl -l                            -- see what windows exist
  2. gui_action.sh inspect "Save As"      -- find the Save button's xywh
  3. gui_action.sh click X Y              -- click it
EOF
    exit 1
    ;;
esac
