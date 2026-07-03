#!/usr/bin/env bash
set -euo pipefail

: "${PIP_INDEX_URL:=https://pypi.tuna.tsinghua.edu.cn/simple}"
: "${PIP_TRUSTED_HOST:=pypi.tuna.tsinghua.edu.cn}"
: "${PIP_FALLBACK_INDEX_URL:=https://mirrors.aliyun.com/pypi/simple}"
: "${PIP_FALLBACK_TRUSTED_HOST:=mirrors.aliyun.com}"
: "${DUCKDUCKGO_SEARCH_VERSION:=8.1.1}"

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

pip_install_with_fallback() {
  local package_spec="${1:?missing package spec}"
  local index_url trusted_host
  local -a pip_args
  for index_url in "${PIP_INDEX_URL}" "${PIP_FALLBACK_INDEX_URL}"; do
    [ -n "${index_url}" ] || continue
    trusted_host=""
    if [ "${index_url}" = "${PIP_INDEX_URL}" ]; then
      trusted_host="${PIP_TRUSTED_HOST}"
    else
      trusted_host="${PIP_FALLBACK_TRUSTED_HOST}"
    fi
    pip_args=(
      python3 -m pip install
      --no-cache-dir
      --disable-pip-version-check
      --break-system-packages
      --retries 5
      --timeout 120
      --index-url "${index_url}"
    )
    if [ -n "${trusted_host}" ]; then
      pip_args+=(--trusted-host "${trusted_host}")
    fi
    pip_args+=("${package_spec}")
    if retry_cmd 2 "${pip_args[@]}"; then
      return 0
    fi
  done
  return 1
}

pip_install_with_fallback "duckduckgo-search==${DUCKDUCKGO_SEARCH_VERSION}"
python3 - <<'PY'
import importlib.util
import sys

if importlib.util.find_spec("duckduckgo_search") is None:
    sys.exit("duckduckgo_search module is not importable after install")
PY
