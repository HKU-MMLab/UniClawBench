#!/usr/bin/env bash
# One-shot task-local setup for the GUI receipt workflow.
# The runner starts services before the executor begins. This script is safe
# to run more than once and leaves marker files the executor may inspect.

set -euo pipefail

MARKER_DIR="/tmp_workspace/clawbench/service_state"
READY_MARKER="${MARKER_DIR}/libreoffice-gui-ready"
STATE_JSON="${MARKER_DIR}/libreoffice-gui-setup.json"
LOG_PREFIX="[libreoffice-gui-setup]"

mkdir -p "${MARKER_DIR}" /tmp_workspace/results/gui_evidence

export DEBIAN_FRONTEND=noninteractive

packages=(
  libreoffice-calc
  libreoffice-writer
  libreoffice-gtk3
  dbus-x11
  xdg-utils
  xdotool
  wmctrl
  pcmanfm
  eog
  xvfb
  xauth
  openbox
  procps
)

echo "${LOG_PREFIX} installing LibreOffice Calc/Writer, file manager, image viewer, and GUI helpers"
apt-get update
apt-get install -y --no-install-recommends "${packages[@]}"

command_status() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    printf "true"
  else
    printf "false"
  fi
}

version_for() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    "${name}" --version 2>&1 | head -n 1 | sed 's/"/\\"/g'
  else
    printf "missing"
  fi
}

run_x11_launch_check() {
  local app_name="$1"
  local cmd="$2"

  if xvfb-run -a bash -lc "openbox >/tmp/${app_name}.openbox.log 2>&1 & ${cmd}" >"${MARKER_DIR}/${app_name}.launch.log" 2>&1; then
    printf "pass"
  else
    printf "fail"
  fi
}

echo "${LOG_PREFIX} installed versions:"
libreoffice --version || true
pcmanfm --version || true
eog --version || true

calc_launch="$(run_x11_launch_check calc 'timeout 45s libreoffice --calc --terminate_after_init --nofirststartwizard --norestore || test $? -eq 124')"
writer_launch="$(run_x11_launch_check writer 'timeout 45s libreoffice --writer --terminate_after_init --nofirststartwizard --norestore || test $? -eq 124')"
file_manager_launch="$(run_x11_launch_check file-manager 'timeout 12s pcmanfm --no-desktop /tmp_workspace/clawbench/sources/receipts/week_32 || test $? -eq 124')"
image_viewer_launch="$(run_x11_launch_check image-viewer 'timeout 12s eog /tmp_workspace/clawbench/sources/receipts/week_32/receipt_01.jpg || test $? -eq 124')"

installed_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
status="ready"
if [[ "${calc_launch}" != "pass" || "${writer_launch}" != "pass" || "${file_manager_launch}" != "pass" || "${image_viewer_launch}" != "pass" ]]; then
  status="degraded"
fi

cat > "${STATE_JSON}" <<EOF
{
  "task_id": "task_105_02_week32_receipts_gui_calc_writer",
  "status": "${status}",
  "installed_at": "${installed_at}",
  "ready_marker": "${READY_MARKER}",
  "packages_requested": [
    "libreoffice-calc",
    "libreoffice-writer",
    "libreoffice-gtk3",
    "dbus-x11",
    "xdg-utils",
    "xdotool",
    "wmctrl",
    "pcmanfm",
    "eog",
    "xvfb",
    "xauth",
    "openbox",
    "procps"
  ],
  "commands": {
    "libreoffice": $(command_status libreoffice),
    "localc": $(command_status localc),
    "lowriter": $(command_status lowriter),
    "pcmanfm": $(command_status pcmanfm),
    "eog": $(command_status eog),
    "xvfb-run": $(command_status xvfb-run),
    "openbox": $(command_status openbox)
  },
  "versions": {
    "libreoffice": "$(version_for libreoffice)",
    "pcmanfm": "$(version_for pcmanfm)",
    "eog": "$(version_for eog)"
  },
  "launch_checks": {
    "calc": "${calc_launch}",
    "writer": "${writer_launch}",
    "file_manager": "${file_manager_launch}",
    "image_viewer": "${image_viewer_launch}"
  },
  "expected_gui_evidence_dir": "/tmp_workspace/results/gui_evidence"
}
EOF

date -u +"%Y-%m-%dT%H:%M:%SZ" > "${READY_MARKER}"
echo "${LOG_PREFIX} service state: ${STATE_JSON}"
echo "${LOG_PREFIX} ready marker: ${READY_MARKER}"
