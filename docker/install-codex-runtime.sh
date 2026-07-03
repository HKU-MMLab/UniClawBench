#!/usr/bin/env bash
set -euo pipefail

: "${APT_MIRROR:=http://mirrors.aliyun.com/ubuntu}"
: "${NODE_VERSION:=22.22.1}"
: "${NODE_DIST_MIRROR:=https://npmmirror.com/mirrors/node}"
: "${NODE_DIST_FALLBACK_MIRROR:=https://nodejs.org/dist}"

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

cat > /etc/apt/apt.conf.d/99clawbench-network <<'EOF'
Acquire::ForceIPv4 "true";
Acquire::Retries "5";
Acquire::http::Timeout "60";
Acquire::https::Timeout "60";
EOF

retry_cmd 5 apt-get update
retry_cmd 5 apt-get install -y --no-install-recommends \
  bubblewrap \
  ca-certificates \
  curl \
  git \
  jq \
  poppler-utils \
  python3 \
  python3-pip \
  ripgrep \
  sqlite3 \
  xz-utils
# iter5-fix: supervisor (codex) needs python + common readers so it can
# inspect .docx / .xlsx / .pdf / .db artifacts the executor produces.
# Without these the supervisor can only read plain text and is forced to
# either invent rules or downgrade scores blindly.
retry_cmd 3 python3 -m pip install --no-cache-dir --break-system-packages \
  python-docx==1.1.2 \
  openpyxl==3.1.5 \
  pypdf==4.3.1 \
  pdfplumber==0.11.4 \
  pandas==2.2.3
rm -rf /var/lib/apt/lists/*
rm -rf /root/.cache/pip
rm -f /etc/apt/apt.conf.d/99clawbench-network

download_with_fallback /tmp/node.tar.xz \
  "${NODE_DIST_MIRROR%/}/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
  "${NODE_DIST_FALLBACK_MIRROR%/}/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz"
mkdir -p /usr/local/lib/nodejs
tar -xJf /tmp/node.tar.xz -C /usr/local/lib/nodejs
ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/bin/node" /usr/local/bin/node
ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/bin/npm" /usr/local/bin/npm
ln -sf "/usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-x64/bin/npx" /usr/local/bin/npx
rm -f /tmp/node.tar.xz
