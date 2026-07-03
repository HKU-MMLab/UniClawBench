#!/usr/bin/env bash
# Build all five clawbench docker images in dependency order, sequentially.
#
# Why a dedicated orchestra-layer build script (and not just
# ``scripts/build_image.sh`` per backend)?
#
#  1. Dependency ordering — runtime-base MUST exist before openclaw/nanobot,
#     and openclaw MUST exist before openclaw-edict.  ``scripts/build_image.sh``
#     handles single-image build (with ``ensure_*_base_image`` helpers), but
#     it does NOT serialize "build A, then build B that depends on A" across
#     a top-level cluster invocation.
#  2. BuildKit parallel-race protection — running two ``docker buildx build``
#     invocations against the same context simultaneously can race on
#     ``docker/`` files copied via ``--mount=type=bind``.  Round 13 reproduced
#     this (`lstat docker: no such file or directory`).  This script
#     serializes builds so only one buildx is in flight at a time.
#  3. Remote-host support — pass ``--host worker1`` to ssh into a worker and run
#     the build there.  Combined with ``scripts/orchestra/distribute_images.sh``
#     this is the cluster flow: build on one host, distribute to the rest.
#  4. Single canonical entry point so the Dockerfile + build_image.sh +
#     prepare_node.py story has ONE name that documents it all.
#
# Image set (built in dependency order):
#   runtime-base, codex, openclaw, nanobot, openclaw-edict
#
# Usage:
#   scripts/orchestra/build_images.sh                   # build all 5 locally
#   scripts/orchestra/build_images.sh --host worker1 --remote-root /opt/clawbench/Clawbench
#                                                       # build all 5 on a worker
#   scripts/orchestra/build_images.sh --images runtime-base,openclaw,codex
#                                                       # build a subset (still dep-ordered)
#   scripts/orchestra/build_images.sh --skip-cache      # disable BuildKit cache
#   scripts/orchestra/build_images.sh --host worker1 --remote-root /opt/clawbench/Clawbench \
#     --distribute-to worker2,worker3                  # build on worker1, then copy
#
# Environment passthrough:
#   All ``scripts/build_image.sh`` env vars (HTTP_PROXY, NPM_REGISTRY,
#   *_VERSION pins, etc.) are forwarded both locally and over ssh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

HOST=""
SUBSET=""
SKIP_CACHE=0
DISTRIBUTE=0
DISTRIBUTE_PEERS=""
REMOTE_ROOT="/opt/clawbench/Clawbench"

while [ $# -gt 0 ]; do
  case "$1" in
    --host)
      HOST="${2:?--host requires a hostname}"; shift 2 ;;
    --host=*)
      HOST="${1#*=}"; shift ;;
    --images)
      SUBSET="${2:?--images requires a comma-separated list}"; shift 2 ;;
    --images=*)
      SUBSET="${1#*=}"; shift ;;
    --skip-cache|--no-cache)
      SKIP_CACHE=1; shift ;;
    --distribute)
      DISTRIBUTE=1; shift ;;
    --distribute-to)
      DISTRIBUTE=1
      DISTRIBUTE_PEERS="${2:?--distribute-to requires peers}"; shift 2 ;;
    --remote-root)
      REMOTE_ROOT="${2:?--remote-root requires a remote checkout path}"; shift 2 ;;
    --remote-root=*)
      REMOTE_ROOT="${1#*=}"; shift ;;
    -h|--help)
      sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "unknown arg: $1" >&2
      echo "see --help" >&2
      exit 2 ;;
  esac
done

# Canonical image build order.  Tuples of <BACKEND, image-tag, depends-on>
# where ``depends-on`` is empty for leaves of the dependency DAG.
#
# Why this order:
#   runtime-base  → foundation for openclaw + nanobot
#   codex         → independent (FROM ubuntu directly)
#   openclaw      → FROM runtime-base
#   nanobot       → FROM runtime-base
#   openclaw-edict → FROM openclaw
#
# Both branches (codex vs openclaw/nanobot/edict) could in principle run
# concurrently, but we deliberately serialize to avoid BuildKit
# bind-mount races against ``docker/`` (Round 13 / Round 14 evidence).
ALL_IMAGES=(
  "runtime_base:clawbench-runtime-base:"
  "codex:clawbench-codex:"
  "openclaw:clawbench-openclaw:runtime_base"
  "nanobot:clawbench-nanobot:runtime_base"
  "openclaw_edict:clawbench-openclaw-edict:openclaw"
)

# Validate / filter the subset.
# NOTE: avoid ``declare -A`` (associative arrays) — macOS ships bash 3.2 by
# default and 3.2 does not support -A.  We do the lookup by scanning the
# small ALL_IMAGES array instead.
SELECTED=()
if [ -z "${SUBSET}" ]; then
  SELECTED=("${ALL_IMAGES[@]}")
