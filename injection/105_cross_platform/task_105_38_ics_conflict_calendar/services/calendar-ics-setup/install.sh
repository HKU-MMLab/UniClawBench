#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
STATE_DIR="/tmp_workspace/clawbench/service_state"
mkdir -p "$STATE_DIR" /tmp_workspace/results
APT_OPTS=(-o Acquire::Retries=1 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
apt_refresh() { timeout 90s apt-get "${APT_OPTS[@]}" update -qq || true; }
apt_install() { timeout 240s apt-get "${APT_OPTS[@]}" install -y --no-install-recommends "$@" || true; }
if ! command -v gnome-calendar >/dev/null 2>&1 || ! command -v scrot >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  apt_refresh
  apt_install \
    gnome-calendar evolution-data-server dbus-x11 xdg-utils \
    xdotool wmctrl scrot python3 python3-pip fonts-noto-cjk
fi
python3 - <<'PY' >/dev/null 2>&1 || timeout 120s python3 -m pip install --quiet --break-system-packages icalendar 2>/dev/null || timeout 120s python3 -m pip install --quiet icalendar 2>/dev/null || true
import icalendar
PY
if command -v Xvfb >/dev/null && ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  Xvfb :99 -screen 0 1440x900x24 >/tmp_workspace/clawbench/logs/calendar-xvfb.log 2>&1 &
fi
python3 - <<'PY'
import json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
cmds = {"calendar": ["gnome-calendar", "--version"], "scrot": ["scrot", "--version"], "python": ["python3", "--version"]}
state = {"task_id": "task_105_38_ics_conflict_calendar", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "apps": {}}
for name, cmd in cmds.items():
    exe = shutil.which(cmd[0])
    state["apps"][name] = {"command": cmd[0], "path": exe}
    if exe:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        state["apps"][name]["returncode"] = p.returncode
        state["apps"][name]["version_output"] = p.stdout.strip().splitlines()[:3]
Path("/tmp_workspace/clawbench/service_state/calendar_ics_setup_task_105_38.json").write_text(json.dumps(state, indent=2) + "\n")
PY
