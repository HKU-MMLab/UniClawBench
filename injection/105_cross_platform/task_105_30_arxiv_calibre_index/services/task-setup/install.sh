#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl wget ca-certificates python3 python3-pip \
    poppler-utils \
    calibre \
    libreoffice libreoffice-calc libreoffice-core \
    scrot imagemagick gnome-screenshot \
    xvfb xauth xdotool \
    fonts-noto-cjk fonts-wqy-zenhei fonts-dejavu-core || true

  # ── Extra LibreOffice scripting bridge so executor can drive macros / GUI
  apt-get install -y --no-install-recommends \
    libreoffice-script-provider-python python3-uno || true

  # Python helpers used by the eval (read/write multi-sheet .ods + image dim check)
  # odfpy: directly author content.xml/styles.xml (formula + conditional-format
  #   + chart object xml fragment) and zip into a real .ods.
  # pyexcel-ods3 / openpyxl: tabular write paths.
  # Pillow: PNG dimension checks.
  pip3 install --break-system-packages pyexcel-ods3 openpyxl odfpy Pillow 2>/dev/null \
    || pip3 install pyexcel-ods3 openpyxl odfpy Pillow 2>/dev/null || true
fi

# ── Start a virtual X display so screenshots / libreoffice GUI work ─
if command -v Xvfb >/dev/null; then
  if ! pgrep -x Xvfb >/dev/null 2>&1; then
    Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
    sleep 1
  fi
  export DISPLAY=:99
  echo 'export DISPLAY=:99' >> /etc/profile.d/xvfb_display.sh 2>/dev/null || true
  echo "[task-setup] Xvfb on DISPLAY=:99"
fi

# ── Prepare output directory ───────────────────────────────────────
mkdir -p /tmp_workspace/results

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in pdfinfo pdftotext pdftoppm calibredb libreoffice soffice scrot import montage convert wget curl jq python3 Xvfb; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo '[task-setup] done'
