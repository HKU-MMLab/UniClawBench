---
name: "cli-anything-zoom"
description: >-
  Command-line interface for Zoom — manage meetings, participants, and recordings from the command line via the Zoom REST API.
---

# cli-anything-zoom

CLI harness for **Zoom** — manage meetings, participants, and recordings from the command line via the Zoom REST API.

## Installation

This CLI is installed as part of the cli-anything-zoom package:

```bash
pip install cli-anything-zoom
```

**Prerequisites:**
- Python 3.10+
- zoom must be installed on your system


## Usage

### Basic Commands

```bash
# Show help
zoom --help

# Run with JSON output (for agent consumption)
zoom --json meeting list
```


## Command Groups


### Auth

Authentication and OAuth2 setup.

| Command | Description |
|---------|-------------|
| `zoom auth setup` | Configure OAuth app credentials |
| `zoom auth login` | Login via OAuth2 browser flow |
| `zoom auth status` | Check authentication status |
| `zoom auth logout` | Remove saved tokens |

**Config directory:** `~/.cli-anything-zoom/`

Required files:
- `config.json` — contains `client_id`, `client_secret`, `redirect_uri`
- `tokens.json` — contains `refresh_token` (and optionally `access_token`)

Example `config.json`:
```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "redirect_uri": "http://localhost:4199/callback"
}
```

Example `tokens.json`:
```json
{
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "access_token": ""
}
```

The CLI automatically refreshes `access_token` from the `refresh_token` on each invocation if needed.


### Meeting

Meeting management commands.

| Command | Description |
|---------|-------------|
| `zoom meeting create` | Create a new Zoom meeting |
| `zoom meeting list` | List meetings |
| `zoom meeting info` | Get meeting details |
| `zoom meeting update` | Update a meeting |
| `zoom meeting delete` | Delete a meeting |

#### Create a meeting

```bash
zoom meeting create --topic "Weekly Standup" --start-time "2026-05-12T10:00:00" --duration 30 --json
```

Output includes:
- `id` — meeting ID (numeric)
- `join_url` — e.g. `https://us05web.zoom.us/j/12345678901`
- `start_url` — host start URL
- `topic`, `start_time`, `duration`

#### List meetings

```bash
zoom meeting list --json
```

Returns JSON array of all scheduled meetings for the authenticated user.

#### Delete a meeting

```bash
zoom meeting delete --id <meeting_id>
```


### Participant

Participant management commands.

| Command | Description |
|---------|-------------|
| `zoom participant add` | Register a participant for a meeting |
| `zoom participant list` | List registered participants |
| `zoom participant remove` | Cancel a participant's registration |
| `zoom participant attended` | List participants who attended a past meeting |


### Recording

Cloud recording management.

| Command | Description |
|---------|-------------|
| `zoom recording list` | List cloud recordings |
| `zoom recording files` | List recording files for a specific meeting |
| `zoom recording download` | Download a recording file |
| `zoom recording delete` | Delete all recordings for a meeting |


## Output Formats

All commands support dual output modes:

- **Human-readable** (default): Tables, colors, formatted text
- **Machine-readable** (`--json` flag): Structured JSON for agent consumption

```bash
# Human output
zoom meeting list

# JSON output for agents
zoom meeting list --json
```

## Auth Setup Workflow

To configure from environment variables:

1. Create `~/.cli-anything-zoom/` directory
2. Write `config.json` with `client_id`, `client_secret`, `redirect_uri`
3. Write `tokens.json` with `refresh_token` (access_token can be empty string)
4. Verify with `zoom auth status`

The CLI will auto-refresh the access token on the next API call.

## For AI Agents

When using this CLI programmatically:

1. **Always use `--json` flag** for parseable output
2. **Check return codes** — 0 for success, non-zero for errors
3. **Parse stderr** for error messages on failure
4. **Use ISO 8601 format** for all datetime arguments (e.g., `2026-05-12T10:00:00`)
5. **Duration is in minutes** for meeting create/update

## Version

1.0.0
