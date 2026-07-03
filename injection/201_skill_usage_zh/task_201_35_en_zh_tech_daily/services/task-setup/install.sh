#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends jq curl || true
fi

if command -v pip >/dev/null; then
  # Offline task — only RSS / news / repo snapshot parsing libs needed.
  pip install --break-system-packages --quiet --no-input requests feedparser || true
fi

echo '[task-setup] done'
