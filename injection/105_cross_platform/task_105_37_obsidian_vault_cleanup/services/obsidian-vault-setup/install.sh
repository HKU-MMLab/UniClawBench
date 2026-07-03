#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
STATE_DIR="/tmp_workspace/clawbench/service_state"
mkdir -p "$STATE_DIR" /tmp_workspace/results/project_vault_cleaned
APT_OPTS=(-o Acquire::Retries=1 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
apt_refresh() { timeout 90s apt-get "${APT_OPTS[@]}" update -qq || true; }
apt_install() { timeout 240s apt-get "${APT_OPTS[@]}" install -y --no-install-recommends "$@" || true; }
if ! command -v thunar >/dev/null 2>&1 || ! command -v scrot >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
  apt_refresh
  apt_install \
    curl ca-certificates dbus-x11 xdg-utils xdotool wmctrl scrot \
    thunar python3 fonts-noto-cjk libnss3 libatk-bridge2.0-0 \
    libgtk-3-0 libxss1 libasound2t64
fi
if ! command -v obsidian >/dev/null 2>&1; then
  tmp=/tmp/obsidian-amd64.deb
  url="$(timeout 45s python3 - <<'PY' || true
import json, urllib.request
data = json.load(urllib.request.urlopen("https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest", timeout=30))
print(next(a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".deb") and "amd64" in a["name"]))
PY
)"
  if [ -n "$url" ]; then
    timeout 120s curl -fL --retry 2 --max-time 60 "$url" -o "$tmp" && apt_install "$tmp" || true
  fi
fi
python3 - <<'PY'
import json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
cmds = {"obsidian": ["obsidian", "--version"], "file_manager": ["thunar", "--version"], "scrot": ["scrot", "--version"]}
state = {"task_id": "task_105_37_obsidian_vault_cleanup", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "apps": {}}
for name, cmd in cmds.items():
    exe = shutil.which(cmd[0])
    state["apps"][name] = {"command": cmd[0], "path": exe}
    if exe:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        state["apps"][name]["returncode"] = p.returncode
        state["apps"][name]["version_output"] = p.stdout.strip().splitlines()[:3]
Path("/tmp_workspace/clawbench/service_state/obsidian_vault_setup_task_105_37.json").write_text(json.dumps(state, indent=2) + "\n")
PY
