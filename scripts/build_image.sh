#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="${BACKEND:-openclaw}"
IMAGE_NAME="${IMAGE_NAME:-}"
PLATFORM="${PLATFORM:-linux/amd64}"
BASE_IMAGE="${BASE_IMAGE:-docker.io/library/ubuntu:24.04}"
BUILD_NETWORK="${BUILD_NETWORK:-host}"
APT_MIRROR="${APT_MIRROR:-http://mirrors.aliyun.com/ubuntu}"
NODE_DIST_MIRROR="${NODE_DIST_MIRROR:-https://npmmirror.com/mirrors/node}"
NODE_DIST_FALLBACK_MIRROR="${NODE_DIST_FALLBACK_MIRROR:-https://nodejs.org/dist}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"
PIP_FALLBACK_INDEX_URL="${PIP_FALLBACK_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple}"
PIP_FALLBACK_TRUSTED_HOST="${PIP_FALLBACK_TRUSTED_HOST:-mirrors.aliyun.com}"
DUCKDUCKGO_SEARCH_VERSION="${DUCKDUCKGO_SEARCH_VERSION:-8.1.1}"
CHROME_VERSION="${CHROME_VERSION:-147.0.7727.50}"
CHROME_DIST_MIRROR="${CHROME_DIST_MIRROR:-https://npmmirror.com/mirrors/chrome-for-testing}"
CHROME_FALLBACK_DIST_MIRROR="${CHROME_FALLBACK_DIST_MIRROR:-https://storage.googleapis.com/chrome-for-testing-public}"
NANOBOT_VERSION="${NANOBOT_VERSION:-0.1.5.post3}"
OPENCLAW_VERSION="${OPENCLAW_VERSION:-2026.3.11}"
AGENT_BROWSER_VERSION="${AGENT_BROWSER_VERSION:-0.21.4}"
CODEX_VERSION="${CODEX_VERSION:-0.120.0}"
USE_BUILD_PROXY="${USE_BUILD_PROXY:-0}"

image_exists() {
  docker image inspect "$1" >/dev/null 2>&1
}

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

ensure_edict_assets() {
  local required=(
    "${ROOT}/downloads/edict/agents"
    "${ROOT}/downloads/edict/agents/GLOBAL.md"
    "${ROOT}/downloads/edict/agents/groups/sansheng.md"
    "${ROOT}/downloads/edict/dashboard"
    "${ROOT}/downloads/edict/scripts/kanban_update.py"
    "${ROOT}/downloads/edict/data/schema.json"
    "${ROOT}/downloads/edict/edict/backend/app/models/task.py"
    "${ROOT}/downloads/edict/docker/demo_data/openclaw.json"
    "${ROOT}/downloads/edict/docker/demo_data/tasks_source.json"
    "${ROOT}/downloads/edict/agents.json"
  )
  local missing=0
  local path
  for path in "${required[@]}"; do
    if [ ! -e "${path}" ]; then
      missing=1
      break
    fi
  done
  if [ "${missing}" = "0" ]; then
    return 0
  fi
  echo "Missing EDICT assets under downloads/edict. Fetching the upstream EDICT runtime snapshot..."
  "${ROOT}/scripts/fetch_edict.sh"
}

ensure_codex_base_image() {
  if [ "${BACKEND}" != "codex" ]; then
    return 0
  fi
  case "${BASE_IMAGE}" in
    clawbench-openclaw|clawbench-openclaw:*)
      ;;
    *)
      return 0
      ;;
  esac
  if image_exists "${BASE_IMAGE}"; then
    return 0
  fi
  echo "Base image ${BASE_IMAGE} not found. Building it first for Codex..."
  BACKEND=openclaw \
  IMAGE_NAME="${BASE_IMAGE}" \
  PLATFORM="${PLATFORM}" \
  BASE_IMAGE="docker.io/library/ubuntu:24.04" \
  BUILD_NETWORK="${BUILD_NETWORK}" \
  APT_MIRROR="${APT_MIRROR}" \
  NODE_DIST_MIRROR="${NODE_DIST_MIRROR}" \
  NODE_DIST_FALLBACK_MIRROR="${NODE_DIST_FALLBACK_MIRROR}" \
  NPM_REGISTRY="${NPM_REGISTRY}" \
  PIP_INDEX_URL="${PIP_INDEX_URL}" \
  PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" \
  PIP_FALLBACK_INDEX_URL="${PIP_FALLBACK_INDEX_URL}" \
  PIP_FALLBACK_TRUSTED_HOST="${PIP_FALLBACK_TRUSTED_HOST}" \
  DUCKDUCKGO_SEARCH_VERSION="${DUCKDUCKGO_SEARCH_VERSION}" \
  CHROME_VERSION="${CHROME_VERSION}" \
  CHROME_DIST_MIRROR="${CHROME_DIST_MIRROR}" \
  NANOBOT_VERSION="${NANOBOT_VERSION}" \
  OPENCLAW_VERSION="${OPENCLAW_VERSION}" \
  AGENT_BROWSER_VERSION="${AGENT_BROWSER_VERSION}" \
  CODEX_VERSION="${CODEX_VERSION}" \
  USE_BUILD_PROXY="${USE_BUILD_PROXY}" \
  HTTP_PROXY="${HTTP_PROXY:-${http_proxy:-}}" \
  HTTPS_PROXY="${HTTPS_PROXY:-${https_proxy:-}}" \
  ALL_PROXY="${ALL_PROXY:-${all_proxy:-}}" \
  "${BASH_SOURCE[0]}"
}

