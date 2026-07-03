#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/tmp_workspace/clawbench/service_state"
STATE_JSON="${STATE_DIR}/real_rag_gui_apps_task_105_07.json"
TMP_DIR="/tmp/clawbench-real-rag-apps-105-07"
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

install_zotero() {
  if [ -x /opt/zotero/zotero ] && command -v zotero >/dev/null 2>&1; then
    return 0
  fi
  apt_install curl ca-certificates tar xz-utils bzip2 libdbus-glib-1-2
  local archive="${TMP_DIR}/zotero.tar"
  curl -fL --retry 3 \
    "https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64" \
    -o "${archive}"
  rm -rf "${TMP_DIR}/zotero_extract" /opt/zotero
  mkdir -p "${TMP_DIR}/zotero_extract"
  tar -xf "${archive}" -C "${TMP_DIR}/zotero_extract"
  local top
  top="$(find "${TMP_DIR}/zotero_extract" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  mv "${top}" /opt/zotero
  ln -sf /opt/zotero/zotero /usr/local/bin/zotero
}

install_obsidian() {
  if command -v obsidian >/dev/null 2>&1; then
    return 0
  fi
  apt_install curl ca-certificates python3
  local deb="${TMP_DIR}/obsidian-amd64.deb"
  local url
  url="$(python3 - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest", timeout=30) as response:
    data = json.load(response)
for asset in data.get("assets", []):
    name = asset.get("name", "")
    if name.endswith("_amd64.deb") or name.endswith("amd64.deb"):
        print(asset["browser_download_url"])
        break
else:
    raise SystemExit("No Obsidian amd64 deb asset found")
PY
)"
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
  evince \
  libreoffice-calc \
  libreoffice-writer \
  libreoffice-gtk3 \
  mousepad

install_zotero
install_obsidian

python3 - <<'PY'
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

state_path = Path("/tmp_workspace/clawbench/service_state/real_rag_gui_apps_task_105_07.json")
commands = {
    "pdf_reader": ["evince", "--version"],
    "zotero": ["zotero", "--version"],
    "obsidian": ["obsidian", "--version"],
    "libreoffice": ["libreoffice", "--version"],
    "localc": ["localc", "--version"],
    "lowriter": ["lowriter", "--version"],
}
state = {
    "service": "real-rag-gui-apps-setup",
    "task_id": "task_105_07_rag_evaluation_gui_full_stack",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
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
