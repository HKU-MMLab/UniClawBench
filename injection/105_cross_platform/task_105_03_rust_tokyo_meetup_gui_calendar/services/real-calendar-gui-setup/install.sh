#!/usr/bin/env bash
# One-shot task-local setup for the real GUI calendar workflow.

set -euo pipefail

MARKER_DIR="/tmp_workspace/clawbench/service_state"
STATE_JSON="${MARKER_DIR}/real-calendar-text-editor.json"
LOG_PREFIX="[real-calendar-gui-setup]"

mkdir -p "${MARKER_DIR}" /tmp_workspace/results

export DEBIAN_FRONTEND=noninteractive

need_install=0
for cmd in gnome-calendar gedit; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    need_install=1
  fi
done
if ! dpkg-query -W -f='${Status}' evolution-data-server 2>/dev/null | grep -q "install ok installed"; then
  need_install=1
fi

if [[ "${need_install}" -eq 1 ]]; then
  echo "${LOG_PREFIX} installing GNOME Calendar, gedit, and GUI helpers"
  apt-get update
  apt-get install -y --no-install-recommends \
    gnome-calendar \
    gedit \
    evolution-data-server \
    dbus-x11 \
    xdg-utils \
    xdotool \
    wmctrl \
    scrot
else
  echo "${LOG_PREFIX} GNOME Calendar and gedit already present"
fi

calendar_cmd="$(command -v gnome-calendar || true)"
editor_cmd="$(command -v gedit || true)"
eds_calendar_factory="$(command -v evolution-calendar-factory || true)"
if [[ -z "${eds_calendar_factory}" ]]; then
  for candidate in /usr/libexec/evolution-calendar-factory /usr/lib/evolution/evolution-calendar-factory; do
    if [[ -x "${candidate}" ]]; then
      eds_calendar_factory="${candidate}"
      break
    fi
  done
fi
calendar_version="$(gnome-calendar --version 2>&1 | head -n 1 || true)"
editor_version="$(gedit --version 2>&1 | head -n 1 || true)"
eds_version="$(dpkg-query -W -f='${Version}' evolution-data-server 2>/dev/null || true)"

calendar_launch_status="not_attempted"
editor_launch_status="not_attempted"

if [[ -n "${DISPLAY:-}" && -n "${calendar_cmd}" ]]; then
  if dbus-run-session -- timeout 12s gnome-calendar >/tmp/gnome-calendar-launch.log 2>&1; then
    calendar_launch_status="exited_cleanly"
  else
    code=$?
    if [[ "${code}" -eq 124 ]]; then
      calendar_launch_status="started_timeout_after_12s"
    else
      calendar_launch_status="failed_${code}"
    fi
  fi
else
  calendar_launch_status="skipped_no_display_or_command"
fi

if [[ -n "${DISPLAY:-}" && -n "${editor_cmd}" ]]; then
  if dbus-run-session -- timeout 8s gedit --new-window >/tmp/gedit-launch.log 2>&1; then
    editor_launch_status="exited_cleanly"
  else
    code=$?
    if [[ "${code}" -eq 124 ]]; then
      editor_launch_status="started_timeout_after_8s"
    else
      editor_launch_status="failed_${code}"
    fi
  fi
else
  editor_launch_status="skipped_no_display_or_command"
fi

python3 - <<PY
import json
from datetime import datetime, timezone

state = {
    "service": "real-calendar-gui-setup",
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "calendar": {
        "application": "GNOME Calendar",
        "command": ${calendar_cmd@Q},
        "version": ${calendar_version@Q},
        "launch_status": ${calendar_launch_status@Q},
        "evolution_calendar_factory": ${eds_calendar_factory@Q},
        "evolution_data_server_version": ${eds_version@Q},
    },
    "text_editor": {
        "application": "gedit",
        "command": ${editor_cmd@Q},
        "version": ${editor_version@Q},
        "launch_status": ${editor_launch_status@Q},
    },
    "notes": "The task requires the executor to use the real desktop GUI apps; this setup JSON only records installation and launch validation.",
}
with open(${STATE_JSON@Q}, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=True, indent=2)
    f.write("\\n")
PY

echo "${LOG_PREFIX} wrote ${STATE_JSON}"