ensure_runtime_base_image() {
  if [ "${BACKEND}" != "openclaw" ] && [ "${BACKEND}" != "nanobot" ]; then
    return 0
  fi
  case "${BASE_IMAGE}" in
    clawbench-runtime-base|clawbench-runtime-base:*)
      ;;
    *)
      return 0
      ;;
  esac
  if image_exists "${BASE_IMAGE}"; then
    return 0
  fi
  echo "Base image ${BASE_IMAGE} not found. Building it first for ${BACKEND}..."
  BACKEND=runtime_base \
  IMAGE_NAME="${BASE_IMAGE}" \
  PLATFORM="${PLATFORM}" \
  BASE_IMAGE="docker.io/library/ubuntu:24.04" \
  BUILD_NETWORK="${BUILD_NETWORK}" \
  APT_MIRROR="${APT_MIRROR}" \
  NODE_DIST_MIRROR="${NODE_DIST_MIRROR}" \
  NODE_DIST_FALLBACK_MIRROR="${NODE_DIST_FALLBACK_MIRROR}" \
  NPM_REGISTRY="${NPM_REGISTRY}" \
  PIP_INDEX_URL="${PIP_INDEX_URL}" \
  PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" \
  PIP_FALLBACK_INDEX_URL="${PIP_FALLBACK_INDEX_URL}" \
  PIP_FALLBACK_TRUSTED_HOST="${PIP_FALLBACK_TRUSTED_HOST}" \
  DUCKDUCKGO_SEARCH_VERSION="${DUCKDUCKGO_SEARCH_VERSION}" \
  CHROME_VERSION="${CHROME_VERSION}" \
  CHROME_DIST_MIRROR="${CHROME_DIST_MIRROR}" \
  CHROME_FALLBACK_DIST_MIRROR="${CHROME_FALLBACK_DIST_MIRROR}" \
  AGENT_BROWSER_VERSION="${AGENT_BROWSER_VERSION}" \
  CODEX_VERSION="${CODEX_VERSION}" \
  USE_BUILD_PROXY="${USE_BUILD_PROXY}" \
  HTTP_PROXY="${HTTP_PROXY:-${http_proxy:-}}" \
  HTTPS_PROXY="${HTTPS_PROXY:-${https_proxy:-}}" \
  ALL_PROXY="${ALL_PROXY:-${all_proxy:-}}" \
  "${BASH_SOURCE[0]}"
}

ensure_openclaw_base_image() {
  if [ "${BACKEND}" != "openclaw_edict" ]; then
    return 0
  fi
  case "${BASE_IMAGE}" in
    clawbench-openclaw|clawbench-openclaw:*)
      ;;
    *)
      return 0
      ;;
  esac
  if image_exists "${BASE_IMAGE}"; then
    return 0
  fi
  echo "Base image ${BASE_IMAGE} not found. Building it first for openclaw_edict..."
  BACKEND=openclaw \
  IMAGE_NAME="${BASE_IMAGE}" \
  PLATFORM="${PLATFORM}" \
  BASE_IMAGE="docker.io/library/ubuntu:24.04" \
  BUILD_NETWORK="${BUILD_NETWORK}" \
  APT_MIRROR="${APT_MIRROR}" \
  NODE_DIST_MIRROR="${NODE_DIST_MIRROR}" \
  NODE_DIST_FALLBACK_MIRROR="${NODE_DIST_FALLBACK_MIRROR}" \
  NPM_REGISTRY="${NPM_REGISTRY}" \
  PIP_INDEX_URL="${PIP_INDEX_URL}" \
  PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" \
  PIP_FALLBACK_INDEX_URL="${PIP_FALLBACK_INDEX_URL}" \
  PIP_FALLBACK_TRUSTED_HOST="${PIP_FALLBACK_TRUSTED_HOST}" \
  DUCKDUCKGO_SEARCH_VERSION="${DUCKDUCKGO_SEARCH_VERSION}" \
  CHROME_VERSION="${CHROME_VERSION}" \
  CHROME_DIST_MIRROR="${CHROME_DIST_MIRROR}" \
  NANOBOT_VERSION="${NANOBOT_VERSION}" \
  OPENCLAW_VERSION="${OPENCLAW_VERSION}" \
  AGENT_BROWSER_VERSION="${AGENT_BROWSER_VERSION}" \
  CODEX_VERSION="${CODEX_VERSION}" \
  USE_BUILD_PROXY="${USE_BUILD_PROXY}" \
  HTTP_PROXY="${HTTP_PROXY:-${http_proxy:-}}" \
  HTTPS_PROXY="${HTTPS_PROXY:-${https_proxy:-}}" \
  ALL_PROXY="${ALL_PROXY:-${all_proxy:-}}" \
  "${BASH_SOURCE[0]}"
}
LIBSIGNAL_GIT_URL="${LIBSIGNAL_GIT_URL:-https://github.com/whiskeysockets/libsignal-node.git}"

