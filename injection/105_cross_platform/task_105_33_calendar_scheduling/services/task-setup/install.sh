#!/usr/bin/env bash
# task_105_13 setup — Zoom-only.
#
# Sequence:
#   1. apt-get install gnome-calendar / xvfb / scrot / icalendar.
#   2. Start Xvfb :99 + a session dbus so gnome-calendar can launch.
#   3. Bake the messy schedule fixture at ~/clawbench-schedule.txt.
#   4. Install the HKUDS/CLI-Anything `zoom` CLI to /opt/cli-anything/zoom.
#   5. Reset Zoom: bootstrap auth temporarily from
#      ZOOM_CLIENT_ID/SECRET/REFRESH_TOKEN, list+delete every existing
#      meeting under the test account.
#   6. WIPE ~/.cli-anything-zoom/ — the executor must redo the auth
#      wiring themselves from the env vars (per task design).
#
# All three ZOOM_* env vars are required (zoom-only design, no fallback).
# Empty ZOOM_REFRESH_TOKEN => fail loudly, executor will see a clear
# install.sh log message and the supervisor will treat the run as
# infra_error.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ── Install required CLIs / GUI apps ──────────────────────────────
if command -v apt-get >/dev/null; then
  apt-get update -qq || true
  apt-get install -y --no-install-recommends \
    git jq curl wget ca-certificates python3 python3-pip \
    xvfb scrot imagemagick \
    dbus dbus-x11 \
    gnome-calendar evolution-data-server \
    libnotify-bin \
    fonts-noto-cjk fonts-wqy-zenhei || true

  if ! python3 -c 'import icalendar' >/dev/null 2>&1; then
    pip3 install --quiet --break-system-packages icalendar 2>/dev/null \
      || pip3 install --quiet icalendar 2>/dev/null || true
  fi
fi

# ── Start Xvfb + session dbus ─────────────────────────────────────
if command -v Xvfb >/dev/null; then
  pkill -f 'Xvfb :99' 2>/dev/null || true
  Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
  sleep 1
