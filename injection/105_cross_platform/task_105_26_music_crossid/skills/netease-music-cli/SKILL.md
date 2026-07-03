---
name: netease-music-cli
description: CLI for NetEase Cloud Music — search songs/albums/playlists, get lyrics, and manage your music library from the terminal.
---

# NetEase Music CLI (ncm-cli)

Command-line tool for interacting with NetEase Cloud Music. Pre-authenticated in this environment.

## Authentication

Already configured. Credentials and login tokens are pre-installed at `~/.config/ncm-cli/`. No additional auth steps needed.

To verify: `ncm-cli login --check`

## Core Commands

### Search Songs

```bash
ncm-cli search song --keyword "光年之外" --limit 5 --output json
```

Output (JSON array of song objects):
```json
{
  "code": 200,
  "data": {
    "songs": [
      {
        "originalId": 449818741,
        "name": "光年之外",
        "artists": [{"name": "G.E.M.邓紫棋", "id": 7763}],
        "album": {"name": "光年之外", "id": 35069523},
        "duration": 235505
      }
    ]
  }
}
```

Key fields:
- `originalId` — unique song ID on NetEase (integer)
- `duration` — in milliseconds
- `artists[].name` — artist display name
- `album.name` — album title

### Search Albums

```bash
ncm-cli search album --keyword "U87" --limit 3 --output json
```

### Comprehensive Search

```bash
ncm-cli search all --keyword "陈奕迅 浮夸" --limit 5 --output json
```

### Get Song Lyrics

```bash
ncm-cli song lyric --id 449818741 --output json
```

### Album Details

```bash
ncm-cli album --id 35069523 --output json
```

### Playlist Details

```bash
ncm-cli playlist --id <playlist_id> --output json
```

## Output Formats

All commands support `--output <format>`:
- `json` — structured JSON (recommended for programmatic use)
- `human` — human-readable table
- `table` — tabular format

Always use `--output json` when you need to parse the results.

## Common Patterns

### Find a song by lyrics/keywords and get its metadata

```bash
# Search
ncm-cli search song --keyword "缘分让我们相遇乱世以外" --limit 3 --output json

# The first result's originalId is the canonical NetEase song ID
# duration is in milliseconds — divide by 1000 for seconds
```

### Cross-reference with other platforms

The `originalId` is the canonical song identifier. Use it to construct the web URL:
`https://music.163.com/song?id=<originalId>`

## Notes

1. Search queries work best with song name + artist name in Chinese.
2. `duration` is always in **milliseconds**.
3. The `originalId` field is the canonical song ID (same as what appears in NetEase URLs).
4. Rate limits are generous for search — no throttling needed for typical use.
5. If a command hangs, the login token may have expired. Check with `ncm-cli login --check`.
