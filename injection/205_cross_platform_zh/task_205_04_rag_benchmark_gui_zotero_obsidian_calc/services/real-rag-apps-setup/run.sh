#!/usr/bin/env bash
# One-shot setup for the real Zotero, Obsidian, and LibreOffice Calc workflow.
# The script is intentionally idempotent. It installs missing desktop apps,
# verifies their launchers, and writes a JSON state file for task auditing.

set -euo pipefail

MARKER_DIR="/tmp_workspace/clawbench/service_state"
RESULTS_DIR="/tmp_workspace/results"
STATE_JSON="${MARKER_DIR}/task_105_04_real_apps_state.json"
LOG_PREFIX="[task_105_04_real_apps]"

mkdir -p "${MARKER_DIR}" "${RESULTS_DIR}" /tmp/task_105_04_downloads

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))'
}

write_state() {
  local status="$1"
  local message="$2"
  local zotero_path obsidian_path calc_path libreoffice_path
  local zotero_version obsidian_version libreoffice_version

  zotero_path="$(command -v zotero || true)"
  obsidian_path="$(command -v obsidian || true)"
  calc_path="$(command -v localc || true)"
  libreoffice_path="$(command -v libreoffice || true)"

  zotero_version="$(zotero --version 2>/dev/null | head -n 1 || true)"
  obsidian_version="$(obsidian --version 2>/dev/null | head -n 1 || true)"
  libreoffice_version="$(libreoffice --version 2>/dev/null | head -n 1 || true)"

  cat > "${STATE_JSON}" <<EOF
{
  "task_id": "task_105_04_rag_benchmark_gui_zotero_obsidian_calc",
  "status": $(printf '%s' "${status}" | json_escape),
  "message": $(printf '%s' "${message}" | json_escape),
  "checked_at_utc": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "applications": {
    "zotero": {
      "required": true,
      "command": "zotero",
      "path": $(printf '%s' "${zotero_path}" | json_escape),
      "version": $(printf '%s' "${zotero_version}" | json_escape)
    },
    "obsidian": {
      "required": true,
      "command": "obsidian",
      "path": $(printf '%s' "${obsidian_path}" | json_escape),
      "version": $(printf '%s' "${obsidian_version}" | json_escape)
    },
    "libreoffice_calc": {
      "required": true,
      "command": "localc",
      "path": $(printf '%s' "${calc_path}" | json_escape),
      "libreoffice_path": $(printf '%s' "${libreoffice_path}" | json_escape),
      "version": $(printf '%s' "${libreoffice_version}" | json_escape)
    }
  },
  "expected_results_dir": "${RESULTS_DIR}"
}
EOF
}

install_base_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dbus-x11 \
    file \
    libasound2t64 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libsecret-1-0 \
    libreoffice-calc \
    libreoffice-gtk3 \
    pcmanfm \
    python3 \
    unzip \
    wget \
    xdg-utils \
    xdotool \
    wmctrl
}

install_zotero() {
  if command -v zotero >/dev/null 2>&1; then
    echo "${LOG_PREFIX} Zotero already present"
    return 0
  fi

  echo "${LOG_PREFIX} installing Zotero from zotero.org"
  local archive="/tmp/task_105_04_downloads/zotero.tar"
  curl -L --fail --retry 3 \
    "https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64" \
    -o "${archive}"

  rm -rf /opt/zotero
  mkdir -p /opt/zotero
  tar -xf "${archive}" --strip-components=1 -C /opt/zotero
  ln -sf /opt/zotero/zotero /usr/local/bin/zotero
  if [[ -x /opt/zotero/set_launcher_icon ]]; then
    /opt/zotero/set_launcher_icon || true
  fi
}

install_obsidian() {
  if command -v obsidian >/dev/null 2>&1; then
    echo "${LOG_PREFIX} Obsidian already present"
    return 0
  fi

  echo "${LOG_PREFIX} installing Obsidian from the official GitHub release"
  local deb="/tmp/task_105_04_downloads/obsidian.deb"
  local url
  url="$(python3 - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest", timeout=30) as response:
    release = json.load(response)

for asset in release.get("assets", []):
    name = asset.get("name", "")
    if name.endswith("_amd64.deb"):
        print(asset["browser_download_url"])
        break
else:
    raise SystemExit("No amd64 .deb asset found for latest Obsidian release")
PY
)"
  curl -L --fail --retry 3 "${url}" -o "${deb}"
  apt-get install -y --no-install-recommends "${deb}"
}

verify_apps() {
  command -v zotero >/dev/null 2>&1
  command -v obsidian >/dev/null 2>&1
  command -v libreoffice >/dev/null 2>&1
  command -v localc >/dev/null 2>&1
  file "$(command -v zotero)" >/dev/null
  file "$(command -v obsidian)" >/dev/null
  libreoffice --version >/dev/null 2>&1
}

main() {
  write_state "running" "Installing and verifying real desktop applications."
  install_base_packages
  install_zotero
  install_obsidian
  verify_apps
  write_state "ready" "Real Zotero, Obsidian, and LibreOffice Calc are installed and command launchers were verified."
  echo "${LOG_PREFIX} wrote ${STATE_JSON}"
}

if ! main; then
  write_state "failed" "Setup failed before all real applications could be verified."
  exit 1
fi
