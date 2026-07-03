#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu || true
fi

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input pytesseract Pillow || true
fi

# ocr-local skill depends on node + tesseract.js (Tesseract.js, a wasm OCR engine).
# node/npm are preinstalled in the base image; pdfjs-dist/tesseract.js are not.
if command -v npm >/dev/null 2>&1 && [ -d /root/skills/ocr-local ]; then
  (cd /root/skills/ocr-local && npm install --no-audit --no-fund --silent tesseract.js) || true
fi

echo '[task-setup] done'
