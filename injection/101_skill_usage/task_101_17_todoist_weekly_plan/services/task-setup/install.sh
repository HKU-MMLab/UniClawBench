#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input requests feedparser slack_sdk notion-client pyairtable || true
fi

if command -v npm >/dev/null 2>&1; then
  npm install -g --no-audit --no-fund --silent todoist-ts-cli@^0.2.0 || true
fi

echo '[task-setup] done'
