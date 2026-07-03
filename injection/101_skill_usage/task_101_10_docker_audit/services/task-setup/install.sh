#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input bandit semgrep safety || true
fi

echo '[task-setup] done'
