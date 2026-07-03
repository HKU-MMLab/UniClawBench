#!/usr/bin/env bash
# One-shot runtime install for this task.
# Invoked by lib/runner/services.py as `bash install.sh` at container boot.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends git jq curl ca-certificates gnupg || true
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

if ! command -v gh >/dev/null; then
  echo '[task-setup] warning: gh CLI is unavailable; executor should fall back to curl against the GitHub API' >&2
fi

echo '[task-setup] done'
