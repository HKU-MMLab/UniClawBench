#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
STATE_DIR="/tmp_workspace/clawbench/service_state"
mkdir -p "$STATE_DIR" /tmp_workspace/results/clips
APT_OPTS=(-o Acquire::Retries=1 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
apt_refresh() { timeout 90s apt-get "${APT_OPTS[@]}" update -qq || true; }
apt_install() { timeout 180s apt-get "${APT_OPTS[@]}" install -y --no-install-recommends "$@" || true; }
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1 || ! command -v convert >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  apt_refresh
  apt_install ffmpeg imagemagick jq python3 file ca-certificates
fi
python3 - <<'PY'
import json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
cmds = {"ffmpeg": ["ffmpeg", "-version"], "ffprobe": ["ffprobe", "-version"], "convert": ["convert", "-version"], "jq": ["jq", "--version"]}
state = {"task_id": "task_105_39_nasa_audio_ffmpeg_index", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "apps": {}}
for name, cmd in cmds.items():
    exe = shutil.which(cmd[0])
    state["apps"][name] = {"command": cmd[0], "path": exe}
    if exe:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        state["apps"][name]["returncode"] = p.returncode
        state["apps"][name]["version_output"] = p.stdout.strip().splitlines()[:3]
Path("/tmp_workspace/clawbench/service_state/media_cli_setup_task_105_39.json").write_text(json.dumps(state, indent=2) + "\n")
PY
