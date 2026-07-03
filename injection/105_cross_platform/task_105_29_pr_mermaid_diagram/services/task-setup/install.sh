#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl wget ca-certificates gnupg python3 python3-pip nodejs npm \
    pandoc texlive-xetex texlive-fonts-recommended \
    imagemagick \
    chromium chromium-browser \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libasound2 \
    fonts-noto-cjk fonts-wqy-zenhei || true

  # gh CLI (GitHub)
  if ! command -v gh >/dev/null; then
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null 2>&1 || true
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg 2>/dev/null || true
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      >/etc/apt/sources.list.d/github-cli.list
    apt-get update -qq || true
    apt-get install -y --no-install-recommends gh || true
  fi

  # mermaid-cli (mmdc)
  if ! command -v mmdc >/dev/null; then
    npm install -g @mermaid-js/mermaid-cli 2>/dev/null || true
  fi
fi

# ── Authenticate gh with GITHUB_TOKEN from .privacy ────────────────
if [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null \
    || GH_TOKEN="$GITHUB_TOKEN" gh auth status 2>&1 || true
  echo "[task-setup] gh authenticated with GITHUB_TOKEN"
else
  echo "[task-setup] WARNING: GITHUB_TOKEN unset; gh will be rate-limited to 60 req/hr" >&2
fi

# ── puppeteer config so mmdc finds chromium without sandbox ────────
PUPPETEER_CFG="${HOME}/.puppeteerrc.json"
mkdir -p "$(dirname "$PUPPETEER_CFG")"
CHROME_BIN=""
for c in chromium chromium-browser google-chrome; do
  if command -v "$c" >/dev/null; then CHROME_BIN="$(command -v "$c")"; break; fi
done
if [ -n "$CHROME_BIN" ]; then
  cat >"${HOME}/.puppeteer-config.json" <<JSON
{ "executablePath": "${CHROME_BIN}", "args": ["--no-sandbox", "--disable-setuid-sandbox"] }
JSON
  echo "[task-setup] puppeteer-config written; chromium=${CHROME_BIN}"
else
  echo "[task-setup] WARNING: chromium not found; mmdc will likely fail" >&2
fi

# Pre-create result directory.
mkdir -p /tmp_workspace/results

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in gh mmdc npm jq curl wget git pandoc xelatex magick; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo '[task-setup] done'
