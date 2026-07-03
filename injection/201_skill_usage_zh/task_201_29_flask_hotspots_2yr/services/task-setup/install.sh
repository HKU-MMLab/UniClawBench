#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends git jq curl || true
fi

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input \
    gitpython pydriller radon tabulate jinja2 click reportlab pyyaml || true
fi

echo '[task-setup] done'
