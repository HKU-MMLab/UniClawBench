#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends imagemagick || true
fi

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input yfinance pandas Pillow matplotlib wand numpy duckdb seaborn plotly || true
fi

if command -v npm >/dev/null 2>&1 && [ -d /root/skills/chart-image/scripts ]; then
  (cd /root/skills/chart-image/scripts && npm install --no-audit --no-fund --silent) || true
fi

echo '[task-setup] done'