normalize_proxy_for_docker() {
  local value="${1:-}"
  value="${value//127.0.0.1/host.docker.internal}"
  value="${value//localhost/host.docker.internal}"
  printf '%s' "${value}"
}

prepare_libsignal_mirror() {
  local mirror_dir="${ROOT}/build/libsignal-node"

  if ! command -v git >/dev/null 2>&1; then
    echo "git is required to prepare ${mirror_dir}" >&2
    exit 1
  fi

  mkdir -p "${ROOT}/build"
  # ``safe.directory`` exemption: when the libsignal mirror was checked
  # out by one user (e.g. an unprivileged dev account) and the build is
  # later re-run as root (as can happen on a shared worker host),
  # git refuses to operate on the repo with "fatal: detected dubious
  # ownership".  We grant the exception unconditionally — the worst case
  # is the next git op runs against a possibly-tampered repo, but the
  # very next step is ``fetch --depth 1`` + ``reset --hard FETCH_HEAD``
  # which wipes any local divergence anyway.
  if [ -d "${mirror_dir}/.git" ]; then
    git config --global --add safe.directory "${mirror_dir}" 2>/dev/null || true
    echo "Refreshing cached libsignal mirror in ${mirror_dir}"
    git -C "${mirror_dir}" remote set-url origin "${LIBSIGNAL_GIT_URL}"
    if retry_cmd 3 git -C "${mirror_dir}" fetch --depth 1 origin; then
      git -C "${mirror_dir}" reset --hard FETCH_HEAD
      git -C "${mirror_dir}" clean -fdx
    else
      echo "Warning: failed to refresh libsignal mirror, using cached checkout" >&2
    fi
  else
    echo "Cloning libsignal mirror into ${mirror_dir}"
    rm -rf "${mirror_dir}"
    retry_cmd 3 git clone --depth 1 "${LIBSIGNAL_GIT_URL}" "${mirror_dir}"
    git config --global --add safe.directory "${mirror_dir}" 2>/dev/null || true
  fi
}

HTTP_PROXY_ARG=""
HTTPS_PROXY_ARG=""
ALL_PROXY_ARG=""
if [ "${USE_BUILD_PROXY}" = "1" ]; then
  HTTP_PROXY_ARG="$(normalize_proxy_for_docker "${HTTP_PROXY:-${http_proxy:-}}")"
  HTTPS_PROXY_ARG="$(normalize_proxy_for_docker "${HTTPS_PROXY:-${https_proxy:-}}")"
  ALL_PROXY_ARG="$(normalize_proxy_for_docker "${ALL_PROXY:-${all_proxy:-}}")"
fi

cd "${ROOT}"

case "${BACKEND}" in
  runtime_base)
    DEFAULT_IMAGE_NAME="clawbench-runtime-base:latest"
    DOCKERFILE="docker/runtime-base.Dockerfile"
    ;;
  openclaw)
    DEFAULT_IMAGE_NAME="clawbench-openclaw:latest"
    DOCKERFILE="docker/openclaw.Dockerfile"
    if [ "${BASE_IMAGE}" = "docker.io/library/ubuntu:24.04" ]; then
      BASE_IMAGE="clawbench-runtime-base:latest"
    fi
    ensure_runtime_base_image
    ;;
  nanobot)
    DEFAULT_IMAGE_NAME="clawbench-nanobot:latest"
    DOCKERFILE="docker/nanobot.Dockerfile"
    if [ "${BASE_IMAGE}" = "docker.io/library/ubuntu:24.04" ]; then
      BASE_IMAGE="clawbench-runtime-base:latest"
    fi
    ensure_runtime_base_image
    ;;
  openclaw_edict)
    DEFAULT_IMAGE_NAME="clawbench-openclaw-edict:latest"
    DOCKERFILE="docker/openclaw-edict.Dockerfile"
    if [ "${BASE_IMAGE}" = "docker.io/library/ubuntu:24.04" ]; then
      BASE_IMAGE="clawbench-openclaw:latest"
    fi
    ensure_edict_assets
    ensure_openclaw_base_image
    ;;
  codex)
    DEFAULT_IMAGE_NAME="clawbench-codex:latest"
    DOCKERFILE="docker/codex.Dockerfile"
    ensure_codex_base_image
    ;;
  *)
    echo "Unsupported BACKEND=${BACKEND}" >&2
    exit 1
    ;;
