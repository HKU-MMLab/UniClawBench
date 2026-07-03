#!/usr/bin/env bash
# Round 9 / B1: formalize EDICT asset acquisition + record commit/version.
#
# Downloads (or reuses) the official cft0808/edict source archive and
# extracts it into ``downloads/edict/`` for the docker build to copy.
# The image build (``docker/openclaw-edict.Dockerfile``) COPYs the key
# subtrees (agents, dashboard, scripts, data, edict, docker/demo_data,
# agents.json) plus this script's ``EDICT_COMMIT`` / ``EDICT_VERSION``
# metadata files into ``/opt/edict``; Clawbench then reports which
# official revision it ran (Round 9 / B3 threads these into the
# attempt summary and WebUI badge).
#
# Why local-tarball-then-build vs. clone-at-build:
# - The clawbench-openclaw-edict image is built repeatedly across
#   workers; cloning at build time burns rate limits + adds an
#   unreliable network step inside docker build.  Local-tarball pattern
#   matches the existing nanobot / openclaw runtime fetches.
# - Operators in air-gapped lab environments can drop the official
#   tarball into downloads/ manually and skip the curl step.
#
# Env vars (all optional):
#   EDICT_COMMIT   — pin a specific commit sha or branch.  Default
#                    'main' which matches the existing
#                    downloads/edict-main.tar.gz snapshot.
#   EDICT_TARBALL  — explicit tarball path to extract from.  Overrides
#                    the auto-discovery + curl steps.
#   EDICT_FORCE    — set to 1 to force re-extraction even when
#                    downloads/edict/EDICT_COMMIT already matches.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
EDICT_COMMIT="${EDICT_COMMIT:-main}"
EDICT_FORCE="${EDICT_FORCE:-0}"
DOWNLOADS="${ROOT}/downloads"
DEST="${DOWNLOADS}/edict"

mkdir -p "${DOWNLOADS}"

# Required files build_image.sh::ensure_edict_assets() checks.  If any
# of these are missing after extraction we treat the snapshot as broken.
REQUIRED=(
  "agents"
  "agents/GLOBAL.md"
  "agents/groups/sansheng.md"
  "dashboard"
  "scripts/kanban_update.py"
  "data/schema.json"
  "edict/backend/app/models/task.py"
  "docker/demo_data/openclaw.json"
  "docker/demo_data/tasks_source.json"
  "agents.json"
)

required_present() {
  local base="$1"
  local rel
  for rel in "${REQUIRED[@]}"; do
    if [ ! -e "${base}/${rel}" ]; then
      return 1
    fi
  done
  return 0
}

# Step 0: idempotent fast-path.  If the destination already has all
# required files AND records the requested commit, skip extraction.
# This keeps repeated `build_image.sh openclaw_edict` invocations
# cheap and avoids re-extracting on every CI run.
if [ "${EDICT_FORCE}" != "1" ] \
   && [ -f "${DEST}/EDICT_COMMIT" ] \
   && [ "$(cat "${DEST}/EDICT_COMMIT" 2>/dev/null || true)" = "${EDICT_COMMIT}" ] \
   && required_present "${DEST}"; then
  echo "downloads/edict/ already at ${EDICT_COMMIT}; skipping fetch."
  cat "${DEST}/EDICT_COMMIT"
  cat "${DEST}/EDICT_VERSION" 2>/dev/null || true
  exit 0
fi

# Step 1: figure out which tarball to extract.
if [ -n "${EDICT_TARBALL:-}" ] && [ -f "${EDICT_TARBALL}" ]; then
  TARBALL="${EDICT_TARBALL}"
elif [ "${EDICT_COMMIT}" = "main" ] && [ -f "${DOWNLOADS}/edict-main.tar.gz" ]; then
  # Default case: the existing main snapshot bundled with the repo
  TARBALL="${DOWNLOADS}/edict-main.tar.gz"
else
  # Need to download.  Use a commit-pinned tarball for reproducibility.
  TARBALL="${DOWNLOADS}/edict-${EDICT_COMMIT:0:12}.tar.gz"
  if [ ! -f "${TARBALL}" ]; then
    URL="https://github.com/cft0808/edict/archive/${EDICT_COMMIT}.tar.gz"
    echo "Fetching EDICT @ ${EDICT_COMMIT} from ${URL}"
    if ! curl -L --fail --retry 3 --connect-timeout 15 --max-time 1200 \
            "${URL}" -o "${TARBALL}"; then
      echo "ERROR: failed to download EDICT tarball; provide" >&2
      echo "       downloads/edict-main.tar.gz manually or set" >&2
      echo "       EDICT_TARBALL=/abs/path/to.tar.gz" >&2
      rm -f "${TARBALL}"
      exit 1
    fi
  fi
fi

echo "Using EDICT tarball: ${TARBALL}"

# Step 2: extract.  Wipe the destination so we don't mix old + new
# files.  The bundled main tarball has a known-truncated docs/*.mp4
# tail; we tolerate that as long as the required asset list is intact
# afterwards.
rm -rf "${DEST}"
mkdir -p "${DEST}"
# `|| true` so a partial-tail truncation in non-essential docs does not
# fail the entire build.  We re-check required files below.
tar xzf "${TARBALL}" -C "${DEST}" --strip-components=1 || \
  echo "WARNING: tar reported truncation (continuing if required assets are present)"

if ! required_present "${DEST}"; then
  echo "ERROR: extracted ${DEST} is missing required EDICT files:" >&2
  for rel in "${REQUIRED[@]}"; do
    if [ ! -e "${DEST}/${rel}" ]; then
      echo "  - ${rel}" >&2
    fi
  done
  exit 1
fi

# Step 3: record commit + version metadata.  The docker COPY picks
# these up (added in Round 9 / B1), so the resulting image has
# /opt/edict/EDICT_COMMIT and /opt/edict/EDICT_VERSION.
#
# For the bundled 'main' snapshot we cannot recover the precise upstream
# commit without git history, so we record both the requested branch
# name and the tarball's mtime as a poor-man's version.
echo "${EDICT_COMMIT}" > "${DEST}/EDICT_COMMIT"
if [ "${EDICT_COMMIT}" = "main" ]; then
  # Use tarball mtime as the version proxy when committed to 'main'.
  # ``stat`` format strings are platform-divergent: macOS uses
  # ``stat -f %Sm -t %Y%m%d`` (file-info format), Linux uses
  # ``stat -c %Y`` (epoch seconds) which we then pass to ``date``.
  # Without the platform split, the macOS-form on Linux falls back to
  # ``stat -f`` which is *filesystem* info — produces junk like
  # "<path> 4bd6c2e78bc922a8 255 ef53 ...".
  if stat -f %Sm -t %Y%m%d "${TARBALL}" >/dev/null 2>&1; then
    MTIME_DATE="$(stat -f %Sm -t %Y%m%d "${TARBALL}")"
  elif EPOCH="$(stat -c %Y "${TARBALL}" 2>/dev/null)"; then
    MTIME_DATE="$(date -u -d "@${EPOCH}" +%Y%m%d 2>/dev/null || echo unknown)"
  else
    MTIME_DATE="unknown"
  fi
  VERSION="main-${MTIME_DATE}"
else
  VERSION="${EDICT_COMMIT:0:7}"
fi
echo "${VERSION}" > "${DEST}/EDICT_VERSION"

echo "EDICT_COMMIT=${EDICT_COMMIT}"
echo "EDICT_VERSION=${VERSION}"
echo "downloads/edict/ ready."
