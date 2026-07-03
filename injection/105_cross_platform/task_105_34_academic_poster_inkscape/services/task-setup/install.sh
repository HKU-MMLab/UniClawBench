#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs / GUI apps ──────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    wget curl jq ca-certificates \
    git \
    poppler-utils \
    inkscape \
    evince \
    xvfb scrot imagemagick \
    xdotool wmctrl gnome-screenshot \
    xmlstarlet \
    fonts-noto-cjk fonts-wqy-zenhei \
    python3 python3-pil python3-pip || true

  # PDF annotation libraries — pikepdf / pypdf / PyPDF2 — give the executor
  # a programmatic alternative to the GUI annotation tool. Either path is
  # accepted by eval_rule §3.
  pip3 install --break-system-packages pikepdf pypdf PyPDF2 2>/dev/null \
    || pip3 install pikepdf pypdf PyPDF2 2>/dev/null || true
fi

# ── Start Xvfb so headless evince GUI + screenshot work ────────────
if command -v Xvfb >/dev/null; then
  pkill -f 'Xvfb :99' 2>/dev/null || true
  Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
  sleep 1
fi
export DISPLAY=:99

mkdir -p /tmp_workspace/work /tmp_workspace/results

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in wget curl jq git pdfinfo pdftotext pdftocairo pdftoppm \
           inkscape evince xvfb-run scrot Xvfb convert xdotool wmctrl; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo "[task-setup] Xvfb display ready at DISPLAY=:99"
echo '[task-setup] done'
