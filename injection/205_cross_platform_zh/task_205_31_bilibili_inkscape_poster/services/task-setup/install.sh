#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
# This task is browser-driven for Bilibili (the user explicitly
# requested it). Required CLIs:
#   chromium + chromium-driver (headless screenshots + page render)
#   curl, jq                    (HTML fetch + JSON parsing)
#   htmlq                       (CSS-selector HTML extraction)
#   inkscape                    (composite SVG poster + PNG export)
#   imagemagick                 (PNG dimension verification, fallback)
#   xvfb                        (virtual display so inkscape GUI works)
#   python3 + Pillow            (PNG dimension inspection)
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl ca-certificates gnupg python3 python3-pip \
    inkscape imagemagick scrot xdotool gnome-screenshot \
    chromium chromium-driver \
    eog libimage-exiftool-perl ffmpeg \
    xvfb xauth unzip \
    fonts-noto-cjk fonts-wqy-zenhei fonts-dejavu-core || true

  # Pillow for PNG dimension inspection.
  pip3 install --break-system-packages Pillow 2>/dev/null \
    || pip3 install Pillow 2>/dev/null || true

  # htmlq — Rust binary for CSS-selector HTML extraction. Required for
  # the browser-driven Bilibili scrape leg (parse <meta itemprop=...>
  # tags out of the rendered HTML).
  if ! command -v htmlq >/dev/null; then
    HTMLQ_VER="v0.4.0"
    HTMLQ_TGZ="/tmp/htmlq.tar.gz"
    if curl -fsSL -o "$HTMLQ_TGZ" \
        "https://github.com/mgdm/htmlq/releases/download/${HTMLQ_VER}/htmlq-x86_64-linux.tar.gz" 2>/dev/null; then
      tar -xzf "$HTMLQ_TGZ" -C /usr/local/bin/ htmlq 2>/dev/null || true
      chmod +x /usr/local/bin/htmlq 2>/dev/null || true
      rm -f "$HTMLQ_TGZ"
    fi
  fi
fi

# ── Start a virtual X display so inkscape GUI / screenshots work ───
if command -v Xvfb >/dev/null; then
  if ! pgrep -x Xvfb >/dev/null 2>&1; then
    Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
    sleep 1
  fi
  export DISPLAY=:99
  echo 'export DISPLAY=:99' >> /etc/profile.d/xvfb_display.sh 2>/dev/null || true
  echo "[task-setup] Xvfb on DISPLAY=:99"
fi

# ── Prepare output directories ─────────────────────────────────────
mkdir -p /tmp_workspace/results/thumbs /tmp_workspace/results/browser_screenshots

# ImageMagick policy on Debian/Ubuntu blocks reading some image
# formats by default (PDF, etc) — ensure JPG/PNG/WEBP read+write are
# allowed (they normally are; this is just defensive).
if [ -f /etc/ImageMagick-6/policy.xml ]; then
  sed -i 's@<policy domain="coder" rights="none" pattern="JPEG"/>@<!-- JPEG enabled -->@' \
    /etc/ImageMagick-6/policy.xml 2>/dev/null || true
fi

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in inkscape chromium curl jq htmlq python3 scrot import display convert ffmpeg Xvfb; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo '[task-setup] done'
