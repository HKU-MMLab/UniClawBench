#!/usr/bin/env bash
# One-shot setup for the real Zotero + Obsidian GUI workflow.

set -euo pipefail

MARKER_DIR="/tmp_workspace/clawbench/service_state"
STATE_JSON="${MARKER_DIR}/zotero-obsidian-ready.json"
LOG_PREFIX="[zotero-obsidian-setup]"
ZOTERO_URL="https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64"
OBSIDIAN_API="https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"

mkdir -p "${MARKER_DIR}" /tmp_workspace/results

write_state() {
  local status="$1"
  local message="$2"
  python3 - "$status" "$message" <<'PY'
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

status, message = sys.argv[1], sys.argv[2]
state_path = Path("/tmp_workspace/clawbench/service_state/zotero-obsidian-ready.json")
source_pdf = Path("/tmp_workspace/clawbench/sources/rag_survey_pack/rag_survey.pdf")

def run_text(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=5).strip()
    except Exception:
        return ""

zotero_version = ""
app_ini = Path("/opt/zotero/application.ini")
if app_ini.exists():
    for line in app_ini.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Version="):
            zotero_version = line.split("=", 1)[1].strip()
            break

obsidian_version = run_text(["dpkg-query", "-W", "-f=${Version}", "obsidian"])

data = {
    "status": status,
    "message": message,
    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "applications": {
        "zotero": {
            "command": shutil.which("zotero") or "",
            "install_dir": "/opt/zotero",
            "version": zotero_version,
            "download_url": "https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64",
        },
        "obsidian": {
            "command": shutil.which("obsidian") or "",
            "version": obsidian_version,
            "download_source": "https://github.com/obsidianmd/obsidian-releases/releases/latest",
        },
    },
    "source_pdf": {
        "path": str(source_pdf),
        "exists": source_pdf.exists(),
    },
    "expected_results": [
        "/tmp_workspace/results/rag_survey_note_export.md",
        "/tmp_workspace/results/zotero_rag_survey_export.bib",
        "/tmp_workspace/results/pdf_reader_screenshot.png",
        "/tmp_workspace/results/zotero_record_screenshot.png",
        "/tmp_workspace/results/obsidian_note_screenshot.png",
    ],
}
state_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

install_system_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dbus-x11 \
    desktop-file-utils \
    file \
    jq \
    libasound2t64 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    tar \
    xdg-utils \
    xz-utils
}

install_zotero() {
  if command -v zotero >/dev/null 2>&1 && [ -x /opt/zotero/zotero ]; then
    echo "${LOG_PREFIX} Zotero already present"
    return
  fi

  local archive="/tmp/zotero.tar"
  echo "${LOG_PREFIX} downloading Zotero from official client endpoint"
  curl -fL --retry 3 --retry-delay 2 -o "${archive}" "${ZOTERO_URL}"
  rm -rf /opt/zotero
  mkdir -p /opt
  tar -xf "${archive}" -C /opt
  local extracted
  extracted="$(find /opt -maxdepth 1 -type d -name 'Zotero_linux*' | head -n 1)"
  if [ -z "${extracted}" ]; then
    echo "${LOG_PREFIX} could not find extracted Zotero directory" >&2
    exit 1
  fi
  mv "${extracted}" /opt/zotero
  ln -sf /opt/zotero/zotero /usr/local/bin/zotero
  if [ -x /opt/zotero/set_launcher_icon ]; then
    /opt/zotero/set_launcher_icon || true
  fi
  desktop-file-install --dir=/usr/share/applications /opt/zotero/zotero.desktop || true
}

install_obsidian() {
  if command -v obsidian >/dev/null 2>&1 && dpkg-query -W obsidian >/dev/null 2>&1; then
    echo "${LOG_PREFIX} Obsidian already present"
    return
  fi

  local arch
  arch="$(dpkg --print-architecture)"
  local asset_filter
  case "${arch}" in
    amd64) asset_filter='amd64\.deb$' ;;
    arm64) asset_filter='arm64\.deb$' ;;
    *)
      echo "${LOG_PREFIX} unsupported architecture for Obsidian deb: ${arch}" >&2
      exit 1
      ;;
  esac

  echo "${LOG_PREFIX} resolving latest Obsidian deb from GitHub releases"
  local deb_url
  deb_url="$(
    curl -fsSL --retry 3 --retry-delay 2 "${OBSIDIAN_API}" |
      jq -r --arg re "${asset_filter}" '.assets[] | select(.browser_download_url | test($re)) | .browser_download_url' |
      head -n 1
  )"
  if [ -z "${deb_url}" ] || [ "${deb_url}" = "null" ]; then
    echo "${LOG_PREFIX} could not find Obsidian ${arch} deb in latest GitHub release" >&2
    exit 1
  fi

  local deb="/tmp/obsidian.deb"
  curl -fL --retry 3 --retry-delay 2 -o "${deb}" "${deb_url}"
  apt-get install -y "${deb}"
}

main() {
  write_state "installing" "Installing or verifying real Zotero and Obsidian desktop applications."
  install_system_packages
  install_zotero
  install_obsidian

  if ! command -v zotero >/dev/null 2>&1; then
    write_state "error" "Zotero command was not found after installation."
    exit 1
  fi
  if ! command -v obsidian >/dev/null 2>&1; then
    write_state "error" "Obsidian command was not found after installation."
    exit 1
  fi

  write_state "ready" "Real Zotero and Obsidian are installed and available for the GUI task."
  echo "${LOG_PREFIX} ready state: ${STATE_JSON}"
}

main "$@"
