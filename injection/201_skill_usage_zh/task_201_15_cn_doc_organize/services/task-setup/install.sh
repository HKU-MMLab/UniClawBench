#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if ! command -v pandoc >/dev/null; then
  apt-get update -qq >/dev/null
  apt-get install -y -qq pandoc >/dev/null
fi

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input python-docx openpyxl python-pptx pandas defusedxml || true
fi

echo '[task-setup] done'
