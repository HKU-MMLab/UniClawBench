#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/tmp_workspace/clawbench/service_state"
STATE_JSON="${STATE_DIR}/real_plan_gui_apps_task_105_09.json"
TMP_DIR="/tmp/clawbench-real-plan-apps-105-09"
SLACK_VERSION="${SLACK_VERSION:-4.47.69}"
mkdir -p "${STATE_DIR}" "${TMP_DIR}" /tmp_workspace/results

export DEBIAN_FRONTEND=noninteractive

retry() {
  local attempts="$1"
  shift
  local n=1
  until "$@"; do
    if [ "${n}" -ge "${attempts}" ]; then
      return 1
    fi
    sleep $((n * 3))
    n=$((n + 1))
  done
}

apt_install() {
  retry 3 apt-get update
  retry 3 apt-get install -y --no-install-recommends "$@"
}

install_slack() {
  if command -v slack >/dev/null 2>&1 || dpkg-query -W slack-desktop >/dev/null 2>&1; then
    return 0
  fi
  apt_install curl ca-certificates
  local deb="${TMP_DIR}/slack-desktop-${SLACK_VERSION}-amd64.deb"
  local url="https://downloads.slack-edge.com/desktop-releases/linux/x64/${SLACK_VERSION}/slack-desktop-${SLACK_VERSION}-amd64.deb"
  curl -fL --retry 3 "${url}" -o "${deb}"
  retry 3 apt-get install -y --no-install-recommends "${deb}"
}

apt_install \
  curl \
  ca-certificates \
  python3 \
  dbus-x11 \
  xdg-utils \
  xdotool \
  wmctrl \
  scrot \
  gnome-calendar \
  evolution-data-server \
  gedit \
  mousepad

install_slack

python3 - <<'PY'
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

state_path = Path("/tmp_workspace/clawbench/service_state/real_plan_gui_apps_task_105_09.json")
commands = {
    "calendar": ["gnome-calendar", "--version"],
    "text_editor_gedit": ["gedit", "--version"],
    "text_editor_mousepad": ["mousepad", "--version"],
    "slack_desktop": ["slack", "--version"],
}
state = {
    "service": "real-plan-gui-apps-setup",
    "task_id": "task_105_09_rust_meetup_plan_gui_slack",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "slack_download_url": "https://downloads.slack-edge.com/desktop-releases/linux/x64/4.47.69/slack-desktop-4.47.69-amd64.deb",
    "apps": {},
}
missing = []
for name, cmd in commands.items():
    exe = shutil.which(cmd[0])
    entry = {"command": cmd[0], "path": exe}
    if exe:
        try:
            out = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
            entry["version_output"] = out.stdout.strip().splitlines()[:3]
            entry["returncode"] = out.returncode
        except Exception as exc:
            entry["version_error"] = repr(exc)
    else:
        missing.append(name)
    state["apps"][name] = entry
state["ok"] = not missing
state["missing"] = missing
state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
if missing:
    raise SystemExit(f"Missing required GUI apps: {', '.join(missing)}")
PY
