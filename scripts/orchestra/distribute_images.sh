#!/usr/bin/env bash
# Distribute Clawbench docker images from a seed host to worker hosts that
# are missing them. Idempotent — workers that already have a tag are skipped.
#
# Usage:
#   scripts/orchestra/distribute_images.sh --seed builder --workers worker1,worker2
#   scripts/orchestra/distribute_images.sh --seed builder worker1 worker2
#
# Env requirements:
#   - The host running this script must be able to SSH to the seed and workers.
#   - Optional SSH_OPTS is appended to every ssh invocation.
set -euo pipefail

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

SEED=""
WORKERS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --seed)
      SEED="${2:?--seed requires a hostname}"; shift 2 ;;
    --seed=*)
      SEED="${1#*=}"; shift ;;
    --workers)
      IFS=',' read -r -a WORKERS <<<"${2:?--workers requires a comma-separated list}"
      shift 2 ;;
    --workers=*)
      IFS=',' read -r -a WORKERS <<<"${1#*=}"
      shift ;;
    -h|--help)
      usage; exit 0 ;;
    --)
      shift; break ;;
    -*)
      echo "unknown arg: $1" >&2
      usage >&2
      exit 2 ;;
    *)
      WORKERS+=("$1"); shift ;;
  esac
done

if [ -z "$SEED" ] || [ "${#WORKERS[@]}" -eq 0 ]; then
  echo "FAIL: --seed and at least one worker are required" >&2
  usage >&2
  exit 2
fi

IMAGES=(
  clawbench-runtime-base
  clawbench-openclaw
  clawbench-nanobot
  clawbench-codex
  clawbench-openclaw-edict
)

ssh_remote() {
  # shellcheck disable=SC2086
  ssh -o ConnectTimeout=20 ${SSH_OPTS:-} "$@"
}

verify_worker_images() {
  local worker="$1"
  local missing=""
  missing=$(ssh_remote "$worker" "
    for img in ${IMAGES[*]}; do
      docker image inspect \"\$img:latest\" >/dev/null 2>&1 || echo \"\$img\"
    done
  ")
  if [ -n "$missing" ]; then
    echo "FAIL: $worker missing required image(s): $missing" >&2
    return 1
  fi
}

for worker in "${WORKERS[@]}"; do
  echo "=== $worker ==="
  missing=$(ssh_remote "$worker" "
    for img in ${IMAGES[*]}; do
      docker image inspect \"\$img:latest\" >/dev/null 2>&1 || echo \"\$img\"
    done
  ")
  if [ -z "$missing" ]; then
    echo "  all images present"
    continue
  fi
  for img in $missing; do
    echo "  → $img"
    ssh_remote "$SEED" "docker save $img:latest | gzip -1" | \
      ssh_remote "$worker" "gunzip | docker load" 2>&1 | tail -2
    ssh_remote "$worker" "docker image inspect $img:latest >/dev/null"
  done
done

echo
echo "=== final verify ==="
for worker in "${WORKERS[@]}"; do
  verify_worker_images "$worker"
  echo "  $worker: all ${#IMAGES[@]} required images present"
done