else
  # Comma-separated list; walk each user pick and find the matching row.
  OLD_IFS="${IFS}"
  IFS=','
  # shellcheck disable=SC2206
  picks=( ${SUBSET} )
  IFS="${OLD_IFS}"
  for p in "${picks[@]}"; do
    # trim whitespace
    p="${p#"${p%%[![:space:]]*}"}"
    p="${p%"${p##*[![:space:]]}"}"
    [ -z "${p}" ] && continue
    found=""
    for row in "${ALL_IMAGES[@]}"; do
      IFS=':' read -r backend tag _ <<<"${row}"
      short="${tag#clawbench-}"
      if [ "${p}" = "${short}" ] || [ "${p}" = "${backend}" ]; then
        found="${row}"
        break
      fi
    done
    if [ -z "${found}" ]; then
      echo "unknown image: ${p}" >&2
      echo "valid: runtime-base, openclaw, nanobot, codex, openclaw-edict" >&2
      exit 2
    fi
    SELECTED+=("${found}")
  done
  # Re-order SELECTED to match ALL_IMAGES dependency order.
  ORDERED=()
  for row in "${ALL_IMAGES[@]}"; do
    for sel in "${SELECTED[@]}"; do
      if [ "${row}" = "${sel}" ]; then
        ORDERED+=("${row}")
        break
      fi
    done
  done
  SELECTED=("${ORDERED[@]}")
fi

build_one_local() {
  local backend="$1"
  local image_tag="$2"
  local cache_arg=""
  if [ "${SKIP_CACHE}" = "1" ]; then
    cache_arg="DOCKER_BUILDKIT_NO_CACHE=1"
  fi
  echo
  echo "=== building ${image_tag} (BACKEND=${backend}) ==="
  # Forward env-vars relevant to build_image.sh.  We don't enumerate them
  # explicitly because new VERSION pins keep getting added — instead, just
  # call the per-image script and let it pick up the existing env.
  (
    cd "${ROOT}"
    eval "${cache_arg:-} BACKEND='${backend}' bash scripts/build_image.sh"
  )
}

build_one_remote() {
  local backend="$1"
  local image_tag="$2"
  local cache_env=""
  if [ "${SKIP_CACHE}" = "1" ]; then
    cache_env="DOCKER_BUILDKIT_NO_CACHE=1 "
  fi
  echo
  echo "=== building ${image_tag} on ${HOST} (BACKEND=${backend}) ==="
  # Pass through any *_VERSION / *_MIRROR / *_PROXY env vars so the remote
  # build is reproducible.  We compose the env line dynamically.
  local fwd=""
  for var in \
      HTTP_PROXY HTTPS_PROXY ALL_PROXY \
      APT_MIRROR NODE_DIST_MIRROR NODE_DIST_FALLBACK_MIRROR NPM_REGISTRY \
      PIP_INDEX_URL PIP_TRUSTED_HOST PIP_FALLBACK_INDEX_URL PIP_FALLBACK_TRUSTED_HOST \
      CHROME_VERSION CHROME_DIST_MIRROR CHROME_FALLBACK_DIST_MIRROR \
      NANOBOT_VERSION OPENCLAW_VERSION CODEX_VERSION AGENT_BROWSER_VERSION \
      DUCKDUCKGO_SEARCH_VERSION; do
    val="${!var:-}"
    if [ -n "${val}" ]; then
      fwd+="${var}=$(printf %q "${val}") "
    fi
  done
  ssh "${HOST}" "${cache_env}${fwd}BACKEND='${backend}' bash ${REMOTE_ROOT}/scripts/build_image.sh"
}

# Main build loop — strictly serial.
for row in "${SELECTED[@]}"; do
  IFS=':' read -r backend tag _ <<<"${row}"
  if [ -n "${HOST}" ]; then
    build_one_remote "${backend}" "${tag}:latest"
  else
    build_one_local "${backend}" "${tag}:latest"
  fi
done

echo
echo "=== build done ==="
if [ -n "${HOST}" ]; then
  echo "  built on: ${HOST}"
  ssh "${HOST}" "docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | grep '^clawbench-.*:latest ' | sort"
else
  docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | grep '^clawbench-.*:latest ' | sort
fi

if [ "${DISTRIBUTE}" = "1" ]; then
  if [ -z "${HOST}" ]; then
    echo "  --distribute set but no --host given; running distribute_images.sh from local docker" >&2
  fi
  echo
  echo "=== distributing images ==="
  seed="${HOST:-localhost}"
  if [ -n "${DISTRIBUTE_PEERS}" ]; then
    bash "${ROOT}/scripts/orchestra/distribute_images.sh" --seed "${seed}" --workers "${DISTRIBUTE_PEERS}"
  else
    echo "FAIL: --distribute requires --distribute-to worker1,worker2" >&2
    exit 2
  fi
fi
