#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR=/tmp_workspace/results
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SERVICE_DIR/minesweeper.py"
README_PATH=/tmp_workspace/clawbench/sources/MINESWEEPER_README.md
LOG_PATH="$RESULTS_DIR/minesweeper_service.log"
SESSIONS_DIR="$RESULTS_DIR/minesweeper_sessions"
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
    echo "readme_path=$README_PATH"
  } > "$LOG_PATH"
  exit 0
fi

printf 'attempt	port	stdin_fifo	board	typescript	duration_txt	cmd	pty_pid	keepalive_pid
' > "$SUMMARY_PATH"

for attempt in 1 2 3; do
  port=8766
  fifo_path="$SESSIONS_DIR/attempt_${attempt}.fifo"
  cmd_path="$SESSIONS_DIR/attempt_${attempt}.launch.sh"
  board_path="$SESSIONS_DIR/attempt_${attempt}_board.txt"
  transcript_path="$SESSIONS_DIR/attempt_${attempt}_terminal.log"
  duration_path="$SESSIONS_DIR/attempt_${attempt}_duration.txt"
  pid_path="$SESSIONS_DIR/attempt_${attempt}.pid"
  keepalive_path="$SESSIONS_DIR/attempt_${attempt}.keepalive.pid"

  rm -f "$fifo_path" "$cmd_path" "$board_path" "$transcript_path" "$duration_path" "$pid_path" "$keepalive_path"
  mkfifo "$fifo_path"
  printf 'attempt=%s
duration_seconds=NOT_STARTED
' "$attempt" > "$duration_path"

  cat > "$cmd_path" <<CMD
#!/usr/bin/env bash
set -euo pipefail
cd /tmp_workspace
export MINESWEEPER_BOARD_PATH="$board_path"
export MINESWEEPER_DURATION_PATH="$duration_path"
export MINESWEEPER_SESSION_PORT="$port"
export MINESWEEPER_ATTEMPT="$attempt"
exec python3 "$SCRIPT_PATH"
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

  printf '%s	%s	%s	%s	%s	%s	%s	%s	%s
'     "$attempt" "$port" "$fifo_path" "$board_path" "$transcript_path" "$duration_path" "$cmd_path" "$pty_pid" "$keepalive_pid" >> "$SUMMARY_PATH"
done

sleep 1

{
  echo "Minesweeper service is ready. Do not start the game yourself."
  echo "Use one of the three prestarted attempts below. Each attempt is already running in its own stdin-driven terminal session."
  echo "The three attempts are your full budget. If attempt 1 or 2 hits a mine within the first four moves, you may continue with the next prestarted attempt. Otherwise stop after that run."
  echo "Read the public README for the exact scoring rule before choosing moves."
  echo "Each attempt also has a duration txt file; use it to read first_move_unix, end_unix, and duration_seconds for score calculation."
  echo
  printf 'attempt	port	stdin_fifo	board	typescript	duration_txt
'
  cut -f1-6 "$SUMMARY_PATH" | tail -n +2
  echo
  echo "README: $README_PATH"
  echo "Summary TSV: $SUMMARY_PATH"
} > "$LOG_PATH"

cat "$LOG_PATH"
