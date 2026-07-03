#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  transcribe.sh <audio-file> [--model NAME] [--out /path/to/out] \
                              [--language en] [--prompt "hint"] \
                              [--srt | --vtt | --json | --verbose-json]

Defaults:
  --model is provider-aware: whisper-large-v3-turbo for Groq/vveai URLs,
  else whisper-1. Override with --model NAME or WHISPER_MODEL.
  Output format defaults to plain text.

  --srt / --vtt: transcript with timestamps. The script always asks the
  API for verbose_json and assembles SRT/VTT locally, so the same flag
  works against providers that don't natively emit SRT (e.g. Groq).

Env:
  WHISPER_API_KEY    required, falls back to OPENAI_API_KEY when present
  WHISPER_BASE_URL   optional, falls back to OPENAI_BASE_URL or
                     https://api.groq.com/openai/v1.
                     Include /v1 in the URL (SDK convention).
  WHISPER_MODEL      optional default model override
  WHISPER_TIMEOUT_SECONDS optional request timeout, defaults to 300
                     Examples:
                       https://api.openai.com/v1
                       https://yunwu.ai/v1
                       https://api.groq.com/openai/v1
EOF
  exit 2
}

if [[ "${1:-}" == "" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

in="${1:-}"
shift || true

model="${WHISPER_MODEL:-}"
out=""
language=""
prompt=""
output_format="text"
out_ext="txt"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)        model="${2:-}"; shift 2 ;;
    --out)          out="${2:-}"; shift 2 ;;
    --language)     language="${2:-}"; shift 2 ;;
    --prompt)       prompt="${2:-}"; shift 2 ;;
    --json)         output_format="json"; out_ext="json"; shift 1 ;;
    --verbose-json) output_format="verbose_json"; out_ext="json"; shift 1 ;;
    --srt)          output_format="srt"; out_ext="srt"; shift 1 ;;
    --vtt)          output_format="vtt"; out_ext="vtt"; shift 1 ;;
    --text)         output_format="text"; out_ext="txt"; shift 1 ;;
    *)              echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ ! -f "$in" ]]; then
  echo "File not found: $in" >&2
  exit 1
fi

api_key="${WHISPER_API_KEY:-${OPENAI_API_KEY:-}}"
if [[ "$api_key" == "" ]]; then
  echo "Missing WHISPER_API_KEY or OPENAI_API_KEY" >&2
  exit 1
fi

base_url="${WHISPER_BASE_URL:-${OPENAI_BASE_URL:-https://api.groq.com/openai/v1}}"
base_url="${base_url%/}"
if [[ "$model" == "" ]]; then
  if [[ "$base_url" == *"groq.com"* || "$base_url" == *"vveai.com"* ]]; then
    model="whisper-large-v3-turbo"
  else
    model="whisper-1"
  fi
fi
timeout_seconds="${WHISPER_TIMEOUT_SECONDS:-300}"

if [[ "$out" == "" ]]; then
  base="${in%.*}"
  out="${base}.${out_ext}"
fi
mkdir -p "$(dirname "$out")"

case "$output_format" in
  srt|vtt) api_format="verbose_json" ;;
  *)       api_format="$output_format" ;;
esac

check_api_response() {
  local path="$1"
  local http_code="$2"
  python3 - "$path" "$http_code" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
http_code = sys.argv[2]
body = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

try:
    code = int(http_code)
except ValueError:
    code = 0
if code < 200 or code >= 300:
    sys.stderr.write(f"Transcription API returned HTTP {http_code}: {body[:800]}\n")
    sys.exit(1)

stripped = body.lstrip()
if stripped.startswith("{"):
    try:
        data = json.loads(body)
    except Exception:
        data = None
    if isinstance(data, dict) and data.get("error"):
        sys.stderr.write("Transcription API error: " + json.dumps(data["error"], ensure_ascii=False) + "\n")
        sys.exit(1)
PY
}

call_api() {
  local format="$1"
  local dest="$2"
  local http_code
  set +e
  http_code=$(curl -sS --connect-timeout 20 --max-time "$timeout_seconds" \
    -o "$dest" -w "%{http_code}" \
    "${base_url}/audio/transcriptions" \
    -H "Authorization: Bearer $api_key" \
    -F "file=@${in}" \
    -F "model=${model}" \
    -F "response_format=${format}" \
    ${language:+-F "language=${language}"} \
    ${prompt:+-F "prompt=${prompt}"})
  local rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    echo "Transcription request failed with curl exit $rc" >&2
    return "$rc"
  fi
  check_api_response "$dest" "$http_code"
}

if [[ "$api_format" == "verbose_json" && "$output_format" != "verbose_json" ]]; then
  tmp_json="$(mktemp -t whisper.XXXXXX.json)"
  trap 'rm -f "$tmp_json"' EXIT
  call_api "verbose_json" "$tmp_json"

  python3 - "$tmp_json" "$output_format" > "$out" <<'PY'
import json, sys
src, fmt = sys.argv[1], sys.argv[2]
with open(src) as f:
    data = json.load(f)

if "error" in data:
    sys.stderr.write(json.dumps(data["error"]) + "\n")
    sys.exit(1)

segs = data.get("segments") or []

def ts(t, sep):
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s_int = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s_int:02d}{sep}{ms:03d}"

out_lines = []
if fmt == "vtt":
    out_lines.append("WEBVTT")
    out_lines.append("")
    sep = "."
else:
    sep = ","

for i, seg in enumerate(segs, 1):
    start = ts(float(seg.get("start") or 0), sep)
    end = ts(float(seg.get("end") or 0), sep)
    text = (seg.get("text") or "").strip()
    if fmt == "srt":
        out_lines.append(str(i))
    out_lines.append(f"{start} --> {end}")
    out_lines.append(text)
    out_lines.append("")

sys.stdout.write("\n".join(out_lines) + "\n")
PY
else
  call_api "$api_format" "$out"
fi

echo "$out"
