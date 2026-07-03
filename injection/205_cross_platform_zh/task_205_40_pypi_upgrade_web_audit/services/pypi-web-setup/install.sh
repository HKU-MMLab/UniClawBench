#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
STATE_DIR="/tmp_workspace/clawbench/service_state"
mkdir -p "$STATE_DIR" /tmp_workspace/results/pypi_screenshots
APT_OPTS=(-o Acquire::Retries=1 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
apt_refresh() { timeout 90s apt-get "${APT_OPTS[@]}" update -qq || true; }
apt_install() { timeout 180s apt-get "${APT_OPTS[@]}" install -y --no-install-recommends "$@" || true; }
if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1 || ! command -v scrot >/dev/null 2>&1 || ! command -v xdotool >/dev/null 2>&1; then
  apt_refresh
  apt_install curl jq python3 ca-certificates scrot xdotool wmctrl
fi
python3 - <<'PY'
import json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
cmds = {"chromium": ["chromium", "--version"], "curl": ["curl", "--version"], "jq": ["jq", "--version"], "python": ["python3", "--version"]}
state = {"task_id": "task_105_40_pypi_upgrade_web_audit", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "apps": {}}
for name, cmd in cmds.items():
    exe = shutil.which(cmd[0])
    state["apps"][name] = {"command": cmd[0], "path": exe}
    if exe:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        state["apps"][name]["returncode"] = p.returncode
        state["apps"][name]["version_output"] = p.stdout.strip().splitlines()[:3]
Path("/tmp_workspace/clawbench/service_state/pypi_web_setup_task_105_40.json").write_text(json.dumps(state, indent=2) + "\n")
PY