esac

if [ -z "${IMAGE_NAME}" ]; then
  IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
fi

if [ "${BACKEND}" != "codex" ]; then
  case "${BACKEND}" in
    runtime_base)
      if [ ! -d "${ROOT}/docker/base_skills/web-search" ]; then
        echo "Missing extracted web-search skill under docker/base_skills/web-search" >&2
        exit 1
      fi
      if [ ! -d "${ROOT}/docker/base_skills/duckduckgo-search" ]; then
        echo "Missing extracted duckduckgo-search skill under docker/base_skills/duckduckgo-search" >&2
        exit 1
      fi
      ;;
  esac

  case "${BACKEND}" in
    openclaw)
      prepare_libsignal_mirror
      ;;
  esac

  case "${BACKEND}" in
    runtime_base)
      mkdir -p "${ROOT}/build"
      CHROME_CACHE_ZIP="${ROOT}/build/chrome-linux64.zip"
      CHROME_VERSION_STAMP="${ROOT}/build/chrome-linux64.version"
      if [ ! -s "${CHROME_CACHE_ZIP}" ] || [ ! -f "${CHROME_VERSION_STAMP}" ] || [ "$(cat "${CHROME_VERSION_STAMP}")" != "${CHROME_VERSION}" ]; then
        chrome_urls=("${CHROME_DIST_MIRROR%/}/${CHROME_VERSION}/linux64/chrome-linux64.zip")
        if [ "${CHROME_FALLBACK_DIST_MIRROR}" != "${CHROME_DIST_MIRROR}" ]; then
          chrome_urls+=("${CHROME_FALLBACK_DIST_MIRROR%/}/${CHROME_VERSION}/linux64/chrome-linux64.zip")
        fi
        download_with_fallback "${CHROME_CACHE_ZIP}" "${chrome_urls[@]}"
        printf '%s\n' "${CHROME_VERSION}" > "${CHROME_VERSION_STAMP}"
      fi
      ;;
  esac
fi

docker buildx build \
  --load \
  --platform "${PLATFORM}" \
  --network "${BUILD_NETWORK}" \
  --build-arg APT_MIRROR="${APT_MIRROR}" \
  --build-arg BASE_IMAGE="${BASE_IMAGE}" \
  --build-arg NODE_DIST_MIRROR="${NODE_DIST_MIRROR}" \
  --build-arg NODE_DIST_FALLBACK_MIRROR="${NODE_DIST_FALLBACK_MIRROR}" \
  --build-arg NPM_REGISTRY="${NPM_REGISTRY}" \
  --build-arg PIP_INDEX_URL="${PIP_INDEX_URL}" \
  --build-arg PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" \
  --build-arg PIP_FALLBACK_INDEX_URL="${PIP_FALLBACK_INDEX_URL}" \
  --build-arg PIP_FALLBACK_TRUSTED_HOST="${PIP_FALLBACK_TRUSTED_HOST}" \
  --build-arg DUCKDUCKGO_SEARCH_VERSION="${DUCKDUCKGO_SEARCH_VERSION}" \
  --build-arg NANOBOT_VERSION="${NANOBOT_VERSION}" \
  --build-arg OPENCLAW_VERSION="${OPENCLAW_VERSION}" \
  --build-arg AGENT_BROWSER_VERSION="${AGENT_BROWSER_VERSION}" \
  --build-arg CODEX_VERSION="${CODEX_VERSION}" \
  --build-arg CHROME_VERSION="${CHROME_VERSION}" \
  --build-arg HTTP_PROXY="${HTTP_PROXY_ARG}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY_ARG}" \
  --build-arg ALL_PROXY="${ALL_PROXY_ARG}" \
  -t "${IMAGE_NAME}" \
  -f "${DOCKERFILE}" \
  .

echo "Built ${IMAGE_NAME}"
