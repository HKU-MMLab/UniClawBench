#!/usr/bin/env bash
# Auto-install step for task_003_jq_json_query.
# Invoked by lib/runner.py:start_services via:
#   nohup bash -lc "bash install.sh" >/tmp_workspace/clawbench/logs/jq-installer.log 2>&1 </dev/null &
# cwd at invocation is
#   /opt/clawbench/runtime/services/task_003_jq_json_query/jq-installer/
# which is where docker cp landed this directory (with jq-linux64 alongside).
#
# The script is one-shot: exiting 0 is fine — the container keeps running
# and the executor starts afterward. Any non-zero exit just surfaces in
# the logs; the installer refuses to claim success if jq is missing.
set -euo pipefail

echo "[jq-installer] cwd=$(pwd)"
ls -la

# 1. Verify the binary was shipped via the services/ injection channel.
if [ ! -f ./jq-linux64 ]; then
  echo "[jq-installer] ERROR: jq-linux64 not found in service dir" >&2
  exit 1
fi

# 2. Install to /usr/local/bin so the executor can discover it via PATH.
#    `install` sets mode 0755 regardless of git's recorded execute bit.
install -m 0755 ./jq-linux64 /usr/local/bin/jq

# 3. Self-verify — refuse to claim success if the install didn't land on
#    an executable PATH entry.
installed_path=$(command -v jq || true)
if [ -z "$installed_path" ]; then
  echo "[jq-installer] ERROR: /usr/local/bin not on PATH, or install failed" >&2
  exit 1
fi

echo "[jq-installer] jq installed at $installed_path"
jq --version
echo "[jq-installer] done"
