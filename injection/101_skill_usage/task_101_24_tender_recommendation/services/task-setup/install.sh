#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-chi-sim || true
fi

if command -v pip >/dev/null; then
  pip install --break-system-packages --quiet --no-input pymupdf pdfminer.six reportlab pytesseract Pillow yfinance pandas httpx || true
fi

echo '[task-setup] done'
