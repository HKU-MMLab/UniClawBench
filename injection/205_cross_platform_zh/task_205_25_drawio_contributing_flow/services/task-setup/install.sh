#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Base CLI tooling ──────────────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl wget ca-certificates gnupg \
    python3 python3-pip python3-venv \
    librsvg2-bin imagemagick \
    fonts-noto-cjk fonts-wqy-zenhei || true

  # gh CLI (GitHub) — needed to fetch CONTRIBUTING.md at a pinned tag
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
fi

# ── Authenticate gh with GITHUB_TOKEN from .privacy ────────────────
if [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null \
    || GH_TOKEN="$GITHUB_TOKEN" gh auth status 2>&1 || true
  echo "[task-setup] gh authenticated with GITHUB_TOKEN"
else
  echo "[task-setup] WARNING: GITHUB_TOKEN unset; gh will be rate-limited" >&2
fi

# ── Install cli-anything-drawio (no API key, pure local Python) ────
# Per HKUDS/CLI-Anything README_CN.md: drawio CLI lives at
#   drawio/agent-harness/  → pip install -e .
# Console entry point becomes `cli-anything-drawio` and operates on
# .drawio (mxGraph XML) files purely locally — no auth needed.
CLIA_DIR=/opt/cli-anything
if [ ! -d "$CLIA_DIR/.git" ]; then
  rm -rf "$CLIA_DIR"
  git clone --depth 1 https://github.com/HKUDS/CLI-Anything.git "$CLIA_DIR" 2>&1 \
    || echo "[task-setup] WARNING: clone CLI-Anything failed" >&2
fi
if [ -d "$CLIA_DIR/drawio/agent-harness" ]; then
  ( cd "$CLIA_DIR/drawio/agent-harness" \
    && pip install --quiet --break-system-packages -e . 2>&1 ) \
    || ( cd "$CLIA_DIR/drawio/agent-harness" && pip install --quiet -e . 2>&1 ) \
    || echo "[task-setup] WARNING: pip install cli-anything-drawio failed" >&2
fi

# ── Optional: draw.io desktop for native PNG export ────────────────
# The Electron AppImage is heavy (~120 MB); skip if unavailable.
# Executor can fall back to SVG via librsvg / ImageMagick on the
# .drawio XML, or accept the .drawio file alone for the eval.
if ! command -v drawio >/dev/null && [ -z "${SKIP_DRAWIO_DESKTOP:-}" ]; then
  DRAWIO_DEB_URL="https://github.com/jgraph/drawio-desktop/releases/download/v24.7.17/drawio-amd64-24.7.17.deb"
  DEB_PATH=/tmp/drawio.deb
  if wget --tries=1 --timeout=20 -qO "$DEB_PATH" "$DRAWIO_DEB_URL" 2>&1; then
    apt-get install -y --no-install-recommends "$DEB_PATH" 2>&1 \
      || dpkg -i "$DEB_PATH" 2>&1 \
      || echo "[task-setup] draw.io desktop install failed; .drawio + librsvg fallback only" >&2
    rm -f "$DEB_PATH"
  else
    echo "[task-setup] draw.io desktop deb fetch skipped (no network); fallback to local renderers" >&2
  fi
fi

# Pre-create result directory.
mkdir -p /tmp_workspace/results

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in gh git python3 pip jq curl wget rsvg-convert; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done
if command -v cli-anything-drawio >/dev/null; then
  echo "[task-setup] cli-anything-drawio: $(command -v cli-anything-drawio)"
else
  echo "[task-setup] WARNING: cli-anything-drawio not on PATH" >&2
fi

echo '[task-setup] done'
