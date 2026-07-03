#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Required CLIs:
#   chromium (headless screenshot of example.com)
#   curl + htmlq (fetch HTML + CSS-selector extraction)
#   unzip + zip (verify .sketch ZIP layout)
#   nodejs (>=16) + npm (sketch-cli is a Node.js package)
#   git (clone HKUDS/CLI-Anything)

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git curl ca-certificates jq unzip zip diffutils \
    python3 python3-pip imagemagick \
    chromium chromium-driver \
    fonts-noto-cjk fonts-wqy-zenhei fonts-dejavu-core || true

  # Pillow gives executors a fast PNG dimension-check option (eval also
  # uses it). Non-fatal if pip is locked.
  pip3 install --break-system-packages Pillow 2>/dev/null \
    || pip3 install Pillow 2>/dev/null || true

  # Node.js: prefer distro nodejs >=16; if too old, install via NodeSource.
  NODE_OK=0
  if command -v node >/dev/null; then
    NODE_MAJOR=$(node -e 'console.log(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)
    if [ "${NODE_MAJOR:-0}" -ge 16 ]; then NODE_OK=1; fi
  fi
  if [ "$NODE_OK" -eq 0 ]; then
    apt-get install -y --no-install-recommends nodejs npm 2>/dev/null || true
    if command -v node >/dev/null; then
      NODE_MAJOR=$(node -e 'console.log(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)
      if [ "${NODE_MAJOR:-0}" -ge 16 ]; then NODE_OK=1; fi
    fi
  fi
  if [ "$NODE_OK" -eq 0 ]; then
    # Fallback to NodeSource 20.x setup script for Debian/Ubuntu.
    if curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/setup_node.sh 2>/dev/null; then
      bash /tmp/setup_node.sh >/dev/null 2>&1 || true
      apt-get install -y --no-install-recommends nodejs 2>/dev/null || true
    fi
  fi

  # htmlq — Rust binary for CSS-selector HTML extraction.
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

# ── Clone + install sketch-cli (HKUDS/CLI-Anything) ────────────────
SKETCH_DIR=/opt/cli-anything
if [ ! -d "$SKETCH_DIR/.git" ]; then
  git clone --depth 1 https://github.com/HKUDS/CLI-Anything.git "$SKETCH_DIR" 2>/dev/null || true
fi
if [ -d "$SKETCH_DIR/sketch/agent-harness" ] && command -v npm >/dev/null; then
  (cd "$SKETCH_DIR/sketch/agent-harness" && npm install --no-audit --no-fund --silent 2>/dev/null) || \
  (cd "$SKETCH_DIR/sketch/agent-harness" && npm install --no-audit --no-fund 2>&1 | tail -5) || true
fi

# Pre-create result directories so the executor can write right away.
mkdir -p /tmp_workspace/results /tmp_workspace/work

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in curl unzip zip jq python3 chromium node npm htmlq git; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

if [ -f "$SKETCH_DIR/sketch/agent-harness/src/cli.js" ]; then
  echo "[task-setup] sketch-cli ready at $SKETCH_DIR/sketch/agent-harness/src/cli.js"
else
  echo "[task-setup] WARNING: sketch-cli not found under $SKETCH_DIR" >&2
fi

echo '[task-setup] done'
