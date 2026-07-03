#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR=/tmp_workspace/results
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SERVICE_DIR/nonogram.py"
LOG_PATH="$RESULTS_DIR/nonogram_service.log"
SESSIONS_DIR="$RESULTS_DIR/nonogram_sessions"
SUMMARY_PATH="$SESSIONS_DIR/summary.tsv"

mkdir -p "$RESULTS_DIR"
chmod +x "$SCRIPT_PATH"
rm -rf "$SESSIONS_DIR"
mkdir -p "$SESSIONS_DIR"
rm -f "$LOG_PATH"

if ! command -v script >/dev/null 2>&1; then
  {
    echo "service_status=failed"
    echo "failure_reason=missing_script_utility"
  } > "$LOG_PATH"
  exit 0
fi

printf 'attempt\tstdin_fifo\tboard\ttypescript\tduration_txt\tcmd\tpty_pid\tkeepalive_pid\n' > "$SUMMARY_PATH"

for attempt in 1 2 3; do
  fifo_path="$SESSIONS_DIR/attempt_${attempt}.fifo"
  cmd_path="$SESSIONS_DIR/attempt_${attempt}.launch.sh"
  board_path="$SESSIONS_DIR/attempt_${attempt}_board.txt"
  transcript_path="$SESSIONS_DIR/attempt_${attempt}_terminal.log"
  duration_path="$SESSIONS_DIR/attempt_${attempt}_duration.txt"
  pid_path="$SESSIONS_DIR/attempt_${attempt}.pid"
  keepalive_path="$SESSIONS_DIR/attempt_${attempt}.keepalive.pid"

  rm -f "$fifo_path" "$cmd_path" "$board_path" "$transcript_path" "$duration_path" "$pid_path" "$keepalive_path"
  mkfifo "$fifo_path"
  printf 'attempt=%s\nduration_seconds=NOT_STARTED\n' "$attempt" > "$duration_path"

  cat > "$cmd_path" <<CMD
#!/usr/bin/env bash
set -euo pipefail
cd /tmp_workspace
export PYTHONUNBUFFERED=1
export NONOGRAM_BOARD_PATH="$board_path"
export NONOGRAM_DURATION_PATH="$duration_path"
export NONOGRAM_ATTEMPT="$attempt"
exec python3 "$SCRIPT_PATH" "$board_path"
CMD
  chmod +x "$cmd_path"

  (
    exec 3>"$fifo_path"
    while :; do sleep 3600; done
  ) &
  keepalive_pid=$!
  echo "$keepalive_pid" > "$keepalive_path"

  (
    exec <"$fifo_path"
    exec script -q "$transcript_path" -c "$cmd_path"
  ) &
  pty_pid=$!
  echo "$pty_pid" > "$pid_path"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$attempt" "$fifo_path" "$board_path" "$transcript_path" "$duration_path" "$cmd_path" "$pty_pid" "$keepalive_pid" >> "$SUMMARY_PATH"
done

sleep 1

{
  echo "Nonogram service is ready. Do not start the game yourself."
  echo "Use one of the three prestarted attempts below. Each attempt is already running in its own stdin-driven terminal session."
  echo "Each attempt has a board txt file that is rewritten after every move."
  echo "Each attempt has a duration txt file that records timing from the first valid move until the game ends."
  echo
  printf 'attempt\tstdin_fifo\tboard\ttypescript\tduration_txt\n'
  cut -f1-5 "$SUMMARY_PATH" | tail -n +2
  echo
  echo "Summary TSV: $SUMMARY_PATH"
} > "$LOG_PATH"

cat "$LOG_PATH"