fi
export DISPLAY=:99
if command -v dbus-launch >/dev/null && [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  eval "$(dbus-launch --sh-syntax)" 2>/dev/null || true
fi

# ── Bake the messy schedule fixture ────────────────────────────────
SCHEDULE_FILE="${HOME}/clawbench-schedule.txt"
cat > "$SCHEDULE_FILE" <<'EOF'
hey, dumping my next-week calendar here, please put it on my actual calendar so i stop forgetting things:

- Q2 planning sync, Wed May 13 2026 at 14:00, 60 min, w/ Alice and Bob
- Bug triage — Friday May 15, 10am, half an hour
- Tech review of the new pipeline, May 18 (Mon) 3pm, 45 minutes
- 1:1 with manager, Tuesday next week (May 19) 11:30, 30 min
- Customer demo (acme corp), Thursday May 21 16:00, runs 1 hour
- Retro / sprint close, Fri May 22 2026 4pm, 45 min

times are local, no tz juggling. each one needs a real zoom link too — i've already got the zoom CLI installed and the OAuth creds in the env, just need someone to wire it up + create the meetings.
EOF

mkdir -p /tmp_workspace/results

# ── Install the zoom CLI (HKUDS/CLI-Anything) ─────────────────────
CLIA_DIR=/opt/cli-anything
if [ ! -d "$CLIA_DIR/.git" ]; then
  rm -rf "$CLIA_DIR"
  git clone --depth 1 https://github.com/HKUDS/CLI-Anything.git "$CLIA_DIR" 2>&1 \
    || echo "[task-setup] WARNING: clone CLI-Anything failed" >&2
fi
if [ -d "$CLIA_DIR/zoom/agent-harness" ]; then
  ( cd "$CLIA_DIR/zoom/agent-harness" \
    && pip install --quiet --break-system-packages -e . 2>&1 ) \
    || ( cd "$CLIA_DIR/zoom/agent-harness" && pip install --quiet -e . 2>&1 ) \
    || echo "[task-setup] WARNING: pip install zoom CLI failed" >&2
fi

# The setup.py installs the binary as `cli-anything-zoom`. Add a `zoom`
# alias so the executor (and the rest of this script) can call it
# naturally — the YAML prompt and eval all reference `zoom`.
if command -v cli-anything-zoom >/dev/null && ! command -v zoom >/dev/null; then
  ln -sf "$(command -v cli-anything-zoom)" /usr/local/bin/zoom
  echo "[task-setup] symlinked zoom -> $(command -v cli-anything-zoom)"
fi

# ── Zoom-only fail-fast: refresh_token MUST be present ─────────────
if [ -z "${ZOOM_REFRESH_TOKEN:-}" ] || [ -z "${ZOOM_CLIENT_ID:-}" ] || [ -z "${ZOOM_CLIENT_SECRET:-}" ]; then
  echo "[task-setup] FATAL: Zoom credentials missing." >&2
  echo "[task-setup]   ZOOM_CLIENT_ID present:     $([ -n "${ZOOM_CLIENT_ID:-}" ] && echo yes || echo no)" >&2
  echo "[task-setup]   ZOOM_CLIENT_SECRET present: $([ -n "${ZOOM_CLIENT_SECRET:-}" ] && echo yes || echo no)" >&2
  echo "[task-setup]   ZOOM_REFRESH_TOKEN present: $([ -n "${ZOOM_REFRESH_TOKEN:-}" ] && echo yes || echo no)" >&2
  echo "[task-setup] Complete the one-time OAuth bootstrap (see /tmp/clawbench_user_actions.md)" >&2
  echo "[task-setup] and populate configs/privacy.local.env, then re-run." >&2
  exit 1
fi

# ── Reset: bootstrap auth temporarily, wipe every existing meeting
# under the test account, then nuke the auth files so the executor
# must re-do the wiring themselves (per task design).
ZCFG_DIR="${HOME}/.cli-anything-zoom"
rm -rf "$ZCFG_DIR"
mkdir -p "$ZCFG_DIR"
chmod 700 "$ZCFG_DIR"
cat > "$ZCFG_DIR/config.json" <<JSON
{"client_id":"${ZOOM_CLIENT_ID}","client_secret":"${ZOOM_CLIENT_SECRET}","redirect_uri":"http://localhost:4199/callback"}
JSON
cat > "$ZCFG_DIR/tokens.json" <<JSON
{"access_token":"placeholder","refresh_token":"${ZOOM_REFRESH_TOKEN}","expires_in":3600,"saved_at":1}
JSON
chmod 600 "$ZCFG_DIR/config.json" "$ZCFG_DIR/tokens.json"

if ! command -v zoom >/dev/null; then
  echo "[task-setup] FATAL: zoom CLI not on PATH after install" >&2
  exit 1
fi

if ! zoom auth status >/dev/null 2>&1; then
  echo "[task-setup] FATAL: zoom auth status failed — refresh_token likely stale or revoked" >&2
  echo "[task-setup] Re-do the one-time OAuth bootstrap (see /tmp/clawbench_user_actions.md)" >&2
  rm -rf "$ZCFG_DIR"
  exit 1
fi

echo "[task-setup] zoom auth ok — listing + deleting any existing meetings"
# `cli-anything-zoom --json meeting list` returns JSON; `--json` is a
# root-level flag, not a `meeting list` subcommand option. We sweep
# every meeting status (upcoming/scheduled/live/pending) so the reset
# is comprehensive — Zoom's default `meeting list` filter is
# "upcoming" only, which would leave past/draft meetings behind.
# Wrap each call in `|| true` so set -e/pipefail don't abort the
# script if a particular status returns 4xx (some Zoom plans don't
# support every status filter).
set +e
collect_ids() {
  local status="$1"
  zoom --json meeting list -s "$status" 2>/dev/null \
    | jq -r '..|.id? // empty' 2>/dev/null | grep -E '^[0-9]+$' | sort -u
}
all_ids=$(
  { collect_ids upcoming; collect_ids scheduled; \
    collect_ids live;     collect_ids pending; } 2>/dev/null | sort -u
)
reset_count=0
while IFS= read -r mid; do
  [ -z "$mid" ] && continue
  if zoom meeting delete "$mid" --confirm >/dev/null 2>&1; then
    reset_count=$((reset_count + 1))
  fi
done <<< "$all_ids"
echo "[task-setup] zoom reset: deleted $reset_count existing meeting(s) — account is now empty"

# Re-confirm empty (defensive).
remaining=$(
  { collect_ids upcoming; collect_ids scheduled; \
    collect_ids live;     collect_ids pending; } 2>/dev/null | sort -u | wc -l
)
echo "[task-setup] zoom meeting list now reports $remaining meeting(s) remaining"
set -e

# ── WIPE auth state — executor must re-create from env vars ───────
rm -rf "$ZCFG_DIR"
echo "[task-setup] wiped $ZCFG_DIR — executor must re-configure Zoom auth from env vars"
echo "[task-setup] env vars exposed to executor: ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, ZOOM_REFRESH_TOKEN"

# ── Sanity ─────────────────────────────────────────────────────────
for cmd in jq curl python3 Xvfb scrot \
           gnome-calendar dbus-launch convert zoom; do
  if ! command -v "$cmd" >/dev/null; then
    echo "[task-setup] WARNING: $cmd unavailable" >&2
  fi
done

echo "[task-setup] schedule fixture written to $SCHEDULE_FILE"
echo "[task-setup] Xvfb display ready at DISPLAY=:99"
echo "[task-setup] done"
