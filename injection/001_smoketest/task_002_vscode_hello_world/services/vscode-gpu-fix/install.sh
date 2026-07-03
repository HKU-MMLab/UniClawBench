#!/usr/bin/env bash
# Task-local fix for the "window terminated unexpectedly (reason:
# clean-exit, code: 0)" pop-up that Electron renderers throw when
# running on a headless Xvfb in a container without GPU access.
#
# We preseed VSCode's first-launch argv.json so that whenever the
# executor eventually launches `code`, Electron disables hardware
# acceleration, the GPU sandbox, and the crash reporter. These are
# exactly the flags that let VSCode run smoothly on a fresh WSL /
# rootless container with only Xvfb for a display server.
#
# Kept as a task-local service (NOT in docker/ or /opt/) because this
# is specific to THIS task which installs VSCode — no reason to
# saddle every container in the fleet with VSCode-specific defaults.
#
# Invoked by lib/runner.py:start_services as:
#   nohup bash -lc "bash install.sh" >/tmp_workspace/clawbench/logs/vscode-gpu-fix.log 2>&1 </dev/null &
# cwd at invocation is the docker-cp'd service dir under
# /opt/clawbench/runtime/services/task_002_vscode_hello_world/vscode-gpu-fix/
#
# The script is one-shot: exit 0 and the container keeps running, the
# executor starts afterward and sees the preseeded config.

set -euo pipefail

TARGET_DIR="${HOME:-/root}/.config/Code/User"
TARGET_FILE="${TARGET_DIR}/argv.json"

mkdir -p "${TARGET_DIR}"

cat > "${TARGET_FILE}" <<'JSON'
{
  "disable-hardware-acceleration": true,
  "disable-gpu-sandbox": true,
  "enable-crash-reporter": false,
  "disable-color-correct-rendering": true
}
JSON

chmod 0644 "${TARGET_FILE}"

echo "[vscode-gpu-fix] preseeded ${TARGET_FILE}:"
cat "${TARGET_FILE}"
echo "[vscode-gpu-fix] done"
