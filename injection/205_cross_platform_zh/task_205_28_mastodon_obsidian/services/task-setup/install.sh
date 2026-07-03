#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl wget ca-certificates gnupg python3 python3-pip pandoc \
    nodejs npm \
    chromium chromium-browser \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libasound2 \
    imagemagick \
    fonts-noto-cjk fonts-wqy-zenhei || true

  # toot — Mastodon CLI
  if ! command -v toot >/dev/null; then
    pip3 install --break-system-packages toot 2>/dev/null \
      || pip3 install toot 2>/dev/null || true
  fi

  # mermaid-cli (mmdc)
  if ! command -v mmdc >/dev/null; then
    npm install -g @mermaid-js/mermaid-cli 2>/dev/null || true
  fi

  # htmlq — Rust binary for CSS-selector HTML parsing.
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

  # pup as a fallback
  if ! command -v pup >/dev/null && ! command -v htmlq >/dev/null; then
    PUP_ZIP="/tmp/pup.zip"
    if curl -fsSL -o "$PUP_ZIP" \
        "https://github.com/ericchiang/pup/releases/download/v0.4.0/pup_v0.4.0_linux_amd64.zip" 2>/dev/null; then
      unzip -o "$PUP_ZIP" -d /usr/local/bin/ 2>/dev/null || true
      chmod +x /usr/local/bin/pup 2>/dev/null || true
      rm -f "$PUP_ZIP"
    fi
  fi
fi

# ── puppeteer config so mmdc finds chromium without sandbox ────────
PUPPETEER_CFG="${HOME}/.puppeteer-config.json"
mkdir -p "$(dirname "$PUPPETEER_CFG")"
CHROME_BIN=""
for c in chromium chromium-browser google-chrome; do
  if command -v "$c" >/dev/null; then CHROME_BIN="$(command -v "$c")"; break; fi
done
if [ -n "$CHROME_BIN" ]; then
  cat >"$PUPPETEER_CFG" <<JSON
{ "executablePath": "${CHROME_BIN}", "args": ["--no-sandbox", "--disable-setuid-sandbox"] }
JSON
  echo "[task-setup] puppeteer-config written; chromium=${CHROME_BIN}"
fi

# ── Configure toot from MASTODON_* env vars ────────────────────────
INSTANCE="${MASTODON_INSTANCE:-mastodon.social}"
HANDLE="${MASTODON_HANDLE:-}"
TOKEN="${MASTODON_ACCESS_TOKEN:-}"
CID="${MASTODON_CLIENT_ID:-}"
CSEC="${MASTODON_CLIENT_SECRET:-}"

if [ -n "$TOKEN" ] && [ -n "$HANDLE" ]; then
  CONFIG_DIR="${HOME}/.config/toot"
  mkdir -p "$CONFIG_DIR"
  USER_KEY="${HANDLE}@${INSTANCE}"
  cat >"${CONFIG_DIR}/config.json" <<JSON
{
  "apps": {
    "${INSTANCE}": {
      "instance": "${INSTANCE}",
      "base_url": "https://${INSTANCE}",
      "client_id": "${CID}",
      "client_secret": "${CSEC}"
    }
  },
  "users": {
    "${USER_KEY}": {
      "instance": "${INSTANCE}",
      "username": "${HANDLE}",
      "access_token": "${TOKEN}"
    }
  },
  "active_user": "${USER_KEY}"
}
JSON
  chmod 600 "${CONFIG_DIR}/config.json"
  echo "[task-setup] toot configured for ${USER_KEY}"
else
  echo "[task-setup] WARNING: MASTODON_ACCESS_TOKEN or MASTODON_HANDLE unset; toot CLI will not be authenticated (public read API still works via curl)" >&2
fi

# Pre-create result and work directories.
mkdir -p /tmp_workspace/work/url_pages /tmp_workspace/work/og_images \
         /tmp_workspace/work/contexts \
         /tmp_workspace/results/vault /tmp_workspace/results/thumbs \
         /tmp_workspace/results/media

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in toot pandoc curl wget jq python3 mmdc magick; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

if command -v htmlq >/dev/null; then
  echo "[task-setup] htmlq available"
elif command -v pup >/dev/null; then
  echo "[task-setup] pup available (htmlq fallback)"
else
  echo "[task-setup] WARNING: neither htmlq nor pup is installed" >&2
fi

echo '[task-setup] done'
