#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
# imagemagick → `convert` for the 4-panel language_bars composite.
# pandoc + texlive-xetex + fonts-noto-cjk → CJK-capable comparison.pdf.
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl wget ca-certificates gnupg python3 python3-pip \
    nodejs npm chromium chromium-sandbox \
    imagemagick pandoc texlive-xetex texlive-fonts-recommended \
    fonts-noto-cjk fonts-noto-cjk-extra poppler-utils || true
fi

# ── mermaid-cli (mmdc) for PNG rendering ───────────────────────────
if ! command -v mmdc >/dev/null; then
  npm install -g @mermaid-js/mermaid-cli 2>&1 | tail -5 || true
fi

# Puppeteer config to use system chromium with --no-sandbox so it works
# in containerised executor environments
cat >/tmp/puppeteer-config.json <<'EOF'
{
  "executablePath": "/usr/bin/chromium",
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
}
EOF
echo "[task-setup] puppeteer config at /tmp/puppeteer-config.json"
echo "[task-setup] use mmdc with: mmdc -p /tmp/puppeteer-config.json -i in.mmd -o out.png"

# ── ImageMagick policy: allow PDF/PNG read-write in container ─────
# Some apt builds ship a policy.xml that blocks PNG write inside
# scripted contexts. Loosen the policy for the executor.
for policy in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do
  if [ -f "$policy" ]; then
    sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' "$policy" 2>/dev/null || true
    sed -i 's/rights="none" pattern="PNG"/rights="read|write" pattern="PNG"/' "$policy" 2>/dev/null || true
  fi
done

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in jq curl wget python3 mmdc convert pandoc xelatex pdfinfo; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo '[task-setup] done'
