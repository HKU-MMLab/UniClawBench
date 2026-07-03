#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  # Core CLIs + LibreOffice + GUI-control toolchain (xdotool/wmctrl/scrot/
  # gnome-screenshot/imagemagick) — needed because §2 of eval_rule.md now
  # requires a Insert>Chart screenshot taken AFTER driving the LibreOffice
  # Calc GUI under Xvfb. python3-tk + python3-pyautogui are alternative
  # drivers if the executor prefers PyAutoGUI over xdotool.
  apt-get install -y --no-install-recommends \
    git jq curl ca-certificates gnupg python3 python3-pip \
    libreoffice libreoffice-calc libreoffice-core \
    libreoffice-script-provider-python python3-uno \
    scrot xdotool wmctrl imagemagick gnome-screenshot \
    python3-tk python3-pyautogui \
    ffmpeg \
    xvfb xauth \
    fonts-noto-cjk fonts-wqy-zenhei fonts-dejavu-core || true

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

  # yt-dlp (YouTube)
  if ! command -v yt-dlp >/dev/null; then
    pip3 install --break-system-packages yt-dlp 2>/dev/null \
      || pip3 install yt-dlp 2>/dev/null || true
  fi

  # Python ODF library (alternative to LibreOffice headless conversion)
  # Pillow is used by some agents for PNG dimension verification.
  pip3 install --break-system-packages odfpy pyexcel-ods3 Pillow 2>/dev/null \
    || pip3 install odfpy pyexcel-ods3 Pillow 2>/dev/null || true
fi

# ── Authenticate gh with GITHUB_TOKEN from .privacy ────────────────
if [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null \
    || GH_TOKEN="$GITHUB_TOKEN" gh auth status 2>&1 || true
  echo "[task-setup] gh authenticated with GITHUB_TOKEN"
else
  echo "[task-setup] WARNING: GITHUB_TOKEN unset; gh will be rate-limited to 60 req/hr" >&2
fi

# ── Start a virtual X display so libreoffice GUI / screenshots work ─
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
for cmd in gh yt-dlp libreoffice soffice jq curl python3 scrot import gnome-screenshot convert ffmpeg Xvfb xdotool wmctrl; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo '[task-setup] done'
