#!/usr/bin/env bash
# task_105_06 setup — ncm-cli + yt-dlp.
#
# Sequence:
#   1. apt-get install node/npm, yt-dlp, jq, curl.
#   2. npm install -g @music163/ncm-cli.
#   3. Restore ncm-cli credentials + login tokens from env vars.
#   4. Verify ncm-cli search works (login --check).
#
# Required env vars (all four mandatory):
#   NCM_APP_ID           — NetEase Open Platform App ID
#   NCM_PRIVATE_KEY      — RSA private key (PKCS#8 PEM body, no headers)
#   NCM_TOKENS_ENC       — base64 of ~/.config/ncm-cli/tokens.enc.json
#   NCM_DEVICE_JSON      — base64 of ~/.netease_mcp_device.json (deviceId
#                          + createdAt).  tokens.enc.json is symmetrically
#                          encrypted under this device's key, so they MUST
#                          travel together; restoring tokens alone yields
#                          "AuthManager: token 文件解密失败".
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install system packages ───────────────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    jq curl ca-certificates python3 python3-pip \
    nodejs npm || true

  # yt-dlp
  if ! command -v yt-dlp >/dev/null; then
    pip3 install --break-system-packages yt-dlp 2>/dev/null \
      || pip3 install yt-dlp 2>/dev/null || true
  fi
fi

# ── Install ncm-cli ───────────────────────────────────────────────
if ! command -v ncm-cli >/dev/null; then
  npm install -g @music163/ncm-cli 2>&1 || {
    echo "[task-setup] FATAL: npm install @music163/ncm-cli failed" >&2
    exit 1
  }
fi

# ── Fail-fast: all four env vars must be present ──────────────────
missing=0
for var in NCM_APP_ID NCM_PRIVATE_KEY NCM_TOKENS_ENC NCM_DEVICE_JSON; do
  if [ -z "${!var:-}" ]; then
    echo "[task-setup] FATAL: $var is empty" >&2
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "[task-setup] All four NCM_* env vars are required. See privacy.example.env." >&2
  exit 1
fi

# ── Restore device fingerprint FIRST (before config set / tokens) ──
# Both ``credentials.enc.json`` (which ``config set`` writes below) and
# ``tokens.enc.json`` are symmetrically encrypted under the deviceId in
# ``~/.netease_mcp_device.json``.  If we ran ``config set`` first, ncm-cli
# would mint a fresh random device.json and encrypt credentials under
# that — then overwriting the device file afterwards would leave the
# credentials undecryptable (``error:1C800064: bad decrypt``) and
# every API call would fail with "API key 未设置".
printf '%s' "$NCM_DEVICE_JSON" | base64 -d > "${HOME}/.netease_mcp_device.json"
chmod 600 "${HOME}/.netease_mcp_device.json"
echo "[task-setup] ncm-cli device fingerprint restored to ${HOME}/.netease_mcp_device.json"

# ── Configure ncm-cli identity ────────────────────────────────────
# Encrypts credentials.enc.json under the device key we just placed.
ncm-cli config set appId "$NCM_APP_ID" 2>&1 || {
  echo "[task-setup] FATAL: ncm-cli config set appId failed" >&2
  exit 1
}
ncm-cli config set privateKey "$NCM_PRIVATE_KEY" 2>&1 || {
  echo "[task-setup] FATAL: ncm-cli config set privateKey failed" >&2
  exit 1
}
echo "[task-setup] ncm-cli appId + privateKey configured"

# ── Restore login tokens (also encrypted under the same device key) ───
NCM_DIR="${HOME}/.config/ncm-cli"
mkdir -p "$NCM_DIR"
chmod 700 "$NCM_DIR"
printf '%s' "$NCM_TOKENS_ENC" | base64 -d > "$NCM_DIR/tokens.enc.json"
chmod 600 "$NCM_DIR/tokens.enc.json"
echo "[task-setup] ncm-cli tokens restored to $NCM_DIR"

# ── Verify login status ──────────────────────────────────────────
login_result=$(ncm-cli login --check 2>&1 || true)
if echo "$login_result" | grep -qiE '已登录|success|logged.in|check.*ok'; then
  echo "[task-setup] ncm-cli login verified: OK"
else
  echo "[task-setup] WARNING: ncm-cli login --check returned:" >&2
  echo "$login_result" | head -5 >&2
  echo "[task-setup] Token may be expired — try continuing anyway" >&2
  # Don't exit 1 here: let the executor see the error and decide
fi

# ── Quick search sanity check ─────────────────────────────────────
search_result=$(ncm-cli search song --keyword "test" --limit 1 --output json 2>&1 || true)
if echo "$search_result" | grep -q '"code": 200'; then
  echo "[task-setup] ncm-cli search: OK"
else
  echo "[task-setup] WARNING: ncm-cli search returned unexpected result:" >&2
  echo "$search_result" | head -5 >&2
fi

# ── Sanity check other tools ─────────────────────────────────────
for cmd in yt-dlp jq curl python3 ncm-cli; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

mkdir -p /tmp_workspace/results
echo '[task-setup] done'
