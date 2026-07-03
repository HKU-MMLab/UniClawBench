#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/tmp_workspace/clawbench/service_state"
STATE_JSON="${STATE_DIR}/real_route_gui_apps_task_105_06.json"
mkdir -p "${STATE_DIR}" /tmp_workspace/results

export DEBIAN_FRONTEND=noninteractive

need_install=0
for cmd in gnome-calendar gedit; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    need_install=1
  fi
done

if [[ "${need_install}" -eq 1 ]]; then
  apt-get update
  apt-get install -y --no-install-recommends \
    gnome-calendar \
    gedit \
    dbus-x11 \
    xdg-utils \
    xdotool \
    wmctrl \
    scrot
fi

calendar_cmd="$(command -v gnome-calendar || true)"
editor_cmd="$(command -v gedit || true)"
calendar_version="$(gnome-calendar --version 2>&1 | head -n 1 || true)"
editor_version="$(gedit --version 2>&1 | head -n 1 || true)"

python3 - <<PY
import json
from datetime import datetime, timezone

state = {
    "service": "real-route-gui-apps-setup",
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "calendar": {
        "application": "GNOME Calendar",
        "command": ${calendar_cmd@Q},
        "version": ${calendar_version@Q},
    },
    "text_editor": {
        "application": "gedit",
        "command": ${editor_cmd@Q},
        "version": ${editor_version@Q},
    },
    "notes": "This service installs/verifies real GUI apps only. It does not serve local event or route pages.",
}
with open(${STATE_JSON@Q}, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=True, indent=2)
    f.write("\\n")
PY
