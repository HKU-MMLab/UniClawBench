#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
STATE_DIR="/tmp_workspace/clawbench/service_state"
mkdir -p "$STATE_DIR" /tmp_workspace/results/gui_evidence
APT_OPTS=(-o Acquire::Retries=1 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
apt_refresh() { timeout 90s apt-get "${APT_OPTS[@]}" update -qq || true; }
apt_install() { timeout 240s apt-get "${APT_OPTS[@]}" install -y --no-install-recommends "$@" || true; }
if ! command -v thunar >/dev/null 2>&1 || ! command -v ristretto >/dev/null 2>&1 || ! command -v libreoffice >/dev/null 2>&1; then
  apt_refresh
  apt_install \
    thunar ristretto evince \
    libreoffice-calc libreoffice-writer libreoffice-gtk3 \
    dbus-x11 xdg-utils xdotool wmctrl scrot python3 python3-pip \
    fonts-noto-cjk fonts-liberation
fi
python3 - <<'PY'
import json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
cmds = {
    "file_manager": ["thunar", "--version"],
    "image_viewer": ["ristretto", "--version"],
    "pdf_viewer": ["evince", "--version"],
    "libreoffice": ["libreoffice", "--version"],
    "localc": ["localc", "--version"],
    "lowriter": ["lowriter", "--version"],
}
state = {"task_id": "task_105_36_receipt_packet_gui_audit", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "apps": {}}
for name, cmd in cmds.items():
    exe = shutil.which(cmd[0])
    entry = {"command": cmd[0], "path": exe}
    if exe:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        entry["returncode"] = p.returncode
        entry["version_output"] = p.stdout.strip().splitlines()[:3]
    state["apps"][name] = entry
Path("/tmp_workspace/clawbench/service_state/receipt_gui_setup_task_105_36.json").write_text(json.dumps(state, indent=2) + "\n")
PY
