#!/usr/bin/env bash
set -euo pipefail

: "${APT_MIRROR:=http://mirrors.aliyun.com/ubuntu}"
: "${HTTP_PROXY:=}"
: "${HTTPS_PROXY:=}"
: "${ALL_PROXY:=}"
: "${NODE_VERSION:=22.22.1}"
: "${NODE_DIST_MIRROR:=https://npmmirror.com/mirrors/node}"
: "${NODE_DIST_FALLBACK_MIRROR:=https://nodejs.org/dist}"
: "${CHROME_VERSION:=147.0.7727.50}"

export DEBIAN_FRONTEND=noninteractive

retry_cmd() {
  local attempt=1
  local max_attempts="${1:?missing max attempts}"
  shift
  while true; do
    if "$@"; then
      return 0
    fi
    if [ "${attempt}" -ge "${max_attempts}" ]; then
      return 1
    fi
    echo "Command failed (attempt ${attempt}/${max_attempts}): $*" >&2
    sleep $((attempt * 5))
    attempt=$((attempt + 1))
  done
}

download_with_fallback() {
  local output="${1:?missing output path}"
  shift
  local url
  for url in "$@"; do
    [ -n "${url}" ] || continue
    echo "Downloading $(basename "${output}") from ${url}"
    if retry_cmd 5 curl -L --fail --retry 5 --connect-timeout 15 --max-time 1800 "${url}" -o "${output}"; then
      return 0
    fi
    rm -f "${output}"
    echo "Warning: failed to download from ${url}" >&2
  done
  return 1
}

if [ -n "${APT_MIRROR}" ]; then
  for f in /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list; do
    if [ -f "$f" ]; then
      sed -i \
        -e "s|http://archive.ubuntu.com/ubuntu/|${APT_MIRROR%/}/|g" \
        -e "s|http://security.ubuntu.com/ubuntu/|${APT_MIRROR%/}/|g" \
        -e "s|http://archive.ubuntu.com/ubuntu|${APT_MIRROR%/}|g" \
        -e "s|http://security.ubuntu.com/ubuntu|${APT_MIRROR%/}|g" \
        "$f"
    fi
  done
fi

rm -f /etc/apt/apt.conf.d/80proxy
if [ -n "${HTTP_PROXY}" ]; then
  printf 'Acquire::http::Proxy "%s";\n' "${HTTP_PROXY}" >> /etc/apt/apt.conf.d/80proxy
fi
if [ -n "${HTTPS_PROXY}" ]; then
  printf 'Acquire::https::Proxy "%s";\n' "${HTTPS_PROXY}" >> /etc/apt/apt.conf.d/80proxy
fi

cat > /etc/apt/apt.conf.d/99clawbench-network <<'EOF'
Acquire::ForceIPv4 "true";
Acquire::Retries "5";
Acquire::http::Timeout "60";
Acquire::https::Timeout "60";
EOF

retry_cmd 5 apt-get update
retry_cmd 5 apt-get install -y --fix-missing --no-install-recommends \
  at-spi2-core \
  ca-certificates \
  curl \
  dbus-x11 \
  file \
  fonts-liberation \
  fonts-noto-cjk \
  fonts-noto-color-emoji \
  ffmpeg \
  git \
  libasound2t64 \
  libnspr4 \
  libnss3 \
  novnc \
  pipx \
  poppler-utils \
  python3 \
  python3-matplotlib \
  python3-pip \
  python3-dogtail \
  python3-venv \
  python-is-python3 \
  ripgrep \
  scrot \
  socat \
  thunar \
  tint2 \
  unzip \
  websockify \
  wget \
  wmctrl \
  x11-utils \
  x11vnc \
  xauth \
  xdotool \
  xfce4-appfinder \
  xfce4-terminal \
  xfdesktop4 \
  xfwm4 \
  xvfb \
  xz-utils
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f /etc/apt/apt.conf.d/80proxy
rm -f /etc/apt/apt.conf.d/99clawbench-network
# docker-slim: drop apt-installed doc/man pages (~50-150MB across xfce
# + libreoffice + chromium-deps).  Containers don't need offline docs;
# WebUI/agent never reads /usr/share/doc.  /usr/share/locale keeps only
# en/zh_CN/zh — task content uses English + Chinese.
rm -rf /usr/share/doc/* /usr/share/man/* /var/cache/apt/archives/*
find /usr/share/locale -mindepth 1 -maxdepth 1 -type d \
    ! -name 'en*' ! -name 'zh*' ! -name 'C' ! -name 'locale.alias' \
    -exec rm -rf {} + 2>/dev/null || true

mkdir -p /opt/chrome
unzip -qo /tmp/chrome-linux64.zip -d /opt/chrome
test -x /opt/chrome/chrome-linux64/chrome
ln -sf /opt/chrome/chrome-linux64/chrome /usr/local/bin/chromium
# /tmp/chrome-linux64.zip is now bind-mounted (Dockerfile change),
# nothing to ``rm`` here — kept for backwards compatibility with the
# COPY-based build.

export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy="${ALL_PROXY}"
export HTTP_PROXY="${HTTP_PROXY}" HTTPS_PROXY="${HTTPS_PROXY}" ALL_PROXY="${ALL_PROXY}"
download_with_fallback /tmp/node.tar.xz \
  "${NODE_DIST_MIRROR%/}/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
  "${NODE_DIST_FALLBACK_MIRROR%/}/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz"
mkdir -p /usr/local/lib/nodejs
tar -xJf /tmp/node.tar.xz -C /usr/local/lib/nodejs
ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/bin/node" /usr/local/bin/node
ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/bin/npm" /usr/local/bin/npm
ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/bin/npx" /usr/local/bin/npx
rm -f /tmp/node.tar.xz
# docker-slim: drop Node.js docs (~70MB) — bundled README/CHANGELOG +
# api/ HTML inside the node distribution.  Keep bin + lib + include
# (header files needed by some native modules).
rm -rf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/share"
rm -rf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/CHANGELOG.md" \
       "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/README.md" \
       "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/LICENSE"

ln -sf /usr/bin/python3 /usr/local/bin/python
ln -sf /usr/bin/pip3 /usr/local/bin/pip
