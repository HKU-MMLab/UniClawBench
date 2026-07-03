---
name: openai-whisper-api
description: Transcribe audio via OpenAI Audio Transcriptions API (Whisper).
homepage: https://platform.openai.com/docs/guides/speech-to-text
metadata: {"clawdbot":{"emoji":"☁️","requires":{"bins":["curl"],"env":["WHISPER_API_KEY"]},"primaryEnv":"WHISPER_API_KEY"}}
---

# OpenAI Whisper API (curl)

Transcribe an audio file via OpenAI’s `/v1/audio/transcriptions` endpoint.

## Quick start

```bash
{baseDir}/scripts/transcribe.sh /path/to/audio.m4a
```

Defaults:
- Model: provider-aware. It uses `whisper-large-v3-turbo` for Groq/vveai
  URLs and `whisper-1` otherwise. Override with `--model NAME` or
  `WHISPER_MODEL`.
- Output: `<input>.txt`

## Useful flags

```bash
{baseDir}/scripts/transcribe.sh /path/to/audio.ogg --out /tmp/transcript.txt
{baseDir}/scripts/transcribe.sh /path/to/audio.m4a --language en
{baseDir}/scripts/transcribe.sh /path/to/audio.m4a --prompt "Speaker names: Peter, Daniel"
{baseDir}/scripts/transcribe.sh /path/to/audio.m4a --json --out /tmp/transcript.json
{baseDir}/scripts/transcribe.sh /path/to/video.mp4 --srt --out /tmp/captions.srt
```

For `--srt` / `--vtt` the script always asks the API for `verbose_json`
and assembles SRT/VTT locally, so the same flag works against providers
(e.g. Groq) that don't emit SRT natively.

## API key & base URL

Required env:
- `WHISPER_API_KEY` — your key. The helper falls back to `OPENAI_API_KEY`
  only when `WHISPER_API_KEY` is unset.

Optional env:
- `WHISPER_BASE_URL` — endpoint root, defaults to
  `OPENAI_BASE_URL` when set, otherwise `https://api.groq.com/openai/v1`.
  Include `/v1` in the URL.
- `WHISPER_TIMEOUT_SECONDS` — request timeout; defaults to 300 seconds.
