#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs ──────────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl ca-certificates gnupg python3 python3-pip || true

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
fi

# ── Authenticate gh with GITHUB_TOKEN from .privacy ────────────────
if [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null \
    || GH_TOKEN="$GITHUB_TOKEN" gh auth status 2>&1 || true
  echo "[task-setup] gh authenticated with GITHUB_TOKEN"
else
  echo "[task-setup] WARNING: GITHUB_TOKEN unset; gh will be rate-limited to 60 req/hr" >&2
fi

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in gh jq curl python3; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo '[task-setup] done'
