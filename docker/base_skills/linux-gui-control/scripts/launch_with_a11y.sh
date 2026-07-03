#!/usr/bin/env bash
# launch_with_a11y.sh — start a GUI app with the accessibility bridge
# turned on, so its widgets appear in the AT-SPI tree (and therefore
# in `inspect_ui.py` / `gui_action.sh inspect`).
#
# Why this exists:
#   - GTK and Qt apps join the AT-SPI bus automatically as long as
#     GTK_MODULES=gail:atk-bridge (or QT_ACCESSIBILITY=1) is set.
#     Those vars live in the container ENV; nothing to do.
#   - Chromium-based apps (Chrome / Chromium / Electron: VS Code,
#     Slack, Discord, Obsidian, ...) keep renderer accessibility
#     OFF by default to save RAM. The renderer process only
#     publishes its DOM to AT-SPI when `--force-renderer-accessibility`
#     is on the command line. Without it, inspect_ui.py sees the
#     Electron main frame but every widget underneath has an empty
#     name and role=panel.
#
# Usage:
#   launch_with_a11y.sh <app-executable> [app-args...]
#
# Examples:
#   launch_with_a11y.sh code /tmp_workspace/results/hello.py
#   launch_with_a11y.sh chromium https://example.com
#   launch_with_a11y.sh /usr/share/code/code --user-data-dir /tmp/vd
#
# The script inspects the app's basename to decide which flags to add.
# For unknown apps it starts them unchanged (safer than injecting
# flags the binary doesn't understand).

set -euo pipefail

if [ $# -lt 1 ]; then
    cat >&2 <<EOF
usage: launch_with_a11y.sh <app> [args...]
Launches <app> with accessibility flags appropriate to its framework.
Known Electron / Chromium apps get --force-renderer-accessibility.
EOF
    exit 1
fi

cmd="$1"
shift

base="$(basename "$cmd")"

# Electron / Chromium family — take --force-renderer-accessibility
# and --no-sandbox (the latter because we're root in the container
# and Chromium's sandbox refuses to run as root otherwise).
is_chromium=0
case "$base" in
    code|code-insiders|codium|code-oss|oss-code)       is_chromium=1 ;;
    chromium|chromium-browser|chrome|google-chrome)    is_chromium=1 ;;
    google-chrome-stable|google-chrome-beta)           is_chromium=1 ;;
    slack|discord|element-desktop|teams|obsidian)      is_chromium=1 ;;
    spotify|signal-desktop|skype)                      is_chromium=1 ;;
esac

# Also handle the ``code`` bash wrapper's WSL-detection false
# positive by exporting DONT_PROMPT_WSL_INSTALL=1. The wrapper
# still passes all our flags through.
if [ "$base" = "code" ] || [ "$base" = "code-insiders" ]; then
    export DONT_PROMPT_WSL_INSTALL=1
fi

if [ "$is_chromium" = "1" ]; then
    exec "$cmd" --force-renderer-accessibility --no-sandbox "$@"
fi

# Default: untouched. GTK / Qt / native-X11 apps don't need extra
# flags because the container ENV already has GTK_MODULES and
# QT_ACCESSIBILITY set.
exec "$cmd" "$@"
