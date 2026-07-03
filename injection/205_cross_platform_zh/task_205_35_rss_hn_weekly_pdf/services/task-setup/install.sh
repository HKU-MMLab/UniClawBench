#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs / GUI apps ──────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    curl wget jq ca-certificates \
    newsboat \
    pandoc texlive-xetex texlive-fonts-recommended \
    poppler-utils \
    evince \
    xvfb scrot imagemagick \
    xmlstarlet \
    fonts-noto-cjk fonts-wqy-zenhei \
    python3 python3-pip || true

  # python feedparser as a fallback RSS parser (newsboat is fiddly headless)
  pip3 install --break-system-packages feedparser 2>/dev/null \
    || pip3 install feedparser 2>/dev/null || true

  # ── htmlq (mgdm/htmlq) — XML/HTML tag-extractor used by the executor
  if ! command -v htmlq >/dev/null; then
    arch="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
    case "$arch" in
      amd64) htmlq_arch=x86_64-linux ;;
      arm64) htmlq_arch=x86_64-linux ;;  # no native arm64 release — x86_64 binary works under qemu in most CI envs
      *)     htmlq_arch=x86_64-linux ;;
    esac
    tmp="$(mktemp -d)"
    if wget -qO "$tmp/htmlq.tar.gz" \
         "https://github.com/mgdm/htmlq/releases/download/v0.4.0/htmlq-${htmlq_arch}.tar.gz"; then
      tar -xzf "$tmp/htmlq.tar.gz" -C "$tmp" htmlq 2>/dev/null || true
      install -m 0755 "$tmp/htmlq" /usr/local/bin/htmlq 2>/dev/null || true
    fi
    rm -rf "$tmp"
  fi
fi

# ── Pre-populate ~/.newsboat/urls so `newsboat -x reload` works ───
NEWSBOAT_DIR="${HOME}/.newsboat"
mkdir -p "$NEWSBOAT_DIR"
cat >"$NEWSBOAT_DIR/urls" <<'EOF'
https://news.ycombinator.com/rss
https://lobste.rs/rss
https://feeds.arstechnica.com/arstechnica/index
https://feeds.feedburner.com/TheHackersNews
https://www.wired.com/feed/rss
EOF
chmod 600 "$NEWSBOAT_DIR/urls" 2>/dev/null || true

# ── Start Xvfb so headless evince GUI + screenshot work ────────────
if command -v Xvfb >/dev/null; then
  pkill -f 'Xvfb :99' 2>/dev/null || true
  Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
  sleep 1
fi
export DISPLAY=:99

mkdir -p /tmp_workspace/work /tmp_workspace/results

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in curl jq newsboat pandoc xelatex pdfinfo pdftotext pdfimages \
           evince xvfb-run scrot Xvfb convert htmlq xmlstarlet; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo "[task-setup] Xvfb display ready at DISPLAY=:99"
echo '[task-setup] done'
